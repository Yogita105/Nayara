import logging

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING

from .config import DB_NAME, MONGO_URL


logger = logging.getLogger(__name__)

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# (collection, keys, options). Every filter and sort used by the API should be
# covered here so queries keep using an index as the collections grow.
INDEXES = (
    ("users", [("user_id", ASCENDING)], {"unique": True}),
    ("users", [("email", ASCENDING)], {"unique": True}),
    ("users", [("mobile", ASCENDING)], {"unique": True, "sparse": True}),
    ("users", [("created_at", DESCENDING)], {}),
    (
        "user_sessions",
        [("session_token_hash", ASCENDING)],
        {"unique": True, "sparse": True},
    ),
    ("user_sessions", [("user_id", ASCENDING)], {}),
    ("user_sessions", [("expires_at", ASCENDING)], {"expireAfterSeconds": 0}),
    ("rate_limits", [("expires_at", ASCENDING)], {"expireAfterSeconds": 0}),
    ("products", [("product_id", ASCENDING)], {"unique": True}),
    ("products", [("slug", ASCENDING)], {"unique": True}),
    ("products", [("category", ASCENDING), ("created_at", ASCENDING)], {}),
    ("products", [("featured", ASCENDING), ("created_at", ASCENDING)], {}),
    ("products", [("created_at", ASCENDING)], {}),
    ("orders", [("order_id", ASCENDING)], {"unique": True}),
    ("orders", [("user_id", ASCENDING), ("created_at", DESCENDING)], {}),
    ("orders", [("created_at", DESCENDING)], {}),
    ("orders", [("payment_status", ASCENDING)], {}),
    ("order_claims", [("expires_at", ASCENDING)], {"expireAfterSeconds": 0}),
    ("reviews", [("review_id", ASCENDING)], {"unique": True}),
    ("reviews", [("product_id", ASCENDING), ("created_at", ASCENDING)], {}),
    ("contacts", [("contact_id", ASCENDING)], {"unique": True}),
    ("contacts", [("created_at", DESCENDING)], {}),
    ("bulk_inquiries", [("inquiry_id", ASCENDING)], {"unique": True}),
    ("bulk_inquiries", [("created_at", DESCENDING)], {}),
    ("bulk_inquiries", [("status", ASCENDING)], {}),
    ("carts", [("user_id", ASCENDING)], {"unique": True}),
    ("wishlists", [("user_id", ASCENDING)], {"unique": True}),
    ("files", [("file_id", ASCENDING)], {"unique": True}),
)


async def create_indexes() -> None:
    """Create every index, reporting failures instead of blocking startup.

    A unique index cannot be built over existing duplicates. Logging the
    failure keeps the API available while making the problem visible, and the
    routes that depend on uniqueness also check for conflicts themselves.
    """
    for collection, keys, options in INDEXES:
        try:
            await db[collection].create_index(keys, **options)
        except Exception as error:
            logger.error(
                "Could not create index %s on %s: %s", keys, collection, error
            )


def close_database() -> None:
    client.close()
