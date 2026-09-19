from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..database import db
from ..models import Order, OrderCreate, OrderItemSnapshot
from ..pagination import limit_query, offset_query
from ..security import get_current_user
from ..utils import serialize_doc


router = APIRouter(prefix="/api", tags=["orders"])


def calculate_totals(items_with_products: List[dict]) -> dict:
    subtotal = sum(
        product["price"] * product["quantity"]
        for product in items_with_products
    )
    shipping = 0 if subtotal >= 499 else 49
    total = subtotal + shipping
    return {
        "subtotal": round(subtotal, 2),
        "shipping": shipping,
        "total": round(total, 2),
    }


@router.post("/orders")
async def create_order(
    payload: OrderCreate,
    user: dict = Depends(get_current_user),
):
    product_ids = [item.product_id for item in payload.items]
    products = await db.products.find(
        {"product_id": {"$in": product_ids}},
        {"_id": 0},
    ).to_list(500)
    products_by_id = {product["product_id"]: product for product in products}
    snapshots: List[dict] = []
    for item in payload.items:
        product = products_by_id.get(item.product_id)
        if not product:
            raise HTTPException(
                status_code=400,
                detail=f"Product {item.product_id} not found",
            )
        snapshots.append({
            "product_id": product["product_id"],
            "name": product["name"],
            "image": product["image"],
            "price": product["price"],
            "quantity": item.quantity,
        })

    totals = calculate_totals(snapshots)
    order = Order(
        user_id=user["user_id"],
        user_email=user["email"],
        items=[OrderItemSnapshot(**snapshot) for snapshot in snapshots],
        subtotal=totals["subtotal"],
        shipping=totals["shipping"],
        total=totals["total"],
        address=payload.address,
        payment_method=payload.payment_method,
        payment_status=(
            "pending"
            if payload.payment_method in ("card", "upi")
            else "cod_pending"
        ),
    )
    doc = order.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.orders.insert_one(doc)

    if payload.payment_method == "cod":
        await db.orders.update_one(
            {"order_id": order.order_id},
            {"$set": {"payment_status": "cod_pending", "status": "placed"}},
        )
        await db.carts.update_one(
            {"user_id": user["user_id"]},
            {"$set": {"items": []}},
        )
        doc["payment_status"] = "cod_pending"
        doc["status"] = "placed"
    elif payload.payment_method == "upi":
        await db.orders.update_one(
            {"order_id": order.order_id},
            {"$set": {"payment_status": "paid", "status": "processing"}},
        )
        await db.carts.update_one(
            {"user_id": user["user_id"]},
            {"$set": {"items": []}},
        )
        doc["payment_status"] = "paid"
        doc["status"] = "processing"

    return serialize_doc(doc)


@router.get("/orders")
async def my_orders(
    user: dict = Depends(get_current_user),
    limit: int = limit_query(200),
    offset: int = offset_query(),
):
    docs = await (
        db.orders.find({"user_id": user["user_id"]}, {"_id": 0})
        .sort("created_at", -1)
        .skip(offset)
        .limit(limit)
        .to_list(limit)
    )
    return [serialize_doc(doc) for doc in docs]


@router.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    user: dict = Depends(get_current_user),
):
    doc = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Order not found")
    if doc["user_id"] != user["user_id"] and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return serialize_doc(doc)
