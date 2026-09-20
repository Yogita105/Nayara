"""Every error should reach a client in the same shape."""
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
