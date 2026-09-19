import logging
import time

from fastapi import Request
from fastapi.responses import JSONResponse

from .observability import (
    REQUEST_ID_HEADER,
    clean_request_id,
    get_request_id,
    set_request_id,
)
from .security import (
    CSRF_HEADER_NAME,
    SESSION_COOKIE_NAME,
    csrf_token_matches,
)


SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
SLOW_REQUEST_MS = 1000

logger = logging.getLogger("nayara.request")


async def request_context(request: Request, call_next):
    """Tag each request with an id, then record how it finished.

    Only the method, path and outcome are recorded. Query strings, headers and
    bodies are left out because they can contain credentials.
    """
    set_request_id(clean_request_id(request.headers.get(REQUEST_ID_HEADER)))
    started = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "Request failed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        response = JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "request_id": get_request_id(),
            },
        )
        response.headers[REQUEST_ID_HEADER] = get_request_id() or ""
        return response

    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers[REQUEST_ID_HEADER] = get_request_id() or ""

    if response.status_code >= 500:
        level = logging.ERROR
    elif response.status_code >= 400 or duration_ms >= SLOW_REQUEST_MS:
        level = logging.WARNING
    else:
        level = logging.INFO

    logger.log(
        level,
        "Request completed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


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
