from database.connection import db

async def get_top_players_runs(limit: int = 10):
    async with db.pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT s.user_id, COALESCE(u.name, s.first_name, 'Player') as name, s.runs, s.matches 
            FROM user_stats s
            LEFT JOIN users u ON s.user_id = u.user_id
            ORDER BY s.runs DESC
            LIMIT $1
            """,
            limit
        )
        
async def add_user(user_id: int, name: str) -> bool:
    async with db.pool.acquire() as conn:
        exists = await conn.fetchval("SELECT user_id FROM users WHERE user_id=$1", user_id)
        if exists:
            return False
        await conn.execute("INSERT INTO users (user_id, name) VALUES ($1, $2)", user_id, name)
        return True

async def total_users() -> int:
    async with db.pool.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM users")

async def get_mod(user_id: int):
    async with db.pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM mods WHERE user_id=$1", user_id)

async def is_mod(user_id: int, min_tier: int = 1) -> bool:
    async with db.pool.acquire() as conn:
        tier = await conn.fetchval("SELECT tier FROM mods WHERE user_id=$1", user_id)
        return tier is not None and tier >= min_tier

async def add_or_update_mod(user_id: int, tier: int, owner_id: int):
    async with db.pool.acquire() as conn:
        await conn.execute("INSERT INTO mods (user_id, tier, added_by) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET tier=$2, added_by=$3", user_id, tier, owner_id)

async def remove_mod(user_id: int):
    async with db.pool.acquire() as conn:
        await conn.execute("DELETE FROM mods WHERE user_id=$1", user_id)

async def list_mods():
    async with db.pool.acquire() as conn:
        return await conn.fetch("SELECT user_id, tier, added_at FROM mods ORDER BY tier DESC")

async def ban_user(user_id, first_name, reason, by):
    async with db.pool.acquire() as conn:
        await conn.execute("INSERT INTO user_bans (user_id, first_name, reason, banned_by) VALUES ($1,$2,$3,$4) ON CONFLICT (user_id) DO UPDATE SET reason=$3, banned_by=$4, banned_at=NOW()", user_id, first_name, reason, by)

async def unban_user(user_id):
    async with db.pool.acquire() as conn:
        await conn.execute("DELETE FROM user_bans WHERE user_id=$1", user_id)

async def get_user_ban(user_id):
    async with db.pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM user_bans WHERE user_id=$1", user_id)

async def list_user_bans():
    async with db.pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM user_bans")

async def ban_group(chat_id, title, reason, by):
    async with db.pool.acquire() as conn:
        await conn.execute("INSERT INTO group_bans (chat_id, title, reason, banned_by) VALUES ($1,$2,$3,$4) ON CONFLICT (chat_id) DO UPDATE SET reason=$3, banned_by=$4, banned_at=NOW()", chat_id, title, reason, by)

async def unban_group(chat_id):
    async with db.pool.acquire() as conn:
        await conn.execute("DELETE FROM group_bans WHERE chat_id=$1", chat_id)

async def get_group_ban(chat_id):
    async with db.pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM group_bans WHERE chat_id=$1", chat_id)

async def list_group_bans():
    async with db.pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM group_bans")
