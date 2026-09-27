from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from ..database import db
from ..idempotency import claim_request, complete_claim, release_claim
from ..inventory import release_stock, reserve_stock
from ..models import (
    Order,
    OrderCreate,
    OrderItemSnapshot,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    ShippingSettings,
)
from ..pagination import limit_query, offset_query
from ..security import get_current_user
from ..utils import serialize_doc
from ..variants import line_key, resolve_variant
from .settings import stored_shipping

router = APIRouter(prefix="/api", tags=["orders"])


def calculate_totals(lines: List[dict], shipping_settings: ShippingSettings) -> dict:
    # These are order lines, not products: the price is the one the chosen
    # form was bought at, copied at purchase time.
    subtotal = sum(line["price"] * line["quantity"] for line in lines)
    # An empty order is not a delivery, so it is not charged for one.
    if not lines or subtotal >= shipping_settings.free_above:
        shipping = 0.0
    else:
        shipping = shipping_settings.flat_rate
    total = subtotal + shipping
    return {
        "subtotal": round(subtotal, 2),
        "shipping": round(shipping, 2),
        "total": round(total, 2),
    }


def unpaid_status(method: PaymentMethod) -> PaymentStatus:
    """The payment status an order starts life with: not yet paid.

    Cash on Delivery is owed at the door and nothing further is expected here.
    Anything paid online starts unpaid, and only a payment provider confirming
    the money arrived may ever change that — never the browser, and never the
    act of placing the order.
    """
    if method == PaymentMethod.COD:
        return PaymentStatus.COD_PENDING
    return PaymentStatus.PENDING


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
        variant = resolve_variant(product, item.variant_id)
        snapshots.append(
            {
                "product_id": product["product_id"],
                "variant_id": variant["variant_id"],
                "variant_label": variant["label"],
                "name": product["name"],
                "image": variant.get("image") or product["image"],
                # The variant's price, since that is what is being bought.
                "price": variant["price"],
                "quantity": item.quantity,
            }
        )
    return snapshots


def merge_duplicate_lines(snapshots: List[dict]) -> List[dict]:
    """Combine repeated lines so stock is checked against the real total.

    Two forms of one product are two separate lines, so only lines naming the
    same variant are combined.
    """
    merged: dict = {}
    for snapshot in snapshots:
        key = line_key(snapshot["product_id"], snapshot["variant_id"])
        existing = merged.get(key)
        if existing:
            existing["quantity"] += snapshot["quantity"]
        else:
            merged[key] = dict(snapshot)
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

    order = Order(
        user_id=user["user_id"],
        user_mobile=user.get("mobile", ""),
        user_email=user.get("email"),
        items=[OrderItemSnapshot(**snapshot) for snapshot in snapshots],
        **calculate_totals(snapshots, await stored_shipping()),
        address=payload.address,
        payment_method=payload.payment_method,
        payment_status=unpaid_status(payload.payment_method),
        status=OrderStatus.PLACED,
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
    # Cash on Delivery asks nothing more of the customer now, so the cart has
    # done its job. An order awaiting an online payment must keep its cart
    # until the money actually arrives.
    if payload.payment_method == PaymentMethod.COD:
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
