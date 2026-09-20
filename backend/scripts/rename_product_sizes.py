"""Drop the size from a product's name now that it is a choice.

"Nayara Washing Powder Detergent 1kg" made sense while a kilo was the only
thing sold. Once the kilo is one form among several, the size in the name is
both wrong and repeated by the form the customer picks.

A name is only shortened where the size it ends with is genuinely one of that
product's variant labels, so the script cannot mangle a name it has
misunderstood. Products without a size in the name are left alone.

    cd backend
    python scripts/rename_product_sizes.py            # show what would change
    python scripts/rename_product_sizes.py --apply    # make the change
"""

import argparse
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")


def shorter_name(product: dict):
    """The product's name without the trailing size, or None to leave it.

    The size must match one of the product's own variant labels. A name
    ending in something that only looks like a size is not touched.
    """
    name = (product.get("name") or "").strip()
    labels = {
        (variant.get("label") or "").strip().lower() for variant in product.get("variants") or []
    }
    if not name or not labels:
        return None

    match = re.search(r"\s+(\S+)$", name)
    if not match or match.group(1).lower() not in labels:
        return None

    shortened = name[: match.start()].strip()
    # Never rename a product down to nothing.
    return shortened or None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the change; without it the script only reports",
    )
    args = parser.parse_args()

    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        print("MONGO_URL and DB_NAME must be set.", file=sys.stderr)
        return 1

    db = MongoClient(mongo_url)[db_name]
    products = list(db.products.find({}, {"_id": 0}))

    plans = []
    for product in products:
        shortened = shorter_name(product)
        if shortened and shortened != product.get("name"):
            plans.append((product["product_id"], product["name"], shortened))

    print(f"Database: {db_name}")
    print(f"Products: {len(products)}  to rename: {len(plans)}")
    print()

    if not plans:
        print("No product still carries its size in its name. Nothing to do.")
        return 0

    width = max(len(old) for _, old, _ in plans)
    for _, old, new in plans:
        print(f"  {old:<{width}}  ->  {new}")

    if not args.apply:
        print()
        print("Nothing was written. Re-run with --apply to make these changes.")
        return 0

    print()
    for product_id, old, new in plans:
        # Guarded by the old name, so a product renamed by someone else in the
        # meantime is left as they left it.
        db.products.update_one({"product_id": product_id, "name": old}, {"$set": {"name": new}})

    print(f"Renamed {len(plans)} products.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
