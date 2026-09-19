from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException

from ..database import db
from ..models import Product, ProductCreate, Review, ReviewCreate
from ..security import get_current_user, require_admin
from ..utils import serialize_doc


router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/products")
async def list_products(
    category: Optional[str] = None,
    q: Optional[str] = None,
    featured: Optional[bool] = None,
):
    query: Dict[str, Any] = {}
    if category and category != "all":
        query["category"] = category
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    if featured is not None:
        query["featured"] = featured
    docs = await db.products.find(query, {"_id": 0}).to_list(200)
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
    await db.products.insert_one(doc)
    return serialize_doc(doc)


@router.put("/products/{product_id}")
async def update_product(
    product_id: str,
    payload: ProductCreate,
    _: dict = Depends(require_admin),
):
    result = await db.products.update_one(
        {"product_id": product_id},
        {"$set": payload.model_dump()},
    )
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
async def list_reviews(product_id: str):
    docs = await db.reviews.find({"product_id": product_id}, {"_id": 0}).to_list(200)
    return [serialize_doc(doc) for doc in docs]


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

    reviews = await db.reviews.find(
        {"product_id": product_id},
        {"_id": 0},
    ).to_list(500)
    average = sum(item["rating"] for item in reviews) / len(reviews) if reviews else 0
    await db.products.update_one(
        {"product_id": product_id},
        {"$set": {"rating": round(average, 2), "reviews_count": len(reviews)}},
    )
    return serialize_doc(doc)
