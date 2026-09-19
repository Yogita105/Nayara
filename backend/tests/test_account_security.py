"""Password change and signing out of every device."""
import uuid

import pytest
import requests


PASSWORD = "OriginalPassword123!"
NEW_PASSWORD = "ReplacementPassword456!"


@pytest.fixture
def account(base_url, mongo_db):
    """A signed-in account, removed afterwards."""
    email = f"account-test-{uuid.uuid4().hex}@example.com"
    mobile = f"9{uuid.uuid4().int % 10**9:09d}"
    client = requests.Session()
    registration = client.post(
        f"{base_url}/api/auth/register",
        json={
            "name": "Account Test",
            "email": email,
            "mobile": mobile,
            "password": PASSWORD,
        },
    )
    assert registration.status_code == 201
    client.headers.update({"X-CSRF-Token": registration.json()["csrf_token"]})

    yield {"client": client, "email": email, "password": PASSWORD}

    user = mongo_db.users.find_one({"email": email})
    if user:
        mongo_db.user_sessions.delete_many({"user_id": user["user_id"]})
        mongo_db.carts.delete_many({"user_id": user["user_id"]})
        mongo_db.users.delete_one({"user_id": user["user_id"]})
    mongo_db.rate_limits.delete_many({})


def sign_in(base_url, email, password):
    client = requests.Session()
    response = client.post(
        f"{base_url}/api/auth/login",
        json={"identifier": email, "password": password},
    )
    if response.status_code == 200:
        client.headers.update({"X-CSRF-Token": response.json()["csrf_token"]})
    return client, response


class TestProfileDetails:
    def test_name_and_mobile_can_be_updated(self, base_url, account):
        new_mobile = f"9{uuid.uuid4().int % 10**9:09d}"
        response = account["client"].put(
            f"{base_url}/api/auth/profile",
            json={"name": "Renamed Shopper", "mobile": new_mobile},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Renamed Shopper"
        assert response.json()["mobile"] == f"+91{new_mobile}"

    def test_the_change_is_visible_afterwards(self, base_url, account):
        new_mobile = f"9{uuid.uuid4().int % 10**9:09d}"
        account["client"].put(
            f"{base_url}/api/auth/profile",
            json={"name": "Renamed Shopper", "mobile": new_mobile},
        )

        me = account["client"].get(f"{base_url}/api/auth/me").json()
        assert me["name"] == "Renamed Shopper"
        assert me["mobile"] == f"+91{new_mobile}"

    def test_an_account_missing_a_mobile_can_add_one(
        self, base_url, account, mongo_db
    ):
        # Older accounts predate mobile numbers, so the field may be absent.
        mongo_db.users.update_one(
            {"email": account["email"]}, {"$unset": {"mobile": ""}}
        )
        assert account["client"].get(f"{base_url}/api/auth/me").json()["mobile"] is None

        new_mobile = f"9{uuid.uuid4().int % 10**9:09d}"
        response = account["client"].put(
            f"{base_url}/api/auth/profile",
            json={"name": "Account Test", "mobile": new_mobile},
        )

        assert response.status_code == 200
        assert response.json()["mobile"] == f"+91{new_mobile}"

    def test_the_email_is_left_alone(self, base_url, account):
        account["client"].put(
            f"{base_url}/api/auth/profile",
            json={
                "name": "Renamed Shopper",
                "mobile": f"9{uuid.uuid4().int % 10**9:09d}",
                "email": "someone.else@example.com",
            },
        )

        me = account["client"].get(f"{base_url}/api/auth/me").json()
        assert me["email"] == account["email"]

    def test_a_mobile_in_use_elsewhere_is_refused(
        self, base_url, account, mongo_db
    ):
        taken = f"9{uuid.uuid4().int % 10**9:09d}"
        other_email = f"account-test-{uuid.uuid4().hex}@example.com"
        requests.post(
            f"{base_url}/api/auth/register",
            json={
                "name": "Other Shopper",
                "email": other_email,
                "mobile": taken,
                "password": PASSWORD,
            },
        )

        response = account["client"].put(
            f"{base_url}/api/auth/profile",
            json={"name": "Account Test", "mobile": taken},
        )
        assert response.status_code == 409

        other = mongo_db.users.find_one({"email": other_email}, {"user_id": 1})
        if other:
            mongo_db.user_sessions.delete_many({"user_id": other["user_id"]})
            mongo_db.users.delete_one({"user_id": other["user_id"]})

    @pytest.mark.parametrize("mobile", ["12345", "1234567890", "not-a-number"])
    def test_an_invalid_mobile_is_refused(self, base_url, account, mobile):
        response = account["client"].put(
            f"{base_url}/api/auth/profile",
            json={"name": "Account Test", "mobile": mobile},
        )

        assert response.status_code == 422

    def test_a_blank_name_is_refused(self, base_url, account):
        response = account["client"].put(
            f"{base_url}/api/auth/profile",
            json={"name": "  ", "mobile": f"9{uuid.uuid4().int % 10**9:09d}"},
        )

        assert response.status_code == 422

    def test_signed_out_callers_are_refused(self, base_url, anon_client):
        response = anon_client.put(
            f"{base_url}/api/auth/profile",
            json={"name": "Nobody", "mobile": "9876500011"},
        )

        assert response.status_code == 401


class TestChangePassword:
    def test_the_new_password_replaces_the_old_one(self, base_url, account):
        response = account["client"].post(
            f"{base_url}/api/auth/password",
            json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        )
        assert response.status_code == 200

        _, refused = sign_in(base_url, account["email"], PASSWORD)
        assert refused.status_code == 401

        _, accepted = sign_in(base_url, account["email"], NEW_PASSWORD)
        assert accepted.status_code == 200

    def test_a_wrong_current_password_is_refused(self, base_url, account):
        response = account["client"].post(
            f"{base_url}/api/auth/password",
            json={"current_password": "NotMyPassword1!", "new_password": NEW_PASSWORD},
        )

        assert response.status_code == 403
        _, still_valid = sign_in(base_url, account["email"], PASSWORD)
        assert still_valid.status_code == 200

    def test_reusing_the_same_password_is_refused(self, base_url, account):
        response = account["client"].post(
            f"{base_url}/api/auth/password",
            json={"current_password": PASSWORD, "new_password": PASSWORD},
        )

        assert response.status_code == 422

    def test_a_short_password_is_refused(self, base_url, account):
        response = account["client"].post(
            f"{base_url}/api/auth/password",
            json={"current_password": PASSWORD, "new_password": "short"},
        )

        assert response.status_code == 422

    def test_signed_out_callers_cannot_change_a_password(self, base_url, anon_client):
        response = anon_client.post(
            f"{base_url}/api/auth/password",
            json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        )

        assert response.status_code == 401


class TestOtherSessionsEnd:
    def test_a_password_change_logs_out_other_devices(self, base_url, account):
        other, response = sign_in(base_url, account["email"], PASSWORD)
        assert response.status_code == 200
        assert other.get(f"{base_url}/api/auth/me").status_code == 200

        changed = account["client"].post(
            f"{base_url}/api/auth/password",
            json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        )
        assert changed.status_code == 200
        assert changed.json()["other_sessions_ended"] >= 1

        # The other device is cut off, while this one stays signed in.
        assert other.get(f"{base_url}/api/auth/me").status_code == 401
        assert account["client"].get(f"{base_url}/api/auth/me").status_code == 200


class TestSignOutEverywhere:
    def test_every_session_ends(self, base_url, account, mongo_db):
        other, _ = sign_in(base_url, account["email"], PASSWORD)

        response = account["client"].post(f"{base_url}/api/auth/logout-all")
        assert response.status_code == 200
        assert response.json()["sessions_ended"] >= 2

        assert other.get(f"{base_url}/api/auth/me").status_code == 401
        assert account["client"].get(f"{base_url}/api/auth/me").status_code == 401

        user = mongo_db.users.find_one({"email": account["email"]}, {"user_id": 1})
        assert mongo_db.user_sessions.count_documents(
            {"user_id": user["user_id"]}
        ) == 0

    def test_the_account_can_sign_in_again(self, base_url, account):
        account["client"].post(f"{base_url}/api/auth/logout-all")

        _, response = sign_in(base_url, account["email"], PASSWORD)
        assert response.status_code == 200

    def test_signed_out_callers_are_refused(self, base_url, anon_client):
        assert anon_client.post(
            f"{base_url}/api/auth/logout-all"
        ).status_code == 401
