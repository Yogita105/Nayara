"""A record of security-relevant actions.

Answers "who did this, and when" after the fact: which account changed an
order, whether a run of failed sign-ins preceded a successful one, when a
password was last changed. Without it there is nothing to look at when
something appears to have gone wrong.

Nothing recorded here may be a credential. A log holding passwords or session
tokens is worth stealing in its own right, and would hand over the very
accounts it exists to protect. Values are therefore scrubbed on the way in
rather than trusted to arrive clean.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import Request

from .config import AUDIT_RETENTION_DAYS
from .database import db
from .observability import get_request_id
from .rate_limit import get_client_ip

logger = logging.getLogger("nayara.audit")

REDACTED = "[redacted]"

# Matched against the name of a field, not its contents. Guessing from the
# value is unreliable; a caller naming a field "password" tells us plainly.
SENSITIVE_NAME = re.compile(
    r"pass(word|phrase)|token|secret|credential|authorization|api[_-]?key|cookie|hash",
    re.IGNORECASE,
)

MAX_TEXT_LENGTH = 200
MAX_ITEMS = 20
MAX_DEPTH = 3


def scrub(value: Any, depth: int = 0) -> Any:
    """Return a value safe to store, replacing anything credential-shaped."""
    if depth >= MAX_DEPTH:
        return REDACTED
    if isinstance(value, dict):
        cleaned = {}
        for key, item in list(value.items())[:MAX_ITEMS]:
            if SENSITIVE_NAME.search(str(key)):
                cleaned[str(key)] = REDACTED
            else:
                cleaned[str(key)] = scrub(item, depth + 1)
        return cleaned
    if isinstance(value, (list, tuple, set)):
        return [scrub(item, depth + 1) for item in list(value)[:MAX_ITEMS]]
    if isinstance(value, str):
        return value[:MAX_TEXT_LENGTH]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:MAX_TEXT_LENGTH]


async def record(
    event: str,
    *,
    actor_id: Optional[str] = None,
    request: Optional[Request] = None,
    **details: Any,
) -> None:
    """Note that something happened, without ever failing the request.

    An action that already succeeded must not be reported as an error because
    its audit record could not be written, so a failure here is logged and
    otherwise ignored.
    """
    now = datetime.now(timezone.utc)
    entry = {
        "event": event,
        "actor_id": actor_id,
        "at": now,
        "expires_at": now + timedelta(days=AUDIT_RETENTION_DAYS),
        "request_id": get_request_id(),
        "details": scrub(details),
    }
    if request is not None:
        entry["ip"] = get_client_ip(request)

    logger.info(
        "Audit event",
        extra={"event": event, "actor_id": actor_id},
    )

    try:
        await db.audit_events.insert_one(entry)
    except Exception:
        logger.exception("Could not write an audit event", extra={"event": event})
