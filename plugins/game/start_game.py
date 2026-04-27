"""Group game entry: `/play` opens the mode picker.

`/start` in groups is intentionally NOT a game entry anymore — it just nudges
users to open the bot DM. `/duel` in groups also redirects to DM (1v1 only
runs in DM). Use `/play` in the group to bring up the team / solo picker.
"""

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from Assets.files import START_IMAGE_GROUP
from config import Config
from database.games import is_game_active


_BOT_USERNAME = Config.BOT_USERNAME.lstrip("@")
_DM_LINK = f"https://t.me/{_BOT_USERNAME}"


def _mode_buttons() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🏏 Team", callback_data="mode_team"),
                InlineKeyboardButton("👤 Solo", callback_data="mode_solo"),
            ],
            [
                InlineKeyboardButton(
                    "⚔️ 1v1 Duel (DM)",
                    url=f"{_DM_LINK}?start=duel",
                ),
            ],
            [InlineKeyboardButton("✖ Cancel", callback_data="mode_cancel")],
        ]
    )


def _dm_redirect_buttons(payload: str = "") -> InlineKeyboardMarkup:
    url = f"{_DM_LINK}?start={payload}" if payload else _DM_LINK
    return InlineKeyboardMarkup([[InlineKeyboardButton("📩 Open bot in DM", url=url)]])


async def _bot_can_send_media(client: Client, chat_id: int) -> bool:
    try:
        me = await client.get_me()
        member = await client.get_chat_member(chat_id, me.id)
        if member.status.name == "ADMINISTRATOR":
            return getattr(member.privileges, "can_send_media_messages", True) is not False
        return True
    except Exception:
        return True


# ─── /start in groups → DM redirect (not a game entry anymore) ───────────────

@Client.on_message(filters.command("start") & filters.group)
async def start_in_group(client: Client, message):
    await message.reply_text(
        "👋 <b>Hey!</b>\n"
        "──┈┄┄╌╌╌╌┄┄┈──\n"
        "<code>/start</code> works in <b>my DM</b>.\n"
        "To start a match here, use <code>/play</code> 🏏",
        parse_mode=ParseMode.HTML,
        reply_markup=_dm_redirect_buttons(),
    )


# ─── /play → mode picker (the old /start behavior) ───────────────────────────

@Client.on_message(filters.command(["play", "newgame"]) & filters.group)
async def play_cmd(client: Client, message):
    chat_id = message.chat.id

    if await is_game_active(chat_id):
        return await message.reply_text(
            "⚠️ <b>Game already running</b>\nFinish the current match first 🏏",
            parse_mode=ParseMode.HTML,
        )

    caption = (
        "🎮 <b>SELECT MODE</b>\n"
        "──┈┄┄╌╌╌╌┄┄┈──\n"
        "Choose how you want to play 👇\n\n"
        "⚔️ <i>1v1 Duel runs in the bot DM — tap the button to queue.</i>"
    )

    if await _bot_can_send_media(client, chat_id):
        try:
            await message.reply_photo(
                photo=START_IMAGE_GROUP,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=_mode_buttons(),
            )
            return
        except Exception:
            pass

    await message.reply_text(
        caption,
        parse_mode=ParseMode.HTML,
        reply_markup=_mode_buttons(),
    )


@Client.on_callback_query(filters.regex("^mode_cancel$"))
async def cancel_start(client, query):
    try:
        await query.message.delete()
    except Exception:
        try:
            await query.message.edit_text("✖ Cancelled.")
        except Exception:
            pass
    await query.answer("Cancelled")
