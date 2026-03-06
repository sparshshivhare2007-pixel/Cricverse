from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config

DIV = "───┈┄┄╌╌╌╌┄┄┈───"

@Client.on_message(filters.command("feedback") & filters.private)
async def feedback_cmd(client, message):
    if len(message.command) < 2:
        return await message.reply_text(
            f"💬 <b>FEEDBACK CENTER</b>\n{DIV}\n"
            "Share your thoughts to help improve the bot.\n"
            "<b>Usage:</b>\n"
            "<code>/feedback your message</code>",
            parse_mode=ParseMode.HTML
        )

    text = message.text.split(maxsplit=1)[1]
    user = message.from_user
    name = user.first_name or "Player"

    log = (
        "💬 <b>NEW FEEDBACK</b>\n"
        f"{DIV}\n"
        f"👤 <b>User:</b> {name}\n"
        f"🆔 <code>{user.id}</code>\n"
        f"📝 <b>Message:</b>{text}\n"
        "⭐ <b>Rating:</b> Pending"
    )

    try:
        await client.send_message(Config.LOG_CHANNEL, log, parse_mode=ParseMode.HTML)
    except:
        pass

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⭐ 1", callback_data="rate_1"),
            InlineKeyboardButton("⭐ 2", callback_data="rate_2"),
            InlineKeyboardButton("⭐ 3", callback_data="rate_3"),
            InlineKeyboardButton("⭐ 4", callback_data="rate_4"),
            InlineKeyboardButton("⭐ 5", callback_data="rate_5")
        ]
    ])

    await message.reply_text(
        f"✅ <b>Feedback Submitted</b>\n{DIV}\n\n"
        "Thanks for your feedback.\n"
        "Please rate your experience:",
        parse_mode=ParseMode.HTML,
        reply_markup=buttons
    )


@Client.on_callback_query(filters.regex("^rate_"))
async def rating_handler(client, callback_query):
    rating = callback_query.data.split("_")[1]
    user = callback_query.from_user
    name = user.first_name or "Player"

    log = (
        "⭐ <b>USER RATING</b>\n"
        f"{DIV}\n\n"
        f"👤 <b>User:</b> {name}\n"
        f"🆔 <code>{user.id}</code>\n"
        f"🌟 <b>Rating:</b> {rating}/5"
    )

    try:
        await client.send_message(Config.LOG_CHANNEL, log, parse_mode=ParseMode.HTML)
    except:
        pass

    await callback_query.message.edit_text(
        f"⭐ <b>Rating Received</b>\n{DIV}\n"
        f"Thanks for rating the experience <b>{rating}/5</b>.\n"
        "Your support helps us improve.",
        parse_mode=ParseMode.HTML
    )

@Client.on_message(filters.command("bug") & filters.private)
async def bug_cmd(client, message):
    if len(message.command) < 2:
        return await message.reply_text(
            f"🐞 <b>BUG REPORT</b>\n{DIV}\n"
            "Found something broken?\n"
            "<b>Usage:</b>\n"
            "<code>/bug describe the issue</code>",
            parse_mode=ParseMode.HTML
        )

    text = message.text.split(maxsplit=1)[1]
    user = message.from_user
    name = user.first_name or "Player"

    log = (
        "🐞 <b>BUG REPORT RECEIVED</b>\n"
        f"{DIV}\n\n"
        f"👤 <b>User:</b> {name}\n"
        f"🆔 <code>{user.id}</code>\n"
        f"📝 <b>Issue:</b>\n{text}"
    )

    try:
        await client.send_message(Config.LOG_CHANNEL, log, parse_mode=ParseMode.HTML)
    except:
        pass

    await message.reply_text(
        f"📨 <b>Bug Report Submitted</b>\n{DIV}\n"
        "Our developers have received your report.\n"
        "Thanks for helping improve the experience.",
        parse_mode=ParseMode.HTML
    )
