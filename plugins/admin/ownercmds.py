import html
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import Config
from database.connection import db

OWNER_FILTER = filters.user(list(Config.OWNER_IDS))

EDITABLE_STATS = {
    "matches", "wins", "losses", "runs", "balls_faced", "highest_score",
    "fours", "sixes", "centuries", "fifties", "ducks", "wickets",
    "balls_bowled", "runs_conceded", "hat_tricks", "moms",
}


async def _resolve_user(client, identifier):
    identifier = identifier.strip()
    if identifier.lstrip("-").isdigit():
        try:
            return await client.get_users(int(identifier))
        except Exception:
            return None
    try:
        return await client.get_users(identifier)
    except Exception:
        return None


@Client.on_message(filters.command("resetstats") & OWNER_FILTER)
async def reset_stats_cmd(client, message):
    args = message.command

    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(args) >= 2:
        wait = await message.reply_text("🔍 Looking up user…")
        target = await _resolve_user(client, args[1])
        await wait.delete()
    else:
        return await message.reply_text(
            "⚠️ <b>Usage:</b>\n"
            "• Reply to a message: <code>/resetstats</code>\n"
            "• By ID/username: <code>/resetstats [user_id or @username]</code>",
            parse_mode=ParseMode.HTML,
        )

    if not target:
        return await message.reply_text("❌ User not found.")

    confirm_btn = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Yes, Reset", callback_data=f"ownerreset:{target.id}"),
        InlineKeyboardButton("❌ Cancel", callback_data="ownerreset:cancel"),
    ]])
    await message.reply_text(
        f"⚠️ <b>Reset all stats for</b> <a href='tg://user?id={target.id}'>{html.escape(target.first_name)}</a> "
        f"(<code>{target.id}</code>)?\n\n"
        "This will <b>wipe</b> matches, runs, wickets, wins, losses and all records.",
        parse_mode=ParseMode.HTML,
        reply_markup=confirm_btn,
    )


@Client.on_callback_query(filters.regex(r"^ownerreset:(.+)$") & OWNER_FILTER)
async def reset_stats_confirm(client, query):
    payload = query.data.split(":", 1)[1]
    if payload == "cancel":
        await query.message.delete()
        return await query.answer("Cancelled.")

    user_id = int(payload)
    await query.answer("Resetting…")
    try:
        async with db.acquire() as conn:
            await conn.execute(
                """
                UPDATE user_stats SET
                    matches=0, wins=0, losses=0, runs=0, balls_faced=0,
                    highest_score=0, fours=0, sixes=0, centuries=0, fifties=0,
                    ducks=0, wickets=0, balls_bowled=0, runs_conceded=0,
                    hat_tricks=0, moms=0, best_partnership=0, penalties_received=0,
                    recent_form='', last_played_at=NULL
                WHERE user_id=$1
                """,
                user_id,
            )
            await conn.execute(
                "UPDATE duel_stats SET wins=0, losses=0, matches=0, "
                "runs=0, wickets=0, highest_score=0, ducks=0 WHERE user_id=$1",
                user_id,
            )
        await query.message.edit_text(
            f"✅ <b>Stats reset</b> for user <code>{user_id}</code>.\n"
            f"Duel stats also cleared.",
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await query.message.edit_text(f"❌ Error: <code>{html.escape(str(e))}</code>", parse_mode=ParseMode.HTML)


@Client.on_message(filters.command("editstat") & OWNER_FILTER)
async def edit_stat_cmd(client, message):
    args = message.command

    if message.reply_to_message and len(args) >= 3:
        target = message.reply_to_message.from_user
        field = args[1].lower()
        raw_val = args[2]
    elif len(args) >= 4:
        wait = await message.reply_text("🔍 Looking up user…")
        target = await _resolve_user(client, args[1])
        await wait.delete()
        field = args[2].lower()
        raw_val = args[3]
    else:
        fields_list = " | ".join(sorted(EDITABLE_STATS))
        return await message.reply_text(
            "⚠️ <b>Usage:</b>\n"
            "• Reply + <code>/editstat [field] [value]</code>\n"
            "• <code>/editstat [user_id] [field] [value]</code>\n\n"
            f"<b>Editable fields:</b>\n<code>{fields_list}</code>",
            parse_mode=ParseMode.HTML,
        )

    if not target:
        return await message.reply_text("❌ User not found.")

    if field not in EDITABLE_STATS:
        return await message.reply_text(
            f"❌ Unknown field <code>{html.escape(field)}</code>.\n"
            f"Allowed: <code>{' | '.join(sorted(EDITABLE_STATS))}</code>",
            parse_mode=ParseMode.HTML,
        )

    try:
        value = int(raw_val)
        if value < 0:
            return await message.reply_text("❌ Value must be ≥ 0.")
    except ValueError:
        return await message.reply_text("❌ Value must be a whole number.")

    try:
        async with db.acquire() as conn:
            result = await conn.execute(
                f"UPDATE user_stats SET {field}=$1 WHERE user_id=$2",
                value, target.id,
            )
        if result == "UPDATE 0":
            return await message.reply_text(
                f"⚠️ No stats row found for <code>{target.id}</code>. "
                "They need to play at least one match first.",
                parse_mode=ParseMode.HTML,
            )
        await message.reply_text(
            f"✅ <b>{html.escape(target.first_name)}</b>'s "
            f"<code>{field}</code> set to <b>{value}</b>.",
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: <code>{html.escape(str(e))}</code>", parse_mode=ParseMode.HTML)


@Client.on_message(filters.command("botstats") & OWNER_FILTER)
async def bot_stats_cmd(client, message):
    wait = await message.reply_text("📊 Fetching stats…")
    try:
        async with db.acquire() as conn:
            total_users = await conn.fetchval("SELECT COUNT(*) FROM user_stats")
            total_matches = await conn.fetchval("SELECT COUNT(*) FROM games")
            active_matches = await conn.fetchval("SELECT COUNT(*) FROM games WHERE status='active'")
            total_runs = await conn.fetchval("SELECT COALESCE(SUM(runs), 0) FROM user_stats")
            total_wickets = await conn.fetchval("SELECT COALESCE(SUM(wickets), 0) FROM user_stats")
            top_batter = await conn.fetchrow(
                "SELECT first_name, runs FROM user_stats ORDER BY runs DESC LIMIT 1"
            )
            top_bowler = await conn.fetchrow(
                "SELECT first_name, wickets FROM user_stats ORDER BY wickets DESC LIMIT 1"
            )
            duel_count = await conn.fetchval("SELECT COUNT(*) FROM duel_stats")

        tb_name = html.escape(top_batter["first_name"] or "—") if top_batter else "—"
        tb_runs = top_batter["runs"] if top_batter else 0
        twk_name = html.escape(top_bowler["first_name"] or "—") if top_bowler else "—"
        twk_wkts = top_bowler["wickets"] if top_bowler else 0

        text = (
            "📊 <b>BOT STATISTICS</b>\n"
            "────┈┄┄╌╌╌╌┄┄┈────\n\n"
            f"👥 <b>Total Players:</b> {total_users:,}\n"
            f"🏏 <b>Total Matches:</b> {total_matches:,}\n"
            f"🔴 <b>Live Matches:</b> {active_matches}\n"
            f"⚔️ <b>Duel Players:</b> {duel_count:,}\n\n"
            f"🏃 <b>Total Runs Scored:</b> {total_runs:,}\n"
            f"🎯 <b>Total Wickets:</b> {total_wickets:,}\n\n"
            f"👑 <b>Top Batter:</b> {tb_name} ({tb_runs:,} runs)\n"
            f"🏆 <b>Top Bowler:</b> {twk_name} ({twk_wkts} wkts)"
        )
        await wait.edit_text(text, parse_mode=ParseMode.HTML)
    except Exception as e:
        await wait.edit_text(f"❌ Error: <code>{html.escape(str(e))}</code>", parse_mode=ParseMode.HTML)


@Client.on_message(filters.command("broadcast") & OWNER_FILTER)
async def broadcast_cmd(client, message):
    if not message.reply_to_message:
        return await message.reply_text(
            "⚠️ <b>Reply to the message you want to broadcast</b> and use <code>/broadcast</code>.\n\n"
            "The replied message will be forwarded to all groups the bot is in.",
            parse_mode=ParseMode.HTML,
        )

    wait = await message.reply_text("📡 Broadcasting…")
    try:
        async with db.acquire() as conn:
            chat_ids = await conn.fetch("SELECT DISTINCT chat_id FROM games")

        sent, failed = 0, 0
        unique_chats = {row["chat_id"] for row in chat_ids}
        for cid in unique_chats:
            try:
                await message.reply_to_message.forward(cid)
                sent += 1
            except Exception:
                failed += 1

        await wait.edit_text(
            f"📡 <b>Broadcast complete!</b>\n"
            f"✅ Sent: {sent} | ❌ Failed: {failed}",
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await wait.edit_text(f"❌ Error: <code>{html.escape(str(e))}</code>", parse_mode=ParseMode.HTML)


@Client.on_message(filters.command("givemom") & OWNER_FILTER)
async def give_mom_cmd(client, message):
    args = message.command
    target = None

    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(args) >= 2:
        wait = await message.reply_text("🔍 Looking up…")
        target = await _resolve_user(client, args[1])
        await wait.delete()
    else:
        return await message.reply_text("⚠️ Reply to a user or use <code>/givemom [user_id]</code>", parse_mode=ParseMode.HTML)

    if not target:
        return await message.reply_text("❌ User not found.")

    try:
        async with db.acquire() as conn:
            await conn.execute(
                "UPDATE user_stats SET moms = COALESCE(moms,0) + 1 WHERE user_id=$1",
                target.id,
            )
        await message.reply_text(
            f"🏅 <b>Man of the Match</b> awarded to "
            f"<a href='tg://user?id={target.id}'>{html.escape(target.first_name)}</a>!",
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: <code>{html.escape(str(e))}</code>", parse_mode=ParseMode.HTML)
