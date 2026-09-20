"""Print the catalogue and the forms each product is sold in.

A read-only look at what is there, used while setting variants up.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env")


def main() -> None:
    client = MongoClient(os.environ["MONGO_URL"])
    database = client[os.environ.get("DB_NAME", "Nayara_dev")]
    for product in database.products.find({}, {"_id": 0}).sort("category", 1):
        print(f"{product['name']}  [{product['category']}]  option={product.get('option_name')}")
        print(f"    id={product['product_id']}  slug={product['slug']}")
        for variant in product.get("variants", []):
            print(
                f"    - {variant['label']}: price {variant['price']}, "
                f"mrp {variant['mrp']}, stock {variant['stock']}"
            )


if __name__ == "__main__":
    main()
