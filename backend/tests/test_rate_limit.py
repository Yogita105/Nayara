"""Rate limiting: pure helpers plus live account-lockout behaviour."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests

from app.rate_limit import (
    LOGIN_IDENTIFIER_RULE,
    build_key,
    seconds_until,
)


class TestRateLimitHelpers:
    def test_key_is_scoped_and_case_insensitive(self):
        assert build_key("login", "User@Example.com") == "login:user@example.com"

    def test_key_separates_scopes(self):
        assert build_key("login", "a@b.com") != build_key("register", "a@b.com")

    def test_retry_after_is_rounded_up(self):
        now = datetime.now(timezone.utc)
        assert seconds_until(now + timedelta(seconds=30.2), now) == 31

    def test_retry_after_is_never_below_one_second(self):
        now = datetime.now(timezone.utc)
        assert seconds_until(now - timedelta(seconds=5), now) == 1

    def test_naive_expiry_is_treated_as_utc(self):
        now = datetime.now(timezone.utc)
        naive_expiry = (now + timedelta(seconds=60)).replace(tzinfo=None)
        assert 1 <= seconds_until(naive_expiry, now) <= 60


class TestLoginLockout:
    @pytest.fixture(autouse=True)
    def clean_rate_limits(self, mongo_db):
        """Keep each lockout test independent of earlier attempts."""
        mongo_db.rate_limits.delete_many({})

    @pytest.fixture
    def locked_account(self, base_url, mongo_db):
        """Create an account and exhaust its failed sign-in allowance."""
        email = f"lockout-{uuid.uuid4().hex}@example.com"
        mobile = f"9{uuid.uuid4().int % 10**9:09d}"
        password = "LockoutTest123!"
        registration = requests.post(
            f"{base_url}/api/auth/register",
            json={
                "name": "Lockout Test",
                "email": email,
                "mobile": mobile,
                "password": password,
            },
        )
        assert registration.status_code == 201

        yield {"email": email, "password": password}

        user = mongo_db.users.find_one({"email": email})
        if user:
            mongo_db.user_sessions.delete_many({"user_id": user["user_id"]})
            mongo_db.users.delete_one({"user_id": user["user_id"]})
        mongo_db.rate_limits.delete_one({"_id": f"login-identifier:{email}"})

    def test_repeated_failures_lock_the_account(self, base_url, locked_account):
        email = locked_account["email"]

        for attempt in range(LOGIN_IDENTIFIER_RULE.limit):
            response = requests.post(
                f"{base_url}/api/auth/login",
                json={"identifier": email, "password": "WrongPassword123!"},
            )
            assert response.status_code == 401, f"attempt {attempt + 1}"

        blocked = requests.post(
            f"{base_url}/api/auth/login",
            json={"identifier": email, "password": "WrongPassword123!"},
        )
        assert blocked.status_code == 429
        assert int(blocked.headers["Retry-After"]) > 0

    def test_lockout_also_blocks_the_correct_password(self, base_url, locked_account):
        email = locked_account["email"]

        for _ in range(LOGIN_IDENTIFIER_RULE.limit):
            requests.post(
                f"{base_url}/api/auth/login",
                json={"identifier": email, "password": "WrongPassword123!"},
            )

        blocked = requests.post(
            f"{base_url}/api/auth/login",
            json={"identifier": email, "password": locked_account["password"]},
        )
        assert blocked.status_code == 429

    def test_successful_login_clears_failed_attempts(self, base_url, locked_account, mongo_db):
        email = locked_account["email"]

        for _ in range(LOGIN_IDENTIFIER_RULE.limit - 1):
            requests.post(
                f"{base_url}/api/auth/login",
                json={"identifier": email, "password": "WrongPassword123!"},
            )

        success = requests.post(
            f"{base_url}/api/auth/login",
            json={"identifier": email, "password": locked_account["password"]},
        )
        assert success.status_code == 200
        assert mongo_db.rate_limits.find_one({"_id": f"login-identifier:{email}"}) is None
