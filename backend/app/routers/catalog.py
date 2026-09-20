import re
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from .. import audit
from ..database import db
from ..models import (
    Product,
    ProductCreate,
    Review,
    ReviewCreate,
    cheapest_price,
    default_variant,
)
from ..pagination import TOTAL_COUNT_HEADER, limit_query, offset_query
from ..security import get_current_user, require_admin
from ..utils import serialize_doc

router = APIRouter(prefix="/api", tags=["catalog"])

DUPLICATE_SLUG_DETAIL = "Another product already uses this slug"

# Paging a sort that leaves ties in an arbitrary order can show the same
# product on two pages and hide another entirely, so every option ends with a
# unique field to make the order total.
#
# The tiebreaker follows the direction of the field before it wherever that
# lets an existing index supply the order. An index is only readable backwards
# when every one of its keys reverses together, so a mixed-direction sort
# would need an index of its own and otherwise reads the whole catalogue.
PRODUCT_SORTS: Dict[str, list] = {
    "popular": [("created_at", ASCENDING), ("product_id", ASCENDING)],
    "newest": [("created_at", DESCENDING), ("product_id", DESCENDING)],
    "price_asc": [("price", ASCENDING), ("product_id", ASCENDING)],
    "price_desc": [("price", DESCENDING), ("product_id", DESCENDING)],
    "rating": [("rating", DESCENDING), ("product_id", ASCENDING)],
}
ProductSort = Literal["popular", "newest", "price_asc", "price_desc", "rating"]


@router.get("/products")
async def list_products(
    response: Response,
    category: Optional[str] = None,
    q: Optional[str] = None,
    featured: Optional[bool] = None,
    max_price: Optional[float] = Query(None, ge=0),
    sort: ProductSort = "popular",
    limit: int = limit_query(200),
    offset: int = offset_query(),
):
    query: Dict[str, Any] = {}
    if category and category != "all":
        query["category"] = category
    if q:
        # The term is escaped so punctuation cannot be read as a pattern.
        term = re.escape(q)
        query["$or"] = [
            {"name": {"$regex": term, "$options": "i"}},
            {"description": {"$regex": term, "$options": "i"}},
        ]
    if featured is not None:
        query["featured"] = featured
    if max_price is not None:
        query["price"] = {"$lte": max_price}

    response.headers[TOTAL_COUNT_HEADER] = str(await db.products.count_documents(query))
    docs = await (
        db.products.find(query, {"_id": 0})
        .sort(PRODUCT_SORTS[sort])
        .skip(offset)
        .limit(limit)
        .to_list(limit)
    )
    return [serialize_doc(doc) for doc in docs]


@router.get("/products/{product_id}")
async def get_product(product_id: str):
    doc = await db.products.find_one({"product_id": product_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize_doc(doc)


@router.post("/products")
async def create_product(
    payload: ProductCreate,
    request: Request,
    user: dict = Depends(require_admin),
):
    product = Product(**payload.model_dump())
    doc = product.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    # Every product carries at least one variant, so nothing downstream has
    # to handle a product that has none.
    if not doc["variants"]:
        doc["variants"] = [default_variant(doc)]
    doc["price_from"] = cheapest_price(doc["variants"], doc["price"])
    try:
        await db.products.insert_one(doc)
    except DuplicateKeyError as error:
        raise HTTPException(status_code=409, detail=DUPLICATE_SLUG_DETAIL) from error
    await audit.record(
        "admin.product_created",
        actor_id=user["user_id"],
        request=request,
        product_id=doc["product_id"],
        slug=doc["slug"],
    )
    return serialize_doc(doc)


@router.put("/products/{product_id}")
async def update_product(
    product_id: str,
    payload: ProductCreate,
    request: Request,
    user: dict = Depends(require_admin),
):
    previous = await db.products.find_one(
        {"product_id": product_id}, {"_id": 0, "price": 1, "stock": 1, "variants": 1}
    )
    changes = payload.model_dump()
    # Until variants can be edited in their own right, a product that has
    # only the one created for it keeps in step with the price and stock on
    # the product itself. Without this the two drift apart silently, and the
    # variant becomes authoritative later holding a stale figure.
    existing_variants = (previous or {}).get("variants") or []
    if len(existing_variants) == 1:
        only = dict(existing_variants[0])
        only.update(
            {
                "price": changes["price"],
                "mrp": changes["mrp"],
                "stock": changes["stock"],
            }
        )
        changes["variants"] = [only]
        changes["price_from"] = only["price"]

    try:
        result = await db.products.update_one(
            {"product_id": product_id},
            {"$set": changes},
        )
    except DuplicateKeyError as error:
        raise HTTPException(status_code=409, detail=DUPLICATE_SLUG_DETAIL) from error
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.products.find_one({"product_id": product_id}, {"_id": 0})
    if doc is None:
        # The update matched, so the product existed a moment ago. Finding it
        # gone means another administrator deleted it in between.
        raise HTTPException(status_code=404, detail="Not found")
    await audit.record(
        "admin.product_updated",
        actor_id=user["user_id"],
        request=request,
        product_id=product_id,
        # Price and stock are the fields worth being able to trace later.
        price_from=(previous or {}).get("price"),
        price_to=doc.get("price"),
        stock_from=(previous or {}).get("stock"),
        stock_to=doc.get("stock"),
    )
    return serialize_doc(doc)


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: str,
    request: Request,
    user: dict = Depends(require_admin),
):
    result = await db.products.delete_one({"product_id": product_id})
    await audit.record(
        "admin.product_deleted",
        actor_id=user["user_id"],
        request=request,
        product_id=product_id,
        existed=result.deleted_count > 0,
    )
    return {"ok": True}


@router.get("/products/{product_id}/reviews")
async def list_reviews(
    product_id: str,
    limit: int = limit_query(200),
    offset: int = offset_query(),
):
    docs = await (
        db.reviews.find({"product_id": product_id}, {"_id": 0})
        .sort("created_at", 1)
        .skip(offset)
        .limit(limit)
        .to_list(limit)
    )
    return [serialize_doc(doc) for doc in docs]


async def refresh_product_rating(product_id: str) -> None:
    """Recalculate the stored rating in the database.

    Averaging happens inside MongoDB so the cost does not grow with the number
    of reviews on a popular product.
    """
    summary = await db.reviews.aggregate(
        [
            {"$match": {"product_id": product_id}},
            {
                "$group": {
                    "_id": None,
                    "average": {"$avg": "$rating"},
                    "count": {"$sum": 1},
                }
            },
        ]
    ).to_list(1)

    average = summary[0]["average"] if summary else 0
    count = summary[0]["count"] if summary else 0
    await db.products.update_one(
        {"product_id": product_id},
        {"$set": {"rating": round(average, 2), "reviews_count": count}},
    )


@router.post("/products/{product_id}/reviews")
async def create_review(
    product_id: str,
    payload: ReviewCreate,
    user: dict = Depends(get_current_user),
):
    review = Review(
        product_id=product_id,
        user_id=user["user_id"],
        user_name=user["name"],
        rating=payload.rating,
        title=payload.title,
        comment=payload.comment,
    )
    doc = review.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.reviews.insert_one(doc)

    await refresh_product_rating(product_id)
    return serialize_doc(doc)
