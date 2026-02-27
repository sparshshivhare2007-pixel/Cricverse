import io
import time
import traceback
from PIL import Image, ImageDraw, ImageFont
from pyrogram import Client, filters

from database.users import total_users
from database.groups import total_groups
from database.connection import db

FONT_PATH = "Assets/fonts.ttf"
OWNER_ID = 8294062042
BOT_START_TIME = time.time()

BG_COLOR = (14, 10, 20)
PURPLE = (155, 89, 255)
WHITE = (240, 240, 240)
MUTED = (170, 170, 170)

def get_uptime():
    secs = int(time.time() - BOT_START_TIME)
    h = secs // 3600
    m = (secs % 3600) // 60
    return f"{h}h {m}m"

def build_stats_image(users, groups, games_today, games_total, active_games, uptime):
    img = Image.new("RGB", (1280, 720), BG_COLOR)
    draw = ImageDraw.Draw(img)

    try:
        font_big = ImageFont.truetype(FONT_PATH, 90)
        font_mid = ImageFont.truetype(FONT_PATH, 48)
        font_small = ImageFont.truetype(FONT_PATH, 34)
    except Exception:
        font_big = font_mid = font_small = ImageFont.load_default()

    draw.text((640, 60), "CRICKET LEGACY",
              font=font_mid, fill=PURPLE, anchor="mm")

    draw.ellipse((490, 140, 790, 440), outline=PURPLE, width=8)
    draw.text((640, 250), str(users), font=font_big, fill=WHITE, anchor="mm")
    draw.text((640, 320), "PLAYERS", font=font_mid, fill=MUTED, anchor="mm")

    y1 = 500
    y2 = 560

    draw.text((250, y1), f"👥 Groups: {groups}", font=font_small, fill=WHITE, anchor="mm")
    draw.text((640, y1), f"🎮 Games Today: {games_today}", font=font_small, fill=WHITE, anchor="mm")
    draw.text((1030, y1), f"⚡ Active Games: {active_games}", font=font_small, fill=WHITE, anchor="mm")

    draw.text((250, y2), f"📊 Total Games: {games_total}", font=font_small, fill=WHITE, anchor="mm")
    draw.text((640, y2), f"⏱ Uptime: {uptime}", font=font_small, fill=WHITE, anchor="mm")
    draw.text((1030, y2), "🟢 System: Stable", font=font_small, fill=WHITE, anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

@Client.on_message(filters.command("stats"))
async def stats_cmd(client, message):
    loading = None
    try:
        try:
            loading = await message.reply_text("🌀 Pulling live system stats…")
        except Exception:
            pass

        users = groups = games_today = games_total = active_games = 0

        try:
            users = await total_users()
        except Exception:
            users = 0
            
        try:
            groups = await total_groups()
        except Exception:
            groups = 0

        try:
            async with db.pool.acquire() as conn:
                games_today = await conn.fetchval(
                    "SELECT COUNT(*) FROM games WHERE created_at::date = CURRENT_DATE"
                ) or 0

                games_total = await conn.fetchval(
                    "SELECT COUNT(*) FROM games"
                ) or 0

                active_games = await conn.fetchval(
                    "SELECT COUNT(*) FROM games WHERE status = 'active'"
                ) or 0
        except Exception:
            pass

        uptime = get_uptime()

        img = build_stats_image(
            users=users,
            groups=groups,
            games_today=games_today,
            games_total=games_total,
            active_games=active_games,
            uptime=uptime
        )

        if loading:
            try:
                await loading.delete()
            except Exception:
                pass

        await client.send_photo(
            chat_id=message.chat.id,
            photo=img
        )

    except Exception:
        print("❌ /stats CRITICAL ERROR")
        traceback.print_exc()

        try:
            if loading:
                await loading.edit_text(
                    "⚠️ Stats are temporarily unavailable.\nTry again in a bit."
                )
            else:
                await message.reply_text(
                    "⚠️ Stats are temporarily unavailable.\nTry again in a bit."
                )
        except Exception:
            pass
