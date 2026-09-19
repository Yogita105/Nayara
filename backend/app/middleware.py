from fastapi import Request
from fastapi.responses import JSONResponse

from .security import (
    CSRF_HEADER_NAME,
    SESSION_COOKIE_NAME,
    csrf_token_matches,
)


SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


async def csrf_protection(request: Request, call_next):
    """Reject cross-site writes that rely on the browser's session cookie.

    Requests authenticated with an Authorization header are exempt because
    browsers never attach that header automatically.
    """
    if request.method in SAFE_METHODS:
        return await call_next(request)

    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_token:
        return await call_next(request)

    submitted_token = request.headers.get(CSRF_HEADER_NAME, "")
    if not csrf_token_matches(session_token, submitted_token):
        return JSONResponse(
            status_code=403,
            content={"detail": "Invalid or missing CSRF token"},
        )

    return await call_next(request)
