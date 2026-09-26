"""Remove the product-level price, MRP and stock.

These were a summary of the variants, kept while the storefront still read
them. Nothing does any more: price sorting and filtering use `price_from`,
and stock is added up from the forms. Leaving the fields behind would invite
something to read a figure that is no longer maintained.

The index on the old `price` field goes too. Indexes are created at startup
but never dropped, so an index whose field no longer exists would sit there
being updated for nothing.

Run it only once the application no longer writes these fields.

    cd backend
    python scripts/drop_product_price_and_stock.py            # report
    python scripts/drop_product_price_and_stock.py --apply    # make the change
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from app.models import advertised_price  # noqa: E402

DEAD_FIELDS = ["price", "mrp", "stock"]
DEAD_INDEX = "price_1_product_id_1"


def unsafe_to_drop(product: dict) -> str:
    """Why this product is not ready to lose its own figures, if it is not.

    The fields being removed are the only record of what a product without
    variants costs, so one that never got them would lose everything. And
    `price_from` has to already agree with the variants, or the catalogue
    would be sorted by a figure nothing recomputes.
    """
    variants = product.get("variants") or []
    if not variants:
        return "has no variants; run add_product_variants.py first"
    expected = advertised_price(variants)
    if product.get("price_from") != expected:
        return f"price_from is {product.get('price_from')}, but its cheapest form is {expected}"
    return ""


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

    blocked = [(p["name"], reason) for p in products if (reason := unsafe_to_drop(p))]
    carrying = db.products.count_documents(
        {"$or": [{field: {"$exists": True}} for field in DEAD_FIELDS]}
    )
    has_index = DEAD_INDEX in db.products.index_information()

    print(f"Database: {db_name}")
    print(f"Products: {len(products)}  still carrying the old fields: {carrying}")
    print(f"Stale index {DEAD_INDEX}: {'present' if has_index else 'already gone'}")
    print()

    if blocked:
        print("Refusing to drop anything; these products are not ready:")
        for name, reason in blocked:
            print(f"  {name}: {reason}")
        return 1

    if not carrying and not has_index:
        print("Nothing to do.")
        return 0

    if not args.apply:
        print(f"Would remove {DEAD_FIELDS} from {carrying} products", end="")
        print(f" and drop {DEAD_INDEX}." if has_index else ".")
        print("Nothing was written. Re-run with --apply to make these changes.")
        return 0

    result = db.products.update_many({}, {"$unset": {field: "" for field in DEAD_FIELDS}})
    print(f"Removed the old fields from {result.modified_count} products.")
    if has_index:
        db.products.drop_index(DEAD_INDEX)
        print(f"Dropped {DEAD_INDEX}.")

    left = db.products.count_documents(
        {"$or": [{field: {"$exists": True}} for field in DEAD_FIELDS]}
    )
    print(f"Products still carrying them: {left}")
    return 0 if left == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
