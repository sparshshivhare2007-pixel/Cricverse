import asyncio
import time
import uuid
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.connection import db
from database.games import (
    get_active_game,
    end_game as close_db_game,
    user_in_other_game,
)
from plugins.game.team import ACTIVE_MATCHES
from Assets.files import MEMBERS_IMAGE

SOLO_JOIN_SECONDS = 120


def _fresh_player_stats():
    return {
        "runs": 0,
        "balls_faced": 0,
        "is_out": False,
        "batting_balls": [],
        "bowling_balls": [],
        "wickets": 0,
        "runs_conceded": 0,
        "balls_bowled": 0,
        "fours_count": 0,
        "sixes_count": 0,
    }


async def _ensure_user_exists(conn, user):
    await conn.execute(
        "INSERT INTO users (user_id, name) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING",
        user.id,
        user.first_name or "Player",
    )


@Client.on_callback_query(filters.regex("^mode_solo$"))
async def solo_mode_selected(client, query):
    await query.answer()
    chat_id = query.message.chat.id
    user = query.from_user

    # fast parallel validation
    existing, other = await asyncio.gather(
        get_active_game(chat_id),
        user_in_other_game(user.id, chat_id),
    )

    if existing:
        return await query.answer("⚠️ A game is already running in this group.", show_alert=True)
    if other:
        return await query.answer(f"⚠️ You are already in another game.", show_alert=True)

    game_id = uuid.uuid4()
    group_title = query.message.chat.title or "Cricket Arena"

    # Build match state immediately — don't wait for DB
    ACTIVE_MATCHES[chat_id] = {
        "chat_id": chat_id,
        "game_id": game_id,
        "host_id": user.id,
        "host_name": user.first_name,
        "client": client,
        "mode": "Solo",
        "phase": "SOLO_JOIN",
        "players": [user.id],
        "user_cache": {user.id: user.first_name or "Player"},
        "username_cache": {user.id: user.username or user.first_name or "Player"},
        "player_stats": {user.id: _fresh_player_stats()},
        "current_batter": None,
        "current_bowler": None,
        "bowler_rotation_pos": 1,
        "balls_in_spell": 0,
        "total_runs": 0,
        "total_wickets": 0,
        "total_balls": 0,
        "bowled": False,
        "batted": False,
        "last_bowl": None,
        "prompt_dispatched": False,
        "join_timer_task": None,
        "timeouts": {
            "bowler": {"fails": 0, "task": None},
            "batter": {"fails": 0, "task": None},
        },
        "last_active": time.time(),
        "announced_achievements": {"batting": {}, "bowling": {}},
    }
    match = ACTIVE_MATCHES[chat_id]

    # Edit message immediately, DB write runs in background
    try:
        await query.message.edit_caption(
            caption=(
                "👤 <b>𝗦𝗢𝗟𝗢 𝗠𝗢𝗗𝗘 𝗦𝗘𝗟𝗘𝗖𝗧𝗘𝗗</b>\n"
                "────┈┄┄╌╌╌╌┄┄┈────\n\n"
                "📢 Join using <code>/joingame</code>\n"
                "📤 Leave using <code>/leave</code>\n"
                f"⏳ Lobby closes in <b>{SOLO_JOIN_SECONDS // 60} minutes</b>.\n"
                "⚡ Minimum <b>3 players</b> required to start."
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        await client.send_message(
            chat_id,
            "👤 <b>𝗦𝗢𝗟𝗢 𝗠𝗢𝗗𝗘 𝗦𝗘𝗟𝗘𝗖𝗧𝗘𝗗</b>\n\n"
            "📢 Join via <code>/joingame</code> | Leave via <code>/leave</code>\n"
            f"⏳ Lobby closes in <b>{SOLO_JOIN_SECONDS // 60} minutes</b>.",
            parse_mode=ParseMode.HTML,
        )

    # Start join timer
    match["join_timer_task"] = asyncio.create_task(_solo_join_timer(client, chat_id))

    # DB write in background
    asyncio.create_task(_create_solo_game_db(game_id, chat_id, group_title, user))


async def _create_solo_game_db(game_id, chat_id, group_title, user):
    try:
        async with db.acquire() as conn:
            await conn.execute(
                "INSERT INTO games (game_id, chat_id, title, mode, host_id, status, phase) "
                "VALUES ($1, $2, $3, $4, $5, 'active', 'SOLO_JOIN')",
                game_id, chat_id, group_title, "solo", user.id,
            )
            await _ensure_user_exists(conn, user)
            await conn.execute(
                "INSERT INTO game_players (game_id, user_id, team) VALUES ($1, $2, 'solo') ON CONFLICT DO NOTHING",
                game_id, user.id,
            )
    except Exception as e:
        print(f"Solo game DB create (bg) error: {e}")


@Client.on_message(filters.command("joingame") & filters.group)
async def join_solo_game(client, message):
    chat_id = message.chat.id
    user = message.from_user
    match = ACTIVE_MATCHES.get(chat_id)

    if not match or match.get("mode") != "Solo":
        return await message.reply_text("😴 No solo lobby right now. Start one with /start")

    if match.get("phase") != "SOLO_JOIN":
        return await message.reply_text("🔒 Lobby is closed. Game is in progress.")

    if user.id in match["players"]:
        return await message.reply_text("😏 You're already in the lobby.")

    other = await user_in_other_game(user.id, chat_id)
    if other:
        return await message.reply_text(
            f"⚠️ You're already in <b>{other['title']}</b>. Finish that first.",
            parse_mode=ParseMode.HTML,
        )

    match["players"].append(user.id)
    match["user_cache"][user.id] = user.first_name or "Player"
    match["username_cache"][user.id] = user.username or user.first_name or "Player"
    match["player_stats"][user.id] = _fresh_player_stats()

    # DB write in background
    asyncio.create_task(_join_solo_game_db(match["game_id"], user))

    count = len(match["players"])
    await message.reply_text(
        f"✅ <b>{user.first_name}</b> joined! ({count} player{'s' if count != 1 else ''})",
        parse_mode=ParseMode.HTML,
    )


async def _join_solo_game_db(game_id, user):
    try:
        async with db.acquire() as conn:
            await _ensure_user_exists(conn, user)
            await conn.execute(
                "INSERT INTO game_players (game_id, user_id, team) VALUES ($1, $2, 'solo') ON CONFLICT DO NOTHING",
                game_id, user.id,
            )
    except Exception as e:
        print(f"Solo join DB (bg) error: {e}")


@Client.on_message(filters.command("leave") & filters.group)
async def leave_solo_game(client, message):
    chat_id = message.chat.id
    user = message.from_user
    match = ACTIVE_MATCHES.get(chat_id)

    if not match or match.get("mode") != "Solo":
        return

    if match.get("phase") != "SOLO_JOIN":
        return await message.reply_text("🏏 Can't leave during a live game.")

    if user.id not in match["players"]:
        return await message.reply_text("You're not in the lobby.")

    match["players"].remove(user.id)
    match["user_cache"].pop(user.id, None)
    match.get("username_cache", {}).pop(user.id, None)
    match["player_stats"].pop(user.id, None)

    asyncio.create_task(_leave_solo_game_db(match["game_id"], user.id))

    count = len(match["players"])
    await message.reply_text(
        f"👋 <b>{user.first_name}</b> left. ({count} remaining)",
        parse_mode=ParseMode.HTML,
    )


async def _leave_solo_game_db(game_id, user_id):
    try:
        async with db.acquire() as conn:
            await conn.execute(
                "DELETE FROM game_players WHERE game_id=$1 AND user_id=$2",
                game_id, user_id,
            )
    except Exception as e:
        print(f"Solo leave DB (bg) error: {e}")


async def _solo_join_timer(client, chat_id):
    try:
        half = SOLO_JOIN_SECONDS // 2
        await asyncio.sleep(half)

        match = ACTIVE_MATCHES.get(chat_id)
        if not match or match.get("phase") != "SOLO_JOIN":
            return

        count = len(match["players"])
        await client.send_message(
            chat_id,
            f"⏳ <b>1 minute left</b> to join!\nPlayers so far: <b>{count}</b>\n📢 /joingame",
            parse_mode=ParseMode.HTML,
        )

        await asyncio.sleep(SOLO_JOIN_SECONDS - half - 10)

        match = ACTIVE_MATCHES.get(chat_id)
        if not match or match.get("phase") != "SOLO_JOIN":
            return

        await client.send_message(
            chat_id, "⚠️ <b>10 seconds left!</b> Last chance to /joingame", parse_mode=ParseMode.HTML
        )

        await asyncio.sleep(10)

        match = ACTIVE_MATCHES.get(chat_id)
        if not match or match.get("phase") != "SOLO_JOIN":
            return

        count = len(match["players"])
        if count < 3:
            await client.send_message(
                chat_id,
                f"❌ <b>Game Cancelled!</b>\nOnly <b>{count}</b> joined. Need at least <b>3</b>.",
                parse_mode=ParseMode.HTML,
            )
            ACTIVE_MATCHES.pop(chat_id, None)
            await close_db_game(chat_id)
            return

        await start_solo_game(client, chat_id)

    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Solo join timer error: {e}")


async def start_solo_game(client, chat_id):
    match = ACTIVE_MATCHES.get(chat_id)
    if not match:
        return

    match["phase"] = "LIVE"
    match["current_batter"] = match["players"][0]
    match["bowler_rotation_pos"] = 1

    from plugins.game.solo import get_next_solo_bowler
    match["current_bowler"] = get_next_solo_bowler(match)
    match["balls_in_spell"] = 0

    players = match["players"]
    user_cache = match["user_cache"]
    batter_name = user_cache.get(match["current_batter"], "Player")
    bowler_name = user_cache.get(match["current_bowler"], "Player")

    player_list = "\n".join(
        f"{i+1}. {user_cache.get(uid, 'Player')}" for i, uid in enumerate(players)
    )

    # DB update in background
    asyncio.create_task(_update_game_phase_db(chat_id, "LIVE"))

    await client.send_message(
        chat_id,
        f"🏏 <b>𝗦𝗢𝗟𝗢 𝗖𝗥𝗜𝗖𝗞𝗘𝗧 𝗕𝗘𝗚𝗜𝗡𝗦!</b>\n"
        "────┈┄┄╌╌╌╌┄┄┈────\n"
        f"👥 <b>Players ({len(players)}):</b>\n{player_list}\n"
        "────┈┄┄╌╌╌╌┄┄┈────\n"
        f"🏏 <b>First Batter:</b> {batter_name}\n"
        f"⚾ <b>First Bowler:</b> {bowler_name}\n\n"
        "🎯 No dot balls (0) | Same number = OUT ⚡",
        parse_mode=ParseMode.HTML,
    )

    await asyncio.sleep(0.8)
    await client.send_message(chat_id, f"🎉 {batter_name}, you're batting first!", parse_mode=ParseMode.HTML)
    await asyncio.sleep(0.8)
    await client.send_message(chat_id, f"🎯 {bowler_name}, you bowl first!", parse_mode=ParseMode.HTML)

    from plugins.game.solo.state import send_solo_ball_prompt
    await send_solo_ball_prompt(client, match)


async def _update_game_phase_db(chat_id, phase):
    try:
        async with db.acquire() as conn:
            await conn.execute(
                "UPDATE games SET phase=$1 WHERE chat_id=$2 AND status='active'",
                phase, chat_id,
            )
    except Exception as e:
        print(f"Solo phase DB update error: {e}")
