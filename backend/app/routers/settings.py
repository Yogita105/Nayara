"""The shop's own contact details.

Read by every page through the footer, so the read is public and cheap.
Written only by an administrator, and recorded when it changes: a phone
number quietly becoming someone else's is worth being able to trace.
"""

import hashlib
import json

from fastapi import APIRouter, Depends, Request, Response

from .. import audit
from ..database import db
from ..models import DEFAULT_BUSINESS, BusinessSettings
from ..security import require_admin

router = APIRouter(prefix="/api", tags=["settings"])

SETTINGS_KEY = "business"


async def stored_business() -> BusinessSettings:
    """The saved settings, or the defaults when nothing is saved yet.

    A shop that has never opened this screen still has a footer, and one
    whose stored settings cannot be understood still shows something a
    customer can ring rather than a blank space.
    """
    document = await db.settings.find_one({"key": SETTINGS_KEY}, {"_id": 0, "key": 0})
    if not document:
        return DEFAULT_BUSINESS
    try:
        return BusinessSettings(**document)
    except ValueError:
        return DEFAULT_BUSINESS


def version_of(settings: dict) -> str:
    """A tag that changes when the details do.

    Lets a browser ask "still the same?" and be told so in a few bytes,
    instead of being handed the answer once and told to assume it for the
    next five minutes. An owner who corrects their phone number expects to
    see it on the next page, not after a wait they were never told about.
    """
    body = json.dumps(settings, sort_keys=True, ensure_ascii=False)
    return '"' + hashlib.sha256(body.encode("utf-8")).hexdigest()[:16] + '"'


@router.get("/settings/business")
async def get_business(request: Request):
    settings = (await stored_business()).model_dump()
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


@router.put("/admin/settings/business")
async def update_business(
    payload: BusinessSettings,
    request: Request,
    user: dict = Depends(require_admin),
):
    previous = await stored_business()
    settings = payload.model_dump()
    await db.settings.update_one(
        {"key": SETTINGS_KEY},
        {"$set": {**settings, "key": SETTINGS_KEY}},
        upsert=True,
    )
    await audit.record(
        "admin.business_settings_updated",
        actor_id=user["user_id"],
        request=request,
        # Which fields moved, rather than their contents: the trail should say
        # what changed without becoming a second copy of the address book.
        changed=sorted(
            field for field, value in settings.items() if getattr(previous, field) != value
        ),
    )
    return settings
