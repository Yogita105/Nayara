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
        load_settings(
            {
                **PRODUCTION_ENVIRONMENT,
                "SECRET_KEY": DEVELOPMENT_SECRET_KEY,
            }
        )


def test_cors_wildcard_is_rejected():
    with pytest.raises(RuntimeError, match="explicit origins"):
        load_settings(
            {
                **BASE_ENVIRONMENT,
                "CORS_ORIGINS": "*",
            }
        )


def test_invalid_boolean_is_rejected():
    with pytest.raises(RuntimeError, match="COOKIE_SECURE must be true or false"):
        parse_boolean("sometimes", "COOKIE_SECURE")


class TestAutomaticSeeding:
    """Starter products must never appear in a live catalogue on their own."""

    @pytest.mark.parametrize("environment", ["development", "test"])
    def test_seeding_is_on_where_it_is_convenient(self, environment):
        settings = load_settings({**BASE_ENVIRONMENT, "ENVIRONMENT": environment})

        assert settings.auto_seed_products is True

    def test_seeding_is_off_in_production(self):
        assert load_settings(PRODUCTION_ENVIRONMENT).auto_seed_products is False

    def test_seeding_is_off_in_staging(self):
        settings = load_settings(
            {
                **BASE_ENVIRONMENT,
                "ENVIRONMENT": "staging",
                "CORS_ORIGINS": "https://staging.example.com",
            }
        )

        assert settings.auto_seed_products is False

    def test_the_default_can_be_overridden(self):
        settings = load_settings(
            {
                **BASE_ENVIRONMENT,
                "AUTO_SEED_PRODUCTS": "false",
            }
        )

        assert settings.auto_seed_products is False

    def test_an_unreadable_value_is_rejected(self):
        with pytest.raises(RuntimeError, match="AUTO_SEED_PRODUCTS"):
            load_settings({**BASE_ENVIRONMENT, "AUTO_SEED_PRODUCTS": "maybe"})


class TestApiDocumentationExposure:
    """The schema lists the admin API, so the public must not be handed it."""

    @pytest.mark.parametrize("environment", ["development", "test"])
    def test_documentation_is_available_while_building(self, environment):
        settings = load_settings({**BASE_ENVIRONMENT, "ENVIRONMENT": environment})

        assert settings.api_docs_enabled is True

    def test_documentation_is_withheld_in_production(self):
        assert load_settings(PRODUCTION_ENVIRONMENT).api_docs_enabled is False

    def test_documentation_is_withheld_in_staging(self):
        settings = load_settings(
            {
                **BASE_ENVIRONMENT,
                "ENVIRONMENT": "staging",
                "CORS_ORIGINS": "https://staging.example.com",
            }
        )

        assert settings.api_docs_enabled is False

    def test_the_default_can_be_overridden(self):
        settings = load_settings(
            {
                **PRODUCTION_ENVIRONMENT,
                "API_DOCS_ENABLED": "true",
            }
        )

        assert settings.api_docs_enabled is True

    def test_an_unreadable_value_is_rejected(self):
        with pytest.raises(RuntimeError, match="API_DOCS_ENABLED"):
            load_settings({**BASE_ENVIRONMENT, "API_DOCS_ENABLED": "maybe"})


class TestLogSettings:
    def test_production_logs_as_json(self):
        assert load_settings(PRODUCTION_ENVIRONMENT).log_json is True

    def test_development_logs_as_text(self):
        assert load_settings(BASE_ENVIRONMENT).log_json is False

    def test_an_unknown_log_level_is_rejected(self):
        with pytest.raises(RuntimeError, match="LOG_LEVEL must be one of"):
            load_settings({**BASE_ENVIRONMENT, "LOG_LEVEL": "CHATTY"})
