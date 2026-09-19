from motor.motor_asyncio import AsyncIOMotorClient

from .config import DB_NAME, MONGO_URL


client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


async def create_indexes() -> None:
    await db.users.create_index("email", unique=True)
    await db.users.create_index("mobile", unique=True, sparse=True)
    await db.users.create_index("user_id", unique=True)
    await db.user_sessions.create_index("session_token_hash", unique=True, sparse=True)
    await db.user_sessions.create_index("expires_at", expireAfterSeconds=0)
    await db.rate_limits.create_index("expires_at", expireAfterSeconds=0)


def close_database() -> None:
    client.close()
