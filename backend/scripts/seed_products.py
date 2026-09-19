"""Fill an empty product catalogue.

Seeding runs automatically only in development and test. Anywhere else it is a
deliberate step, so an emptied catalogue is never refilled behind your back.

    cd backend
    python scripts/seed_products.py
"""

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.config import ENVIRONMENT  # noqa: E402
from app.database import close_database, db  # noqa: E402
from app.seed import SEED_PRODUCTS, seed_products  # noqa: E402


async def run() -> int:
    existing = await db.products.count_documents({})
    if existing:
        print(f"The catalogue already holds {existing} products in {ENVIRONMENT}.")
        print("Nothing was written, so prices and stock stay as they are.")
        print("Remove the products first if you really want the starter set.")
        return 1

    inserted = await seed_products()
    print(f"Inserted {inserted} of {len(SEED_PRODUCTS)} starter products "
          f"into {ENVIRONMENT}.")
    return 0


def main() -> int:
    try:
        return asyncio.run(run())
    finally:
        close_database()


if __name__ == "__main__":
    raise SystemExit(main())
