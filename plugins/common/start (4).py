from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import random

from config import Config
from database.users import add_user, total_users


START_MOODS = [
    "🏏 𝗪𝗲𝗹𝗰𝗼𝗺𝗲, 𝗖𝗮𝗽𝘁𝗮𝗶𝗻!",
    "✨ 𝗥𝗲𝗮𝗱𝘆 𝘁𝗼 𝗯𝘂𝗶𝗹𝗱 𝘆𝗼𝘂𝗿 𝗰𝗿𝗶𝗰𝗸𝗲𝘁 𝗹𝗲𝗴𝗮𝗰𝘆?",
    "🔥 𝗧𝗵𝗲 𝗽𝗶𝘁𝗰𝗵 𝗶𝘀 𝘀𝗲𝘁. 𝗟𝗲𝘁’𝘀 𝗽𝗹𝗮𝘆!",
]

@Client.on_message(filters.command("start") & filters.private)
async def start_cmd(client: Client, message):
    user = message.from_user
    is_new = await add_user(user.id, user.first_name)

    mood = random.choice(START_MOODS)

    caption = (
        f"{mood}\n"
        "────┈┄┄╌╌╌╌┄┄┈────\n\n"
        f"👤 <b>{user.first_name}</b>, welcome to <b>Cricket Legacy</b> ✨\n\n"
        "🎮 <b>Choose how you want to play</b>\n"
        "• Solo quick matches\n"
        "• Team battles with friends\n"
        "• Live commentary & stats\n\n"
        "🏆 Every run matters.\n"
        "Every match leaves a mark.\n\n"
        "👇 Pick a mode to begin"
    )

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🏏 Solo Mode", callback_data="mode_solo"),
                InlineKeyboardButton("👥 Team Mode", callback_data="mode_team")
            ],
            [
                InlineKeyboardButton("❓ Help & Guide", callback_data="help_main")
            ],
            [
                InlineKeyboardButton(
                    "➕ Add to Group",
                    url=f"https://t.me/{Config.BOT_USERNAME}?startgroup=true"
                )
            ]
        ]
    )

    # 🖼️ Photo → fallback to text
    try:
        await message.reply_photo(
            photo=Config.START_IMAGE,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=buttons
        )
    except Exception:
        try:
            await message.reply_text(
                caption,
                parse_mode=ParseMode.HTML,
                reply_markup=buttons
            )
        except Exception:
            pass

    # 📥 Log new user safely
    if is_new:
        try:
            count = await total_users()
            log_text = (
                "✨ <b>NEW PLAYER JOINED</b>\n\n"
                f"👤 {user.first_name}\n"
                f"🆔 <code>{user.id}</code>\n"
                f"📊 Total Users: {count}"
            )
            await client.send_message(
                Config.LOG_CHANNEL,
                log_text,
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass


from pyrogram import Client, filters
from database.users import add_user

@Client.on_message(filters.private)
async def auto_register_user(client: Client, message):
    user = message.from_user

    # Safety check
    if not user:
        return

    # Silent auto-save (NO reply)
    try:
        await add_user(
            user.id,
            user.first_name
        )
    except Exception:
        pass

@Client.on_message(filters.command("help"))
async def help_cmd(client, message):
    text = (
        "📘 <b>Help & Guide</b>\n\n"
        "Not sure where to start? I got you 😌\n"
        "Pick a topic below and we’ll break it down."
    )

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🎮 How to Play", callback_data="help_play"),
                InlineKeyboardButton("👥 Team Play Mode", callback_data="help_team")
            ],
            [
                InlineKeyboardButton("📋 All Commands", callback_data="help_commands")
            ],
            [
                InlineKeyboardButton("🔙 Back to Menu", callback_data="help_back")
            ]
        ]
    )

    try:
        await message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=buttons
        )
    except Exception:
        pass

@Client.on_callback_query(filters.regex("^help_"))
async def help_callback(client, cb):
    try:
        data = cb.data
        msg = cb.message

        # 🔙 BACK
        if data == "help_back":
            text = (
                "🏏 <b>Cricket Legacy</b>\n\n"
                "Choose how you want to continue 👇"
            )

            buttons = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("🎮 How to Play", callback_data="help_play"),
                        InlineKeyboardButton("👥 Team Play Mode", callback_data="help_team")
                    ],
                    [
                        InlineKeyboardButton("📋 All Commands", callback_data="help_commands")
                    ]
                ]
            )

        # 🎮 HOW TO PLAY
        elif data == "help_play":
            text = (
                "🎮 <b>How to Play</b>\n\n"
                "🏏 <b>During the Game</b>\n"
                "• Solo Mode: Batters choose <b>1–6</b>\n"
                "• Team Mode: Batters choose <b>0–6</b>\n"
                "• Bowlers send <b>1–6</b> in bot DM\n\n"
                "📊 <b>Scoring</b>\n"
                "• Same number = <b>OUT ❌</b>\n"
                "• Batter chooses 0 = Dot ball\n"
                "• Otherwise = runs scored\n\n"
                "✨ <b>Special Rules</b>\n"
                "• Odd runs → strike change\n"
                "• 6 balls = 1 over\n"
                "• Over end → strike change\n\n"
                "⏱ <b>Timeouts</b>\n"
                "• 1 minute per move\n"
                "• 2 timeouts → penalty (±6 runs)\n\n"
                "⚠️ <b>Restriction</b>\n"
                "• 0 is <b>NOT allowed</b> on hat-trick bowling"
            )

            buttons = InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Back", callback_data="help_back")]]
            )

        # 👥 TEAM MODE
        elif data == "help_team":
            text = (
                "👥 <b>Team Play Mode</b>\n\n"
                "Create teams & play cricket with friends 🏏\n\n"
                "🚀 <b>Quick Start</b>\n"
                "1. Use /start\n"
                "2. Select <b>Team Mode</b>\n"
                "3. Click <b>I'm the Host</b>\n"
                "4. Create teams\n"
                "5. Players join Team A or B\n\n"
                "Play together. Win together 🔥"
            )

            buttons = InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Back", callback_data="help_back")]]
            )

        # 📋 COMMAND LIST
        elif data == "help_commands":
            text = (
                "📋 <b>All Commands</b>\n\n"
                "⚙️ <b>Setup</b>\n"
                "/start – Start the bot\n"
                "/create_team – Create teams (host)\n"
                "/join_teamA – Join Team A\n"
                "/join_teamB – Join Team B\n"
                "/choose_cap – Choose captains\n"
                "/set_overs – Set overs\n\n"
                "🎮 <b>Game</b>\n"
                "/teams – View teams\n"
                "/score – Live score\n"
                "/graph – Match graph\n"
                "/endgame – End match\n\n"
                "🏏 <b>Play</b>\n"
                "/batting [user]\n"
                "/bowling [user]"
            )

            buttons = InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Back", callback_data="help_back")]]
            )

        else:
            return await cb.answer("Expired 😴", show_alert=True)

        await msg.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=buttons
        )
        await cb.answer()

    except Exception:
        try:
            await cb.answer("Something glitched 😅", show_alert=True)
        except Exception:
            pass
