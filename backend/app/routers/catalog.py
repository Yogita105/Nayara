import re
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import DuplicateKeyError

from ..database import db
from ..models import Product, ProductCreate, Review, ReviewCreate
from ..pagination import limit_query, offset_query
from ..security import get_current_user, require_admin
from ..utils import serialize_doc


router = APIRouter(prefix="/api", tags=["catalog"])

DUPLICATE_SLUG_DETAIL = "Another product already uses this slug"


@router.get("/products")
async def list_products(
    category: Optional[str] = None,
    q: Optional[str] = None,
    featured: Optional[bool] = None,
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
    docs = await (
        db.products.find(query, {"_id": 0})
        .sort("created_at", 1)
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
    _: dict = Depends(require_admin),
):
    product = Product(**payload.model_dump())
    doc = product.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    try:
        await db.products.insert_one(doc)
    except DuplicateKeyError as error:
        raise HTTPException(status_code=409, detail=DUPLICATE_SLUG_DETAIL) from error
    return serialize_doc(doc)


@router.put("/products/{product_id}")
async def update_product(
    product_id: str,
    payload: ProductCreate,
    _: dict = Depends(require_admin),
):
    try:
        result = await db.products.update_one(
            {"product_id": product_id},
            {"$set": payload.model_dump()},
        )
    except DuplicateKeyError as error:
        raise HTTPException(status_code=409, detail=DUPLICATE_SLUG_DETAIL) from error
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.products.find_one({"product_id": product_id}, {"_id": 0})
    return serialize_doc(doc)


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: str,
    _: dict = Depends(require_admin),
):
    await db.products.delete_one({"product_id": product_id})
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
    summary = await db.reviews.aggregate([
        {"$match": {"product_id": product_id}},
        {
            "$group": {
                "_id": None,
                "average": {"$avg": "$rating"},
                "count": {"$sum": 1},
            }
        },
    ]).to_list(1)

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
