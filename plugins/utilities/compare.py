import asyncio
import io
import math
import html
import random
import os
from PIL import Image, ImageDraw, ImageFont
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from database.connection import db

ASSETS = os.path.join(os.path.dirname(__file__), "..", "..", "Assets")
FONT_PATH = os.path.join(ASSETS, "namefont.ttf")

CW, CH = 920, 560


def _font(size: int):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()


def _circle_mask(size: int) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size - 1, size - 1), fill=255)
    return m


def _glow_ring(img: Image.Image, cx, cy, r, rgb, thickness=6):
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(thickness, 0, -1):
        a = int(230 * (i / thickness))
        d.ellipse((cx - r - i, cy - r - i, cx + r + i, cy + r + i), outline=rgb + (a,), width=2)
    img.paste(ov, mask=ov.split()[3])


def _paste_avatar(card, photo_data, cx, cy, size=120, ring_rgb=(255, 200, 0)):
    r = size // 2
    mask = _circle_mask(size)

    av = None
    if photo_data is not None:
        try:
            raw = photo_data.read() if hasattr(photo_data, "read") else bytes(photo_data)
            av = Image.open(io.BytesIO(raw)).convert("RGBA").resize((size, size), Image.LANCZOS)
        except Exception:
            av = None

    if av is None:
        av = Image.new("RGBA", (size, size), (50, 50, 65, 255))
        dd = ImageDraw.Draw(av)
        dd.ellipse((0, 0, size - 1, size - 1), fill=(70, 70, 90))

    av.putalpha(mask)
    _glow_ring(card, cx, cy, r, ring_rgb, thickness=5)
    card.paste(av, (cx - r, cy - r), av)


def _draw_field_rows(card, rows, c1, c2, winner_idx):
    """Draw 5 stat comparison rows on the lower portion of the card."""
    d = ImageDraw.Draw(card, "RGBA")
    fx = 80
    col_cx1, col_cx2, col_mid = 190, CW - 190, CW // 2
    fy = 310
    rh = 46

    for i, (label, v1, v2, hw) in enumerate(rows):
        y = fy + i * rh
        bg = (22, 24, 36, 210) if i % 2 == 0 else (16, 18, 28, 200)
        d.rectangle([(0, y), (CW, y + rh - 2)], fill=bg)

        fv1 = float(v1) if isinstance(v1, (int, float)) else 0.0
        fv2 = float(v2) if isinstance(v2, (int, float)) else 0.0
        tie = abs(fv1 - fv2) < 0.01
        p1_wins = (fv1 > fv2 if hw else fv1 < fv2) if not tie else False

        gold = (255, 215, 0)
        dim  = (140, 140, 160)
        tc1 = gold if (p1_wins and not tie) else (dim if tie else dim)
        tc2 = gold if (not p1_wins and not tie) else (dim if tie else dim)

        vs1 = f"{fv1:.1f}" if isinstance(v1, float) else str(v1)
        vs2 = f"{fv2:.1f}" if isinstance(v2, float) else str(v2)

        mid_y = y + rh // 2

        d.text((col_cx1, mid_y), vs1, fill=tc1 if c1 else (220,220,220), font=_font(20), anchor="mm")
        d.text((col_mid, mid_y), str(label), fill=(190, 190, 210), font=_font(14), anchor="mm")
        d.text((col_cx2, mid_y), vs2, fill=tc2 if c2 else (220,220,220), font=_font(20), anchor="mm")

    return card


# ─────────────────────────────────────────────────────────────────────────────
#  DESIGN A — NEON DARK  (deep space, neon side glow panels)
# ─────────────────────────────────────────────────────────────────────────────

def _design_neon_dark(av1, av2, n1, n2, score1, score2, rows):
    C1 = (255, 60, 100)
    C2 = (60, 140, 255)
    bg = (8, 9, 18)

    card = Image.new("RGBA", (CW, CH), bg + (255,))
    ov = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    def poly(pts, c, a):
        d.polygon(pts, fill=c + (a,))

    # Left glowing panel
    poly([(0, 0), (300, 0), (250, CH), (0, CH)], C1, 28)
    poly([(0, 0), (180, 0), (140, CH), (0, CH)], C1, 20)
    poly([(0, 0), (60, 0), (40, CH), (0, CH)], C1, 40)
    # Right glowing panel
    poly([(CW, 0), (CW - 300, 0), (CW - 250, CH), (CW, CH)], C2, 28)
    poly([(CW, 0), (CW - 180, 0), (CW - 140, CH), (CW, CH)], C2, 20)
    poly([(CW, 0), (CW - 60, 0), (CW - 40, CH), (CW, CH)], C2, 40)
    # Center divider
    cx = CW // 2
    poly([(cx - 16, 0), (cx + 16, 0), (cx + 12, CH), (cx - 12, CH)], (120, 100, 200), 30)
    poly([(cx - 5, 0), (cx + 5, 0), (cx + 4, CH), (cx - 4, CH)], (180, 160, 255), 70)
    # Header / footer bars
    poly([(0, 0), (CW, 0), (CW, 60), (0, 75)], (20, 20, 35), 200)
    poly([(0, CH - 55), (CW, CH - 42), (CW, CH), (0, CH)], (20, 20, 35), 200)

    card.paste(ov, mask=ov.split()[3])

    _paste_avatar(card, av1, 155, 190, size=120, ring_rgb=C1[:3])
    _paste_avatar(card, av2, CW - 155, 190, size=120, ring_rgb=C2[:3])

    d2 = ImageDraw.Draw(card)
    d2.text((155, 270), n1[:14], fill=C1, font=_font(22), anchor="mm")
    d2.text((CW - 155, 270), n2[:14], fill=C2, font=_font(22), anchor="mm")

    sc1_c = (255, 215, 0) if score1 >= score2 else (150, 150, 170)
    sc2_c = (255, 215, 0) if score2 >= score1 else (150, 150, 170)
    d2.text((155, 296), f"{score1} pts", fill=sc1_c, font=_font(15), anchor="mm")
    d2.text((CW - 155, 296), f"{score2} pts", fill=sc2_c, font=_font(15), anchor="mm")

    d2.text((CW // 2, 15), "⚔  HEAD TO HEAD  ⚔", fill=(200, 190, 255), font=_font(20), anchor="mm")
    d2.text((CW // 2, 40), "Nexora Cricket", fill=(80, 80, 110), font=_font(12), anchor="mm")

    _draw_field_rows(card, rows, C1[:3], C2[:3], score1 > score2)

    # Verdict bar
    if score1 > score2:
        vtext = f"🏆 {n1} dominates"
        vc = C1
    elif score2 > score1:
        vtext = f"🏆 {n2} takes the edge"
        vc = C2
    else:
        vtext = "⚖️ Dead Heat"
        vc = (200, 200, 255)
    d2.text((CW // 2, CH - 22), vtext, fill=vc, font=_font(18), anchor="mm")

    buf = io.BytesIO()
    card.convert("RGB").save(buf, format="JPEG", quality=92)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
#  DESIGN B — STADIUM  (dark center pitch, burning side colors)
# ─────────────────────────────────────────────────────────────────────────────

def _design_stadium(av1, av2, n1, n2, score1, score2, rows):
    C1 = (255, 90, 0)
    C2 = (0, 180, 255)
    bg = (6, 10, 8)

    card = Image.new("RGBA", (CW, CH), bg + (255,))
    ov = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    def poly(pts, c, a):
        d.polygon(pts, fill=c + (a,))

    # Stadium arc — oval green pitch overlay in center
    d.ellipse([(CW // 2 - 260, 60), (CW // 2 + 260, 310)], fill=(15, 45, 15, 120), outline=(40, 120, 40, 60), width=2)
    d.ellipse([(CW // 2 - 160, 90), (CW // 2 + 160, 280)], fill=(20, 60, 20, 80))

    # Diagonal fire sweeps from left
    for i in range(5):
        ox = i * 55
        poly([(ox, 0), (ox + 90, 0), (ox - 80, CH), (ox - 140, CH)], C1, 18 - i * 2)

    # Diagonal ice sweeps from right
    for i in range(5):
        ox = CW - i * 55
        poly([(ox, 0), (ox - 90, 0), (ox + 80, CH), (ox + 140, CH)], C2, 18 - i * 2)

    # Header bright band
    poly([(0, 0), (CW, 0), (CW, 58), (0, 74)], (10, 14, 10), 230)
    poly([(0, CH - 52), (CW, CH - 40), (CW, CH), (0, CH)], (10, 14, 10), 230)

    # Center seam line (pitch)
    d.line([(CW // 2, 80), (CW // 2, 295)], fill=(100, 160, 100, 80), width=2)

    card.paste(ov, mask=ov.split()[3])

    _paste_avatar(card, av1, 145, 188, size=120, ring_rgb=C1[:3])
    _paste_avatar(card, av2, CW - 145, 188, size=120, ring_rgb=C2[:3])

    d2 = ImageDraw.Draw(card)
    d2.text((145, 268), n1[:14], fill=C1, font=_font(22), anchor="mm")
    d2.text((CW - 145, 268), n2[:14], fill=C2, font=_font(22), anchor="mm")
    sc1_c = (255, 215, 0) if score1 >= score2 else (160, 140, 100)
    sc2_c = (255, 215, 0) if score2 >= score1 else (160, 140, 100)
    d2.text((145, 293), f"{score1} pts", fill=sc1_c, font=_font(15), anchor="mm")
    d2.text((CW - 145, 293), f"{score2} pts", fill=sc2_c, font=_font(15), anchor="mm")

    d2.text((CW // 2, 185), "VS", fill=(255, 215, 0), font=_font(42), anchor="mm")
    d2.text((CW // 2, 16), "🏟  CRICKET CLASH", fill=(200, 240, 200), font=_font(20), anchor="mm")
    d2.text((CW // 2, 40), "Nexora Stadium", fill=(70, 110, 70), font=_font(12), anchor="mm")

    _draw_field_rows(card, rows, C1[:3], C2[:3], score1 > score2)

    if score1 > score2:
        vt = f"🔥 {n1} wins this clash"
        vc = C1
    elif score2 > score1:
        vt = f"💧 {n2} wins this clash"
        vc = C2
    else:
        vt = "⚖️ Perfect Tie!"
        vc = (200, 255, 200)
    d2.text((CW // 2, CH - 22), vt, fill=vc, font=_font(18), anchor="mm")

    buf = io.BytesIO()
    card.convert("RGB").save(buf, format="JPEG", quality=92)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
#  DESIGN C — BATTLE CLASH  (bold split, geometric arrows)
# ─────────────────────────────────────────────────────────────────────────────

def _design_battle_clash(av1, av2, n1, n2, score1, score2, rows):
    C1 = (180, 30, 255)
    C2 = (255, 200, 0)
    bg = (10, 8, 18)

    card = Image.new("RGBA", (CW, CH), bg + (255,))
    ov = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    def poly(pts, c, a):
        d.polygon(pts, fill=c + (a,))

    # Starburst from center-top
    cx, cy = CW // 2, 190
    for angle in range(0, 360, 22):
        rad = math.radians(angle)
        rad2 = math.radians(angle + 11)
        r1, r2 = 250, 180
        x1 = int(cx + r1 * math.cos(rad))
        y1 = int(cy + r1 * math.sin(rad))
        x2 = int(cx + r2 * math.cos(rad2))
        y2 = int(cy + r2 * math.sin(rad2))
        shade = C1 if angle % 44 < 22 else C2
        poly([(cx, cy), (x1, y1), (x2, y2)], shade, 18)

    # Hard split left / right
    poly([(0, 0), (CW // 2, 0), (CW // 2 - 30, CH), (0, CH)], C1, 30)
    poly([(0, 0), (CW // 2, 0), (CW // 2 - 60, CH), (0, CH)], C1, 18)
    poly([(CW, 0), (CW // 2, 0), (CW // 2 + 30, CH), (CW, CH)], C2, 30)
    poly([(CW, 0), (CW // 2, 0), (CW // 2 + 60, CH), (CW, CH)], C2, 18)

    # Header
    poly([(0, 0), (CW, 0), (CW, 62), (0, 80)], (15, 12, 28), 230)
    poly([(0, CH - 55), (CW, CH - 42), (CW, CH), (0, CH)], (15, 12, 28), 230)

    # Center lightning bolt shape
    bolt = [(cx - 6, 80), (cx + 18, 175), (cx - 2, 175), (cx + 22, 305), (cx - 22, 175), (cx + 2, 175)]
    d.polygon(bolt, fill=(255, 255, 255, 40))

    card.paste(ov, mask=ov.split()[3])

    _paste_avatar(card, av1, 145, 190, size=120, ring_rgb=C1[:3])
    _paste_avatar(card, av2, CW - 145, 190, size=120, ring_rgb=C2[:3])

    d2 = ImageDraw.Draw(card)
    d2.text((145, 270), n1[:14], fill=C1, font=_font(22), anchor="mm")
    d2.text((CW - 145, 270), n2[:14], fill=C2, font=_font(22), anchor="mm")
    sc1_c = (255, 255, 255) if score1 >= score2 else (140, 120, 160)
    sc2_c = (255, 255, 255) if score2 >= score1 else (140, 120, 160)
    d2.text((145, 295), f"{score1} pts", fill=sc1_c, font=_font(15), anchor="mm")
    d2.text((CW - 145, 295), f"{score2} pts", fill=sc2_c, font=_font(15), anchor="mm")

    d2.text((CW // 2, 16), "⚡  BATTLE CLASH  ⚡", fill=(230, 210, 255), font=_font(20), anchor="mm")
    d2.text((CW // 2, 42), "Nexora Rivalry", fill=(90, 70, 120), font=_font(12), anchor="mm")

    _draw_field_rows(card, rows, C1[:3], C2[:3], score1 > score2)

    if score1 > score2:
        vt = f"⚡ {n1} reigns supreme"
        vc = C1
    elif score2 > score1:
        vt = f"⚡ {n2} reigns supreme"
        vc = C2
    else:
        vt = "⚡ Sparks fly — it's a tie!"
        vc = (230, 210, 255)
    d2.text((CW // 2, CH - 22), vt, fill=vc, font=_font(18), anchor="mm")

    buf = io.BytesIO()
    card.convert("RGB").save(buf, format="JPEG", quality=92)
    buf.seek(0)
    return buf


DESIGNS = [_design_neon_dark, _design_stadium, _design_battle_clash]


def build_compare_card(av1, av2, n1, n2, score1, score2, rows) -> io.BytesIO:
    fn = random.choice(DESIGNS)
    return fn(av1, av2, n1, n2, score1, score2, rows)


# ─────────────────────────────────────────────────────────────────────────────
#  /compare  command
# ─────────────────────────────────────────────────────────────────────────────

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
                "❌ Use <code>/compare @user</code> or reply to someone.",
                parse_mode=ParseMode.HTML,
            )
    except Exception:
        return await message.reply_text("❌ Invalid user(s). Try username or user ID.")

    u1, u2 = users
    uid1, uid2 = u1.id, u2.id

    status = await message.reply_text("⚔️ Building compare card…")

    async with db.pool.acquire() as conn:
        s1 = await conn.fetchrow("SELECT * FROM user_stats WHERE user_id=$1", uid1)
        s2 = await conn.fetchrow("SELECT * FROM user_stats WHERE user_id=$1", uid2)

    if not s1 or not s2:
        return await status.edit_text(
            "⚠️ One or both players have no stats yet. Play some matches first 🏏"
        )

    def safe(v):
        return v or 0

    def batting_avg(s):
        outs = max(1, safe(s["matches"]) - safe(s.get("not_outs", 0)))
        return safe(s["runs"]) / outs

    def strike_rate(s):
        bf = safe(s["balls_faced"])
        return (safe(s["runs"]) / bf * 100) if bf > 0 else 0.0

    def economy(s):
        bb = safe(s["balls_bowled"])
        return (safe(s["runs_conceded"]) / (bb / 6)) if bb > 0 else 99.0

    def win_rate(s):
        m = safe(s["matches"])
        return (safe(s["wins"]) / m * 100) if m > 0 else 0.0

    fields_raw = [
        ("Runs",      s1["runs"],    s2["runs"],    True),
        ("Wickets",   s1["wickets"], s2["wickets"], True),
        ("Avg",       batting_avg(s1), batting_avg(s2), True),
        ("Strike Rate", strike_rate(s1), strike_rate(s2), True),
        ("Economy",   economy(s1),   economy(s2),   False),
    ]

    score1 = score2 = 0
    text_lines = []
    for label, v1, v2, hw in fields_raw:
        fv1 = float(v1) if isinstance(v1, (int, float)) else 0.0
        fv2 = float(v2) if isinstance(v2, (int, float)) else 0.0
        tie = abs(fv1 - fv2) < 0.01
        if not tie:
            if (fv1 > fv2 and hw) or (fv1 < fv2 and not hw):
                score1 += 1
                mk = "✅"
            else:
                score2 += 1
                mk = "❌"
        else:
            mk = "➖"
        vs1 = f"{fv1:.1f}" if isinstance(v1, float) else str(v1)
        vs2 = f"{fv2:.1f}" if isinstance(v2, float) else str(v2)
        sym = ">" if mk == "✅" else "<" if mk == "❌" else "="
        text_lines.append(f"• {label:<14}: {vs1} {sym} {vs2} {mk}")

    extra_fields = [
        ("Hat-Tricks", safe(s1.get("hat_tricks", 0)), safe(s2.get("hat_tricks", 0)), True),
        ("MOMs",       safe(s1["moms"]), safe(s2["moms"]), True),
        ("Ducks",      safe(s1["ducks"]), safe(s2["ducks"]), False),
        ("Matches",    safe(s1["matches"]), safe(s2["matches"]), True),
        ("Win Rate",   win_rate(s1), win_rate(s2), True),
    ]
    for label, v1, v2, hw in extra_fields:
        fv1 = float(v1)
        fv2 = float(v2)
        tie = abs(fv1 - fv2) < 0.01
        if not tie:
            if (fv1 > fv2 and hw) or (fv1 < fv2 and not hw):
                score1 += 1
                mk = "✅"
            else:
                score2 += 1
                mk = "❌"
        else:
            mk = "➖"
        vs1 = f"{fv1:.1f}" if isinstance(v1, float) else str(v1)
        vs2 = f"{fv2:.1f}" if isinstance(v2, float) else str(v2)
        sym = ">" if mk == "✅" else "<" if mk == "❌" else "="
        text_lines.append(f"• {label:<14}: {vs1} {sym} {vs2} {mk}")

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
        + "\n".join(text_lines)
        + f"\n\n🔥 <b>𝗩𝗘𝗥𝗗𝗜𝗖𝗧:</b> {verdict}"
    )

    try:
        from plugins.utilities.profile_card import download_user_photo
        av1_data, av2_data = await asyncio.gather(
            download_user_photo(client, uid1),
            download_user_photo(client, uid2),
        )
        display_rows = fields_raw[:5]
        loop = asyncio.get_event_loop()
        buf = await loop.run_in_executor(
            None,
            lambda: build_compare_card(av1_data, av2_data, u1.first_name, u2.first_name, score1, score2, display_rows),
        )
        await status.delete()
        await message.reply_photo(photo=buf, caption=caption, parse_mode=ParseMode.HTML)
    except Exception as e:
        print(f"Compare card error: {e}")
        await status.edit_text(caption, parse_mode=ParseMode.HTML)
