import argparse
import getpass
import os
import sys
from pathlib import Path

import bcrypt
from dotenv import load_dotenv
from pymongo import MongoClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Set a password for an existing Nayara user.")
    parser.add_argument("email", help="Email address of the existing user")
    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parents[1]
    load_dotenv(backend_dir / ".env")

    password = getpass.getpass("New password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        print("Passwords do not match.", file=sys.stderr)
        return 1
    if len(password) < 8:
        print("Password must contain at least 8 characters.", file=sys.stderr)
        return 1
    if len(password.encode("utf-8")) > 72:
        print("Password must not exceed 72 bytes.", file=sys.stderr)
        return 1

    email = args.email.strip().lower()
    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

    client = MongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=10000)
    try:
        db = client[os.environ["DB_NAME"]]
        result = db.users.update_one(
            {"email": email},
            {"$set": {"password_hash": password_hash}},
        )
    finally:
        client.close()

    if result.matched_count == 0:
        print(f"No user found for {email}.", file=sys.stderr)
        return 1

    print(f"Password updated for {email}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
