import logging
from typing import Any, Dict, List, Tuple

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import OperationFailure

from .config import (
    DB_NAME,
    MONGO_MAX_POOL_SIZE,
    MONGO_SOCKET_TIMEOUT_MS,
    MONGO_TIMEOUT_MS,
    MONGO_URL,
)

logger = logging.getLogger(__name__)

client: AsyncIOMotorClient = AsyncIOMotorClient(
    MONGO_URL,
    # Each worker keeps its own pool, and the cluster caps total connections,
    # so an unbounded default would let a few workers exhaust it.
    maxPoolSize=MONGO_MAX_POOL_SIZE,
    minPoolSize=0,
    maxIdleTimeMS=60_000,
    serverSelectionTimeoutMS=MONGO_TIMEOUT_MS,
    connectTimeoutMS=MONGO_TIMEOUT_MS,
    socketTimeoutMS=MONGO_SOCKET_TIMEOUT_MS,
    retryWrites=True,
)
db = client[DB_NAME]

# (collection, keys, options). Every filter and sort used by the API should be
# covered here so queries keep using an index as the collections grow.
INDEXES: Tuple[Tuple[str, List[Tuple[str, int]], Dict[str, Any]], ...] = (
    ("users", [("user_id", ASCENDING)], {"unique": True}),
    # Email is optional, so only accounts that actually have one are indexed.
    # The filter matches on presence rather than type: MongoDB only uses a
    # partial index when the query provably implies its filter, and an
    # equality match on an address implies the field exists but says nothing
    # about its type. With a type filter the index was skipped and signing in
    # by email read every account in the collection.
    (
        "users",
        [("email", ASCENDING)],
        {
            "unique": True,
            "partialFilterExpression": {"email": {"$exists": True}},
        },
    ),
    ("users", [("mobile", ASCENDING)], {"unique": True}),
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
    # The date ordering carries the product_id tiebreaker so the unfiltered
    # shop page, which is the most visited one, is answered from the index
    # rather than by sorting the whole catalogue in memory. Reading it
    # backwards serves the newest-first ordering too.
    ("products", [("created_at", ASCENDING), ("product_id", ASCENDING)], {}),
    # Storefront sorting. The trailing product_id matches the tiebreaker the
    # catalogue query appends, so paging stays stable when prices or ratings
    # are equal.
    ("products", [("price", ASCENDING), ("product_id", ASCENDING)], {}),
    ("products", [("rating", DESCENDING), ("product_id", ASCENDING)], {}),
    ("orders", [("order_id", ASCENDING)], {"unique": True}),
    ("orders", [("user_id", ASCENDING), ("created_at", DESCENDING)], {}),
    ("orders", [("created_at", DESCENDING)], {}),
    ("orders", [("payment_status", ASCENDING)], {}),
    ("order_claims", [("expires_at", ASCENDING)], {"expireAfterSeconds": 0}),
    ("audit_events", [("at", DESCENDING)], {}),
    ("audit_events", [("actor_id", ASCENDING), ("at", DESCENDING)], {}),
    ("audit_events", [("event", ASCENDING), ("at", DESCENDING)], {}),
    # Retention: records are removed once they are older than the configured
    # window, so the shop is not holding a sign-in history indefinitely.
    ("audit_events", [("expires_at", ASCENDING)], {"expireAfterSeconds": 0}),
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
        except OperationFailure as error:
            # An index already exists on these keys with different options,
            # so replace it rather than leaving the old rules in force.
            if error.code not in (85, 86):
                logger.error("Could not create index %s on %s: %s", keys, collection, error)
                continue
            try:
                await db[collection].drop_index(_index_name(keys))
                await db[collection].create_index(keys, **options)
                logger.info("Replaced index %s on %s", keys, collection)
            except Exception as replace_error:
                logger.error(
                    "Could not replace index %s on %s: %s",
                    keys,
                    collection,
                    replace_error,
                )
        except Exception as error:
            logger.error("Could not create index %s on %s: %s", keys, collection, error)


def _index_name(keys) -> str:
    return "_".join(f"{field}_{direction}" for field, direction in keys)


def close_database() -> None:
    client.close()
