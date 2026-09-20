from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from ..database import db
from ..errors import FieldError
from ..models import AddToCartRequest, UpdateCartRequest, WishlistRequest
from ..security import get_current_user
from ..utils import serialize_doc
from ..variants import find_variant, resolve_variant, variants_of

router = APIRouter(prefix="/api", tags=["shopping"])


async def get_or_create_cart(user_id: str) -> dict:
    cart = await db.carts.find_one({"user_id": user_id}, {"_id": 0})
    if not cart:
        cart = {"user_id": user_id, "items": []}
        await db.carts.insert_one(dict(cart))
    return cart


async def require_available(
    product_id: str, variant_id, wanted: int, already_held: int = 0
) -> dict:
    """Refuse a cart quantity the shop cannot fill.

    An order is all or nothing, so a cart holding more than exists is an order
    that will be refused. Saying so when the item is added means the customer
    finds out while they are still shopping, rather than after filling in an
    address. The reservation at checkout remains the real guard: stock can
    fall between the two moments.
    """
    product = await db.products.find_one({"product_id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    variant = resolve_variant(product, variant_id)
    stock = variant.get("stock", 0)
    name = product.get("name", "This product")
    # Only worth naming the form when there is more than one to choose from.
    if len(variants_of(product)) > 1:
        name = f"{name} ({variant['label']})"

    if stock <= 0:
        raise FieldError(409, "quantity", f"{name} is out of stock.")
    if wanted > stock:
        if already_held:
            detail = f"Only {stock} left of {name}, and your cart already has " f"{already_held}."
        else:
            detail = f"Only {stock} left of {name}."
        raise FieldError(409, "quantity", detail)
    return variant


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

    enriched = []
    for item in items:
        product = products_by_id.get(item["product_id"])
        if not product:
            continue
        variant_id = item.get("variant_id")
        if variant_id:
            variant = find_variant(product, variant_id)
        else:
            # A line stored before variants existed belongs to the product's
            # only one.
            available = variants_of(product)
            variant = available[0] if available else None
        if not variant:
            # The chosen form has since been removed from the catalogue.
            continue
        enriched.append(
            {
                **serialize_doc(dict(product)),
                "quantity": item["quantity"],
                "variant_id": variant["variant_id"],
                "variant_label": variant["label"],
                # What the line is actually sold at and how many remain of it,
                # under the names the rest of the app already reads.
                "price": variant["price"],
                "mrp": variant.get("mrp", variant["price"]),
                "stock": variant.get("stock", 0),
                "image": variant.get("image") or product.get("image", ""),
            }
        )
    return {"items": enriched}


@router.post("/cart")
async def add_to_cart(
    request: AddToCartRequest,
    user: dict = Depends(get_current_user),
):
    cart = await get_or_create_cart(user["user_id"])
    items = cart.get("items", [])

    # The variant has to be settled before the line can be found, since two
    # forms of one product are two separate lines.
    variant = await require_available(request.product_id, request.variant_id, request.quantity)
    variant_id = variant["variant_id"]

    already_held = next(
        (
            item["quantity"]
            for item in items
            if item["product_id"] == request.product_id and item.get("variant_id") == variant_id
        ),
        0,
    )
    if already_held:
        await require_available(
            request.product_id,
            variant_id,
            already_held + request.quantity,
            already_held,
        )

    for item in items:
        if item["product_id"] == request.product_id and item.get("variant_id") == variant_id:
            item["quantity"] += request.quantity
            break
    else:
        items.append(
            {
                "product_id": request.product_id,
                "variant_id": variant_id,
                "quantity": request.quantity,
            }
        )
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
    existing = cart.get("items", [])

    # A request that names no variant means the line for this product, which
    # is unambiguous while the cart holds only one of them.
    variant_id = request.variant_id
    if not variant_id:
        for_product = [item for item in existing if item["product_id"] == product_id]
        if len(for_product) == 1:
            variant_id = for_product[0].get("variant_id")

    def is_target(item: dict) -> bool:
        if item["product_id"] != product_id:
            return False
        return variant_id is None or item.get("variant_id") == variant_id

    items = [item for item in existing if not is_target(item)]
    if request.quantity > 0:
        # Setting a quantity replaces whatever was there, so the whole amount
        # is what has to be available.
        variant = await require_available(product_id, variant_id, request.quantity)
        items.append(
            {
                "product_id": product_id,
                "variant_id": variant["variant_id"],
                "quantity": request.quantity,
            }
        )
    await db.carts.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"items": items}},
    )
    return {"ok": True}


@router.delete("/cart/{product_id}")
async def delete_cart_item(
    product_id: str,
    variant_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    cart = await get_or_create_cart(user["user_id"])

    def is_target(item: dict) -> bool:
        if item["product_id"] != product_id:
            return False
        # Naming no variant removes every form of the product, which is what
        # a client that predates them means by removing it.
        return variant_id is None or item.get("variant_id") == variant_id

    items = [item for item in cart.get("items", []) if not is_target(item)]
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
