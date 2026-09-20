from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from ..database import db
from ..idempotency import claim_request, complete_claim, release_claim
from ..inventory import release_stock, reserve_stock
from ..models import Order, OrderCreate, OrderItemSnapshot
from ..pagination import limit_query, offset_query
from ..security import get_current_user
from ..utils import serialize_doc

router = APIRouter(prefix="/api", tags=["orders"])


def calculate_totals(items_with_products: List[dict]) -> dict:
    subtotal = sum(product["price"] * product["quantity"] for product in items_with_products)
    shipping = 0 if subtotal >= 499 else 49
    total = subtotal + shipping
    return {
        "subtotal": round(subtotal, 2),
        "shipping": shipping,
        "total": round(total, 2),
    }


def build_snapshots(payload: OrderCreate, products_by_id: dict) -> List[dict]:
    """Copy the price and name at purchase time so later edits cannot change an order."""
    snapshots: List[dict] = []
    for item in payload.items:
        product = products_by_id.get(item.product_id)
        if not product:
            raise HTTPException(
                status_code=400,
                detail=f"Product {item.product_id} not found",
            )
        snapshots.append(
            {
                "product_id": product["product_id"],
                "name": product["name"],
                "image": product["image"],
                "price": product["price"],
                "quantity": item.quantity,
            }
        )
    return snapshots


def merge_duplicate_lines(snapshots: List[dict]) -> List[dict]:
    """Combine repeated products so stock is checked against the real total."""
    merged: dict = {}
    for snapshot in snapshots:
        existing = merged.get(snapshot["product_id"])
        if existing:
            existing["quantity"] += snapshot["quantity"]
        else:
            merged[snapshot["product_id"]] = dict(snapshot)
    return list(merged.values())


@router.post("/orders")
async def create_order(
    payload: OrderCreate,
    user: dict = Depends(get_current_user),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    existing_order_id = await claim_request(user["user_id"], idempotency_key)
    if existing_order_id:
        doc = await db.orders.find_one({"order_id": existing_order_id}, {"_id": 0})
        if doc:
            return serialize_doc(doc)

    try:
        product_ids = [item.product_id for item in payload.items]
        products = await db.products.find(
            {"product_id": {"$in": product_ids}},
            {"_id": 0},
        ).to_list(len(product_ids))
        products_by_id = {product["product_id"]: product for product in products}

        snapshots = build_snapshots(payload, products_by_id)
        await reserve_stock(merge_duplicate_lines(snapshots))
    except Exception:
        await release_claim(user["user_id"], idempotency_key)
        raise

    paid_immediately = payload.payment_method == "upi"
    order = Order(
        user_id=user["user_id"],
        user_mobile=user.get("mobile", ""),
        user_email=user.get("email"),
        items=[OrderItemSnapshot(**snapshot) for snapshot in snapshots],
        **calculate_totals(snapshots),
        address=payload.address,
        payment_method=payload.payment_method,
        payment_status=(
            "paid"
            if paid_immediately
            else "pending" if payload.payment_method == "card" else "cod_pending"
        ),
        status="processing" if paid_immediately else "placed",
    )
    doc = order.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()

    try:
        await db.orders.insert_one(doc)
    except Exception:
        # The order never reached the database, so the held stock must go back.
        await release_stock(merge_duplicate_lines(snapshots))
        await release_claim(user["user_id"], idempotency_key)
        raise

    await complete_claim(user["user_id"], idempotency_key, order.order_id)
    if payload.payment_method in ("cod", "upi"):
        await db.carts.update_one(
            {"user_id": user["user_id"]},
            {"$set": {"items": []}},
        )
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
