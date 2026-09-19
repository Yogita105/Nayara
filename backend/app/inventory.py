"""Stock reservation for orders.

Each product is adjusted with a single conditional update, so two shoppers
competing for the last unit cannot both succeed. MongoDB transactions are not
used because they require a replica set, which a local development database may
not provide; instead a partial reservation is rolled back explicitly.
"""

import logging
from typing import List, Sequence

from fastapi import HTTPException

from .database import db


logger = logging.getLogger(__name__)


async def release_stock(items: Sequence[dict]) -> None:
    """Return reserved units to the catalogue."""
    for item in items:
        await db.products.update_one(
            {"product_id": item["product_id"]},
            {"$inc": {"stock": item["quantity"]}},
        )


async def reserve_stock(items: Sequence[dict]) -> None:
    """Hold stock for an order, or raise 409 and leave the catalogue unchanged.

    The condition and the decrement happen in one operation, so stock can never
    drop below zero even when orders arrive at the same moment.
    """
    reserved: List[dict] = []
    for item in items:
        result = await db.products.update_one(
            {
                "product_id": item["product_id"],
                "stock": {"$gte": item["quantity"]},
            },
            {"$inc": {"stock": -item["quantity"]}},
        )
        if result.matched_count == 0:
            await release_stock(reserved)
            product = await db.products.find_one(
                {"product_id": item["product_id"]},
                {"_id": 0, "stock": 1},
            )
            available = product.get("stock", 0) if product else 0
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Only {available} left of {item['name']}. "
                    "Please reduce the quantity."
                ),
            )
        reserved.append(item)
