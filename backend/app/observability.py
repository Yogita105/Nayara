"""Structured logging and per-request correlation.

Every log line carries the id of the request that produced it, so a single
customer report can be traced through the whole service. Request bodies and
headers are never logged, because they carry passwords and session tokens.
"""

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional


REQUEST_ID_HEADER = "X-Request-ID"
MAX_REQUEST_ID_LENGTH = 64

_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

# Fields LogRecord always defines; anything else was supplied by the caller.
_STANDARD_FIELDS = frozenset(logging.LogRecord("", 0, "", 0, "", None, None).__dict__)
_STANDARD_FIELDS = _STANDARD_FIELDS | {"message", "asctime", "taskName"}


def new_request_id() -> str:
    return uuid.uuid4().hex


def clean_request_id(value: Optional[str]) -> str:
    """Accept a caller's id only when it is short and printable."""
    if not value:
        return new_request_id()
    candidate = value.strip()[:MAX_REQUEST_ID_LENGTH]
    if not candidate or not candidate.isprintable():
        return new_request_id()
    return candidate


def set_request_id(value: str) -> None:
    _request_id.set(value)


def get_request_id() -> Optional[str]:
    return _request_id.get()


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = getattr(record, "request_id", None)
        if request_id:
            payload["request_id"] = request_id
        for key, value in record.__dict__.items():
            if key not in _STANDARD_FIELDS and key != "request_id":
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class TextFormatter(logging.Formatter):
    """Readable output for local development."""

    def format(self, record: logging.LogRecord) -> str:
        request_id = getattr(record, "request_id", None)
        prefix = f"[{request_id[:8]}] " if request_id else ""
        base = (
            f"{self.formatTime(record)} {record.levelname:<8} "
            f"{record.name} {prefix}{record.getMessage()}"
        )
        extras = " ".join(
            f"{key}={value}"
            for key, value in record.__dict__.items()
            if key not in _STANDARD_FIELDS and key != "request_id"
        )
        if extras:
            base = f"{base} {extras}"
        if record.exc_info:
            base = f"{base}\n{self.formatException(record.exc_info)}"
        return base


def configure_logging(level: str, as_json: bool) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if as_json else TextFormatter())
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    # Our own middleware records richer access logs, so the plain uvicorn
    # equivalent would only duplicate every line.
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = False
    for noisy in ("pymongo", "motor"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
