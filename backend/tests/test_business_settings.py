"""The shop's own contact details, which an administrator can now change.

These were fixed in the code. Making them editable means a bad value is now
possible, so what matters is that the shop refuses to publish one, and that a
shop which has never opened the screen still tells customers how to get in
touch.
"""

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models import DEFAULT_BUSINESS, BusinessSettings  # noqa: E402

SETTINGS = "/api/settings/business"
ADMIN_SETTINGS = "/api/admin/settings/business"

FIELDS = {
    "name",
    "founder",
    "founder_title",
    "address_lines",
    "phone",
    "hours",
    "email",
    "wholesale_email",
}


def valid(**overrides):
    payload = DEFAULT_BUSINESS.model_dump()
    payload.update(overrides)
    return payload


@pytest.fixture
def restore_settings(mongo_db):
    """Put the settings back however the test leaves them."""
    before = mongo_db.settings.find_one({"key": "business"})
    yield
    if before:
        mongo_db.settings.replace_one({"key": "business"}, before, upsert=True)
    else:
        mongo_db.settings.delete_one({"key": "business"})


class TestReadingThem:
    def test_anyone_may_read_them(self, base_url, anon_client):
        """The footer is on every page, including for a stranger."""
        response = anon_client.get(f"{base_url}{SETTINGS}")

        assert response.status_code == 200
        assert set(response.json()) == FIELDS

    def test_an_unopened_shop_still_has_a_phone_number(
        self, base_url, anon_client, mongo_db, restore_settings
    ):
        """Nothing saved yet must not mean a blank footer."""
        mongo_db.settings.delete_one({"key": "business"})

        body = anon_client.get(f"{base_url}{SETTINGS}").json()

        assert body["phone"] == DEFAULT_BUSINESS.phone
        assert body["email"] == DEFAULT_BUSINESS.email

    def test_settings_that_cannot_be_understood_fall_back(
        self, base_url, anon_client, mongo_db, restore_settings
    ):
        """A half-written record should not take the footer down with it."""
        mongo_db.settings.replace_one(
            {"key": "business"},
            {"key": "business", "phone": "not a number"},
            upsert=True,
        )

        response = anon_client.get(f"{base_url}{SETTINGS}")

        assert response.status_code == 200
        assert response.json()["phone"] == DEFAULT_BUSINESS.phone

    def test_the_answer_may_be_cached_briefly(self, base_url, anon_client):
        """Every page asks for this, so it should not be a fresh request each
        time; but a corrected number should still reach customers today."""
        response = anon_client.get(f"{base_url}{SETTINGS}")

        assert "max-age" in response.headers.get("Cache-Control", "")


class TestChangingThem:
    def test_an_administrator_may_change_them(
        self, base_url, admin_client, anon_client, restore_settings
    ):
        response = admin_client.put(
            f"{base_url}{ADMIN_SETTINGS}", json=valid(phone="+91 90000 11111")
        )

        assert response.status_code == 200, response.text
        assert anon_client.get(f"{base_url}{SETTINGS}").json()["phone"] == "+91 90000 11111"

    def test_a_customer_may_not(self, base_url, user_client):
        response = user_client.put(f"{base_url}{ADMIN_SETTINGS}", json=valid())

        assert response.status_code == 403

    def test_a_stranger_may_not(self, base_url, anon_client):
        response = anon_client.put(f"{base_url}{ADMIN_SETTINGS}", json=valid())

        assert response.status_code == 401

    @pytest.mark.parametrize(
        "phone",
        ["", "12", "not a number", "+91 97808 44330 extension 4", "<script>x</script>"],
    )
    def test_an_unreachable_phone_number_is_refused(
        self, base_url, admin_client, restore_settings, phone
    ):
        """Publishing a number nobody can ring is worse than refusing to save."""
        response = admin_client.put(f"{base_url}{ADMIN_SETTINGS}", json=valid(phone=phone))

        assert response.status_code == 422

    @pytest.mark.parametrize("email", ["", "hello", "hello@", "@nayara.in", "a b@nayara.in"])
    def test_an_unusable_email_is_refused(self, base_url, admin_client, restore_settings, email):
        response = admin_client.put(f"{base_url}{ADMIN_SETTINGS}", json=valid(email=email))

        assert response.status_code == 422

    def test_an_address_with_nothing_in_it_is_refused(
        self, base_url, admin_client, restore_settings
    ):
        response = admin_client.put(
            f"{base_url}{ADMIN_SETTINGS}", json=valid(address_lines=["   ", ""])
        )

        assert response.status_code == 422

    def test_blank_address_lines_are_dropped(self, base_url, admin_client, restore_settings):
        response = admin_client.put(
            f"{base_url}{ADMIN_SETTINGS}",
            json=valid(address_lines=["Jaito", "   ", "Punjab"]),
        )

        assert response.status_code == 200
        assert response.json()["address_lines"] == ["Jaito", "Punjab"]

    def test_a_refused_change_leaves_the_old_details_showing(
        self, base_url, admin_client, anon_client, restore_settings
    ):
        """A rejected edit must not take the working number down with it."""
        admin_client.put(f"{base_url}{ADMIN_SETTINGS}", json=valid(phone="+91 90000 22222"))

        admin_client.put(f"{base_url}{ADMIN_SETTINGS}", json=valid(phone="nonsense"))

        assert anon_client.get(f"{base_url}{SETTINGS}").json()["phone"] == "+91 90000 22222"

    def test_the_change_is_recorded(
        self, base_url, admin_client, admin_session, mongo_db, restore_settings
    ):
        """A phone number quietly becoming someone else's is worth tracing."""
        mongo_db.audit_events.delete_many({"event": "admin.business_settings_updated"})

        admin_client.put(f"{base_url}{ADMIN_SETTINGS}", json=valid(phone="+91 90000 33333"))

        event = mongo_db.audit_events.find_one({"event": "admin.business_settings_updated"})
        assert event is not None
        assert event["actor_id"] == admin_session["user_id"]
        assert event["details"]["changed"] == ["phone"]

    def test_the_trail_does_not_copy_the_details_into_itself(
        self, base_url, admin_client, mongo_db, restore_settings
    ):
        """Naming the fields that moved is enough; repeating their contents
        would make the audit log a second address book."""
        mongo_db.audit_events.delete_many({"event": "admin.business_settings_updated"})

        admin_client.put(f"{base_url}{ADMIN_SETTINGS}", json=valid(phone="+91 90000 44444"))

        event = mongo_db.audit_events.find_one({"event": "admin.business_settings_updated"})
        assert "90000 44444" not in str(event)


class TestTheDefaults:
    def test_they_are_a_valid_set_of_settings(self):
        """They are what a shop falls back to, so they cannot be malformed."""
        assert BusinessSettings(**DEFAULT_BUSINESS.model_dump()) == DEFAULT_BUSINESS

    def test_they_carry_every_field_the_shop_shows(self):
        assert set(DEFAULT_BUSINESS.model_dump()) == FIELDS
