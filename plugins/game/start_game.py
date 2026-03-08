From pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from pyrogram.enums import ParseMode
from pyrogram.errors import MessageNotModified 
from Assets.files import START_IMAGE_GROUP
from database.games import is_game_active

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
