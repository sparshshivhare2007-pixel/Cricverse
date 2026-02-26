from database.connection import db

async def add_group(chat_id: int, title: str) -> bool:
    async with db.pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT chat_id FROM groups WHERE chat_id=$1",
            chat_id
        )

        if exists:
            return False

        await conn.execute(
            "INSERT INTO groups (chat_id, title) VALUES ($1, $2)",
            chat_id, title
        )
        return True

async def total_groups() -> int:
    async with db.pool.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM groups")


