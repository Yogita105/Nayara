import asyncio
import bcrypt
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, Response

from .config import COOKIE_SAMESITE, COOKIE_SECURE, SECRET_KEY, SESSION_DAYS
from .database import db

SESSION_COOKIE_NAME = "session_token"
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"


def get_request_token(
    request: Request,
    authorization: Optional[str] = None,
) -> Optional[str]:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    return token


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def validate_password_bytes(password: str) -> None:
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(status_code=422, detail="Password must not exceed 72 bytes")


async def hash_password(password: str) -> str:
    validate_password_bytes(password)
    password_hash = await asyncio.to_thread(
        bcrypt.hashpw,
        password.encode("utf-8"),
        bcrypt.gensalt(),
    )
    return password_hash.decode("utf-8")


async def verify_password(password: str, password_hash: str) -> bool:
    if len(password.encode("utf-8")) > 72:
        return False
    try:
        return await asyncio.to_thread(
            bcrypt.checkpw,
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except ValueError:
        return False


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )


def derive_csrf_token(session_token: str) -> str:
    """Bind a CSRF token to a session without storing additional state."""
    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        session_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def csrf_token_matches(session_token: str, submitted_token: str) -> bool:
    if not session_token or not submitted_token:
        return False
    return hmac.compare_digest(derive_csrf_token(session_token), submitted_token)


def set_csrf_cookie(response: Response, session_token: str) -> None:
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=derive_csrf_token(session_token),
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=False,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )


def clear_session_cookies(response: Response) -> None:
    for cookie_name in (SESSION_COOKIE_NAME, CSRF_COOKIE_NAME):
        response.delete_cookie(
            cookie_name,
            path="/",
            samesite=COOKIE_SAMESITE,
            secure=COOKIE_SECURE,
        )


async def create_user_session(user_id: str, response: Response) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    await db.user_sessions.insert_one(
        {
            "user_id": user_id,
            "session_token_hash": hash_session_token(token),
            "expires_at": now + timedelta(days=SESSION_DAYS),
            "created_at": now,
        }
    )
    set_session_cookie(response, token)
    set_csrf_cookie(response, token)
    return derive_csrf_token(token)


async def end_all_sessions(user_id: str, keep_token: Optional[str] = None) -> int:
    """Sign an account out everywhere, optionally sparing the current caller.

    Used when a password changes and when someone reports a lost device, so a
    stolen session token stops working immediately rather than lasting a week.
    """
    query = {"user_id": user_id}
    if keep_token:
        query["session_token_hash"] = {"$ne": hash_session_token(keep_token)}
    result = await db.user_sessions.delete_many(query)
    return result.deleted_count


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> dict:
    token = get_request_token(request, authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = await db.user_sessions.find_one(
        {"session_token_hash": hash_session_token(token)},
        {"_id": 0},
    )
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    expires_at = session.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    user = await db.users.find_one(
        {"user_id": session["user_id"]},
        {"_id": 0, "password_hash": 0},
    )
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
