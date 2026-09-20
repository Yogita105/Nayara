"""Every error should reach a client in the same shape."""

import uuid
import pytest
import requests


class TestValidationErrors:
    def test_the_detail_is_always_readable_text(self, base_url, anon_client):
        response = anon_client.post(
            f"{base_url}/api/auth/register",
            json={"name": "A B", "mobile": "9876500009", "password": "short"},
        )

        assert response.status_code == 422
        assert isinstance(response.json()["detail"], str)
        assert response.json()["detail"]

    def test_the_failing_field_is_named(self, base_url, anon_client):
        response = anon_client.post(
            f"{base_url}/api/auth/register",
            json={"name": "A B", "mobile": "9876500009", "password": "short"},
        )

        assert "password" in response.json()["detail"].lower()
        assert response.json()["errors"][0]["field"] == "password"

    def test_a_missing_field_reads_as_required(self, base_url, anon_client):
        response = anon_client.post(
            f"{base_url}/api/auth/register",
            json={"mobile": "9876500009", "password": "GoodPassword1!"},
        )

        assert "required" in response.json()["detail"].lower()

    def test_submitted_values_are_never_echoed(self, base_url, anon_client):
        """A rejected sign-up must not send the password back.

        The password has to be one the request actually fails on. A valid one
        would be accepted, and a successful response never echoes it, so the
        check would pass without testing anything.
        """
        secret = "short1"
        response = anon_client.post(
            f"{base_url}/api/auth/register",
            json={"name": "A B", "mobile": "9876500009", "password": secret},
        )

        assert response.status_code == 422, "the sign-up should have been refused"
        assert secret not in response.text
        assert "input" not in response.text

    def test_nested_fields_are_named(self, base_url, user_client, mongo_db):
        product = mongo_db.products.find_one({}, {"product_id": 1})
        response = user_client.post(
            f"{base_url}/api/orders",
            json={
                "items": [{"product_id": product["product_id"], "quantity": 1}],
                "address": {
                    "full_name": "Test Buyer",
                    "phone": "9999900001",
                    "line1": "12 Market Road",
                    "city": "Mumbai",
                    "state": "MH",
                    "pincode": "12",
                },
                "payment_method": "cod",
            },
        )

        assert response.status_code == 422
        assert "pincode" in response.json()["detail"].lower()


class TestOtherErrors:
    def test_not_found_uses_the_same_shape(self, base_url, anon_client):
        response = anon_client.get(f"{base_url}/api/products/does-not-exist")

        assert response.status_code == 404
        assert isinstance(response.json()["detail"], str)

    def test_unauthorised_uses_the_same_shape(self, base_url, anon_client):
        response = anon_client.get(f"{base_url}/api/orders")

        assert response.status_code == 401
        assert isinstance(response.json()["detail"], str)

    def test_forbidden_uses_the_same_shape(self, base_url, user_client):
        response = user_client.get(f"{base_url}/api/admin/users")

        assert response.status_code == 403
        assert isinstance(response.json()["detail"], str)

    def test_errors_carry_the_request_id(self, base_url, anon_client):
        response = anon_client.get(f"{base_url}/api/orders")

        assert response.json()["request_id"]
        assert response.json()["request_id"] == response.headers["X-Request-ID"]

    def test_rate_limit_headers_survive(self, base_url, mongo_db):
        """Retry-After must still reach the client through the handler."""
        mongo_db.rate_limits.delete_many({})
        email = "rate-shape@example.com"
        for _ in range(6):
            response = requests.post(
                f"{base_url}/api/auth/login",
                json={"identifier": email, "password": "WrongPassword1!"},
            )
        assert response.status_code == 429
        assert response.headers["Retry-After"]
        assert isinstance(response.json()["detail"], str)
        mongo_db.rate_limits.delete_many({})


class TestRefusalsNameTheirField:
    """A form can only mark the offending box if the API says which it is.

    These refusals are raised by hand rather than by request validation, so
    without naming the field they arrive as a sentence with nothing to attach
    it to, and a screen reader announces a problem without saying where.
    """

    @pytest.fixture
    def claimable_mobile(self, mongo_db):
        """A number to register, cleared away however the test ends.

        Cleaning up at the end of the test body only happens when the test
        passes, so a failing run leaves an account behind. This account has no
        email address, which is what the suite's safety net matches on, so
        nothing else would ever collect it.
        """
        mobile = f"9{uuid.uuid4().int % 10**9:09d}"

        yield mobile

        stored = f"+91{mobile}"
        for user in mongo_db.users.find({"mobile": stored}, {"user_id": 1}):
            mongo_db.user_sessions.delete_many({"user_id": user["user_id"]})
            mongo_db.audit_events.delete_many({"actor_id": user["user_id"]})
            mongo_db.carts.delete_many({"user_id": user["user_id"]})
        mongo_db.users.delete_many({"mobile": stored})
        mongo_db.rate_limits.delete_many({})

    def test_an_unusable_mobile_number_names_the_field(self, base_url, anon_client):
        response = anon_client.post(
            f"{base_url}/api/auth/register",
            json={"name": "A B", "mobile": "1234567890", "password": "GoodPassword1!"},
        )

        assert response.status_code == 422
        assert response.json()["errors"][0]["field"] == "mobile"

    def test_a_short_name_names_the_field(self, base_url, anon_client):
        response = anon_client.post(
            f"{base_url}/api/auth/register",
            json={"name": "A", "mobile": "9876512345", "password": "GoodPassword1!"},
        )

        assert response.status_code == 422
        assert response.json()["errors"][0]["field"] == "name"

    def test_a_taken_mobile_number_names_the_field(self, base_url, anon_client, claimable_mobile):
        payload = {
            "name": "First Owner",
            "mobile": claimable_mobile,
            "password": "GoodPassword1!",
        }
        first = anon_client.post(f"{base_url}/api/auth/register", json=payload)
        assert first.status_code == 201

        # A fresh caller: the first registration left a session cookie on that
        # client, which CSRF protection would refuse before the API ever
        # reached the duplicate check.
        second = requests.post(f"{base_url}/api/auth/register", json=payload)

        assert second.status_code == 409
        assert second.json()["errors"][0]["field"] == "mobile"

    def test_the_message_is_still_a_readable_sentence(self, base_url, anon_client):
        response = anon_client.post(
            f"{base_url}/api/auth/register",
            json={"name": "A B", "mobile": "1234567890", "password": "GoodPassword1!"},
        )

        body = response.json()
        assert isinstance(body["detail"], str)
        assert body["detail"] == body["errors"][0]["message"]
