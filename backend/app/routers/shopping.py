from fastapi import APIRouter, Depends

from ..database import db
from ..models import AddToCartRequest, UpdateCartRequest, WishlistRequest
from ..security import get_current_user
from ..utils import serialize_doc


router = APIRouter(prefix="/api", tags=["shopping"])


async def get_or_create_cart(user_id: str) -> dict:
    cart = await db.carts.find_one({"user_id": user_id}, {"_id": 0})
    if not cart:
        cart = {"user_id": user_id, "items": []}
        await db.carts.insert_one(dict(cart))
    return cart


@router.get("/cart")
async def get_cart(user: dict = Depends(get_current_user)):
    cart = await get_or_create_cart(user["user_id"])
    items = cart.get("items", [])
    if not items:
        return {"items": []}
    product_ids = [item["product_id"] for item in items]
    products = await db.products.find(
        {"product_id": {"$in": product_ids}},
        {"_id": 0},
    ).to_list(500)
    products_by_id = {product["product_id"]: product for product in products}
    enriched = [
        {
            **serialize_doc(products_by_id[item["product_id"]]),
            "quantity": item["quantity"],
        }
        for item in items
        if item["product_id"] in products_by_id
    ]
    return {"items": enriched}


@router.post("/cart")
async def add_to_cart(
    request: AddToCartRequest,
    user: dict = Depends(get_current_user),
):
    cart = await get_or_create_cart(user["user_id"])
    items = cart.get("items", [])
    for item in items:
        if item["product_id"] == request.product_id:
            item["quantity"] += request.quantity
            break
    else:
        items.append({
            "product_id": request.product_id,
            "quantity": request.quantity,
        })
    await db.carts.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"items": items}},
    )
    return {"ok": True, "items": items}


@router.put("/cart/{product_id}")
async def update_cart(
    product_id: str,
    request: UpdateCartRequest,
    user: dict = Depends(get_current_user),
):
    cart = await get_or_create_cart(user["user_id"])
    items = [
        item
        for item in cart.get("items", [])
        if item["product_id"] != product_id
    ]
    if request.quantity > 0:
        items.append({"product_id": product_id, "quantity": request.quantity})
    await db.carts.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"items": items}},
    )
    return {"ok": True}


@router.delete("/cart/{product_id}")
async def delete_cart_item(
    product_id: str,
    user: dict = Depends(get_current_user),
):
    cart = await get_or_create_cart(user["user_id"])
    items = [
        item
        for item in cart.get("items", [])
        if item["product_id"] != product_id
    ]
    await db.carts.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"items": items}},
    )
    return {"ok": True}


@router.delete("/cart")
async def clear_cart(user: dict = Depends(get_current_user)):
    await db.carts.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"items": []}},
    )
    return {"ok": True}


@router.get("/wishlist")
async def get_wishlist(user: dict = Depends(get_current_user)):
    wishlist = await db.wishlists.find_one(
        {"user_id": user["user_id"]},
        {"_id": 0},
    )
    items = (wishlist or {}).get("items", [])
    if not items:
        return {"items": []}
    products = await db.products.find(
        {"product_id": {"$in": items}},
        {"_id": 0},
    ).to_list(500)
    return {"items": [serialize_doc(product) for product in products]}


@router.post("/wishlist")
async def add_wishlist(
    request: WishlistRequest,
    user: dict = Depends(get_current_user),
):
    await db.wishlists.update_one(
        {"user_id": user["user_id"]},
        {"$addToSet": {"items": request.product_id}},
        upsert=True,
    )
    return {"ok": True}


@router.delete("/wishlist/{product_id}")
async def remove_wishlist(
    product_id: str,
    user: dict = Depends(get_current_user),
):
    await db.wishlists.update_one(
        {"user_id": user["user_id"]},
        {"$pull": {"items": product_id}},
    )
    return {"ok": True}
