import asyncio
import html
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.enums import ParseMode

from config import Config
from database.connection import db

OWNER_FILTER = filters.user(list(Config.OWNER_IDS))

COLLECTIONS_MAP = {
    "user_stats": {
        "pg_table": "user_stats",
        "key": "user_id",
        "fields": [
            "user_id", "username", "first_name", "matches", "wins", "losses",
            "runs", "wickets", "balls_faced", "balls_bowled", "runs_conceded",
            "sixes", "fours", "centuries", "fifties", "ducks", "hat_tricks",
            "moms", "highest_score", "best_partnership", "penalties_received",
            "recent_form", "not_outs", "last_played_at",
        ],
    },
    "users": {
        "pg_table": "users",
        "key": "user_id",
        "fields": ["user_id", "name", "coins", "games_played", "notify_enabled", "created_at"],
    },
    "games": {
        "pg_table": "games",
        "key": "game_id",
        "fields": [
            "game_id", "chat_id", "title", "mode", "host_id", "status", "phase",
            "winner", "team_a_runs", "team_b_runs", "team_a_wickets", "team_b_wickets",
            "team_a_balls", "team_b_balls", "team_a_penalty", "team_b_penalty",
            "target", "innings", "motm", "toss_winner", "batting_team", "bowling_team",
            "overs", "created_at",
        ],
    },
    "duel_stats": {
        "pg_table": "duel_stats",
        "key": "user_id",
        "fields": [
            "user_id", "wins", "losses", "matches", "runs", "wickets",
            "highest_score", "ducks",
        ],
    },
    "mods": {
        "pg_table": "mods",
        "key": "user_id",
        "fields": ["user_id", "tier", "added_by", "added_at"],
    },
    "user_bans": {
        "pg_table": "user_bans",
        "key": "user_id",
        "fields": ["user_id", "first_name", "reason", "banned_by", "banned_at"],
    },
    "group_bans": {
        "pg_table": "group_bans",
        "key": "chat_id",
        "fields": ["chat_id", "title", "reason", "banned_by", "banned_at"],
    },
    "groups": {
        "pg_table": "groups",
        "key": "chat_id",
        "fields": ["chat_id", "title", "created_at"],
    },
    "restricted_users": {
        "pg_table": "restricted_users",
        "key": "user_id",
        "fields": ["user_id", "reason", "admin_id", "timestamp"],
    },
}


async def _transfer_table(pg_conn, collection_name: str, config: dict, status_msg) -> tuple:
    table = config["pg_table"]
    key_field = config["key"]
    fields = config["fields"]

    try:
        rows = await pg_conn.fetch(f"SELECT * FROM {table}")
    except Exception as e:
        return 0, 0, f"Table '{table}' fetch failed: {str(e)[:80]}"

    if not rows:
        return 0, 0, None

    col = db.db[collection_name]
    added = skipped = 0

    for row in rows:
        try:
            doc = {}
            for f in fields:
                if f in row.keys():
                    val = row[f]
                    if isinstance(val, datetime):
                        val = val
                    doc[f] = val

            key_val = doc.get(key_field)
            if key_val is None:
                skipped += 1
                continue

            existing = await col.find_one({key_field: key_val})
            if existing:
                skipped += 1
                continue

            await col.insert_one(doc)
            added += 1
        except Exception:
            skipped += 1

    return added, skipped, None


@Client.on_message(filters.command("transfer") & OWNER_FILTER)
async def transfer_cmd(client, message):
    args = message.command

    if len(args) < 2:
        return await message.reply_text(
            "📦 <b>PostgreSQL → MongoDB Transfer</b>\n\n"
            "<b>Usage:</b>\n"
            "<code>/transfer postgresql://user:pass@host:port/dbname</code>\n\n"
            "This will migrate all tables (user_stats, users, games, duel_stats, "
            "mods, bans, groups, restricted_users) from PostgreSQL into MongoDB.\n\n"
            "⚠️ Existing documents in MongoDB are <b>skipped</b> (no overwrite).\n"
            "📂 For JSON import use <b>/dbtrans</b> by replying to a JSON file.",
            parse_mode=ParseMode.HTML,
        )

    pg_url = args[1].strip()
    if not pg_url.startswith(("postgresql://", "postgres://")):
        return await message.reply_text(
            "❌ Invalid connection string.\n"
            "Must start with <code>postgresql://</code> or <code>postgres://</code>",
            parse_mode=ParseMode.HTML,
        )

    status = await message.reply_text(
        "🔌 <b>Connecting to PostgreSQL…</b>",
        parse_mode=ParseMode.HTML,
    )

    try:
        import asyncpg
        pg_conn = await asyncpg.connect(pg_url, timeout=15)
    except Exception as e:
        return await status.edit_text(
            f"❌ <b>PostgreSQL connection failed:</b>\n<code>{html.escape(str(e))}</code>",
            parse_mode=ParseMode.HTML,
        )

    try:
        await status.edit_text(
            "✅ <b>PostgreSQL connected!</b>\n🔄 Starting migration…\n\n"
            "This may take a while depending on data size.",
            parse_mode=ParseMode.HTML,
        )

        total_added = 0
        total_skipped = 0
        results_text = "📊 <b>Migration Results:</b>\n\n"

        for col_name, config in COLLECTIONS_MAP.items():
            try:
                await status.edit_text(
                    f"🔄 <b>Migrating:</b> <code>{col_name}</code>…",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass

            added, skipped, err = await _transfer_table(pg_conn, col_name, config, status)
            total_added += added
            total_skipped += skipped

            if err:
                results_text += f"⚠️ <code>{col_name}</code>: {html.escape(err)}\n"
            else:
                results_text += f"✅ <code>{col_name}</code>: +{added} added, {skipped} skipped\n"

            await asyncio.sleep(0.2)

        results_text += (
            f"\n────┈┄┄╌╌╌╌┄┄┈────\n"
            f"📦 <b>Total Added:</b> {total_added}\n"
            f"⏭️ <b>Total Skipped:</b> {total_skipped}\n"
            f"✅ <b>Migration Complete!</b>"
        )

        await status.edit_text(results_text, parse_mode=ParseMode.HTML)

    except Exception as e:
        await status.edit_text(
            f"❌ <b>Migration error:</b>\n<code>{html.escape(str(e))}</code>",
            parse_mode=ParseMode.HTML,
        )
    finally:
        try:
            await pg_conn.close()
        except Exception:
            pass
