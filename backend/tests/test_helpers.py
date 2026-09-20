"""The small functions that decide who someone is and what they may do.

These are exercised indirectly by the endpoint tests, but only along the paths
those endpoints happen to take. A mistake in one of them is a security
mistake, so the edges are pinned down here: unusual ways of writing a mobile
number, passwords measured in bytes rather than characters, and tokens that
almost match.
"""

import asyncio
import re

import pytest
from fastapi import HTTPException

from app.config import _normalize_admin_mobile, parse_boolean, parse_positive_int
from app.security import (
    csrf_token_matches,
    derive_csrf_token,
    get_request_token,
    hash_password,
    hash_session_token,
    validate_password_bytes,
    verify_password,
)
from app.utils import normalize_indian_mobile, public_user, serialize_doc


class TestMobileNumbers:
    """People write their number in whatever form they are used to."""

    @pytest.mark.parametrize(
        "written",
        [
            "9876512345",
            "+919876512345",
            "919876512345",
            "09876512345",
            "98765 12345",
            "+91 98765 12345",
            "98765-12345",
            "(98765) 12345",
            "  9876512345  ",
        ],
    )
    def test_usual_forms_reach_the_same_number(self, written):
        assert normalize_indian_mobile(written) == "+919876512345"

    def test_normalising_twice_changes_nothing(self):
        once = normalize_indian_mobile("98765 12345")

        assert normalize_indian_mobile(once) == once

    @pytest.mark.parametrize("first", ["6", "7", "8", "9"])
    def test_every_indian_mobile_prefix_is_accepted(self, first):
        assert normalize_indian_mobile(f"{first}876512345") == f"+91{first}876512345"

    @pytest.mark.parametrize("first", ["0", "1", "2", "3", "4", "5"])
    def test_a_landline_style_prefix_is_refused(self, first):
        with pytest.raises(ValueError):
            normalize_indian_mobile(f"{first}876512345")

    @pytest.mark.parametrize(
        "written",
        [
            "",
            "   ",
            "98765",
            "98765123456",
            "abcdefghij",
            "9876512a45",
            "+1 415 555 0100",
            "+9198765123456",
        ],
    )
    def test_a_number_that_is_not_one_is_refused(self, written):
        with pytest.raises(ValueError):
            normalize_indian_mobile(written)

    def test_the_message_tells_someone_what_to_enter(self):
        with pytest.raises(ValueError, match="10-digit"):
            normalize_indian_mobile("12345")


class TestAdministratorNumbers:
    def test_an_administrator_is_recognised_however_it_is_written(self):
        assert _normalize_admin_mobile(" +91 98765 12345 ") == "+919876512345"

    def test_a_blank_entry_is_ignored(self):
        assert _normalize_admin_mobile("   ") == ""

    def test_an_invalid_entry_stops_startup(self):
        """A typo must not silently leave nobody as administrator."""
        with pytest.raises(RuntimeError, match="ADMIN_MOBILES"):
            _normalize_admin_mobile("not-a-number")


class TestSettingParsers:
    @pytest.mark.parametrize("value", ["true", "TRUE", " yes ", "1"])
    def test_affirmative_values(self, value):
        assert parse_boolean(value, "FLAG") is True

    @pytest.mark.parametrize("value", ["false", "FALSE", " no ", "0"])
    def test_negative_values(self, value):
        assert parse_boolean(value, "FLAG") is False

    def test_an_unreadable_boolean_names_the_setting(self):
        with pytest.raises(RuntimeError, match="FLAG"):
            parse_boolean("perhaps", "FLAG")

    def test_a_whole_number_is_accepted(self):
        assert parse_positive_int(" 42 ", "COUNT") == 42

    @pytest.mark.parametrize("value", ["0", "-1"])
    def test_a_number_below_one_is_refused(self, value):
        with pytest.raises(RuntimeError, match="greater than zero"):
            parse_positive_int(value, "COUNT")

    @pytest.mark.parametrize("value", ["ten", "1.5", ""])
    def test_something_that_is_not_a_number_is_refused(self, value):
        with pytest.raises(RuntimeError, match="whole number"):
            parse_positive_int(value, "COUNT")


class TestRecordsSentToClients:
    def test_the_database_id_is_removed(self):
        assert "_id" not in serialize_doc({"_id": "abc", "name": "Soap"})

    def test_dates_become_text(self):
        from datetime import datetime, timezone

        moment = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

        assert serialize_doc({"created_at": moment})["created_at"] == moment.isoformat()

    def test_an_empty_record_is_left_alone(self):
        assert serialize_doc({}) == {}

    def test_an_account_never_carries_its_password(self):
        """The single most important thing this function does."""
        stored = {
            "user_id": "user_1",
            "mobile": "+919876512345",
            "name": "Someone",
            "password_hash": "$2b$12$notarealhashbutlongenoughtolooklikeone",
            "is_admin": False,
        }

        shared = public_user(stored)

        assert "password_hash" not in shared
        assert "$2b$" not in str(shared)

    def test_only_the_agreed_fields_are_shared(self):
        stored = {
            "user_id": "user_1",
            "password_hash": "secret",
            "internal_note": "do not publish",
            "reset_token": "also secret",
        }

        shared = public_user(stored)

        assert set(shared) == {
            "user_id", "mobile", "email", "name", "picture", "is_admin", "created_at",
        }


class TestSessionTokens:
    def test_the_same_token_always_hashes_alike(self):
        assert hash_session_token("abc") == hash_session_token("abc")

    def test_different_tokens_hash_differently(self):
        assert hash_session_token("abc") != hash_session_token("abd")

    def test_the_stored_value_does_not_contain_the_token(self):
        """The database holds the hash, so a copy of it is not a credential."""
        token = "a-very-secret-session-token"

        assert token not in hash_session_token(token)

    def test_the_hash_is_sha256_in_hexadecimal(self):
        assert re.fullmatch(r"[0-9a-f]{64}", hash_session_token("abc"))


class FakeRequest:
    def __init__(self, cookies):
        self.cookies = cookies


class TestReadingTheToken:
    def test_a_cookie_is_used(self):
        request = FakeRequest({"session_token": "from-cookie"})

        assert get_request_token(request, None) == "from-cookie"

    def test_a_bearer_header_is_used_when_there_is_no_cookie(self):
        request = FakeRequest({})

        assert get_request_token(request, "Bearer from-header") == "from-header"

    def test_the_scheme_is_matched_regardless_of_case(self):
        request = FakeRequest({})

        assert get_request_token(request, "bearer from-header") == "from-header"

    def test_the_cookie_wins(self):
        """A browser sends the cookie by itself; the header is deliberate."""
        request = FakeRequest({"session_token": "from-cookie"})

        assert get_request_token(request, "Bearer from-header") == "from-cookie"

    @pytest.mark.parametrize("header", [None, "", "Basic abc", "Token abc", "Bearer"])
    def test_anything_else_yields_nothing(self, header):
        assert get_request_token(FakeRequest({}), header) is None


class TestPasswords:
    def test_a_password_survives_a_round_trip(self):
        stored = asyncio.run(hash_password("CorrectHorseBattery1!"))

        assert asyncio.run(verify_password("CorrectHorseBattery1!", stored)) is True

    def test_the_wrong_password_is_refused(self):
        stored = asyncio.run(hash_password("CorrectHorseBattery1!"))

        assert asyncio.run(verify_password("CorrectHorseBattery2!", stored)) is False

    def test_the_stored_value_is_not_the_password(self):
        stored = asyncio.run(hash_password("CorrectHorseBattery1!"))

        assert "CorrectHorseBattery1!" not in stored

    def test_two_accounts_with_one_password_store_different_values(self):
        """Salting: identical passwords must not be recognisable as identical."""
        first = asyncio.run(hash_password("SharedPassword1!"))
        second = asyncio.run(hash_password("SharedPassword1!"))

        assert first != second
        assert asyncio.run(verify_password("SharedPassword1!", first)) is True
        assert asyncio.run(verify_password("SharedPassword1!", second)) is True

    def test_a_damaged_stored_value_is_refused_rather_than_raising(self):
        assert asyncio.run(verify_password("anything", "not-a-bcrypt-hash")) is False

    def test_a_password_within_the_limit_is_accepted(self):
        validate_password_bytes("x" * 72)

    def test_a_longer_password_is_refused(self):
        with pytest.raises(HTTPException) as refusal:
            validate_password_bytes("x" * 73)

        assert refusal.value.status_code == 422

    def test_the_limit_counts_bytes_not_characters(self):
        """bcrypt truncates past 72 bytes, and one character can be several.

        Counting characters would let a shorter-looking password be silently
        cut short, so two different passwords could open the same account.
        """
        password = "अ" * 25  # 3 bytes each: 75 bytes, 25 characters

        assert len(password) < 72
        assert len(password.encode("utf-8")) > 72
        with pytest.raises(HTTPException):
            validate_password_bytes(password)

    def test_an_overlong_password_never_verifies(self):
        stored = asyncio.run(hash_password("x" * 72))

        assert asyncio.run(verify_password("x" * 73, stored)) is False


class TestCsrfTokens:
    def test_a_session_always_derives_the_same_token(self):
        assert derive_csrf_token("session-a") == derive_csrf_token("session-a")

    def test_each_session_gets_its_own_token(self):
        assert derive_csrf_token("session-a") != derive_csrf_token("session-b")

    def test_the_token_does_not_reveal_the_session(self):
        assert "session-a" not in derive_csrf_token("session-a")

    def test_the_matching_token_is_accepted(self):
        session = "session-a"

        assert csrf_token_matches(session, derive_csrf_token(session)) is True

    def test_another_sessions_token_is_refused(self):
        """A token lifted from one session must not work on another."""
        assert csrf_token_matches("session-a", derive_csrf_token("session-b")) is False

    @pytest.mark.parametrize(
        "session,submitted",
        [("", "anything"), ("session-a", ""), ("", ""), ("session-a", "wrong")],
    )
    def test_missing_or_wrong_tokens_are_refused(self, session, submitted):
        assert csrf_token_matches(session, submitted) is False

    def test_a_near_miss_is_refused(self):
        session = "session-a"
        correct = derive_csrf_token(session)
        altered = ("b" if correct[0] == "a" else "a") + correct[1:]

        assert csrf_token_matches(session, altered) is False
