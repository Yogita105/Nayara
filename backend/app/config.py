import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping, Optional, Tuple

import cloudinary
from dotenv import load_dotenv

from .utils import normalize_indian_mobile

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

LOCAL_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)
VALID_ENVIRONMENTS = {"development", "test", "staging", "production"}
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
DEVELOPMENT_SECRET_KEY = "insecure-development-secret-key"
MINIMUM_SECRET_KEY_LENGTH = 32


@dataclass(frozen=True)
class Settings:
    environment: str
    mongo_url: str
    db_name: str
    secret_key: str
    admin_mobiles: frozenset[str]
    cookie_secure: bool
    cookie_samesite: Literal["lax", "none"]
    cors_origins: Tuple[str, ...]
    rate_limit_enabled: bool
    trust_proxy_headers: bool
    log_level: str
    log_json: bool
    auto_seed_products: bool
    api_docs_enabled: bool
    mongo_max_pool_size: int
    mongo_timeout_ms: int
    mongo_socket_timeout_ms: int
    max_request_body_bytes: int
    max_upload_bytes: int
    audit_retention_days: int
    session_days: int
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str


def parse_boolean(value: str, variable_name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise RuntimeError(f"{variable_name} must be true or false")


def parse_positive_int(value: str, variable_name: str) -> int:
    try:
        parsed = int(str(value).strip())
    except ValueError as error:
        raise RuntimeError(f"{variable_name} must be a whole number") from error
    if parsed < 1:
        raise RuntimeError(f"{variable_name} must be greater than zero")
    return parsed


def _normalize_admin_mobile(entry: str) -> str:
    """Accept an administrator number in any of the usual written forms."""
    candidate = entry.strip()
    if not candidate:
        return ""
    try:
        return normalize_indian_mobile(candidate)
    except ValueError as error:
        raise RuntimeError(f"ADMIN_MOBILES contains an invalid number: {entry}") from error


def load_settings(environment: Optional[Mapping[str, str]] = None) -> Settings:
    values = os.environ if environment is None else environment
    runtime_environment = values.get("ENVIRONMENT", "development").strip().lower()
    if runtime_environment not in VALID_ENVIRONMENTS:
        allowed = ", ".join(sorted(VALID_ENVIRONMENTS))
        raise RuntimeError(f"ENVIRONMENT must be one of: {allowed}")

    mongo_url = values.get("MONGO_URL", "").strip()
    db_name = values.get("DB_NAME", "").strip()
    if not mongo_url:
        raise RuntimeError("MONGO_URL is required")
    if not db_name:
        raise RuntimeError("DB_NAME is required")

    configured_origins = tuple(
        origin.strip().rstrip("/")
        for origin in values.get("CORS_ORIGINS", "").split(",")
        if origin.strip()
    )
    if runtime_environment == "production" and not configured_origins:
        raise RuntimeError("CORS_ORIGINS is required in production")
    cors_origins = configured_origins or LOCAL_CORS_ORIGINS
    if "*" in cors_origins:
        raise RuntimeError("CORS_ORIGINS must contain explicit origins, not '*'")

    cookie_value = values.get("COOKIE_SECURE")
    cookie_secure = (
        runtime_environment == "production"
        if cookie_value is None
        else parse_boolean(cookie_value, "COOKIE_SECURE")
    )
    if runtime_environment == "production" and not cookie_secure:
        raise RuntimeError("COOKIE_SECURE must be true in production")

    secret_key = values.get("SECRET_KEY", "").strip()
    if runtime_environment == "production":
        if not secret_key:
            raise RuntimeError("SECRET_KEY is required in production")
        if secret_key == DEVELOPMENT_SECRET_KEY:
            raise RuntimeError("SECRET_KEY must not use the development default")
        if len(secret_key) < MINIMUM_SECRET_KEY_LENGTH:
            raise RuntimeError(
                f"SECRET_KEY must be at least {MINIMUM_SECRET_KEY_LENGTH} characters"
            )
    secret_key = secret_key or DEVELOPMENT_SECRET_KEY

    log_level = values.get("LOG_LEVEL", "INFO").strip().upper()
    if log_level not in VALID_LOG_LEVELS:
        allowed = ", ".join(sorted(VALID_LOG_LEVELS))
        raise RuntimeError(f"LOG_LEVEL must be one of: {allowed}")

    # Machine-readable logs suit a log aggregator; plain text suits a terminal.
    log_json_value = values.get("LOG_JSON")
    log_json = (
        runtime_environment in {"production", "staging"}
        if log_json_value is None
        else parse_boolean(log_json_value, "LOG_JSON")
    )

    # Starter products are a convenience for local work. Writing them
    # automatically elsewhere could refill a catalogue that was emptied by
    # mistake, hiding the incident behind plausible-looking data.
    auto_seed_value = values.get("AUTO_SEED_PRODUCTS")
    auto_seed_products = (
        runtime_environment in {"development", "test"}
        if auto_seed_value is None
        else parse_boolean(auto_seed_value, "AUTO_SEED_PRODUCTS")
    )

    # The interactive documentation publishes every route and request shape,
    # including the admin API. That is useful while building, but on an
    # internet-facing deployment it hands out a map of the attack surface, so
    # it stays off anywhere the public can reach.
    api_docs_value = values.get("API_DOCS_ENABLED")
    api_docs_enabled = (
        runtime_environment in {"development", "test"}
        if api_docs_value is None
        else parse_boolean(api_docs_value, "API_DOCS_ENABLED")
    )

    return Settings(
        environment=runtime_environment,
        mongo_url=mongo_url,
        db_name=db_name,
        secret_key=secret_key,
        admin_mobiles=frozenset(
            normalized
            for normalized in (
                _normalize_admin_mobile(entry)
                for entry in values.get("ADMIN_MOBILES", "").split(",")
            )
            if normalized
        ),
        cookie_secure=cookie_secure,
        cookie_samesite="none" if cookie_secure else "lax",
        cors_origins=cors_origins,
        rate_limit_enabled=parse_boolean(
            values.get("RATE_LIMIT_ENABLED", "true"),
            "RATE_LIMIT_ENABLED",
        ),
        trust_proxy_headers=parse_boolean(
            values.get("TRUST_PROXY_HEADERS", "false"),
            "TRUST_PROXY_HEADERS",
        ),
        log_level=log_level,
        log_json=log_json,
        auto_seed_products=auto_seed_products,
        api_docs_enabled=api_docs_enabled,
        mongo_max_pool_size=parse_positive_int(
            values.get("MONGO_MAX_POOL_SIZE", "20"), "MONGO_MAX_POOL_SIZE"
        ),
        mongo_timeout_ms=parse_positive_int(
            values.get("MONGO_TIMEOUT_MS", "10000"), "MONGO_TIMEOUT_MS"
        ),
        mongo_socket_timeout_ms=parse_positive_int(
            values.get("MONGO_SOCKET_TIMEOUT_MS", "20000"),
            "MONGO_SOCKET_TIMEOUT_MS",
        ),
        # A request is held in memory while it is handled, and the machine
        # serving the shop has far less memory than a determined caller can
        # send. These are generous for real orders and admin edits.
        max_request_body_bytes=parse_positive_int(
            values.get("MAX_REQUEST_BODY_BYTES", str(1024 * 1024)),
            "MAX_REQUEST_BODY_BYTES",
        ),
        max_upload_bytes=parse_positive_int(
            values.get("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)),
            "MAX_UPLOAD_BYTES",
        ),
        # Long enough to investigate something noticed late, short enough that
        # the shop is not holding records of who signed in indefinitely.
        audit_retention_days=parse_positive_int(
            values.get("AUDIT_RETENTION_DAYS", "180"), "AUDIT_RETENTION_DAYS"
        ),
        session_days=7,
        cloudinary_cloud_name=values.get("CLOUDINARY_CLOUD_NAME", ""),
        cloudinary_api_key=values.get("CLOUDINARY_API_KEY", ""),
        cloudinary_api_secret=values.get("CLOUDINARY_API_SECRET", ""),
    )


settings = load_settings()

MONGO_URL = settings.mongo_url
DB_NAME = settings.db_name
ENVIRONMENT = settings.environment
SECRET_KEY = settings.secret_key
ADMIN_MOBILES = settings.admin_mobiles
COOKIE_SECURE = settings.cookie_secure
COOKIE_SAMESITE = settings.cookie_samesite
CORS_ORIGINS = settings.cors_origins
RATE_LIMIT_ENABLED = settings.rate_limit_enabled
TRUST_PROXY_HEADERS = settings.trust_proxy_headers
LOG_LEVEL = settings.log_level
LOG_JSON = settings.log_json
AUTO_SEED_PRODUCTS = settings.auto_seed_products
API_DOCS_ENABLED = settings.api_docs_enabled
MONGO_MAX_POOL_SIZE = settings.mongo_max_pool_size
MONGO_TIMEOUT_MS = settings.mongo_timeout_ms
MONGO_SOCKET_TIMEOUT_MS = settings.mongo_socket_timeout_ms
MAX_REQUEST_BODY_BYTES = settings.max_request_body_bytes
MAX_UPLOAD_BYTES = settings.max_upload_bytes
AUDIT_RETENTION_DAYS = settings.audit_retention_days
SESSION_DAYS = settings.session_days

cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
    secure=True,
)
