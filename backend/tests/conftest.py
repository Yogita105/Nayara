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


@pytest.fixture(scope="session", autouse=True)
def reset_rate_limits(mongo_db):
    """Start each run with empty rate-limit windows."""
    mongo_db.rate_limits.delete_many({})
    yield
    mongo_db.rate_limits.delete_many({})


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
    mongo_db.users.delete_one({"user_id": user_id})
    mongo_db.user_sessions.delete_one({
        "session_token_hash": hashlib.sha256(token.encode("utf-8")).hexdigest()
    })
    mongo_db.carts.delete_one({"user_id": user_id})
    mongo_db.wishlists.delete_one({"user_id": user_id})
    mongo_db.orders.delete_many({"user_id": user_id})


@pytest.fixture(scope="session")
def admin_session(mongo_db):
    user_id, token, email = _mk_session(mongo_db, True)
    yield {"user_id": user_id, "token": token, "email": email}
    mongo_db.users.delete_one({"user_id": user_id})
    mongo_db.user_sessions.delete_one({
        "session_token_hash": hashlib.sha256(token.encode("utf-8")).hexdigest()
    })


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
