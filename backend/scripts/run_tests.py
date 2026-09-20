"""Run the backend tests against an isolated database.

The suite creates and deletes accounts, orders and stock, so it starts its own
API on a separate port pointed at a separate database. The shop's data is never
touched.

    cd backend
    python scripts/run_tests.py
    python scripts/run_tests.py tests/test_inventory.py -k stock

Anything after the script name is passed straight through to pytest.
"""

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import dotenv_values

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_PORT = int(os.environ.get("TEST_API_PORT", "8001"))
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"
STARTUP_TIMEOUT_SECONDS = 90


def resolve_test_database() -> str:
    live_name = (dotenv_values(BACKEND_DIR / ".env").get("DB_NAME") or "").strip()
    test_name = (os.environ.get("TEST_DB_NAME") or "").strip()
    if not test_name:
        # A local database is usually named <project>_dev; tests belong beside
        # it as <project>_test rather than <project>_dev_test.
        base = live_name[:-4] if live_name.endswith("_dev") else live_name
        test_name = f"{base}_test" if base else "nayara_test"
    if live_name and test_name == live_name:
        raise SystemExit(
            f"TEST_DB_NAME is '{test_name}', which is the database this project "
            "is configured to use. Choose a different name."
        )
    return test_name


def wait_until_ready() -> bool:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE_URL}/api/health/ready", timeout=5):
                return True
        except (urllib.error.URLError, OSError):
            time.sleep(1)
    return False


def main() -> int:
    test_database = resolve_test_database()
    environment = {
        **os.environ,
        # Both the API and the tests must agree on the database.
        "DB_NAME": test_database,
        "TEST_DB_NAME": test_database,
        "ENVIRONMENT": "test",
        "REACT_APP_BACKEND_URL": BASE_URL,
        # Keep pytest output readable; many tests deliberately provoke 4xx
        # responses, which the API records as warnings.
        "LOG_LEVEL": os.environ.get("LOG_LEVEL", "ERROR"),
    }

    print(f"Starting an API on port {TEST_PORT} using database '{test_database}'.")
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "server:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(TEST_PORT),
            "--log-level",
            "warning",
        ],
        cwd=BACKEND_DIR,
        env=environment,
    )

    try:
        if not wait_until_ready():
            print("The test API did not become ready in time.", file=sys.stderr)
            return 1
        print(f"Running tests against {BASE_URL}.\n")
        return subprocess.run(
            [sys.executable, "-m", "pytest", *sys.argv[1:]],
            cwd=BACKEND_DIR,
            env=environment,
        ).returncode
    finally:
        server.terminate()
        try:
            server.wait(timeout=15)
        except subprocess.TimeoutExpired:
            server.kill()
        print("\nStopped the test API.")


if __name__ == "__main__":
    raise SystemExit(main())
