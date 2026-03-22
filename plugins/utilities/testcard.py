import io
import os
import math
import random
import asyncio
from PIL import Image, ImageDraw, ImageFont
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InputMediaPhoto

ASSETS = os.path.join(os.path.dirname(__file__), "..", "..", "Assets")
FONT_PATH = os.path.join(ASSETS, "namefont.ttf")

CW, CH = 920, 520


def _font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()


def _circle_mask(size: int) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size - 1, size - 1), fill=255)
    return m


def _text_center(d: ImageDraw.Draw, cx: int, cy: int, text: str, font, fill):
    d.text((cx, cy), text, fill=fill, font=font, anchor="mm")


def _paste_avatar(card: Image.Image, photo_bytes, cx: int, cy: int, size: int = 170, ring_rgb=(255, 200, 0)):
    r = size // 2
    mask = _circle_mask(size)

    if photo_bytes:
        try:
            raw = photo_bytes.read() if hasattr(photo_bytes, "read") else bytes(photo_bytes)
            av = Image.open(io.BytesIO(raw)).convert("RGBA").resize((size, size), Image.LANCZOS)
        except Exception:
            av = None
    else:
        av = None

    if av is None:
        av = Image.new("RGBA", (size, size), (40, 40, 55, 255))
        dd = ImageDraw.Draw(av)
        dd.ellipse((0, 0, size - 1, size - 1), fill=(60, 60, 80))
        _text_center(dd, size // 2, size // 2, "?", _font(60), (180, 180, 180))

    av.putalpha(mask)

    ov = Image.new("RGBA", card.size, (0, 0, 0, 0))
    ring_d = ImageDraw.Draw(ov)
    for i in range(8, 0, -1):
        alpha = int(220 * (i / 8))
        ring_d.ellipse(
            (cx - r - i, cy - r - i, cx + r + i, cy + r + i),
            outline=ring_rgb + (alpha,),
            width=3,
        )
    card.paste(ov, mask=ov.split()[3])
    card.paste(av, (cx - r, cy - r), av)


def _left_dark_vignette(card: Image.Image, split_x: int = 310):
    ov = Image.new("RGBA", card.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(split_x, 0, -1):
        alpha = int(160 * (1 - i / split_x) ** 0.6)
        d.rectangle([(i, 0), (i + 1, CH)], fill=(0, 0, 0, alpha))
    card.paste(ov, mask=ov.split()[3])


def _draw_stats_panel(card: Image.Image, stats_rows: list, accent: tuple, label_col: tuple):
    d = ImageDraw.Draw(card, "RGBA")
    px = 340
    py = 110
    row_h = 70
    val_x = 700

    f_lbl = _font(15)
    f_val = _font(34)

    for i, (label, value) in enumerate(stats_rows):
        y = py + i * row_h
        if i > 0:
            d.line([(px - 10, y - 2), (CW - 40, y - 2)], fill=accent + (50,), width=1)
        d.text((px, y + 6), label.upper(), fill=label_col, font=f_lbl)
        d.text((val_x, y + 2), str(value), fill=(255, 255, 255), font=f_val, anchor="ra")

    return card


def _draw_dna_badge(d: ImageDraw.Draw, x: int, y: int, text: str, bg: tuple, fg: tuple = (255, 255, 255)):
    f = _font(14)
    bbox = d.textbbox((0, 0), text, font=f)
    w, h = bbox[2] - bbox[0] + 20, bbox[3] - bbox[1] + 10
    d.rounded_rectangle([(x, y), (x + w, y + h)], radius=8, fill=bg + (220,))
    d.text((x + 10, y + 5), text, fill=fg, font=f)


# ─────────────────────────────────────────────────────────────────────────────
#  CARD 1 — POWER HITTING  (red / gold, diagonal slashes)
# ─────────────────────────────────────────────────────────────────────────────

def gen_power_hitting_card(photo_bytes, name: str, stats: list) -> io.BytesIO:
    bg = (12, 4, 4)
    accent = (220, 60, 0)
    accent2 = (255, 190, 0)

    card = Image.new("RGBA", (CW, CH), bg + (255,))
    ov = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    def poly(pts, c, a):
        d.polygon(pts, fill=c + (a,))

    # Diagonal bat-swing slash marks
    for i, ox in enumerate(range(-100, CW + 300, 90)):
        shade = accent if i % 2 == 0 else accent2
        a = 45 - i * 1
        if a < 8:
            a = 8
        poly([(ox, 0), (ox + 55, 0), (ox - 215, CH), (ox - 270, CH)], shade, a)

    # Bold accent corner slabs
    poly([(0, 0), (CW, 0), (CW, 50), (0, 65)], accent, 90)
    poly([(0, 0), (CW, 0), (CW, 28), (0, 38)], accent2, 60)
    poly([(0, CH - 50), (CW, CH - 38), (CW, CH), (0, CH)], accent, 70)
    poly([(0, CH - 28), (CW, CH - 18), (CW, CH), (0, CH)], accent2, 50)

    # Right glow block
    poly([(CW - 90, 0), (CW, 0), (CW, CH), (CW - 70, CH)], accent, 55)
    poly([(CW - 50, 0), (CW, 0), (CW, CH), (CW - 35, CH)], accent2, 45)

    card.paste(ov, mask=ov.split()[3])

    _left_dark_vignette(card)
    _paste_avatar(card, photo_bytes, 155, 230, size=170, ring_rgb=accent)

    d2 = ImageDraw.Draw(card)
    _draw_dna_badge(d2, 20, 18, "⚔️  POWER HITTING", accent, (255, 255, 255))

    n = name[:18]
    d2.text((155, 335), n, fill=(255, 255, 255), font=_font(26), anchor="mm")
    d2.text((155, 368), "Aggressive ⚔️", fill=accent2, font=_font(16), anchor="mm")
    d2.text((155, 392), "DNA • Power Hitter", fill=(180, 140, 100), font=_font(12), anchor="mm")

    _draw_stats_panel(card, stats, accent, (255, 160, 80))

    d2.text((CW - 30, CH - 18), "NEXORA CRICKET", fill=(100, 60, 40), font=_font(11), anchor="rm")

    buf = io.BytesIO()
    card.convert("RGB").save(buf, format="JPEG", quality=92)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
#  CARD 2 — SPIN MASTERY  (teal / purple, concentric circles)
# ─────────────────────────────────────────────────────────────────────────────

def gen_spin_mastery_card(photo_bytes, name: str, stats: list) -> io.BytesIO:
    bg = (4, 10, 22)
    accent = (0, 210, 190)
    accent2 = (160, 60, 255)

    card = Image.new("RGBA", (CW, CH), bg + (255,))
    ov = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    def poly(pts, c, a):
        d.polygon(pts, fill=c + (a,))

    def ring(cx, cy, r, c, a, w=2):
        d.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline=c + (a,), width=w)

    # Spin trails — concentric circles on the right side
    cx, cy = 650, 260
    for i, r in enumerate(range(18, 380, 28)):
        shade = accent if i % 2 == 0 else accent2
        alpha = max(8, 60 - i * 2)
        ring(cx, cy, r, shade, alpha, w=2 + (i % 3))

    # Small satellite circles
    for angle_deg in range(0, 360, 45):
        angle = math.radians(angle_deg)
        sr = 90 + (angle_deg % 3) * 20
        scx = int(cx + sr * math.cos(angle))
        scy = int(cy + sr * math.sin(angle))
        ring(scx, scy, 12, accent, 35, w=1)

    # Header strip
    poly([(0, 0), (CW, 0), (CW, 55), (0, 70)], accent2, 75)
    poly([(0, 0), (CW, 0), (CW, 32), (0, 42)], accent, 55)
    poly([(0, CH - 45), (CW, CH - 35), (CW, CH), (0, CH)], accent2, 60)

    # Left vertical accent
    poly([(0, 0), (18, 0), (18, CH), (0, CH)], accent, 90)
    poly([(18, 0), (30, 0), (30, CH), (18, CH)], accent2, 55)

    card.paste(ov, mask=ov.split()[3])
    _left_dark_vignette(card)
    _paste_avatar(card, photo_bytes, 155, 230, size=170, ring_rgb=accent)

    d2 = ImageDraw.Draw(card)
    _draw_dna_badge(d2, 20, 18, "🌀  SPIN MASTERY", accent2, (255, 255, 255))
    d2.text((155, 335), name[:18], fill=(255, 255, 255), font=_font(26), anchor="mm")
    d2.text((155, 368), "Spin Wizard 🌀", fill=accent, font=_font(16), anchor="mm")
    d2.text((155, 392), "DNA • Spin Wizard", fill=(120, 160, 180), font=_font(12), anchor="mm")

    _draw_stats_panel(card, stats, accent, (100, 210, 200))
    d2.text((CW - 30, CH - 18), "NEXORA CRICKET", fill=(60, 100, 100), font=_font(11), anchor="rm")

    buf = io.BytesIO()
    card.convert("RGB").save(buf, format="JPEG", quality=92)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
#  CARD 3 — FINISHER MODE  (lime / dark, bullseye target rings)
# ─────────────────────────────────────────────────────────────────────────────

def gen_finisher_card(photo_bytes, name: str, stats: list) -> io.BytesIO:
    bg = (4, 14, 8)
    accent = (50, 220, 80)
    accent2 = (180, 255, 100)

    card = Image.new("RGBA", (CW, CH), bg + (255,))
    ov = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    def poly(pts, c, a):
        d.polygon(pts, fill=c + (a,))

    def ring(cx, cy, r, c, a, w=2):
        d.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline=c + (a,), width=w)

    # Bullseye / target on right-center
    cx, cy = 660, 255
    for i, r in enumerate(range(15, 360, 45)):
        shade = accent if i % 2 == 0 else accent2
        alpha = max(12, 70 - i * 6)
        ring(cx, cy, r, shade, alpha, w=3)

    # Crosshair lines
    d.line([(cx - 350, cy), (CW + 20, cy)], fill=accent + (20,), width=1)
    d.line([(cx, 0), (cx, CH)], fill=accent + (20,), width=1)
    d.line([(cx - 180, cy - 180), (cx + 180, cy + 180)], fill=accent2 + (12,), width=1)
    d.line([(cx + 180, cy - 180), (cx - 180, cy + 180)], fill=accent2 + (12,), width=1)

    # Corner accents
    poly([(0, 0), (CW, 0), (CW, 52), (0, 66)], accent, 80)
    poly([(0, 0), (CW, 0), (CW, 28), (0, 36)], accent2, 55)
    poly([(0, CH - 48), (CW, CH - 36), (CW, CH), (0, CH)], accent, 65)

    card.paste(ov, mask=ov.split()[3])
    _left_dark_vignette(card)
    _paste_avatar(card, photo_bytes, 155, 230, size=170, ring_rgb=accent)

    d2 = ImageDraw.Draw(card)
    _draw_dna_badge(d2, 20, 18, "🏆  FINISHER MODE", accent, (0, 0, 0))
    d2.text((155, 335), name[:18], fill=(255, 255, 255), font=_font(26), anchor="mm")
    d2.text((155, 368), "Finisher 🏆", fill=accent2, font=_font(16), anchor="mm")
    d2.text((155, 392), "DNA • Clutch Player", fill=(120, 200, 130), font=_font(12), anchor="mm")

    _draw_stats_panel(card, stats, accent, (140, 230, 140))
    d2.text((CW - 30, CH - 18), "NEXORA CRICKET", fill=(60, 110, 60), font=_font(11), anchor="rm")

    buf = io.BytesIO()
    card.convert("RGB").save(buf, format="JPEG", quality=92)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
#  CARD 4 — STRATEGIC PLAY  (steel blue / silver, diamond hex grid)
# ─────────────────────────────────────────────────────────────────────────────

def gen_strategic_card(photo_bytes, name: str, stats: list) -> io.BytesIO:
    bg = (5, 10, 22)
    accent = (30, 130, 255)
    accent2 = (190, 220, 255)

    card = Image.new("RGBA", (CW, CH), bg + (255,))
    ov = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    def poly(pts, c, a):
        d.polygon(pts, fill=c + (a,))

    # Diamond / hex grid on right half
    gx, gy = 50, 40
    for row in range(-1, CH // gy + 2):
        for col in range(3, CW // gx + 3):
            cx = col * gx + (row % 2) * (gx // 2)
            cy = row * gy
            if cx < 290:
                continue
            shade = accent if (row + col) % 2 == 0 else accent2
            alpha = 18
            pts = [
                (cx, cy - gy // 2),
                (cx + gx // 2, cy),
                (cx, cy + gy // 2),
                (cx - gx // 2, cy),
            ]
            d.polygon(pts, outline=shade + (alpha,))

    # Bold header/footer strips
    poly([(0, 0), (CW, 0), (CW, 52), (0, 68)], accent, 85)
    poly([(0, 0), (CW, 0), (CW, 28), (0, 38)], accent2, 60)
    poly([(0, CH - 48), (CW, CH - 36), (CW, CH), (0, CH)], accent, 70)

    # Right edge accent bars
    poly([(CW - 80, 0), (CW, 0), (CW, CH), (CW - 65, CH)], accent, 55)
    poly([(CW - 40, 0), (CW, 0), (CW, CH), (CW - 28, CH)], accent2, 45)

    card.paste(ov, mask=ov.split()[3])
    _left_dark_vignette(card)
    _paste_avatar(card, photo_bytes, 155, 230, size=170, ring_rgb=accent)

    d2 = ImageDraw.Draw(card)
    _draw_dna_badge(d2, 20, 18, "🧠  STRATEGIC PLAY", accent, (255, 255, 255))
    d2.text((155, 335), name[:18], fill=(255, 255, 255), font=_font(26), anchor="mm")
    d2.text((155, 368), "Strategic 🧠", fill=accent2, font=_font(16), anchor="mm")
    d2.text((155, 392), "DNA • Mastermind", fill=(140, 180, 230), font=_font(12), anchor="mm")

    _draw_stats_panel(card, stats, accent, (140, 180, 230))
    d2.text((CW - 30, CH - 18), "NEXORA CRICKET", fill=(50, 80, 140), font=_font(11), anchor="rm")

    buf = io.BytesIO()
    card.convert("RGB").save(buf, format="JPEG", quality=92)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
#  Sample stats for each DNA type (used in /testcard)
# ─────────────────────────────────────────────────────────────────────────────

def _fresh_sample_stats():
    return {
        "power": [
            ("Strike Rate", f"{random.randint(155, 195)}.{random.randint(0, 9)}"),
            ("Sixes",        str(random.randint(28, 60))),
            ("Fours",        str(random.randint(40, 90))),
            ("Runs",         str(random.randint(900, 2000))),
        ],
        "spin": [
            ("Wickets",   str(random.randint(45, 100))),
            ("Economy",   f"{random.uniform(4.5, 6.5):.2f}"),
            ("5-Wicket",  str(random.randint(2, 8))),
            ("Maidens",   str(random.randint(8, 25))),
        ],
        "finish": [
            ("Win Rate",  f"{random.randint(62, 84)}%"),
            ("MOMs",      str(random.randint(8, 22))),
            ("Matches",   str(random.randint(30, 80))),
            ("Centuries", str(random.randint(3, 12))),
        ],
        "strategic": [
            ("Average",     f"{random.uniform(30, 55):.1f}"),
            ("50s / 100s",  f"{random.randint(8, 20)} / {random.randint(2, 8)}"),
            ("Economy",     f"{random.uniform(5.0, 7.0):.2f}"),
            ("Consistency", f"{random.randint(70, 92)}%"),
        ],
    }


CARD_GENERATORS = [
    ("⚔️ Power Hitting",  "power",    gen_power_hitting_card),
    ("🌀 Spin Mastery",   "spin",     gen_spin_mastery_card),
    ("🏆 Finisher Mode",  "finish",   gen_finisher_card),
    ("🧠 Strategic Play", "strategic",gen_strategic_card),
]


@Client.on_message(filters.command("testcard"))
async def testcard_cmd(client, message):
    user = message.from_user

    loading = await message.reply_text("🎨 Generating your DNA cards…")

    try:
        from plugins.utilities.profile_card import download_user_photo
        photo_data = await download_user_photo(client, user.id)
    except Exception:
        photo_data = None

    def _all_cards():
        sample = _fresh_sample_stats()
        cards = []
        for label, key, gen_fn in CARD_GENERATORS:
            stats = sample[key][:]
            buf = gen_fn(photo_data, user.first_name, stats)
            cards.append((label, buf))
        return cards

    loop = asyncio.get_event_loop()
    cards = await loop.run_in_executor(None, _all_cards)

    try:
        await loading.delete()
    except Exception:
        pass

    media_group = []
    for i, (label, buf) in enumerate(cards):
        caption = f"🧬 <b>{label}</b>" if i == 0 else label
        media_group.append(InputMediaPhoto(media=buf, caption=caption))

    try:
        await message.reply_media_group(media=media_group)
    except Exception as e:
        print(f"testcard media group error: {e}")
        for label, buf in cards:
            try:
                buf.seek(0)
                await message.reply_photo(photo=buf, caption=f"🧬 <b>{label}</b>", parse_mode=ParseMode.HTML)
            except Exception as e2:
                print(f"testcard single send error: {e2}")
