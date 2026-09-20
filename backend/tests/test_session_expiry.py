"""Session lifetime: an old, revoked or orphaned token must stop working.

A session token is a bearer credential that lives for a week, so the checks
that retire one are the difference between a stolen laptop being a nuisance
and being an open door. The TTL index eventually removes expired records, but
it runs on its own schedule, so the request path has to reject a stale token
on its own.
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests


def _hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@pytest.fixture
def session_factory(mongo_db):
    """Build accounts whose session expiry is set deliberately."""
    created = []

    def _create(expires_at, is_admin=False):
        user_id = f"test-user-{uuid.uuid4().hex[:10]}"
        token = f"test_session_{uuid.uuid4().hex}"
        now = datetime.now(timezone.utc)
        mongo_db.users.insert_one(
            {
                "user_id": user_id,
                "mobile": f"+91{uuid.uuid4().int % 10**9:09d}",
                "email": f"test.{user_id}@example.com",
                "name": "Expiry Test",
                "picture": "",
                "is_admin": is_admin,
                "created_at": now.isoformat(),
            }
        )
        mongo_db.user_sessions.insert_one(
            {
                "user_id": user_id,
                "session_token_hash": _hash(token),
                "expires_at": expires_at,
                "created_at": now.isoformat(),
            }
        )
        created.append(user_id)
        return {"token": token, "user_id": user_id}

    yield _create

    owner = {"user_id": {"$in": created}}
    mongo_db.user_sessions.delete_many(owner)
    mongo_db.users.delete_many(owner)


def whoami(base_url, token):
    return requests.get(
        f"{base_url}/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )


PAST = datetime.now(timezone.utc) - timedelta(minutes=1)
FUTURE = datetime.now(timezone.utc) + timedelta(days=1)


class TestExpiredSessions:
    def test_an_expired_session_is_refused(self, base_url, session_factory):
        session = session_factory(PAST.isoformat())

        response = whoami(base_url, session["token"])

        assert response.status_code == 401

    def test_a_live_session_is_accepted(self, base_url, session_factory):
        session = session_factory(FUTURE.isoformat())

        response = whoami(base_url, session["token"])

        assert response.status_code == 200
        assert response.json()["user_id"] == session["user_id"]

    def test_the_reason_is_reported(self, base_url, session_factory):
        session = session_factory(PAST.isoformat())

        body = whoami(base_url, session["token"]).json()

        assert "expired" in body["detail"].lower()

    def test_a_session_expiring_while_in_use_stops_working(
        self, base_url, session_factory, mongo_db
    ):
        """Someone already signed in is turned away once their week is up."""
        session = session_factory(FUTURE.isoformat())
        assert whoami(base_url, session["token"]).status_code == 200

        mongo_db.user_sessions.update_one(
            {"session_token_hash": _hash(session["token"])},
            {"$set": {"expires_at": PAST.isoformat()}},
        )

        assert whoami(base_url, session["token"]).status_code == 401


class TestStoredTimestampForms:
    """Expiry is written as an ISO string in places and as a BSON date in
    others. A date without a zone must not be read as local time, or a token
    would outlive its week wherever the server is not on UTC."""

    def test_a_past_date_without_a_zone_is_refused(self, base_url, session_factory):
        session = session_factory(PAST.replace(tzinfo=None))

        assert whoami(base_url, session["token"]).status_code == 401

    def test_a_future_date_without_a_zone_is_accepted(self, base_url, session_factory):
        session = session_factory(FUTURE.replace(tzinfo=None))

        assert whoami(base_url, session["token"]).status_code == 200

    def test_a_past_string_with_a_zone_is_refused(self, base_url, session_factory):
        session = session_factory(PAST.isoformat())

        assert whoami(base_url, session["token"]).status_code == 401


class TestRevokedSessions:
    def test_an_unknown_token_is_refused(self, base_url):
        assert whoami(base_url, f"test_session_{uuid.uuid4().hex}").status_code == 401

    def test_a_deleted_session_is_refused(self, base_url, session_factory, mongo_db):
        session = session_factory(FUTURE.isoformat())
        assert whoami(base_url, session["token"]).status_code == 200

        mongo_db.user_sessions.delete_one({"session_token_hash": _hash(session["token"])})

        assert whoami(base_url, session["token"]).status_code == 401

    def test_a_session_without_its_account_is_refused(self, base_url, session_factory, mongo_db):
        """A closed account must not keep working through an open session."""
        session = session_factory(FUTURE.isoformat())
        assert whoami(base_url, session["token"]).status_code == 200

        mongo_db.users.delete_one({"user_id": session["user_id"]})

        assert whoami(base_url, session["token"]).status_code == 401


class TestExpiryAppliesToPrivilegedRoutes:
    def test_an_expired_administrator_is_refused(self, base_url, session_factory):
        """Refused for being signed out, not merely for lacking the role."""
        session = session_factory(PAST.isoformat(), is_admin=True)

        response = requests.get(
            f"{base_url}/api/admin/stats",
            headers={"Authorization": f"Bearer {session['token']}"},
        )

        assert response.status_code == 401

    def test_a_live_administrator_is_accepted(self, base_url, session_factory):
        session = session_factory(FUTURE.isoformat(), is_admin=True)

        response = requests.get(
            f"{base_url}/api/admin/stats",
            headers={"Authorization": f"Bearer {session['token']}"},
        )

        assert response.status_code == 200


class TestIssuedSessionsExpire:
    def test_signing_in_creates_a_session_that_expires(self, base_url, mongo_db):
        """A record with no expiry would never be retired, by the request path
        or by the TTL index."""
        mobile = f"9{uuid.uuid4().int % 10**9:09d}"
        email = f"auth-test-{uuid.uuid4().hex}@example.com"
        registration = requests.post(
            f"{base_url}/api/auth/register",
            json={
                "name": "Expiry Check",
                "email": email,
                "mobile": mobile,
                "password": "ExpiryCheck123!",
            },
        )
        assert registration.status_code == 201

        user = mongo_db.users.find_one({"mobile": f"+91{mobile}"})
        session = mongo_db.user_sessions.find_one({"user_id": user["user_id"]})

        assert session is not None
        expires_at = session["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        assert expires_at > datetime.now(timezone.utc)

        mongo_db.user_sessions.delete_many({"user_id": user["user_id"]})
        mongo_db.users.delete_one({"user_id": user["user_id"]})
        mongo_db.rate_limits.delete_many({})
