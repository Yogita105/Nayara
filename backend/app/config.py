import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Tuple

import cloudinary
from dotenv import load_dotenv


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
    admin_emails: frozenset[str]
    cookie_secure: bool
    cookie_samesite: str
    cors_origins: Tuple[str, ...]
    rate_limit_enabled: bool
    trust_proxy_headers: bool
    log_level: str
    log_json: bool
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

    return Settings(
        environment=runtime_environment,
        mongo_url=mongo_url,
        db_name=db_name,
        secret_key=secret_key,
        admin_emails=frozenset(
            email.strip().lower()
            for email in values.get("ADMIN_EMAILS", "").split(",")
            if email.strip()
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
ADMIN_EMAILS = settings.admin_emails
COOKIE_SECURE = settings.cookie_secure
COOKIE_SAMESITE = settings.cookie_samesite
CORS_ORIGINS = settings.cors_origins
RATE_LIMIT_ENABLED = settings.rate_limit_enabled
TRUST_PROXY_HEADERS = settings.trust_proxy_headers
LOG_LEVEL = settings.log_level
LOG_JSON = settings.log_json
SESSION_DAYS = settings.session_days

cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
    secure=True,
)
