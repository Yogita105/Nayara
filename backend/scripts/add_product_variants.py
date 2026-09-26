"""Give every product the variant it is currently sold as.

Price and stock are moving from the product onto a variant of it, so that a
kilo and a half-kilo can be priced and counted separately. This is the first
step: each existing product gains exactly one variant holding what it sells
for today, and nothing yet reads it.

Running it changes nothing a customer can see. It is safe to run twice: a
product that already has variants is left alone.

    cd backend
    python scripts/add_product_variants.py            # show what would change
    python scripts/add_product_variants.py --apply    # make the change
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

from app.models import ProductVariant, advertised_price  # noqa: E402

# A size already written into the product's name is the label that product is
# really sold under, so it is reused rather than inventing "Standard" for it.
SIZE_IN_NAME = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(kg|g|gm|grams?|ml|l|ltr|litres?|liters?)\b",
    re.IGNORECASE,
)

WEIGHT_UNITS = {"kg", "g", "gm", "gram", "grams"}
VOLUME_UNITS = {"ml", "l", "ltr", "litre", "litres", "liter", "liters"}

TIDY_UNIT = {
    "gm": "g",
    "gram": "g",
    "grams": "g",
    "ltr": "L",
    "litre": "L",
    "litres": "L",
    "liter": "L",
    "liters": "L",
    "l": "L",
}


def read_size(name: str):
    """Return (label, option_name) taken from a product name, if it has one."""
    match = SIZE_IN_NAME.search(name or "")
    if not match:
        return None, "Size"

    amount, unit = match.group(1), match.group(2).lower()
    label = f"{amount}{TIDY_UNIT.get(unit, unit)}"
    if unit in WEIGHT_UNITS:
        return label, "Weight"
    if unit in VOLUME_UNITS:
        return label, "Volume"
    return label, "Size"


def plan_for(product: dict) -> dict:
    label, option_name = read_size(product.get("name", ""))
    variant = ProductVariant(
        label=label or "Standard",
        price=product.get("price", 0) or 0.01,
        mrp=product.get("mrp") or product.get("price", 0) or 0.01,
        stock=product.get("stock", 0),
    ).model_dump()
    return {
        "product_id": product["product_id"],
        "name": product.get("name", ""),
        "option_name": option_name,
        "variant": variant,
    }


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

    already = [p for p in products if p.get("variants")]
    todo = [p for p in products if not p.get("variants")]

    print(f"Database: {db_name}")
    print(f"Products: {len(products)}  already done: {len(already)}  to change: {len(todo)}")
    print()

    if not todo:
        print("Every product already has a variant. Nothing to do.")
        return 0

    plans = [plan_for(product) for product in todo]
    width = max(len(plan["name"]) for plan in plans)
    for plan in plans:
        variant = plan["variant"]
        print(
            f"  {plan['name']:<{width}}  {plan['option_name']:<7} "
            f"{variant['label']:<8} price={variant['price']:<8} stock={variant['stock']}"
        )

    if not args.apply:
        print()
        print("Nothing was written. Re-run with --apply to make these changes.")
        return 0

    print()
    for plan in plans:
        variant = plan["variant"]
        db.products.update_one(
            # Only where variants are still absent, so a product given one by
            # another run in the meantime is not overwritten.
            {"product_id": plan["product_id"], "variants": {"$in": [None, []]}},
            {
                "$set": {
                    "option_name": plan["option_name"],
                    "variants": [variant],
                    "price_from": advertised_price([variant]),
                }
            },
        )

    remaining = db.products.count_documents({"variants": {"$in": [None, []]}})
    print(f"Done. Products still without a variant: {remaining}")
    return 0 if remaining == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
