"""Stock reservation for orders.

Stock belongs to a variant: a kilo bag and a half-kilo bag run out
independently. Each is adjusted with a single conditional update, so two
shoppers competing for the last unit cannot both succeed. MongoDB transactions
are not used because they require a replica set, which a local development
database may not provide; instead a partial reservation is rolled back
explicitly.
"""

import logging
from typing import List, Sequence

from fastapi import HTTPException

from .database import db

logger = logging.getLogger(__name__)


def describe(item: dict) -> str:
    """Name what ran out, including which form of it."""
    label = item.get("variant_label")
    return f"{item['name']} ({label})" if label else item["name"]


async def remaining_of(product_id: str, variant_id: str) -> int:
    product = await db.products.find_one(
        {"product_id": product_id},
        {"_id": 0, "variants": 1},
    )
    for variant in (product or {}).get("variants") or []:
        if variant.get("variant_id") == variant_id:
            return variant.get("stock", 0)
    return 0


async def release_stock(items: Sequence[dict]) -> None:
    """Return reserved units to the catalogue."""
    for item in items:
        variant_id = item.get("variant_id")
        if variant_id:
            criteria = {
                "product_id": item["product_id"],
                "variants.variant_id": variant_id,
            }
            field = "variants.$.stock"
        else:
            # An order placed before variants existed names none, so the units
            # go back to the product's first and only one.
            criteria = {"product_id": item["product_id"]}
            field = "variants.0.stock"

        await db.products.update_one(
            criteria,
            # The product's own count mirrors its variants while anything
            # still reads it, and is dropped once nothing does.
            {"$inc": {field: item["quantity"], "stock": item["quantity"]}},
        )


async def reserve_stock(items: Sequence[dict]) -> None:
    """Hold stock for an order, or raise 409 and leave the catalogue unchanged.

    The condition and the decrement happen in one operation, so stock can never
    drop below zero even when orders arrive at the same moment. The condition
    names the variant and its remaining count together, so the positional
    update can only reach the variant that satisfied it.
    """
    reserved: List[dict] = []
    for item in items:
        result = await db.products.update_one(
            {
                "product_id": item["product_id"],
                "variants": {
                    "$elemMatch": {
                        "variant_id": item["variant_id"],
                        "stock": {"$gte": item["quantity"]},
                    }
                },
            },
            {
                "$inc": {
                    "variants.$.stock": -item["quantity"],
                    "stock": -item["quantity"],
                }
            },
        )
        if result.matched_count == 0:
            await release_stock(reserved)
            available = await remaining_of(item["product_id"], item["variant_id"])
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Only {available} left of {describe(item)}. " "Please reduce the quantity."
                ),
            )
        reserved.append(item)
