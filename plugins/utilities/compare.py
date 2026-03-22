import asyncio
import io
import html
import httpx
from PIL import Image, ImageDraw, ImageFont
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from database.connection import db
import os

ASSETS = os.path.join(os.path.dirname(__file__), "..", "..", "Assets")
FONT_PATH = os.path.join(ASSETS, "namefont.ttf")

CW, CH = 920, 540

SEARCH_FRAMES = [
    "🔍 Scanning scorecards…",
    "📊 Crunching numbers…",
    "⚔️ Analyzing rivalry…",
    "🔥 Building compare card…"
]


def _font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()


def _circle_mask(size):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size - 1, size - 1), fill=255)
    return m


def _draw_glow_ring(img: Image.Image, cx, cy, radius, color, thickness=6):
    draw = ImageDraw.Draw(img, "RGBA")
    for i in range(thickness, 0, -1):
        alpha = int(200 * (i / thickness))
        draw.ellipse(
            (cx - radius - i, cy - radius - i, cx + radius + i, cy + radius + i),
            outline=color + (alpha,),
            width=2,
        )


async def _fetch_avatar(client, user_id) -> Image.Image | None:
    try:
        photos = await client.get_profile_photos(user_id, limit=1)
        if not photos:
            return None
        file_path = await client.download_media(photos[0].file_id, in_memory=True)
        return Image.open(io.BytesIO(bytes(file_path))).convert("RGBA")
    except Exception:
        return None


def _paste_avatar(card: Image.Image, avatar: Image.Image | None, cx, cy, size=130, ring_color=(255, 200, 50)):
    r = size // 2
    mask = _circle_mask(size)

    if avatar:
        av = avatar.convert("RGBA").resize((size, size), Image.LANCZOS)
    else:
        av = Image.new("RGBA", (size, size), (50, 50, 60, 255))
        d = ImageDraw.Draw(av)
        d.ellipse((0, 0, size - 1, size - 1), fill=(70, 70, 85))
        d.text((size // 2, size // 2), "?", fill=(200, 200, 200), font=_font(50), anchor="mm")

    av.putalpha(mask)
    _draw_glow_ring(card, cx, cy, r, ring_color[:3], thickness=5)
    card.paste(av, (cx - r, cy - r), av)


def build_compare_card(
    av1: Image.Image | None,
    av2: Image.Image | None,
    name1: str,
    name2: str,
    fields: list,
    score1: int,
    score2: int,
) -> io.BytesIO:
    card = Image.new("RGBA", (CW, CH), (15, 17, 25, 255))
    d = ImageDraw.Draw(card, "RGBA")

    def poly(pts, color, alpha=255):
        d.polygon(pts, fill=color + (alpha,))

    ac1 = (255, 80, 80)
    ac2 = (80, 160, 255)
    gold = (255, 215, 0)
    mid = (160, 140, 200)

    poly([(0, 0), (360, 0), (280, CH), (0, CH)], ac1, 30)
    poly([(0, 0), (200, 0), (140, CH), (0, CH)], ac1, 20)
    poly([(CW, 0), (CW - 360, 0), (CW - 280, CH), (CW, CH)], ac2, 30)
    poly([(CW, 0), (CW - 200, 0), (CW - 140, CH), (CW, CH)], ac2, 20)
    poly([(CW // 2 - 14, 0), (CW // 2 + 14, 0), (CW // 2 + 10, CH), (CW // 2 - 10, CH)], mid, 35)
    poly([(CW // 2 - 5, 0), (CW // 2 + 5, 0), (CW // 2 + 3, CH), (CW // 2 - 3, CH)], mid, 60)

    d.line([(0, 260), (CW, 260)], fill=(60, 60, 80, 120), width=1)

    _paste_avatar(card, av1, 155, 130, size=130, ring_color=ac1)
    _paste_avatar(card, av2, CW - 155, 130, size=130, ring_color=ac2)

    n1 = name1[:14]
    n2 = name2[:14]
    d.text((155, 205), n1, fill=ac1, font=_font(22), anchor="mm")
    d.text((CW - 155, 205), n2, fill=ac2, font=_font(22), anchor="mm")

    d.text((CW // 2, 100), "⚔", fill=gold, font=_font(42), anchor="mm")
    d.text((CW // 2, 150), "VS", fill=gold, font=_font(36), anchor="mm")

    sc1_color = gold if score1 > score2 else (180, 180, 180)
    sc2_color = gold if score2 > score1 else (180, 180, 180)
    d.text((155, 230), f"{score1} pts", fill=sc1_color, font=_font(18), anchor="mm")
    d.text((CW - 155, 230), f"{score2} pts", fill=sc2_color, font=_font(18), anchor="mm")

    y = 280
    row_h = 36
    for i, (label, v1, v2, higher_better) in enumerate(fields):
        bg = (25, 27, 38, 200) if i % 2 == 0 else (20, 22, 32, 200)
        d.rectangle([(0, y), (CW, y + row_h - 2)], fill=bg)

        if abs(float(v1 if isinstance(v1, (int, float)) else 0) - float(v2 if isinstance(v2, (int, float)) else 0)) < 0.01:
            c1 = c2 = (200, 200, 200)
        elif (v1 >= v2 if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) else False) if higher_better else (v1 <= v2 if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) else False):
            c1, c2 = gold, (180, 180, 180)
        else:
            c1, c2 = (180, 180, 180), gold

        mid_y = y + row_h // 2
        lbl_str = str(label)[:16]
        d.text((CW // 2, mid_y), lbl_str, fill=(200, 200, 220), font=_font(15), anchor="mm")

        v1_str = f"{float(v1):.1f}" if isinstance(v1, float) else str(v1)
        v2_str = f"{float(v2):.1f}" if isinstance(v2, float) else str(v2)
        d.text((CW // 2 - 160, mid_y), v1_str, fill=c1, font=_font(17), anchor="mm")
        d.text((CW // 2 + 160, mid_y), v2_str, fill=c2, font=_font(17), anchor="mm")

        y += row_h

    if score1 > score2:
        verdict = f"{name1} leads"
        vc = ac1
    elif score2 > score1:
        verdict = f"{name2} leads"
        vc = ac2
    else:
        verdict = "Dead heat 🔥"
        vc = gold

    if y + 35 <= CH:
        d.rectangle([(0, y), (CW, CH)], fill=(10, 12, 20))
        d.text((CW // 2, y + 18), verdict, fill=vc, font=_font(20), anchor="mm")

    buf = io.BytesIO()
    card.convert("RGB").save(buf, format="JPEG", quality=90)
    buf.seek(0)
    return buf


@Client.on_message(filters.command("compare"))
async def head2head_cmd(client, message):
    args = message.command[1:]
    users = []

    try:
        if message.reply_to_message and message.reply_to_message.from_user:
            users = [message.from_user, message.reply_to_message.from_user]
        elif len(args) == 1:
            u2 = await client.get_users(args[0])
            users = [message.from_user, u2]
        elif len(args) >= 2:
            u1 = await client.get_users(args[0])
            u2 = await client.get_users(args[1])
            users = [u1, u2]
        else:
            return await message.reply_text(
                "❌ Use <code>/compare @user</code> or reply to someone",
                parse_mode=ParseMode.HTML
            )
    except Exception:
        return await message.reply_text("❌ Invalid user(s). Try username or user_id.")

    u1, u2 = users
    uid1, uid2 = u1.id, u2.id

    loading = await message.reply_text("🔍 Initializing comparison…")
    for frame in SEARCH_FRAMES:
        await asyncio.sleep(0.5)
        try:
            await loading.edit_text(frame)
        except Exception:
            pass

    async with db.pool.acquire() as conn:
        s1 = await conn.fetchrow("SELECT * FROM user_stats WHERE user_id=$1", uid1)
        s2 = await conn.fetchrow("SELECT * FROM user_stats WHERE user_id=$1", uid2)

    if not s1 or not s2:
        return await loading.edit_text(
            "⚠️ One or both players have no stats yet.\nPlay some matches first 🏏"
        )

    def safe(v):
        return v or 0

    def batting_avg(s):
        outs = max(1, safe(s["matches"]) - safe(s.get("not_outs", 0)))
        return safe(s["runs"]) / outs

    def strike_rate(s):
        return (safe(s["runs"]) / safe(s["balls_faced"]) * 100) if safe(s["balls_faced"]) > 0 else 0.0

    def economy(s):
        return (safe(s["runs_conceded"]) / (safe(s["balls_bowled"]) / 6)) if safe(s["balls_bowled"]) > 0 else 99.0

    def win_rate(s):
        return (safe(s["wins"]) / safe(s["matches"]) * 100) if safe(s["matches"]) > 0 else 0.0

    fields_raw = [
        ("🏃 Runs",         s1["runs"],       s2["runs"],       True),
        ("⚾ Wickets",      s1["wickets"],    s2["wickets"],    True),
        ("📈 Avg",           batting_avg(s1),  batting_avg(s2),  True),
        ("⚡ SR",            strike_rate(s1),  strike_rate(s2),  True),
        ("🎯 Economy",       economy(s1),      economy(s2),      False),
        ("🎩 Hat-Tricks",    safe(s1.get("hat_tricks", 0)), safe(s2.get("hat_tricks", 0)), True),
        ("🏅 MOMs",          safe(s1["moms"]), safe(s2["moms"]), True),
        ("🦆 Ducks",         safe(s1["ducks"]),safe(s2["ducks"]),False),
        ("🎮 Matches",       safe(s1["matches"]), safe(s2["matches"]), True),
        ("🏆 Win Rate",      win_rate(s1),     win_rate(s2),     True),
    ]

    score1 = score2 = 0
    lines = []

    for label, v1, v2, higher_better in fields_raw:
        fv1 = float(v1) if isinstance(v1, (int, float)) else 0.0
        fv2 = float(v2) if isinstance(v2, (int, float)) else 0.0

        if abs(fv1 - fv2) < 0.01:
            mark = "➖"
        elif (fv1 > fv2 and higher_better) or (fv1 < fv2 and not higher_better):
            score1 += 1
            mark = "✅"
        else:
            score2 += 1
            mark = "❌"

        val1 = f"{fv1:.1f}" if isinstance(v1, float) else str(v1)
        val2 = f"{fv2:.1f}" if isinstance(v2, float) else str(v2)
        sym = ">" if mark == "✅" else "<" if mark == "❌" else "="
        lines.append(f"• {label:<14}:  {val1}  {sym}  {val2}  {mark}")

    if score1 > score2:
        verdict = f"{html.escape(u1.first_name)} dominates 😤"
    elif score2 > score1:
        verdict = f"{html.escape(u2.first_name)} takes the edge 🔥"
    else:
        verdict = "Too close to call 🤝"

    caption = (
        "⚔️ <b>𝗛𝗘𝗔𝗗 𝗧𝗢 𝗛𝗘𝗔𝗗</b>\n\n"
        f"🔴 {html.escape(u1.first_name)}  <b>{score1}</b> 🆚 <b>{score2}</b>  🔵 {html.escape(u2.first_name)}\n"
        "────┈┄┄╌╌╌╌┄┄┈────\n\n"
        "📊 <b>𝗦𝗧𝗔𝗧𝗦</b>\n"
        + "\n".join(lines)
        + f"\n\n🔥 <b>𝗩𝗘𝗥𝗗𝗜𝗖𝗧:</b> {verdict}"
    )

    try:
        av1, av2 = await asyncio.gather(
            _fetch_avatar(client, uid1),
            _fetch_avatar(client, uid2),
        )
        loop = asyncio.get_event_loop()
        card_fields = [(lbl, v1, v2, hb) for lbl, v1, v2, hb in fields_raw]
        buf = await loop.run_in_executor(
            None,
            lambda: build_compare_card(
                av1, av2,
                u1.first_name, u2.first_name,
                card_fields, score1, score2,
            )
        )
        await loading.delete()
        await message.reply_photo(photo=buf, caption=caption, parse_mode=ParseMode.HTML)
    except Exception as e:
        print(f"Compare card error: {e}")
        await loading.edit_text(caption, parse_mode=ParseMode.HTML)
