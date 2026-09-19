import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient


load_dotenv()
BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://nayara-marketplace.preview.emergentagent.com",
).rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def mongo_db():
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


TEST_EMAIL_PATTERN = r"^(auth-test-|lockout-|test\.test-user-)"


def _return_reserved_stock(mongo_db, owner):
    """Give back the stock held by orders that are about to be deleted.

    Placing an order decrements product stock, so deleting test orders without
    this would slowly drain the real catalogue on every run.
    """
    for order in mongo_db.orders.find(owner, {"items": 1, "stock_released": 1}):
        if order.get("stock_released"):
            continue
        for item in order.get("items", []):
            mongo_db.products.update_one(
                {"product_id": item["product_id"]},
                {"$inc": {"stock": item["quantity"]}},
            )


def _remove_user_data(mongo_db, user_ids):
    owner = {"user_id": {"$in": list(user_ids)}}
    _return_reserved_stock(mongo_db, owner)
    mongo_db.users.delete_many(owner)
    mongo_db.user_sessions.delete_many(owner)
    mongo_db.carts.delete_many(owner)
    mongo_db.wishlists.delete_many(owner)
    mongo_db.orders.delete_many(owner)


def _purge_test_artifacts(mongo_db):
    """Remove records created by the suite.

    Individual fixtures clean up after themselves, but an interrupted run can
    still leave accounts behind, so this runs as a safety net.
    """
    mongo_db.rate_limits.delete_many({})
    mongo_db.order_claims.delete_many({})
    mongo_db.contacts.delete_many({"name": "TEST_ctc", "email": "t@e.com"})

    leftovers = [
        user["user_id"]
        for user in mongo_db.users.find(
            {"email": {"$regex": TEST_EMAIL_PATTERN}}, {"user_id": 1}
        )
    ]
    if leftovers:
        _remove_user_data(mongo_db, leftovers)


@pytest.fixture(scope="session", autouse=True)
def clean_test_artifacts(mongo_db):
    """Keep the database free of leftovers before and after a run."""
    _purge_test_artifacts(mongo_db)
    yield
    _purge_test_artifacts(mongo_db)


def _mk_session(mongo_db, is_admin=False):
    user_id = f"test-user-{uuid.uuid4().hex[:10]}"
    token = f"test_session_{uuid.uuid4().hex}"
    email = f"test.{user_id}@example.com"
    mongo_db.users.insert_one({
        "user_id": user_id,
        "email": email,
        "name": "Test User",
        "picture": "",
        "is_admin": is_admin,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    mongo_db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token_hash": hashlib.sha256(token.encode("utf-8")).hexdigest(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return user_id, token, email


@pytest.fixture(scope="session")
def user_session(mongo_db):
    user_id, token, email = _mk_session(mongo_db, False)
    yield {"user_id": user_id, "token": token, "email": email}
    _remove_user_data(mongo_db, [user_id])


@pytest.fixture(scope="session")
def admin_session(mongo_db):
    user_id, token, email = _mk_session(mongo_db, True)
    yield {"user_id": user_id, "token": token, "email": email}
    _remove_user_data(mongo_db, [user_id])


@pytest.fixture
def user_client(user_session):
    client = requests.Session()
    client.headers.update({
        "Authorization": "Bearer " + user_session["token"],
        "Content-Type": "application/json",
    })
    return client


@pytest.fixture
def admin_client(admin_session):
    client = requests.Session()
    client.headers.update({
        "Authorization": "Bearer " + admin_session["token"],
        "Content-Type": "application/json",
    })
    return client


@pytest.fixture
def anon_client():
    client = requests.Session()
    client.headers.update({"Content-Type": "application/json"})
    return client
