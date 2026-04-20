from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, Cookie, Header
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import httpx
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta

from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout,
    CheckoutSessionRequest,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "sk_test_emergent")
ADMIN_EMAILS = [e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()]

app = FastAPI(title="Nayara API")
api_router = APIRouter(prefix="/api")

# ---------- Models ----------
class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = ""
    is_admin: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SessionExchangeRequest(BaseModel):
    session_id: str


class Product(BaseModel):
    product_id: str = Field(default_factory=lambda: f"prod_{uuid.uuid4().hex[:10]}")
    name: str
    slug: str
    category: str
    description: str
    short_description: str
    price: float
    mrp: float
    image: str
    images: List[str] = []
    stock: int = 100
    rating: float = 4.5
    reviews_count: int = 0
    badges: List[str] = []
    featured: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProductCreate(BaseModel):
    name: str
    slug: str
    category: str
    description: str
    short_description: str
    price: float
    mrp: float
    image: str
    images: List[str] = []
    stock: int = 100
    badges: List[str] = []
    featured: bool = False


class CartItem(BaseModel):
    product_id: str
    quantity: int


class AddToCartRequest(BaseModel):
    product_id: str
    quantity: int = 1


class UpdateCartRequest(BaseModel):
    quantity: int


class WishlistRequest(BaseModel):
    product_id: str


class ReviewCreate(BaseModel):
    rating: int
    title: str
    comment: str


class Review(BaseModel):
    review_id: str = Field(default_factory=lambda: f"rev_{uuid.uuid4().hex[:10]}")
    product_id: str
    user_id: str
    user_name: str
    rating: int
    title: str
    comment: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ContactRequest(BaseModel):
    name: str
    email: str
    phone: Optional[str] = ""
    subject: str
    message: str


class Address(BaseModel):
    full_name: str
    phone: str
    line1: str
    line2: Optional[str] = ""
    city: str
    state: str
    pincode: str


class OrderCreate(BaseModel):
    items: List[CartItem]
    address: Address
    payment_method: str  # "card" | "upi" | "cod"
    origin_url: Optional[str] = ""


class OrderItemSnapshot(BaseModel):
    product_id: str
    name: str
    image: str
    price: float
    quantity: int


class Order(BaseModel):
    order_id: str = Field(default_factory=lambda: f"ord_{uuid.uuid4().hex[:10]}")
    user_id: str
    user_email: str
    items: List[OrderItemSnapshot]
    subtotal: float
    shipping: float
    total: float
    address: Address
    payment_method: str
    payment_status: str = "pending"  # pending, paid, failed
    status: str = "placed"  # placed, processing, shipped, delivered, cancelled
    stripe_session_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CheckoutSessionInit(BaseModel):
    order_id: str
    origin_url: str


# ---------- Helpers ----------
def serialize_doc(doc: dict) -> dict:
    if not doc:
        return doc
    doc.pop("_id", None)
    for k, v in list(doc.items()):
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


async def get_current_user(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
) -> dict:
    token = session_token
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    expires_at = session.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ---------- Auth Routes ----------
@api_router.post("/auth/session")
async def create_session(body: SessionExchangeRequest, response: Response):
    """Exchange Emergent session_id for session_token + cookie."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": body.session_id},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session_id")
    data = r.json()
    email = data["email"].lower()
    name = data.get("name", email.split("@")[0])
    picture = data.get("picture", "")
    session_token = data["session_token"]

    is_admin = email in ADMIN_EMAILS
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": name, "picture": picture, "is_admin": is_admin}},
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user_doc = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "is_admin": is_admin,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(user_doc)

    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return {"user": serialize_doc(user_doc), "session_token": session_token}


@api_router.get("/auth/me")
async def auth_me(user: dict = Depends(get_current_user)):
    return serialize_doc(user)


@api_router.post("/auth/logout")
async def logout(response: Response, session_token: Optional[str] = Cookie(None)):
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    response.delete_cookie("session_token", path="/", samesite="none", secure=True)
    return {"ok": True}


# ---------- Products ----------
@api_router.get("/products")
async def list_products(category: Optional[str] = None, q: Optional[str] = None, featured: Optional[bool] = None):
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
    return [serialize_doc(d) for d in docs]


@api_router.get("/products/{product_id}")
async def get_product(product_id: str):
    doc = await db.products.find_one({"product_id": product_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize_doc(doc)


@api_router.post("/products")
async def create_product(payload: ProductCreate, _: dict = Depends(require_admin)):
    p = Product(**payload.model_dump())
    doc = p.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.products.insert_one(doc)
    return serialize_doc(doc)


@api_router.put("/products/{product_id}")
async def update_product(product_id: str, payload: ProductCreate, _: dict = Depends(require_admin)):
    res = await db.products.update_one({"product_id": product_id}, {"$set": payload.model_dump()})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.products.find_one({"product_id": product_id}, {"_id": 0})
    return serialize_doc(doc)


@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, _: dict = Depends(require_admin)):
    await db.products.delete_one({"product_id": product_id})
    return {"ok": True}


# ---------- Cart ----------
async def _get_cart(user_id: str) -> dict:
    cart = await db.carts.find_one({"user_id": user_id}, {"_id": 0})
    if not cart:
        cart = {"user_id": user_id, "items": []}
        await db.carts.insert_one(dict(cart))
    return cart


@api_router.get("/cart")
async def get_cart(user: dict = Depends(get_current_user)):
    cart = await _get_cart(user["user_id"])
    items = cart.get("items", [])
    if not items:
        return {"items": []}
    pids = [it["product_id"] for it in items]
    products = await db.products.find({"product_id": {"$in": pids}}, {"_id": 0}).to_list(500)
    pmap = {p["product_id"]: p for p in products}
    enriched = [{**serialize_doc(pmap[it["product_id"]]), "quantity": it["quantity"]} for it in items if it["product_id"] in pmap]
    return {"items": enriched}


@api_router.post("/cart")
async def add_to_cart(req: AddToCartRequest, user: dict = Depends(get_current_user)):
    cart = await _get_cart(user["user_id"])
    items = cart.get("items", [])
    for it in items:
        if it["product_id"] == req.product_id:
            it["quantity"] += req.quantity
            break
    else:
        items.append({"product_id": req.product_id, "quantity": req.quantity})
    await db.carts.update_one({"user_id": user["user_id"]}, {"$set": {"items": items}})
    return {"ok": True, "items": items}


@api_router.put("/cart/{product_id}")
async def update_cart(product_id: str, req: UpdateCartRequest, user: dict = Depends(get_current_user)):
    cart = await _get_cart(user["user_id"])
    items = [it for it in cart.get("items", []) if it["product_id"] != product_id]
    if req.quantity > 0:
        items.append({"product_id": product_id, "quantity": req.quantity})
    await db.carts.update_one({"user_id": user["user_id"]}, {"$set": {"items": items}})
    return {"ok": True}


@api_router.delete("/cart/{product_id}")
async def delete_cart_item(product_id: str, user: dict = Depends(get_current_user)):
    cart = await _get_cart(user["user_id"])
    items = [it for it in cart.get("items", []) if it["product_id"] != product_id]
    await db.carts.update_one({"user_id": user["user_id"]}, {"$set": {"items": items}})
    return {"ok": True}


@api_router.delete("/cart")
async def clear_cart(user: dict = Depends(get_current_user)):
    await db.carts.update_one({"user_id": user["user_id"]}, {"$set": {"items": []}})
    return {"ok": True}


# ---------- Wishlist ----------
@api_router.get("/wishlist")
async def get_wishlist(user: dict = Depends(get_current_user)):
    wl = await db.wishlists.find_one({"user_id": user["user_id"]}, {"_id": 0})
    items = (wl or {}).get("items", [])
    if not items:
        return {"items": []}
    products = await db.products.find({"product_id": {"$in": items}}, {"_id": 0}).to_list(500)
    return {"items": [serialize_doc(p) for p in products]}


@api_router.post("/wishlist")
async def add_wishlist(req: WishlistRequest, user: dict = Depends(get_current_user)):
    await db.wishlists.update_one(
        {"user_id": user["user_id"]},
        {"$addToSet": {"items": req.product_id}},
        upsert=True,
    )
    return {"ok": True}


@api_router.delete("/wishlist/{product_id}")
async def remove_wishlist(product_id: str, user: dict = Depends(get_current_user)):
    await db.wishlists.update_one(
        {"user_id": user["user_id"]},
        {"$pull": {"items": product_id}},
    )
    return {"ok": True}


# ---------- Reviews ----------
@api_router.get("/products/{product_id}/reviews")
async def list_reviews(product_id: str):
    docs = await db.reviews.find({"product_id": product_id}, {"_id": 0}).to_list(200)
    return [serialize_doc(d) for d in docs]


@api_router.post("/products/{product_id}/reviews")
async def create_review(product_id: str, payload: ReviewCreate, user: dict = Depends(get_current_user)):
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

    # Update product rating
    all_revs = await db.reviews.find({"product_id": product_id}, {"_id": 0}).to_list(500)
    avg = sum(r["rating"] for r in all_revs) / len(all_revs) if all_revs else 0
    await db.products.update_one(
        {"product_id": product_id},
        {"$set": {"rating": round(avg, 2), "reviews_count": len(all_revs)}},
    )
    return serialize_doc(doc)


# ---------- Contact ----------
@api_router.post("/contact")
async def contact_submit(payload: ContactRequest):
    doc = payload.model_dump()
    doc["contact_id"] = f"ct_{uuid.uuid4().hex[:10]}"
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.contacts.insert_one(doc)
    return {"ok": True, "contact_id": doc["contact_id"]}


# ---------- Orders ----------
def _calc_totals(items_with_products: List[dict]) -> dict:
    subtotal = sum(p["price"] * p["quantity"] for p in items_with_products)
    shipping = 0 if subtotal >= 499 else 49
    total = subtotal + shipping
    return {"subtotal": round(subtotal, 2), "shipping": shipping, "total": round(total, 2)}


@api_router.post("/orders")
async def create_order(payload: OrderCreate, user: dict = Depends(get_current_user)):
    # Bulk fetch products in a single query
    pids = [it.product_id for it in payload.items]
    products_list = await db.products.find({"product_id": {"$in": pids}}, {"_id": 0}).to_list(500)
    pmap = {p["product_id"]: p for p in products_list}
    snap: List[dict] = []
    for it in payload.items:
        p = pmap.get(it.product_id)
        if not p:
            raise HTTPException(status_code=400, detail=f"Product {it.product_id} not found")
        snap.append({
            "product_id": p["product_id"],
            "name": p["name"],
            "image": p["image"],
            "price": p["price"],
            "quantity": it.quantity,
        })
    totals = _calc_totals(snap)
    order = Order(
        user_id=user["user_id"],
        user_email=user["email"],
        items=[OrderItemSnapshot(**s) for s in snap],
        subtotal=totals["subtotal"],
        shipping=totals["shipping"],
        total=totals["total"],
        address=payload.address,
        payment_method=payload.payment_method,
        payment_status="pending" if payload.payment_method in ("card", "upi") else "cod_pending",
    )
    doc = order.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.orders.insert_one(doc)

    # For COD / UPI (mock) immediately mark appropriately
    if payload.payment_method == "cod":
        await db.orders.update_one({"order_id": order.order_id}, {"$set": {"payment_status": "cod_pending", "status": "placed"}})
        await db.carts.update_one({"user_id": user["user_id"]}, {"$set": {"items": []}})
        doc["payment_status"] = "cod_pending"
        doc["status"] = "placed"
    elif payload.payment_method == "upi":
        # Mock UPI flow - in reality integrate with a PSP
        await db.orders.update_one({"order_id": order.order_id}, {"$set": {"payment_status": "paid", "status": "processing"}})
        await db.carts.update_one({"user_id": user["user_id"]}, {"$set": {"items": []}})
        doc["payment_status"] = "paid"
        doc["status"] = "processing"

    return serialize_doc(doc)


@api_router.get("/orders")
async def my_orders(user: dict = Depends(get_current_user)):
    docs = await db.orders.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return [serialize_doc(d) for d in docs]


@api_router.get("/orders/{order_id}")
async def get_order(order_id: str, user: dict = Depends(get_current_user)):
    doc = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Order not found")
    if doc["user_id"] != user["user_id"] and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return serialize_doc(doc)


# ---------- Stripe Payments ----------
@api_router.post("/payments/checkout/session")
async def create_checkout_session(payload: CheckoutSessionInit, request: Request, user: dict = Depends(get_current_user)):
    order = await db.orders.find_one({"order_id": payload.order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)

    origin = payload.origin_url.rstrip("/")
    success_url = f"{origin}/order-success?order_id={order['order_id']}&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/checkout?order_id={order['order_id']}"

    amount = float(order["total"])
    checkout_req = CheckoutSessionRequest(
        amount=amount,
        currency="inr",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "order_id": order["order_id"],
            "user_id": user["user_id"],
            "user_email": user["email"],
        },
    )
    session = await stripe_checkout.create_checkout_session(checkout_req)

    # Record transaction
    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "order_id": order["order_id"],
        "user_id": user["user_id"],
        "amount": amount,
        "currency": "inr",
        "payment_status": "initiated",
        "metadata": {"order_id": order["order_id"]},
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.orders.update_one(
        {"order_id": order["order_id"]},
        {"$set": {"stripe_session_id": session.session_id}},
    )
    return {"url": session.url, "session_id": session.session_id}


@api_router.get("/payments/checkout/status/{session_id}")
async def get_checkout_status(session_id: str, request: Request):
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    status = await stripe_checkout.get_checkout_status(session_id)

    tx = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if tx and tx.get("payment_status") != "paid" and status.payment_status == "paid":
        # Update only once
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"payment_status": "paid", "status": status.status}},
        )
        order_id = (tx.get("metadata") or {}).get("order_id") or tx.get("order_id")
        if order_id:
            await db.orders.update_one(
                {"order_id": order_id},
                {"$set": {"payment_status": "paid", "status": "processing"}},
            )
            order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
            if order:
                await db.carts.update_one({"user_id": order["user_id"]}, {"$set": {"items": []}})
    elif tx and status.status == "expired":
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"payment_status": "expired", "status": "expired"}},
        )

    return {
        "status": status.status,
        "payment_status": status.payment_status,
        "amount_total": status.amount_total,
        "currency": status.currency,
        "metadata": status.metadata,
    }


@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("Stripe-Signature", "")
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    try:
        event = await stripe_checkout.handle_webhook(body, signature)
    except Exception as e:
        logger.warning(f"Webhook error: {e}")
        return {"ok": False}
    if event.payment_status == "paid":
        order_id = (event.metadata or {}).get("order_id")
        if order_id:
            await db.orders.update_one(
                {"order_id": order_id},
                {"$set": {"payment_status": "paid", "status": "processing"}},
            )
            await db.payment_transactions.update_one(
                {"session_id": event.session_id},
                {"$set": {"payment_status": "paid"}},
            )
    return {"ok": True}


# ---------- Admin ----------
@api_router.get("/admin/stats")
async def admin_stats(_: dict = Depends(require_admin)):
    total_orders = await db.orders.count_documents({})
    total_users = await db.users.count_documents({})
    total_products = await db.products.count_documents({})
    orders = await db.orders.find({"payment_status": {"$in": ["paid", "cod_pending"]}}, {"_id": 0, "total": 1}).to_list(2000)
    revenue = sum(o.get("total", 0) for o in orders)
    return {
        "total_orders": total_orders,
        "total_users": total_users,
        "total_products": total_products,
        "revenue": round(revenue, 2),
    }


@api_router.get("/admin/orders")
async def admin_all_orders(_: dict = Depends(require_admin)):
    docs = await db.orders.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [serialize_doc(d) for d in docs]


@api_router.put("/admin/orders/{order_id}")
async def admin_update_order(order_id: str, payload: Dict[str, Any], _: dict = Depends(require_admin)):
    allowed = {k: v for k, v in payload.items() if k in {"status", "payment_status"}}
    await db.orders.update_one({"order_id": order_id}, {"$set": allowed})
    doc = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    return serialize_doc(doc)


@api_router.get("/admin/users")
async def admin_users(_: dict = Depends(require_admin)):
    docs = await db.users.find({}, {"_id": 0}).to_list(500)
    return [serialize_doc(d) for d in docs]


@api_router.get("/admin/contacts")
async def admin_contacts(_: dict = Depends(require_admin)):
    docs = await db.contacts.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [serialize_doc(d) for d in docs]


# ---------- Seed Products ----------
SEED_PRODUCTS = [
    {
        "name": "Nayara Washing Soap Bar",
        "slug": "washing-soap-bar",
        "category": "laundry",
        "short_description": "Pure herbal laundry soap bar that lifts stains without harshness.",
        "description": "A gentle yet powerful laundry soap bar made with plant-derived actives. Removes tough stains from cottons, silks and everyday wear while keeping fabric colours bright. Factory-pressed in small batches for a premium, long-lasting bar.",
        "price": 45.0,
        "mrp": 60.0,
        "image": "https://images.unsplash.com/photo-1542038335240-86aea625b913?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NzV8MHwxfHNlYXJjaHwyfHxtaW5pbWFsJTIwc29hcCUyMHBhY2thZ2luZ3xlbnwwfHx8fDE3NzY2ODM4Nzh8MA&ixlib=rb-4.1.0&q=85",
        "badges": ["Made in India", "Factory Direct"],
        "featured": True,
        "stock": 250,
    },
    {
        "name": "Nayara Washing Powder Detergent 1kg",
        "slug": "washing-powder-1kg",
        "category": "laundry",
        "short_description": "Active-enzyme powder detergent for machine & hand wash.",
        "description": "Premium high-foam washing powder with active enzymes that attack tough stains on collars, cuffs and underarms. Safe for both top-load and front-load machines. Fresh citrus fragrance that lingers all day.",
        "price": 180.0,
        "mrp": 240.0,
        "image": "https://images.unsplash.com/photo-1582020711621-ab153a0f3631?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMjV8MHwxfHNlYXJjaHwzfHxmcmVzaCUyMGNsZWFuaW5nJTIwcHJvZHVjdHN8ZW58MHx8fHwxNzc2NjgzODQ4fDA&ixlib=rb-4.1.0&q=85",
        "badges": ["Made in India", "Factory Direct"],
        "featured": True,
        "stock": 180,
    },
    {
        "name": "Nayara Liquid Detergent 1L",
        "slug": "liquid-detergent-1l",
        "category": "laundry",
        "short_description": "Concentrated liquid detergent — low suds, deep clean.",
        "description": "A concentrated formula designed for modern washing machines. Dissolves fully in cold or hot water with no residue. 1 litre delivers up to 33 washes. Dermatologically tested for sensitive skin.",
        "price": 249.0,
        "mrp": 329.0,
        "image": "https://images.unsplash.com/photo-1585670210693-ff8fe3ff7a00?crop=entropy&cs=srgb&fm=jpg&w=1200&q=85",
        "badges": ["Made in India", "Skin Safe"],
        "featured": True,
        "stock": 150,
    },
    {
        "name": "Nayara Handwash Soap Bar",
        "slug": "handwash-soap-bar",
        "category": "personal-care",
        "short_description": "Germ-fighting hand soap bar with neem & tulsi.",
        "description": "Traditional Indian hand soap bar enriched with neem and tulsi extracts. Kills 99.9% of common household germs while keeping hands soft. Long-lasting bar with a grounded herbal fragrance.",
        "price": 35.0,
        "mrp": 50.0,
        "image": "https://images.unsplash.com/photo-1600857544200-b2f666a9a2ec?crop=entropy&cs=srgb&fm=jpg&w=1200&q=85",
        "badges": ["Made in India", "Herbal"],
        "featured": False,
        "stock": 300,
    },
    {
        "name": "Nayara Handwash Liquid 250ml",
        "slug": "handwash-liquid-250ml",
        "category": "personal-care",
        "short_description": "Moisturising liquid handwash with aloe & glycerin.",
        "description": "A pH-balanced liquid handwash that cleanses without stripping natural moisture. Aloe vera and glycerin keep skin hydrated; a fresh green-tea fragrance leaves you feeling renewed after every wash.",
        "price": 99.0,
        "mrp": 145.0,
        "image": "https://images.unsplash.com/photo-1633933319282-7eec2b2c2346?crop=entropy&cs=srgb&fm=jpg&w=1200&q=85",
        "badges": ["Made in India", "pH Balanced"],
        "featured": True,
        "stock": 220,
    },
    {
        "name": "Nayara Bathing Soap",
        "slug": "bathing-soap",
        "category": "personal-care",
        "short_description": "Premium bathing bar with shea butter & sandalwood.",
        "description": "A luxurious daily bathing bar enriched with shea butter and Mysore sandalwood oil. Leaves skin silky smooth with a lingering temple-grade sandalwood aroma. Crafted in small factory batches.",
        "price": 55.0,
        "mrp": 75.0,
        "image": "https://images.unsplash.com/photo-1556228578-8c89e6adf883?crop=entropy&cs=srgb&fm=jpg&w=1200&q=85",
        "badges": ["Made in India", "Shea Butter"],
        "featured": True,
        "stock": 400,
    },
    {
        "name": "Nayara Toilet Cleaner 500ml",
        "slug": "toilet-cleaner-500ml",
        "category": "home-care",
        "short_description": "Thick disinfectant gel for sparkling toilets.",
        "description": "Ultra-thick toilet bowl cleaner that clings to vertical surfaces for maximum contact time. Dissolves hard water stains, limescale and yellow deposits. Kills 99.9% germs with a fresh pine fragrance.",
        "price": 120.0,
        "mrp": 165.0,
        "image": "https://images.unsplash.com/photo-1626806787461-102c1bfaaea1?crop=entropy&cs=srgb&fm=jpg&w=1200&q=85",
        "badges": ["Made in India", "99.9% Germ Kill"],
        "featured": False,
        "stock": 160,
    },
]


async def seed_products():
    count = await db.products.count_documents({})
    if count > 0:
        return
    for sp in SEED_PRODUCTS:
        p = Product(**sp)
        doc = p.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await db.products.insert_one(doc)
    logger.info("Seeded %d products", len(SEED_PRODUCTS))


@api_router.get("/")
async def root():
    return {"message": "Nayara API", "status": "ok"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def on_startup():
    await seed_products()


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
