"""The record of who did what, and what it must never contain.

An audit log holding passwords or session tokens would be worth stealing in
its own right, and would hand over the very accounts it exists to protect.
"""

import asyncio
import uuid

import pytest
import requests

from app import audit
from app.audit import MAX_TEXT_LENGTH, REDACTED, scrub

PASSWORD = "AuditTestPassword1!"


@pytest.fixture
def audited_account(base_url, mongo_db):
    """An account whose audit trail is inspected, removed afterwards."""
    mobile = f"9{uuid.uuid4().int % 10**9:09d}"
    email = f"auth-test-{uuid.uuid4().hex}@example.com"
    client = requests.Session()
    registration = client.post(
        f"{base_url}/api/auth/register",
        json={
            "name": "Audit Test",
            "email": email,
            "mobile": mobile,
            "password": PASSWORD,
        },
    )
    assert registration.status_code == 201
    client.headers.update({"X-CSRF-Token": registration.json()["csrf_token"]})
    user = mongo_db.users.find_one({"mobile": f"+91{mobile}"})

    yield {
        "client": client,
        "user_id": user["user_id"],
        "mobile": mobile,
        "email": email,
    }

    mongo_db.audit_events.delete_many({"actor_id": user["user_id"]})
    mongo_db.user_sessions.delete_many({"user_id": user["user_id"]})
    mongo_db.users.delete_one({"user_id": user["user_id"]})
    mongo_db.rate_limits.delete_many({})


def events_for(mongo_db, user_id, event=None):
    query = {"actor_id": user_id}
    if event:
        query["event"] = event
    return list(mongo_db.audit_events.find(query, {"_id": 0}))


class TestScrubbing:
    """Field names are the reliable signal; guessing from values is not."""

    @pytest.mark.parametrize(
        "name",
        [
            "password",
            "new_password",
            "current_password",
            "passphrase",
            "token",
            "session_token",
            "csrf_token",
            "password_hash",
            "api_key",
            "apiKey",
            "authorization",
            "secret",
            "client_secret",
            "cookie",
        ],
    )
    def test_anything_credential_shaped_is_replaced(self, name):
        assert scrub({name: "the actual value"})[name] == REDACTED

    def test_ordinary_fields_are_kept(self):
        cleaned = scrub({"order_id": "ord_1", "status": "shipped", "count": 3})

        assert cleaned == {"order_id": "ord_1", "status": "shipped", "count": 3}

    def test_a_nested_credential_is_replaced(self):
        cleaned = scrub({"outer": {"inner": {"password": "hunter2"}}})

        assert "hunter2" not in str(cleaned)

    def test_deep_nesting_is_cut_off(self):
        """A runaway structure must not be copied into the record wholesale."""
        cleaned = scrub({"a": {"b": {"c": {"d": {"e": "far too deep"}}}}})

        assert "far too deep" not in str(cleaned)

    def test_long_text_is_shortened(self):
        cleaned = scrub({"note": "x" * (MAX_TEXT_LENGTH + 500)})

        assert len(cleaned["note"]) == MAX_TEXT_LENGTH

    def test_a_long_list_is_shortened(self):
        cleaned = scrub({"items": list(range(500))})

        assert len(cleaned["items"]) <= 20

    def test_unusual_values_become_text(self):
        cleaned = scrub({"when": object()})

        assert isinstance(cleaned["when"], str)


class TestSignIn:
    def test_creating_an_account_is_recorded(self, mongo_db, audited_account):
        events = events_for(mongo_db, audited_account["user_id"], "auth.account_created")

        assert len(events) == 1

    def test_signing_in_is_recorded(self, base_url, mongo_db, audited_account):
        requests.post(
            f"{base_url}/api/auth/login",
            json={"identifier": audited_account["mobile"], "password": PASSWORD},
        )

        events = events_for(mongo_db, audited_account["user_id"], "auth.signed_in")
        assert len(events) == 1

    def test_a_wrong_password_is_recorded_against_the_account(
        self, base_url, mongo_db, audited_account
    ):
        """A run of these before a success is the thing worth noticing."""
        requests.post(
            f"{base_url}/api/auth/login",
            json={"identifier": audited_account["mobile"], "password": "WrongOne1!"},
        )

        events = events_for(mongo_db, audited_account["user_id"], "auth.sign_in_failed")
        assert len(events) == 1
        assert events[0]["details"]["reason"] == "wrong_password"

    def test_the_attempted_password_is_not_stored(self, base_url, mongo_db, audited_account):
        secret = "ThisWasTypedByMistake1!"
        requests.post(
            f"{base_url}/api/auth/login",
            json={"identifier": audited_account["mobile"], "password": secret},
        )

        events = events_for(mongo_db, audited_account["user_id"], "auth.sign_in_failed")
        assert secret not in str(events)

    def test_an_unknown_account_records_no_identifier(self, base_url, mongo_db):
        """Someone may type their password into the identifier box.

        Recording what was typed would store that password as plainly as if it
        had been asked for, so only the failure itself is noted.
        """
        typed = f"MistypedSecret{uuid.uuid4().hex}"
        requests.post(
            f"{base_url}/api/auth/login",
            json={"identifier": typed, "password": "AnythingAtAll1!"},
        )

        recent = list(mongo_db.audit_events.find({"event": "auth.sign_in_failed"}))
        assert typed not in str(recent)


class TestAccountChanges:
    def test_changing_a_password_is_recorded(self, base_url, mongo_db, audited_account):
        response = audited_account["client"].post(
            f"{base_url}/api/auth/password",
            json={"current_password": PASSWORD, "new_password": "ReplacedPassword2!"},
        )
        assert response.status_code == 200

        events = events_for(mongo_db, audited_account["user_id"], "auth.password_changed")
        assert len(events) == 1

    def test_neither_password_is_stored(self, base_url, mongo_db, audited_account):
        audited_account["client"].post(
            f"{base_url}/api/auth/password",
            json={"current_password": PASSWORD, "new_password": "ReplacedPassword2!"},
        )

        stored = str(events_for(mongo_db, audited_account["user_id"]))
        assert PASSWORD not in stored
        assert "ReplacedPassword2!" not in stored

    def test_a_refused_password_change_is_recorded(self, base_url, mongo_db, audited_account):
        audited_account["client"].post(
            f"{base_url}/api/auth/password",
            json={"current_password": "NotTheRightOne1!", "new_password": "Another2!"},
        )

        events = events_for(mongo_db, audited_account["user_id"], "auth.password_change_refused")
        assert len(events) == 1

    def test_signing_out_everywhere_is_recorded(self, base_url, mongo_db, audited_account):
        audited_account["client"].post(f"{base_url}/api/auth/logout-all")

        events = events_for(mongo_db, audited_account["user_id"], "auth.signed_out_everywhere")
        assert len(events) == 1

    def test_updating_details_records_what_changed_not_the_values(
        self, base_url, mongo_db, audited_account
    ):
        new_email = f"auth-test-{uuid.uuid4().hex}@example.com"
        audited_account["client"].put(
            f"{base_url}/api/auth/profile",
            json={"name": "Renamed Person", "email": new_email},
        )

        events = events_for(mongo_db, audited_account["user_id"], "auth.profile_updated")
        assert len(events) == 1
        assert events[0]["details"]["email_changed"] is True
        assert new_email not in str(events)


class TestAdministratorActions:
    def test_a_product_change_names_who_made_it(
        self, base_url, admin_session, admin_client, mongo_db
    ):
        suffix = uuid.uuid4().hex[:8]
        created = admin_client.post(
            f"{base_url}/api/products",
            json={
                "name": f"Audit Product {suffix}",
                "slug": f"audit-product-{suffix}",
                "category": "home-care",
                "variants": [{"label": "Standard", "price": 100.0, "mrp": 120.0, "stock": 5}],
            },
        )
        assert created.status_code == 200
        product_id = created.json()["product_id"]

        admin_client.delete(f"{base_url}/api/products/{product_id}")

        events = events_for(mongo_db, admin_session["user_id"])
        names = [event["event"] for event in events]
        assert "admin.product_created" in names
        assert "admin.product_deleted" in names

        mongo_db.audit_events.delete_many({"actor_id": admin_session["user_id"]})
        mongo_db.products.delete_many({"product_id": product_id})


class TestRecordShape:
    def test_what_is_written_is_scrubbed_first(self, mongo_db):
        """The unit tests above prove scrub works; this proves it is used.

        Without this, removing the call from the write path would leave every
        test passing while a future caller quietly stored a credential.
        """
        actor = f"test-user-audit-{uuid.uuid4().hex[:8]}"
        asyncio.run(
            audit.record(
                "test.scrub_is_applied",
                actor_id=actor,
                password="hunter2",
                session_token="tok_abcdef",
                order_id="ord_kept",
            )
        )

        stored = mongo_db.audit_events.find_one({"actor_id": actor}, {"_id": 0})
        mongo_db.audit_events.delete_many({"actor_id": actor})

        assert stored is not None, "the event was not written"
        assert stored["details"]["password"] == REDACTED
        assert stored["details"]["session_token"] == REDACTED
        assert stored["details"]["order_id"] == "ord_kept"
        assert "hunter2" not in str(stored)
        assert "tok_abcdef" not in str(stored)

    def test_an_event_carries_when_and_for_how_long(self, mongo_db, audited_account):
        event = events_for(mongo_db, audited_account["user_id"], "auth.account_created")[0]

        assert event["at"] is not None
        assert event["expires_at"] > event["at"], "records must expire eventually"

    def test_an_event_can_be_traced_back_to_its_request(self, mongo_db, audited_account):
        event = events_for(mongo_db, audited_account["user_id"], "auth.account_created")[0]

        assert event["request_id"]
