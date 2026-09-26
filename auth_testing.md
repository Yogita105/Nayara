# Testing and authentication

Tests run against a real API and a real MongoDB, not mocks. `scripts/run_tests.py`
starts an API on port 8001 pointed at a separate database (`Nayara_test`), runs pytest
against it, and stops it afterwards. Running pytest directly is refused when it would
touch the database this project is configured to use, so a test run cannot drain the
catalogue it is developing against.

```powershell
cd backend
python scripts/run_tests.py                  # the whole suite
python scripts/run_tests.py -q tests/test_inventory.py
```

## How tests sign in

There is no OAuth and no browser in the loop. The fixtures in `tests/conftest.py`
insert a user and a session row directly, then send the session token as a bearer
header:

- `user_session` / `admin_session` — create the account and session, and delete
  everything belonging to it afterwards
- `user_client` / `admin_client` — a `requests.Session` carrying that token
- `anon_client` — no credentials, for checking what a stranger can reach

Session tokens are stored as SHA-256 hashes, so the fixture writes the hash and keeps
the plain token for the header, exactly as the login endpoint does.

Cleanup lives in fixtures rather than test bodies, because a test body does not run its
cleanup when it fails, and a failed order test would otherwise leave stock reserved.

## What is deliberately not mocked

Stock reservation, session expiry and the concurrency tests need real database
behaviour to mean anything: a mocked driver would happily accept the oversell those
tests exist to catch.
