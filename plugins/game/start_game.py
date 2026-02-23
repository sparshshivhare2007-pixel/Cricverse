from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from Assets.files import START_IMAGE_GROUP, SOLO_MODE_IMAGE
from database.games import is_game_active
from pyrogram.types import Message

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

ALLOWED_GROUP = -1003692127639

@Client.on_message(filters.command("start") & filters.group)
async def start_game(client, message):
    chat_id = message.chat.id

    # 🔒 If not allowed group → maintenance message
    if chat_id != ALLOWED_GROUP:
        return await message.reply_text(
            "🚧 <b>Game Under Maintenance</b>\n\n"
            "Please use 👉 @cricketlegacybot for now.",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )

    # ✅ Normal Game Flow (only for allowed group)
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
    await query.answer("Solo mode is currently under development.")

    await query.message.edit_media(
        media=InputMediaPhoto(
            media=SOLO_MODE_IMAGE,
            caption=(
                "👤 **𝗦𝗢𝗟𝗢 𝗠𝗢𝗗𝗘**\n"
                "`Coming soon in the next update!`"
            )
        ),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="mode_back")]])
    )

@Client.on_callback_query(filters.regex("^mode_cancel$"))
async def cancel_start(client, query):
    await query.answer("Cancelled")
    await query.message.delete()

@Client.on_callback_query(filters.regex("^mode_back$"))
async def back_to_start(client, query):
    """Returns user to the initial mode selection."""
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
    await query.message.edit_media(
        media=InputMediaPhoto(
            media=START_IMAGE_GROUP,
            caption="🎮 **𝗦𝗘𝗟𝗘𝗖𝗧 𝗠𝗢𝗗𝗘**\n`Choose how to play.`"
        ),
        reply_markup=buttons
    )
