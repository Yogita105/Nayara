"""Fixed-window rate limiting backed by MongoDB.

MongoDB is used instead of process memory so that limits stay correct when the
API runs as several workers or containers.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, Request
from pymongo import ReturnDocument

from .config import RATE_LIMIT_ENABLED, TRUST_PROXY_HEADERS
from .database import db


@dataclass(frozen=True)
class RateLimitRule:
    limit: int
    window_seconds: int


# Total sign-in attempts allowed from one network address. This is deliberately
# generous because many customers share one address behind carrier NAT; the
# per-account rule below is the real brute-force defence.
LOGIN_IP_RULE = RateLimitRule(limit=50, window_seconds=15 * 60)
# Failed sign-in attempts allowed against one account.
LOGIN_IDENTIFIER_RULE = RateLimitRule(limit=5, window_seconds=15 * 60)
# New accounts allowed from one network address.
REGISTER_IP_RULE = RateLimitRule(limit=10, window_seconds=60 * 60)
# Password attempts allowed for one account, to slow down someone guessing the
# current password from a session they should not have.
PASSWORD_CHANGE_RULE = RateLimitRule(limit=5, window_seconds=15 * 60)

UNKNOWN_CLIENT = "unknown"


def get_client_ip(request: Request) -> str:
    """Resolve the caller address.

    Forwarded headers are only honoured when the deployment explicitly marks
    them as trustworthy, because any client can otherwise spoof them.
    """
    if TRUST_PROXY_HEADERS:
        forwarded_for = request.headers.get("x-forwarded-for", "")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return UNKNOWN_CLIENT


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def seconds_until(expires_at: datetime, now: datetime) -> int:
    return max(1, math.ceil((_as_utc(expires_at) - now).total_seconds()))


def build_key(scope: str, identifier: str) -> str:
    return f"{scope}:{identifier.strip().lower()}"


async def enforce_rate_limit(
    scope: str,
    identifier: str,
    rule: RateLimitRule,
    message: str,
) -> None:
    """Count one attempt and reject the request once the rule is exceeded."""
    if not RATE_LIMIT_ENABLED:
        return

    now = datetime.now(timezone.utc)
    key = build_key(scope, identifier)

    record = await db.rate_limits.find_one_and_update(
        {"_id": key, "expires_at": {"$gt": now}},
        {"$inc": {"count": 1}},
        return_document=ReturnDocument.AFTER,
    )

    if record is None:
        record = {
            "_id": key,
            "count": 1,
            "expires_at": now + timedelta(seconds=rule.window_seconds),
        }
        await db.rate_limits.replace_one({"_id": key}, record, upsert=True)

    if record["count"] > rule.limit:
        retry_after = seconds_until(record["expires_at"], now)
        raise HTTPException(
            status_code=429,
            detail=message,
            headers={"Retry-After": str(retry_after)},
        )


async def reset_rate_limit(scope: str, identifier: Optional[str]) -> None:
    """Clear a counter, for example after a successful sign-in."""
    if not RATE_LIMIT_ENABLED or not identifier:
        return
    await db.rate_limits.delete_one({"_id": build_key(scope, identifier)})


async def ensure_not_blocked(
    scope: str,
    identifier: str,
    rule: RateLimitRule,
    message: str,
) -> None:
    """Reject a request that is already locked out, without counting it.

    This runs before credentials are checked so that a locked account stays
    locked even when an attacker eventually guesses the correct password.
    """
    if not RATE_LIMIT_ENABLED:
        return

    now = datetime.now(timezone.utc)
    record = await db.rate_limits.find_one(
        {"_id": build_key(scope, identifier), "expires_at": {"$gt": now}}
    )
    if record and record["count"] >= rule.limit:
        raise HTTPException(
            status_code=429,
            detail=message,
            headers={"Retry-After": str(seconds_until(record["expires_at"], now))},
        )
