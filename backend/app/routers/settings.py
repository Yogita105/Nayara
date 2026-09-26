"""The shop's own contact details.

Read by every page through the footer, so the read is public and cheap.
Written only by an administrator, and recorded when it changes: a phone
number quietly becoming someone else's is worth being able to trace.
"""

from fastapi import APIRouter, Depends, Request, Response

from .. import audit
from ..database import db
from ..models import DEFAULT_BUSINESS, BusinessSettings
from ..security import require_admin

router = APIRouter(prefix="/api", tags=["settings"])

SETTINGS_KEY = "business"
# Long enough that a browser is not asking on every page, short enough that a
# corrected phone number reaches customers the same afternoon.
CACHE_SECONDS = 300


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


@router.get("/settings/business")
async def get_business(response: Response):
    response.headers["Cache-Control"] = f"public, max-age={CACHE_SECONDS}"
    return (await stored_business()).model_dump()


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
