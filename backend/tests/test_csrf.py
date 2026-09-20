import pytest

from app.middleware import SAFE_METHODS
from app.security import csrf_token_matches, derive_csrf_token

SESSION_TOKEN = "session-token-example"


def test_csrf_token_is_deterministic_for_a_session():
    assert derive_csrf_token(SESSION_TOKEN) == derive_csrf_token(SESSION_TOKEN)


def test_csrf_token_differs_between_sessions():
    assert derive_csrf_token(SESSION_TOKEN) != derive_csrf_token("another-session")


def test_csrf_token_is_not_the_session_token():
    assert derive_csrf_token(SESSION_TOKEN) != SESSION_TOKEN


def test_matching_token_is_accepted():
    assert csrf_token_matches(SESSION_TOKEN, derive_csrf_token(SESSION_TOKEN))


@pytest.mark.parametrize(
    "submitted",
    ["", "wrong-token", derive_csrf_token("different-session")],
)
def test_invalid_tokens_are_rejected(submitted):
    assert csrf_token_matches(SESSION_TOKEN, submitted) is False


def test_missing_session_token_is_rejected():
    assert csrf_token_matches("", derive_csrf_token(SESSION_TOKEN)) is False


def test_read_only_methods_are_exempt():
    assert SAFE_METHODS == {"GET", "HEAD", "OPTIONS", "TRACE"}
