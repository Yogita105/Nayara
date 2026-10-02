"""The customer's address book.

Addresses saved here are a convenience for filling in checkout. They are not
the record of where anything was sent: each order keeps its own copy of the
address at the time it was placed, so editing or deleting one here can never
rewrite where a past parcel went.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends

from ..database import db
from ..errors import FieldError
from ..models import MAX_ADDRESSES, AddressInput, SavedAddress
from ..security import get_current_user

router = APIRouter(prefix="/api", tags=["addresses"])


async def saved_for(user_id: str) -> List[dict]:
    doc = await db.addresses.find_one({"user_id": user_id}, {"_id": 0})
    return list(doc.get("items", [])) if doc else []


def with_one_default(items: List[dict], prefer: Optional[str] = None) -> List[dict]:
    """Keep exactly one address marked as the usual one.

    A book with no default leaves checkout nothing to pre-select; a book with
    two leaves it guessing. Neither is something the customer could diagnose
    or repair, so the rule is enforced on every write rather than trusted.

    This is also why an address cannot simply be un-defaulted: with nothing
    else chosen it stays the default. Choosing another is how you move it.
    """
    if not items:
        return items
    chosen = prefer
    if chosen is None:
        marked = [a["address_id"] for a in items if a.get("is_default")]
        chosen = marked[0] if marked else items[0]["address_id"]
    return [{**a, "is_default": a["address_id"] == chosen} for a in items]


async def store(user_id: str, items: List[dict]) -> dict:
    await db.addresses.update_one(
        {"user_id": user_id},
        {"$set": {"items": items}},
        upsert=True,
    )
    return {"items": items}


@router.get("/addresses")
async def list_addresses(user: dict = Depends(get_current_user)):
    return {"items": await saved_for(user["user_id"])}


@router.post("/addresses")
async def add_address(payload: AddressInput, user: dict = Depends(get_current_user)):
    items = await saved_for(user["user_id"])
    if len(items) >= MAX_ADDRESSES:
        raise FieldError(
            409,
            "label",
            f"You can keep {MAX_ADDRESSES} addresses. Remove one to add another.",
        )

    saved = SavedAddress(**payload.model_dump()).model_dump()
    items.append(saved)
    # The first address saved is the only one there is, so it is the default
    # whatever was asked for.
    prefer = saved["address_id"] if (saved["is_default"] or len(items) == 1) else None
    return await store(user["user_id"], with_one_default(items, prefer))


@router.put("/addresses/{address_id}")
async def edit_address(
    address_id: str,
    payload: AddressInput,
    user: dict = Depends(get_current_user),
):
    items = await saved_for(user["user_id"])
    if not any(a["address_id"] == address_id for a in items):
        raise FieldError(404, "address_id", "That address is no longer saved.")

    edited = SavedAddress(**payload.model_dump(), address_id=address_id).model_dump()
    items = [edited if a["address_id"] == address_id else a for a in items]
    prefer = address_id if payload.is_default else None
    return await store(user["user_id"], with_one_default(items, prefer))


@router.delete("/addresses/{address_id}")
async def delete_address(address_id: str, user: dict = Depends(get_current_user)):
    items = await saved_for(user["user_id"])
    remaining = [a for a in items if a["address_id"] != address_id]
    if len(remaining) == len(items):
        raise FieldError(404, "address_id", "That address is no longer saved.")
    # Deleting the default leaves nobody chosen, so another takes its place.
    return await store(user["user_id"], with_one_default(remaining))
