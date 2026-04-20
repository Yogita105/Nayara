import os
import time
import uuid
import pytest
import requests
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://nayara-marketplace.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

@pytest.fixture(scope="session")
def base_url():
    return BASE_URL

@pytest.fixture(scope="session")
def mongo_db():
    c = MongoClient(MONGO_URL)
    return c[DB_NAME]

def _mk_session(mongo_db, is_admin=False):
    uid = f"test-user-{uuid.uuid4().hex[:10]}"
    token = f"test_session_{uuid.uuid4().hex}"
    email = f"test.{uid}@example.com"
    mongo_db.users.insert_one({
        "user_id": uid, "email": email, "name": "Test User",
        "picture": "", "is_admin": is_admin,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    mongo_db.user_sessions.insert_one({
        "user_id": uid, "session_token": token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return uid, token, email

@pytest.fixture(scope="session")
def user_session(mongo_db):
    uid, token, email = _mk_session(mongo_db, False)
    yield {"user_id": uid, "token": token, "email": email}
    mongo_db.users.delete_one({"user_id": uid})
    mongo_db.user_sessions.delete_one({"session_token": token})
    mongo_db.carts.delete_one({"user_id": uid})
    mongo_db.wishlists.delete_one({"user_id": uid})
    mongo_db.orders.delete_many({"user_id": uid})

@pytest.fixture(scope="session")
def admin_session(mongo_db):
    uid, token, email = _mk_session(mongo_db, True)
    yield {"user_id": uid, "token": token, "email": email}
    mongo_db.users.delete_one({"user_id": uid})
    mongo_db.user_sessions.delete_one({"session_token": token})

@pytest.fixture
def user_client(user_session):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {user_session['token']}", "Content-Type": "application/json"})
    return s

@pytest.fixture
def admin_client(admin_session):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {admin_session['token']}", "Content-Type": "application/json"})
    return s

@pytest.fixture
def anon_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s
