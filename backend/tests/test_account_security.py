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

    yield {
        "client": client,
        "email": email,
        "mobile": mobile,
        "password": PASSWORD,
    }

    user = mongo_db.users.find_one({"mobile": f"+91{mobile}"})
    if user:
        mongo_db.user_sessions.delete_many({"user_id": user["user_id"]})
        mongo_db.carts.delete_many({"user_id": user["user_id"]})
        mongo_db.users.delete_one({"user_id": user["user_id"]})
    mongo_db.rate_limits.delete_many({})


def sign_in(base_url, identifier, password):
    client = requests.Session()
    response = client.post(
        f"{base_url}/api/auth/login",
        json={"identifier": identifier, "password": password},
    )
    if response.status_code == 200:
        client.headers.update({"X-CSRF-Token": response.json()["csrf_token"]})
    return client, response


class TestRegistrationIdentity:
    """The mobile number identifies an account; email is a bonus."""

    def test_an_account_can_be_created_without_an_email(self, base_url, mongo_db):
        mobile = f"9{uuid.uuid4().int % 10**9:09d}"
        response = requests.post(
            f"{base_url}/api/auth/register",
            json={"name": "No Email", "mobile": mobile, "password": PASSWORD},
        )

        assert response.status_code == 201
        assert response.json()["user"]["mobile"] == f"+91{mobile}"
        assert response.json()["user"]["email"] is None

        mongo_db.users.delete_one({"mobile": f"+91{mobile}"})

    def test_several_accounts_can_have_no_email(self, base_url, mongo_db):
        created = []
        for _ in range(2):
            mobile = f"9{uuid.uuid4().int % 10**9:09d}"
            response = requests.post(
                f"{base_url}/api/auth/register",
                json={"name": "No Email", "mobile": mobile, "password": PASSWORD},
            )
            assert response.status_code == 201
            created.append(f"+91{mobile}")

        assert len(set(created)) == 2
        mongo_db.users.delete_many({"mobile": {"$in": created}})

    def test_signing_in_by_mobile_works(self, base_url, account):
        _, response = sign_in(base_url, account["mobile"], PASSWORD)
        assert response.status_code == 200

    def test_a_duplicate_mobile_is_refused(self, base_url, account):
        response = requests.post(
            f"{base_url}/api/auth/register",
            json={
                "name": "Copycat",
                "mobile": account["mobile"],
                "password": PASSWORD,
            },
        )

        assert response.status_code == 409


class TestProfileDetails:
    def test_the_name_can_be_updated(self, base_url, account):
        response = account["client"].put(
            f"{base_url}/api/auth/profile",
            json={"name": "Renamed Shopper", "email": account["email"]},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Renamed Shopper"

    def test_an_email_can_be_added_later(self, base_url, mongo_db):
        mobile = f"9{uuid.uuid4().int % 10**9:09d}"
        client = requests.Session()
        registration = client.post(
            f"{base_url}/api/auth/register",
            json={"name": "No Email", "mobile": mobile, "password": PASSWORD},
        )
        client.headers.update({"X-CSRF-Token": registration.json()["csrf_token"]})

        added = f"later-{uuid.uuid4().hex}@example.com"
        response = client.put(
            f"{base_url}/api/auth/profile",
            json={"name": "No Email", "email": added},
        )

        assert response.status_code == 200
        assert response.json()["email"] == added

        mongo_db.users.delete_one({"mobile": f"+91{mobile}"})

    def test_an_email_can_be_removed(self, base_url, account):
        response = account["client"].put(
            f"{base_url}/api/auth/profile",
            json={"name": "Account Test", "email": None},
        )

        assert response.status_code == 200
        assert response.json()["email"] is None

    def test_the_mobile_number_is_left_alone(self, base_url, account):
        account["client"].put(
            f"{base_url}/api/auth/profile",
            json={
                "name": "Account Test",
                "email": account["email"],
                "mobile": "9998887777",
            },
        )

        me = account["client"].get(f"{base_url}/api/auth/me").json()
        assert me["mobile"] == f"+91{account['mobile']}"

    def test_an_email_in_use_elsewhere_is_refused(self, base_url, account, mongo_db):
        taken = f"account-test-{uuid.uuid4().hex}@example.com"
        other_mobile = f"9{uuid.uuid4().int % 10**9:09d}"
        requests.post(
            f"{base_url}/api/auth/register",
            json={
                "name": "Other Shopper",
                "email": taken,
                "mobile": other_mobile,
                "password": PASSWORD,
            },
        )

        response = account["client"].put(
            f"{base_url}/api/auth/profile",
            json={"name": "Account Test", "email": taken},
        )
        assert response.status_code == 409

        mongo_db.users.delete_one({"mobile": f"+91{other_mobile}"})

    def test_an_invalid_email_is_refused(self, base_url, account):
        response = account["client"].put(
            f"{base_url}/api/auth/profile",
            json={"name": "Account Test", "email": "not-an-email"},
        )

        assert response.status_code == 422

    def test_a_blank_name_is_refused(self, base_url, account):
        response = account["client"].put(
            f"{base_url}/api/auth/profile",
            json={"name": "  ", "email": account["email"]},
        )

        assert response.status_code == 422

    def test_signed_out_callers_are_refused(self, base_url, anon_client):
        response = anon_client.put(
            f"{base_url}/api/auth/profile",
            json={"name": "Nobody"},
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
