"""Behaviour when two requests race.

Checking a condition and then acting on it is safe in a single-threaded test
and unsafe in production, where a second request can slip between the two
steps. These tests put real requests in flight together, so the guarantees
rest on the unique index and the conditional update rather than on timing.
"""

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests


ADDRESS = {
    "full_name": "Race Tester",
    "phone": "9999900002",
    "line1": "9 Contention Street",
    "line2": "",
    "city": "Mumbai",
    "state": "MH",
    "pincode": "400001",
}

ATTEMPTS = 5


def run_together(call, count):
    """Fire the same call several times at once and collect the responses."""
    with ThreadPoolExecutor(max_workers=count) as pool:
        return [future.result() for future in [pool.submit(call, i) for i in range(count)]]


@pytest.fixture
def clear_rate_limits(mongo_db):
    """Several attempts at once would otherwise count against the throttle."""
    mongo_db.rate_limits.delete_many({})
    yield
    mongo_db.rate_limits.delete_many({})


@pytest.fixture
def registered_accounts(mongo_db):
    """Remove whatever the race actually managed to create."""
    identifiers = {}
    yield identifiers
    if identifiers.get("mobile"):
        users = list(mongo_db.users.find({"mobile": identifiers["mobile"]}, {"user_id": 1}))
        ids = [user["user_id"] for user in users]
        mongo_db.user_sessions.delete_many({"user_id": {"$in": ids}})
        mongo_db.users.delete_many({"mobile": identifiers["mobile"]})
    if identifiers.get("email"):
        users = list(mongo_db.users.find({"email": identifiers["email"]}, {"user_id": 1}))
        ids = [user["user_id"] for user in users]
        mongo_db.user_sessions.delete_many({"user_id": {"$in": ids}})
        mongo_db.users.delete_many({"email": identifiers["email"]})


class TestConcurrentRegistration:
    """An identity must belong to exactly one account, however close the
    requests arrive. The pre-flight lookup cannot promise that on its own."""

    def test_one_mobile_number_yields_one_account(
        self, base_url, mongo_db, clear_rate_limits, registered_accounts
    ):
        mobile = f"9{uuid.uuid4().int % 10**9:09d}"
        registered_accounts["mobile"] = f"+91{mobile}"

        responses = run_together(
            lambda index: requests.post(
                f"{base_url}/api/auth/register",
                json={
                    "name": f"Racer {index}",
                    "mobile": mobile,
                    "password": "RacePassword123!",
                },
            ),
            ATTEMPTS,
        )

        codes = sorted(response.status_code for response in responses)
        assert codes.count(201) == 1, f"expected one winner, got {codes}"
        assert all(code == 409 for code in codes if code != 201), codes
        assert mongo_db.users.count_documents({"mobile": f"+91{mobile}"}) == 1

    def test_one_email_address_yields_one_account(
        self, base_url, mongo_db, clear_rate_limits, registered_accounts
    ):
        email = f"auth-test-{uuid.uuid4().hex}@example.com"
        registered_accounts["email"] = email

        responses = run_together(
            lambda index: requests.post(
                f"{base_url}/api/auth/register",
                json={
                    "name": f"Racer {index}",
                    "email": email,
                    # A distinct mobile each time, so only the address collides.
                    "mobile": f"9{uuid.uuid4().int % 10**9:09d}",
                    "password": "RacePassword123!",
                },
            ),
            ATTEMPTS,
        )

        codes = sorted(response.status_code for response in responses)
        assert codes.count(201) == 1, f"expected one winner, got {codes}"
        assert mongo_db.users.count_documents({"email": email}) == 1

    def test_no_account_is_left_without_a_password(
        self, base_url, mongo_db, clear_rate_limits, registered_accounts
    ):
        """A loser must not leave a half-built record that could be signed into."""
        mobile = f"9{uuid.uuid4().int % 10**9:09d}"
        registered_accounts["mobile"] = f"+91{mobile}"

        run_together(
            lambda index: requests.post(
                f"{base_url}/api/auth/register",
                json={
                    "name": f"Racer {index}",
                    "mobile": mobile,
                    "password": "RacePassword123!",
                },
            ),
            ATTEMPTS,
        )

        for user in mongo_db.users.find({"mobile": f"+91{mobile}"}):
            assert user.get("password_hash"), "an account was stored without a password"


@pytest.fixture
def scarce_product(mongo_db):
    """A product with a known, small stock level, removed afterwards."""
    created = []

    def _create(stock):
        suffix = uuid.uuid4().hex[:8]
        product = {
            "product_id": f"prod_test_{suffix}",
            "name": f"Race Test {suffix}",
            "slug": f"race-test-{suffix}",
            "category": "home-care",
            "description": "Temporary product used by the concurrency tests.",
            "short_description": "Temporary product.",
            "price": 100.0,
            "mrp": 120.0,
            "image": "",
            "images": [],
            "stock": stock,
            "rating": 4.5,
            "reviews_count": 0,
            "badges": [],
            "featured": False,
            "created_at": "2026-01-01T00:00:00+00:00",
        }
        mongo_db.products.insert_one(dict(product))
        created.append(product["product_id"])
        return product["product_id"]

    yield _create

    mongo_db.orders.delete_many({"items.product_id": {"$in": created}})
    mongo_db.products.delete_many({"product_id": {"$in": created}})


def order_in_parallel(base_url, token, product_id, attempts):
    def place(_index):
        # A session per thread: one is not meant to be shared across them.
        client = requests.Session()
        client.headers.update({"Authorization": f"Bearer {token}"})
        return client.post(
            f"{base_url}/api/orders",
            json={
                "items": [{"product_id": product_id, "quantity": 1}],
                "address": ADDRESS,
                "payment_method": "cod",
            },
        )

    return run_together(place, attempts)


class TestConcurrentOrders:
    """Stock is reserved with a conditional update, so simultaneous shoppers
    cannot both be promised the same unit."""

    def test_the_last_unit_goes_to_exactly_one_shopper(
        self, base_url, user_session, mongo_db, scarce_product
    ):
        product_id = scarce_product(1)

        responses = order_in_parallel(
            base_url, user_session["token"], product_id, ATTEMPTS
        )

        codes = sorted(response.status_code for response in responses)
        assert codes.count(200) == 1, f"expected one sale, got {codes}"
        assert all(code == 409 for code in codes if code != 200), codes
        assert mongo_db.products.find_one({"product_id": product_id})["stock"] == 0

    def test_stock_is_never_oversold(
        self, base_url, user_session, mongo_db, scarce_product
    ):
        """More shoppers than units: the shop sells what it has and no more."""
        available = 3
        product_id = scarce_product(available)

        responses = order_in_parallel(base_url, user_session["token"], product_id, 8)

        sold = sum(1 for response in responses if response.status_code == 200)
        remaining = mongo_db.products.find_one({"product_id": product_id})["stock"]

        assert sold == available, f"sold {sold} of {available}"
        assert remaining == 0
        assert remaining >= 0, "stock went negative"

    def test_every_successful_order_is_recorded_once(
        self, base_url, user_session, mongo_db, scarce_product
    ):
        product_id = scarce_product(2)

        responses = order_in_parallel(base_url, user_session["token"], product_id, 6)

        succeeded = [r.json()["order_id"] for r in responses if r.status_code == 200]
        stored = mongo_db.orders.count_documents(
            {"items.product_id": product_id}
        )

        assert len(set(succeeded)) == len(succeeded), "an order id was reused"
        assert stored == len(succeeded)
