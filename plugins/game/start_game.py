from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, Message
from pyrogram.enums import ParseMode
from pyrogram.errors import MessageNotModified 
from Assets.files import START_IMAGE_GROUP, SOLO_MODE_IMAGE
from database.games import is_game_active
from plugins.game.team import ACTIVE_MATCHES

@Client.on_message(filters.command("start") & filters.group)
async def start_game(client, message):
    chat_id = message.chat.id

    if await is_game_active(chat_id):
        return await message.reply_text(
            "⚠️ <b>Game already running</b>\nFinish it first 🏏",
            parse_mode=ParseMode.HTML
        )

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🏏 Team", callback_data="mode_team"),
                InlineKeyboardButton("👤 Solo", callback_data="mode_solo"),
            ],
            [
                InlineKeyboardButton("✖ Cancel", callback_data="mode_cancel")
            ]
        ]
    )

    await message.reply_photo(
        photo=START_IMAGE_GROUP,
        caption=(
            "🎮 <b>SELECT MODE</b>\n"
            "Choose how you want to play today 👇"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=buttons
    )

@Client.on_callback_query(filters.regex("^mode_solo$"))
async def solo_mode(client, query):
    chat_id = query.message.chat.id
    user = query.from_user

    ACTIVE_MATCHES[chat_id] = {
        "mode": "Solo",
        "phase": "REGISTRATION",
        "host_id": user.id,
        "host_name": user.first_name,
        "players": {},
        "user_cache": {user.id: user.first_name},
        "chat_id": chat_id,
        "client": client
    }

    ACTIVE_MATCHES[chat_id]["players"][user.id] = {
        "runs": 0, "wickets": 0, "balls_faced": 0, "balls_bowled": 0, "is_out": False
    }

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✋ Join Solo", callback_data="join_solo")],
        [InlineKeyboardButton("▶️ Start Match", callback_data="start_solo_match")],
        [InlineKeyboardButton("✖ Cancel Match", callback_data="cancel_solo_match")]
    ])

    await query.answer("Solo Mode Selected! 🏏")

    try:
        await query.message.edit_media(
            media=InputMediaPhoto(
                media=SOLO_MODE_IMAGE,
                caption=(
                    "👤 <b>𝗦𝗢𝗟𝗢 𝗠𝗢𝗗𝗘 — 𝗥𝗘𝗚𝗜𝗦𝗧𝗥𝗔𝗧𝗜𝗢𝗡</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "🔥 <b>Rules:</b> Every man for himself! No 0 (defend) allowed.\n"
                    f"👑 <b>Host:</b> {user.mention}\n"
                    "👥 <b>Players Joined:</b> 1\n\n"
                    "<i>Minimum 3 players required to start.</i>"
                )
            ),
            reply_markup=buttons
        )
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex("^join_solo$"))
async def join_solo(client, query):
    chat_id = query.message.chat.id
    user = query.from_user
    match = ACTIVE_MATCHES.get(chat_id)

    if not match or match.get("phase") != "REGISTRATION" or match.get("mode") != "Solo":
        return await query.answer("No active solo registration here.", show_alert=True)

    if user.id in match["players"]:
        return await query.answer("You are already in the match!", show_alert=True)

    match["players"][user.id] = {
        "runs": 0, "wickets": 0, "balls_faced": 0, "balls_bowled": 0, "is_out": False
    }
    match["user_cache"][user.id] = user.first_name
    
    total_players = len(match["players"])

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✋ Join Solo", callback_data="join_solo")],
        [InlineKeyboardButton("▶️ Start Match", callback_data="start_solo_match")],
        [InlineKeyboardButton("✖ Cancel Match", callback_data="cancel_solo_match")]
    ])

    await query.answer("Joined successfully! ✅")
    
    try:
        await query.message.edit_caption(
            caption=(
                "👤 <b>𝗦𝗢𝗟𝗢 𝗠𝗢𝗗𝗘 — 𝗥𝗘𝗚𝗜𝗦𝗧𝗥𝗔𝗧𝗜𝗢𝗡</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🔥 <b>Rules:</b> Every man for himself! No 0 (defend) allowed.\n"
                f"👑 <b>Host:</b> <a href='tg://user?id={match['host_id']}'>{match['host_name']}</a>\n"
                f"👥 <b>Players Joined:</b> {total_players}\n\n"
                "<i>Minimum 3 players required to start.</i>"
            ),
            reply_markup=buttons,
            parse_mode=ParseMode.HTML
        )
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex("^start_solo_match$"))
async def start_solo_match(client, query):
    chat_id = query.message.chat.id
    user = query.from_user
    match = ACTIVE_MATCHES.get(chat_id)

    if not match or match.get("mode") != "Solo":
        return await query.answer("Invalid match.", show_alert=True)

    if user.id != match["host_id"]:
        return await query.answer("only host can start the match! 👑", show_alert=True)

    if len(match["players"]) < 3:
        return await query.answer("❌ Minimum 3 players required to play solo!", show_alert=True)

    match["phase"] = "LIVE"
    
    await query.message.edit_caption(
        caption="🚀 <b>𝗦𝗢𝗟𝗢 𝗠𝗔𝗧𝗖𝗛 𝗦𝗧𝗔𝗥𝗧𝗘𝗗!</b>\n\nGet ready for the ultimate showdown!",
        parse_mode=ParseMode.HTML
    )
    
    await query.answer("Match is LIVE! 🏏")
    
@Client.on_callback_query(filters.regex("^mode_cancel$"))
async def cancel_start(client, query):
    await query.answer("Cancelled")
    await query.message.delete()

@Client.on_callback_query(filters.regex("^mode_back$"))
async def back_to_start(client, query):
    await query.answer() 
    
    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🏏 Team", callback_data="mode_team"),
                InlineKeyboardButton("👤 Solo", callback_data="mode_solo"),
            ],
            [
                InlineKeyboardButton("✖ Cancel", callback_data="mode_cancel")
            ]
        ]
    )

    try:
        await query.message.edit_media(
            media=InputMediaPhoto(
                media=START_IMAGE_GROUP,
                caption="🎮 **𝗦𝗘𝗟𝗘𝗖𝗧 𝗠𝗢𝗗𝗘**\n`Choose how to play.`"
            ),
            reply_markup=buttons
        )
    except MessageNotModified:
        pass
