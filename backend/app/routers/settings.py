"""Settings the shop's owner can change without a deployment.

Two kinds so far: how customers reach the shop, and what delivery costs.
Both are read by the storefront, so reading is public and cheap. Both are
written by an administrator alone, and recorded when they change -- a phone
number quietly becoming someone else's, or free delivery quietly starting at
a different figure, are worth being able to trace.
"""

import hashlib
import json
from typing import Type, TypeVar

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from .. import audit
from ..database import db
from ..models import (
    DEFAULT_BUSINESS,
    DEFAULT_SHIPPING,
    BusinessSettings,
    ShippingSettings,
)
from ..security import require_admin

router = APIRouter(prefix="/api", tags=["settings"])

BUSINESS_KEY = "business"
SHIPPING_KEY = "shipping"

Settings = TypeVar("Settings", bound=BaseModel)


async def stored(key: str, model: Type[Settings], fallback: Settings) -> Settings:
    """The saved settings, or the defaults when nothing usable is saved.

    A shop that has never opened these screens still has a footer and still
    quotes delivery, and one whose stored settings cannot be understood shows
    something sensible rather than breaking the page that needs them.
    """
    document = await db.settings.find_one({"key": key}, {"_id": 0, "key": 0})
    if not document:
        return fallback
    try:
        return model(**document)
    except ValueError:
        return fallback


async def stored_business() -> BusinessSettings:
    return await stored(BUSINESS_KEY, BusinessSettings, DEFAULT_BUSINESS)


async def stored_shipping() -> ShippingSettings:
    return await stored(SHIPPING_KEY, ShippingSettings, DEFAULT_SHIPPING)


def version_of(settings: dict) -> str:
    """A tag that changes when the settings do.

    Lets a browser ask "still the same?" and be told so in a few bytes,
    instead of being handed the answer once and told to assume it for the
    next five minutes. An owner who corrects a figure expects to see it on
    the next page, not after a wait they were never told about.
    """
    body = json.dumps(settings, sort_keys=True, ensure_ascii=False)
    return '"' + hashlib.sha256(body.encode("utf-8")).hexdigest()[:16] + '"'


def answer(request: Request, settings: dict) -> Response:
    version = version_of(settings)
    # `no-cache` does not mean do not store it; it means ask before reusing
    # it. The tag makes that question cheap.
    headers = {"Cache-Control": "no-cache", "ETag": version}
    if request.headers.get("if-none-match") == version:
        return Response(status_code=304, headers=headers)
    return Response(
        content=json.dumps(settings, ensure_ascii=False),
        media_type="application/json",
        headers=headers,
    )


async def save(
    key: str,
    event: str,
    payload: BaseModel,
    previous: BaseModel,
    user: dict,
    request: Request,
) -> dict:
    settings = payload.model_dump()
    await db.settings.update_one(
        {"key": key},
        {"$set": {**settings, "key": key}},
        upsert=True,
    )
    await audit.record(
        event,
        actor_id=user["user_id"],
        request=request,
        # Which fields moved, rather than their contents: the trail should say
        # what changed without becoming a second copy of the address book.
        changed=sorted(
            field for field, value in settings.items() if getattr(previous, field) != value
        ),
    )
    return settings


@router.get("/settings/business")
async def get_business(request: Request):
    return answer(request, (await stored_business()).model_dump())


@router.put("/admin/settings/business")
async def update_business(
    payload: BusinessSettings,
    request: Request,
    user: dict = Depends(require_admin),
):
    return await save(
        BUSINESS_KEY,
        "admin.business_settings_updated",
        payload,
        await stored_business(),
        user,
        request,
    )


@router.get("/settings/shipping")
async def get_shipping(request: Request):
    return answer(request, (await stored_shipping()).model_dump())


@router.put("/admin/settings/shipping")
async def update_shipping(
    payload: ShippingSettings,
    request: Request,
    user: dict = Depends(require_admin),
):
    return await save(
        SHIPPING_KEY,
        "admin.shipping_settings_updated",
        payload,
        await stored_shipping(),
        user,
        request,
    )
