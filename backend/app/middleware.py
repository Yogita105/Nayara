import logging
import time

from fastapi import Request
from fastapi.responses import JSONResponse

from .config import MAX_REQUEST_BODY_BYTES, MAX_UPLOAD_BYTES
from .errors import build_response
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

# Image uploads are necessarily larger than any other request, so that one
# route is allowed its own ceiling. The slack covers the multipart boundaries
# and part headers wrapped around the file itself.
UPLOAD_PATH = "/api/admin/upload"
MULTIPART_OVERHEAD_BYTES = 16 * 1024

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
        return build_response(403, "Invalid or missing CSRF token", [])

    return await call_next(request)


def limit_for(path: str) -> int:
    if path == UPLOAD_PATH:
        return MAX_UPLOAD_BYTES + MULTIPART_OVERHEAD_BYTES
    return MAX_REQUEST_BODY_BYTES


async def limit_request_size(request: Request, call_next):
    """Turn away an oversized request before its body is read.

    Reading first and measuring afterwards offers no protection: the memory
    has already been spent by the time the size is known. This refuses on the
    declared length instead, so nothing large is ever held.

    A sender that omits the length and streams the body in chunks cannot be
    judged here. The upload route counts those bytes as they arrive, and the
    proxy in front of the API is the other place to cap them.
    """
    if request.method in SAFE_METHODS:
        return await call_next(request)

    declared = request.headers.get("content-length")
    if declared is not None:
        try:
            length = int(declared)
        except ValueError:
            return build_response(400, "Content-Length is not a number", [])
        if length < 0:
            return build_response(400, "Content-Length is not a number", [])

        limit = limit_for(request.url.path)
        if length > limit:
            logger.warning(
                "Request body refused as too large",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "declared_bytes": length,
                    "limit_bytes": limit,
                },
            )
            return build_response(
                413,
                f"Request body is too large. The limit is {limit // 1024} KB.",
                [],
            )

    return await call_next(request)
