import asyncio
from datetime import datetime, timedelta

from pyrogram import Client, filters
from pyrogram.enums import ParseMode

from database.connection import db
from database.mods import is_mod

OWNER_ID = 8294062042


async def is_banned(user_id: int):
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM gbans WHERE user_id=$1",
            user_id
        )

    if not row:
        return False, None

    expire = row["expire_at"]

    if expire and datetime.utcnow() > expire:
        async with db.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM gbans WHERE user_id=$1",
                user_id
            )
        return False, None

    return True, row


def banned_check(func):
    async def wrapper(client, message, *args, **kwargs):

        if not message.from_user:
            return

        banned, data = await is_banned(message.from_user.id)

        if banned:
            reason = data["reason"] or "No reason provided"
            text = (
                "🚫 <b>You are banned from using this bot</b>\n\n"
                f"<b>Reason:</b> {reason}"
            )

            expire = data["expire_at"]
            if expire:
                text += f"\n<b>Expires:</b> {expire}"

            return await message.reply_text(text, parse_mode=ParseMode.HTML)

        return await func(client, message, *args, **kwargs)

    return wrapper


async def resolve_user(client, message):

    if message.reply_to_message:
        return message.reply_to_message.from_user

    args = message.text.split()

    if len(args) >= 2:
        try:
            return await client.get_users(args[1])
        except:
            pass

    return None


@Client.on_message(filters.command("gban"))
async def gban_cmd(client, message):

    uid = message.from_user.id

    if uid != OWNER_ID and not await is_mod(uid, min_tier=2):
        return

    target = await resolve_user(client, message)

    if not target:
        return await message.reply_text("Reply / username / user_id required.")

    args = message.text.split(maxsplit=2)
    reason = args[2] if len(args) >= 3 else "No reason provided"

    async with db.pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO gbans (user_id, reason, banned_by)
            VALUES ($1,$2,$3)
            ON CONFLICT (user_id)
            DO UPDATE SET reason=$2
            """,
            target.id,
            reason,
            uid
        )

    await message.reply_text(
        f"🔨 <b>Global Ban Applied</b>\n\n"
        f"<b>User:</b> {target.mention}\n"
        f"<b>Reason:</b> {reason}",
        parse_mode=ParseMode.HTML
    )


@Client.on_message(filters.command("gunban"))
async def gunban_cmd(client, message):

    uid = message.from_user.id

    if uid != OWNER_ID and not await is_mod(uid, min_tier=2):
        return

    target = await resolve_user(client, message)

    if not target:
        return await message.reply_text("Reply / username / user_id required.")

    async with db.pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM gbans WHERE user_id=$1",
            target.id
        )

    await message.reply_text(
        f"✅ <b>User Unbanned Globally</b>\n\n{target.mention}",
        parse_mode=ParseMode.HTML
    )


@Client.on_message(filters.command("tban"))
async def tban_cmd(client, message):

    uid = message.from_user.id

    if uid != OWNER_ID and not await is_mod(uid, min_tier=2):
        return

    args = message.text.split()

    if len(args) < 3 and not message.reply_to_message:
        return await message.reply_text(
            "Usage:\n/tban <user> <time> <reason>"
        )

    target = await resolve_user(client, message)

    if not target:
        return

    time_str = args[2] if message.reply_to_message else args[2]

    seconds = 0

    if time_str.endswith("m"):
        seconds = int(time_str[:-1]) * 60
    elif time_str.endswith("h"):
        seconds = int(time_str[:-1]) * 3600
    elif time_str.endswith("d"):
        seconds = int(time_str[:-1]) * 86400
    else:
        return await message.reply_text("Invalid time format.")

    expire = datetime.utcnow() + timedelta(seconds=seconds)

    reason = " ".join(args[3:]) if len(args) >= 4 else "Temporary ban"

    async with db.pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO gbans (user_id, reason, banned_by, expire_at)
            VALUES ($1,$2,$3,$4)
            ON CONFLICT (user_id)
            DO UPDATE SET expire_at=$4, reason=$2
            """,
            target.id,
            reason,
            uid,
            expire
        )

    await message.reply_text(
        f"⏳ <b>Temporary Ban Applied</b>\n\n"
        f"<b>User:</b> {target.mention}\n"
        f"<b>Reason:</b> {reason}\n"
        f"<b>Expires:</b> {expire}",
        parse_mode=ParseMode.HTML
    )


@Client.on_message(filters.command("gbans"))
async def list_gbans(client, message):

    uid = message.from_user.id

    if uid != OWNER_ID and not await is_mod(uid, min_tier=2):
        return

    async with db.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM gbans ORDER BY banned_at DESC"
        )

    if not rows:
        return await message.reply_text("No global bans.")

    text = "🚫 <b>Global Ban List</b>\n\n"

    for r in rows:

        line = f"• <code>{r['user_id']}</code>"

        if r["reason"]:
            line += f"\n   Reason: {r['reason']}"

        if r["expire_at"]:
            line += f"\n   Expires: {r['expire_at']}"

        text += line + "\n\n"

    await message.reply_text(text, parse_mode=ParseMode.HTML)
