"""Idempotent order submission.

A client sends the same Idempotency-Key when it retries, so a double-clicked
checkout or an automatic network retry produces one order rather than several.
Claims expire through a TTL index because they only guard a short window.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from .database import db

CLAIM_TTL_HOURS = 24
MAX_KEY_LENGTH = 200


def build_claim_id(user_id: str, key: str) -> str:
    # Scoped per user so one shopper's key cannot collide with another's.
    return f"{user_id}:{key}"


async def claim_request(user_id: str, key: Optional[str]) -> Optional[str]:
    """Reserve a key, or return the order a previous identical request created.

    Raises 409 while an identical request is still being processed, which stops
    two concurrent submissions from both creating an order.
    """
    if not key:
        return None
    key = key.strip()
    if not key:
        return None
    if len(key) > MAX_KEY_LENGTH:
        raise HTTPException(status_code=422, detail="Idempotency-Key is too long")

    now = datetime.now(timezone.utc)
    try:
        await db.order_claims.insert_one(
            {
                "_id": build_claim_id(user_id, key),
                "order_id": None,
                "expires_at": now + timedelta(hours=CLAIM_TTL_HOURS),
            }
        )
        return None
    except DuplicateKeyError:
        existing = await db.order_claims.find_one({"_id": build_claim_id(user_id, key)})
        if existing and existing.get("order_id"):
            return existing["order_id"]
        raise HTTPException(
            status_code=409,
            detail="This order is already being placed",
        )


async def complete_claim(user_id: str, key: Optional[str], order_id: str) -> None:
    if not key:
        return
    await db.order_claims.update_one(
        {"_id": build_claim_id(user_id, key.strip())},
        {"$set": {"order_id": order_id}},
    )


async def release_claim(user_id: str, key: Optional[str]) -> None:
    """Drop a claim after a failure so the shopper can correct and retry."""
    if not key:
        return
    await db.order_claims.delete_one({"_id": build_claim_id(user_id, key.strip())})
