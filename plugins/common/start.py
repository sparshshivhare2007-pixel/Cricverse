import random
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database.users import add_user, total_users

PLAYZONE_LINK = "https://t.me/CLG_fun_zone"
SUPPORT_LINK = "https://t.me/Nexxxxxo_bots"

START_MOODS = [
    "🏏 𝗪𝗲𝗹𝗰𝗼𝗺𝗲, 𝗖𝗮𝗽𝘁𝗮𝗶𝗻!",
    "✨ 𝗥𝗲𝗮𝗱𝘆 𝘁𝗼 𝗯𝘂𝗶𝗹𝗱 𝘆𝗼𝘂𝗿 𝗰𝗿𝗶𝗰𝗸𝗲𝘁 𝗹𝗲𝗴𝗮𝗰𝘆?",
    "🔥 𝗧𝗵𝗲 𝗽𝗶𝘁𝗰𝗵 𝗶𝘀 𝘀𝗲𝘁. 𝗟𝗲𝘁’𝘀 𝗽𝗹𝗮𝘆!",
]

@Client.on_message(filters.command("start") & filters.private)
async def start_cmd(client: Client, message):
    user = message.from_user
    first_name = user.first_name or "Captain"

    is_new = await add_user(user.id, first_name)
    mood = random.choice(START_MOODS)

    caption = (
        f"{mood}\n"
        "────┈┄┄╌╌╌╌┄┄┈────\n\n"
        f"👤 <b>{first_name}</b>, welcome to <b>Cricket Legacy</b> ✨\n\n"
        "🏏 <b>Cricket Legacy v2</b>\n"
        "🚧 <i>Beta Launch</i>\n\n"
        "🎮 Play epic team matches\n"
        "📊 Track stats & achievements\n"
        "🎙 Live match vibes & action\n\n"
        "🐞 Found a bug?\n"
        "Report it in <b>PlayZone</b>\n\n"
        "👇 Use the buttons below"
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🧩 PlayZone", url=PLAYZONE_LINK),
            InlineKeyboardButton("🆘 Support", url=SUPPORT_LINK)
        ],
        [
            InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{Config.BOT_USERNAME.replace('@','')}?startgroup=true")
        ]
    ])

    try:
        await message.reply_photo(
            photo=Config.START_IMAGE,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=buttons
        )
    except Exception:
        await message.reply_text(caption, parse_mode=ParseMode.HTML, reply_markup=buttons)

    if is_new:
        try:
            count = await total_users()
            log_text = (
                "✨ <b>NEW PLAYER JOINED</b>\n\n"
                f"👤 {first_name}\n"
                f"🆔 <code>{user.id}</code>\n"
                f"📊 Total Users: {count}"
            )
            await client.send_message(Config.LOG_CHANNEL, log_text, parse_mode=ParseMode.HTML)
        except Exception:
            pass

@Client.on_message(filters.private, group=1)
async def auto_register_user(client: Client, message):
    user = message.from_user
    if not user:
        return
    try:
        await add_user(user.id, user.first_name)
    except Exception:
        pass
        
