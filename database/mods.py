from database.connection import db


async def get_mod(user_id: int):
    async with db.pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM mods WHERE user_id=$1",
            user_id
        )


async def is_mod(user_id: int, min_tier: int = 1) -> bool:
    async with db.pool.acquire() as conn:
        tier = await conn.fetchval(
            "SELECT tier FROM mods WHERE user_id=$1",
            user_id
        )
        return tier is not None and tier >= min_tier


async def add_or_update_mod(user_id: int, tier: int, owner_id: int):
    async with db.pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO mods (user_id, tier, added_by)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id)
            DO UPDATE SET tier=$2, added_by=$3
            """,
            user_id, tier, owner_id
        )


async def remove_mod(user_id: int):
    async with db.pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM mods WHERE user_id=$1",
            user_id
        )


async def list_mods():
    async with db.pool.acquire() as conn:
        return await conn.fetch(
            "SELECT user_id, tier, added_at FROM mods ORDER BY tier DESC"
        )
