import pytest

from app.config import (
    DEVELOPMENT_SECRET_KEY,
    LOCAL_CORS_ORIGINS,
    load_settings,
    parse_boolean,
)


BASE_ENVIRONMENT = {
    "MONGO_URL": "mongodb://localhost:27017",
    "DB_NAME": "nayara_test",
}
PRODUCTION_SECRET_KEY = "a" * 48
PRODUCTION_ENVIRONMENT = {
    **BASE_ENVIRONMENT,
    "ENVIRONMENT": "production",
    "CORS_ORIGINS": "https://shop.example.com",
    "SECRET_KEY": PRODUCTION_SECRET_KEY,
}


def test_development_defaults_are_local_and_http_compatible():
    settings = load_settings(BASE_ENVIRONMENT)

    assert settings.environment == "development"
    assert settings.cookie_secure is False
    assert settings.cookie_samesite == "lax"
    assert settings.cors_origins == LOCAL_CORS_ORIGINS
    assert settings.secret_key == DEVELOPMENT_SECRET_KEY


def test_production_requires_explicit_cors_origins():
    with pytest.raises(RuntimeError, match="CORS_ORIGINS is required"):
        load_settings({**BASE_ENVIRONMENT, "ENVIRONMENT": "production"})


def test_production_enables_secure_cookies_by_default():
    settings = load_settings(PRODUCTION_ENVIRONMENT)

    assert settings.cookie_secure is True
    assert settings.cookie_samesite == "none"
    assert settings.cors_origins == ("https://shop.example.com",)
    assert settings.secret_key == PRODUCTION_SECRET_KEY


def test_production_rejects_insecure_cookies():
    with pytest.raises(RuntimeError, match="COOKIE_SECURE must be true"):
        load_settings({**PRODUCTION_ENVIRONMENT, "COOKIE_SECURE": "false"})


def test_production_requires_a_secret_key():
    environment = {key: value for key, value in PRODUCTION_ENVIRONMENT.items()}
    environment.pop("SECRET_KEY")

    with pytest.raises(RuntimeError, match="SECRET_KEY is required"):
        load_settings(environment)


def test_production_rejects_a_short_secret_key():
    with pytest.raises(RuntimeError, match="at least 32 characters"):
        load_settings({**PRODUCTION_ENVIRONMENT, "SECRET_KEY": "too-short"})


def test_production_rejects_the_development_secret_key():
    with pytest.raises(RuntimeError, match="development default"):
        load_settings({
            **PRODUCTION_ENVIRONMENT,
            "SECRET_KEY": DEVELOPMENT_SECRET_KEY,
        })


def test_cors_wildcard_is_rejected():
    with pytest.raises(RuntimeError, match="explicit origins"):
        load_settings({
            **BASE_ENVIRONMENT,
            "CORS_ORIGINS": "*",
        })


def test_invalid_boolean_is_rejected():
    with pytest.raises(RuntimeError, match="COOKIE_SECURE must be true or false"):
        parse_boolean("sometimes", "COOKIE_SECURE")
