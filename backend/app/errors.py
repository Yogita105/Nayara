"""One shape for every error the API returns.

Validation failures used to come back as a list of objects that also echoed
what was submitted, including passwords. Clients could not rely on a single
shape, and the browser could not render the list at all.

Every error now returns:

    {"detail": "<a sentence a person can read>",
     "errors": [{"field": "password", "message": "..."}],
     "request_id": "..."}

`detail` is always a string. `errors` names the fields without repeating any
submitted value.
"""

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .observability import REQUEST_ID_HEADER, get_request_id


class FieldError(HTTPException):
    """A refusal that names the field responsible.

    A plain message tells someone that something is wrong; naming the field
    lets the form mark the box itself, which is the difference between a
    sighted guess and a screen reader announcing what to correct.
    """

    def __init__(self, status_code: int, field: str, detail: str):
        super().__init__(status_code=status_code, detail=detail)
        self.field = field


def field_name(location: tuple) -> str:
    """Turn a Pydantic location into something a person recognises."""
    parts = [str(part) for part in location if part not in ("body", "query", "path")]
    return ".".join(parts) if parts else "request"


def readable_label(name: str) -> str:
    return name.replace("_", " ").replace(".", " ").capitalize()


def describe(error: dict) -> str:
    name = field_name(error.get("loc", ()))
    if error.get("type") == "missing":
        return f"{readable_label(name)} is required"
    return f"{readable_label(name)}: {error.get('msg', 'is not valid')}"


def build_response(status_code: int, detail: str, errors: List[dict]) -> JSONResponse:
    body: Dict[str, Any] = {"detail": detail}
    if errors:
        body["errors"] = errors
    request_id = get_request_id()
    if request_id:
        body["request_id"] = request_id
    response = JSONResponse(status_code=status_code, content=body)
    if request_id:
        response.headers[REQUEST_ID_HEADER] = request_id
    return response


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_failed(request: Request, error: RequestValidationError):
        raw = error.errors()
        # `input` is deliberately dropped: it repeats what was submitted, which
        # for a sign-up form is the password.
        errors = [
            {"field": field_name(item.get("loc", ())), "message": item.get("msg", "")}
            for item in raw
        ]
        detail = describe(raw[0]) if raw else "The request could not be understood"
        return build_response(422, detail, errors)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, error: StarletteHTTPException):
        detail = error.detail
        if not isinstance(detail, str):
            detail = "Something went wrong"
        field: Optional[str] = getattr(error, "field", None)
        errors = [{"field": field, "message": detail}] if field else []
        response = build_response(error.status_code, detail, errors)
        # Preserve headers such as Retry-After from rate limiting.
        for key, value in (getattr(error, "headers", None) or {}).items():
            response.headers[key] = value
        return response

    @app.exception_handler(HTTPException)
    async def api_error(request: Request, error: HTTPException):
        return await http_error(request, error)
