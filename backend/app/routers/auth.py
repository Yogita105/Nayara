import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pymongo.errors import DuplicateKeyError

from .. import audit
from ..config import ADMIN_MOBILES
from ..database import db
from ..errors import FieldError
from ..models import (
    LoginRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    RegisterRequest,
)
from ..rate_limit import (
    LOGIN_IDENTIFIER_RULE,
    LOGIN_IP_RULE,
    PASSWORD_CHANGE_RULE,
    REGISTER_IP_RULE,
    enforce_rate_limit,
    ensure_not_blocked,
    get_client_ip,
    reset_rate_limit,
)
from ..security import (
    SESSION_COOKIE_NAME,
    clear_session_cookies,
    create_user_session,
    end_all_sessions,
    get_current_user,
    get_request_token,
    hash_password,
    hash_session_token,
    set_csrf_cookie,
    verify_password,
)
from ..utils import normalize_indian_mobile, public_user

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)

LOGIN_IP_SCOPE = "login-ip"
LOGIN_IDENTIFIER_SCOPE = "login-identifier"
REGISTER_IP_SCOPE = "register-ip"
PASSWORD_CHANGE_SCOPE = "password-change"
TOO_MANY_LOGINS = "Too many sign-in attempts. Please try again later."
TOO_MANY_ACCOUNT_LOGINS = (
    "Too many failed sign-in attempts for this account. Please try again later."
)
TOO_MANY_REGISTRATIONS = "Too many accounts created recently. Please try again later."
TOO_MANY_PASSWORD_CHANGES = "Too many password attempts. Please try again later."


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, request: Request, response: Response):
    await enforce_rate_limit(
        REGISTER_IP_SCOPE,
        get_client_ip(request),
        REGISTER_IP_RULE,
        TOO_MANY_REGISTRATIONS,
    )
    name = body.name.strip()
    if len(name) < 2:
        raise FieldError(422, "name", "Name must contain at least 2 characters")
    try:
        mobile = normalize_indian_mobile(body.mobile)
    except ValueError as error:
        raise FieldError(422, "mobile", str(error)) from error

    email = str(body.email).lower() if body.email else None
    if await db.users.find_one({"mobile": mobile}, {"_id": 1}):
        raise FieldError(409, "mobile", "An account with this mobile number already exists")
    if email and await db.users.find_one({"email": email}, {"_id": 1}):
        raise FieldError(409, "email", "An account with this email already exists")

    user = {
        "user_id": f"user_{uuid.uuid4().hex[:12]}",
        "mobile": mobile,
        "name": name,
        "picture": "",
        "password_hash": await hash_password(body.password),
        "is_admin": mobile in ADMIN_MOBILES,
        "created_at": datetime.now(timezone.utc),
    }
    # The key is left out entirely when there is no address, so the unique
    # index does not treat every account without one as a duplicate.
    if email:
        user["email"] = email

    try:
        await db.users.insert_one(user)
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=409,
            detail="An account with this mobile number or email already exists",
        ) from error
    csrf_token = await create_user_session(user["user_id"], response)
    await audit.record(
        "auth.account_created",
        actor_id=user["user_id"],
        request=request,
        is_admin=user["is_admin"],
        has_email=bool(email),
    )
    return {"user": public_user(user), "csrf_token": csrf_token}


@router.post("/login")
async def login(body: LoginRequest, request: Request, response: Response):
    await enforce_rate_limit(
        LOGIN_IP_SCOPE,
        get_client_ip(request),
        LOGIN_IP_RULE,
        TOO_MANY_LOGINS,
    )

    identifier = body.identifier.strip()
    if "@" in identifier:
        lookup_value = identifier.lower()
        query = {"email": lookup_value}
    else:
        try:
            lookup_value = normalize_indian_mobile(identifier)
        except ValueError as error:
            raise HTTPException(
                status_code=401,
                detail="Invalid email/mobile or password",
            ) from error
        query = {"mobile": lookup_value}

    await ensure_not_blocked(
        LOGIN_IDENTIFIER_SCOPE,
        lookup_value,
        LOGIN_IDENTIFIER_RULE,
        TOO_MANY_ACCOUNT_LOGINS,
    )

    async def reject_invalid_credentials() -> HTTPException:
        await enforce_rate_limit(
            LOGIN_IDENTIFIER_SCOPE,
            lookup_value,
            LOGIN_IDENTIFIER_RULE,
            TOO_MANY_ACCOUNT_LOGINS,
        )
        return HTTPException(
            status_code=401,
            detail="Invalid email/mobile or password",
        )

    user = await db.users.find_one(query, {"_id": 0})
    if not user or not user.get("password_hash"):
        # The identifier someone typed is deliberately not recorded: a
        # password entered in the wrong box would be stored as plainly as if
        # it had been asked for.
        await audit.record("auth.sign_in_failed", request=request, reason="no_account")
        raise await reject_invalid_credentials()
    if not await verify_password(body.password, user["password_hash"]):
        await audit.record(
            "auth.sign_in_failed",
            actor_id=user["user_id"],
            request=request,
            reason="wrong_password",
        )
        raise await reject_invalid_credentials()

    await reset_rate_limit(LOGIN_IDENTIFIER_SCOPE, lookup_value)

    is_admin = bool(user.get("is_admin")) or user.get("mobile") in ADMIN_MOBILES
    if user.get("is_admin", False) != is_admin:
        await db.users.update_one(
            {"user_id": user["user_id"]},
            {"$set": {"is_admin": is_admin}},
        )
        user["is_admin"] = is_admin
        await audit.record(
            "auth.admin_granted",
            actor_id=user["user_id"],
            request=request,
        )

    csrf_token = await create_user_session(user["user_id"], response)
    await audit.record(
        "auth.signed_in",
        actor_id=user["user_id"],
        request=request,
        is_admin=user["is_admin"],
    )
    return {"user": public_user(user), "csrf_token": csrf_token}


@router.get("/me")
async def auth_me(
    request: Request,
    response: Response,
    user: dict = Depends(get_current_user),
):
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token:
        set_csrf_cookie(response, session_token)
    return public_user(user)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    authorization: Optional[str] = Header(None),
):
    token = get_request_token(request, authorization)
    if token:
        session = await db.user_sessions.find_one_and_delete(
            {"session_token_hash": hash_session_token(token)}
        )
        if session:
            await audit.record(
                "auth.signed_out",
                actor_id=session.get("user_id"),
                request=request,
            )
    clear_session_cookies(response)
    return {"ok": True}


@router.put("/profile")
async def update_profile(
    body: ProfileUpdateRequest,
    user: dict = Depends(get_current_user),
):
    """Update the details a customer can correct themselves.

    The mobile number is not editable here: it identifies the account, is how
    people sign in, and grants administrator access through the allowlist.
    Changing it safely needs a verified-number flow.
    """
    email = str(body.email).lower() if body.email else None

    if email:
        clash = await db.users.find_one(
            {"email": email, "user_id": {"$ne": user["user_id"]}},
            {"_id": 1},
        )
        if clash:
            raise FieldError(409, "email", "Another account already uses this email")

    changes = {"$set": {"name": body.name}}
    if email:
        changes["$set"]["email"] = email
    else:
        # Removing the key keeps the unique index from seeing many blanks.
        changes["$unset"] = {"email": ""}

    try:
        await db.users.update_one({"user_id": user["user_id"]}, changes)
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=409,
            detail="Another account already uses this email",
        ) from error

    updated = await db.users.find_one(
        {"user_id": user["user_id"]},
        {"_id": 0, "password_hash": 0},
    )
    await audit.record(
        "auth.profile_updated",
        actor_id=user["user_id"],
        # Which details changed, not what they were changed to.
        name_changed=user.get("name") != body.name,
        email_changed=user.get("email") != email,
    )
    return public_user(updated)


@router.post("/password")
async def change_password(
    body: PasswordChangeRequest,
    request: Request,
    user: dict = Depends(get_current_user),
    authorization: Optional[str] = Header(None),
):
    """Replace the password, then sign the account out of other devices."""
    await enforce_rate_limit(
        PASSWORD_CHANGE_SCOPE,
        user["user_id"],
        PASSWORD_CHANGE_RULE,
        TOO_MANY_PASSWORD_CHANGES,
    )

    record = await db.users.find_one(
        {"user_id": user["user_id"]},
        {"_id": 0, "password_hash": 1},
    )
    current_hash = (record or {}).get("password_hash")
    if not current_hash or not await verify_password(body.current_password, current_hash):
        await audit.record(
            "auth.password_change_refused",
            actor_id=user["user_id"],
            request=request,
            reason="wrong_current_password",
        )
        raise FieldError(403, "current_password", "Current password is incorrect")

    if await verify_password(body.new_password, current_hash):
        raise FieldError(422, "new_password", "The new password must differ from the current one")

    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"password_hash": await hash_password(body.new_password)}},
    )

    # Anyone signed in elsewhere with the old password loses access at once.
    token = get_request_token(request, authorization)
    ended = await end_all_sessions(user["user_id"], keep_token=token)
    await reset_rate_limit(PASSWORD_CHANGE_SCOPE, user["user_id"])
    logger.info(
        "Password changed",
        extra={"user_id": user["user_id"], "sessions_ended": ended},
    )
    await audit.record(
        "auth.password_changed",
        actor_id=user["user_id"],
        request=request,
        other_sessions_ended=ended,
    )
    return {"ok": True, "other_sessions_ended": ended}


@router.post("/logout-all")
async def logout_everywhere(
    response: Response,
    user: dict = Depends(get_current_user),
):
    """End every session for the account, including this one."""
    ended = await end_all_sessions(user["user_id"])
    clear_session_cookies(response)
    logger.info(
        "Signed out of all devices",
        extra={"user_id": user["user_id"], "sessions_ended": ended},
    )
    await audit.record(
        "auth.signed_out_everywhere",
        actor_id=user["user_id"],
        sessions_ended=ended,
    )
    return {"ok": True, "sessions_ended": ended}
