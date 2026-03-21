import io
import os
import random
from PIL import Image, ImageDraw, ImageFont

ASSETS = os.path.join(os.path.dirname(__file__), "..", "..", "Assets")
FONT_BOLD_PATH = os.path.join(ASSETS, "namefont.ttf")
FONT_REG_PATH  = os.path.join(ASSETS, "fonts.ttf")

W, H = 920, 510

THEMES = [
    {
        "id": "neon_green",
        "bg":          (6,  12,  26),
        "accent":      (50, 235,  10),
        "accent_dark": (20, 120,   5),
        "accent_glow": (80, 255,  40),
        "title_color": (50, 235,  10),
        "label_color": (180, 220, 180),
        "value_color": (255, 255, 255),
        "id_color":    (50,  235,  10),
        "divider":     (30,  80,   30),
        "ring_color":  (50,  235,  10),
        "box_bg":      (10,  30,   10),
        "subtitle":    (140, 200, 140),
    },
    {
        "id": "crimson_fire",
        "bg":          (15,   5,   8),
        "accent":      (255,  25,  55),
        "accent_dark": (140,  10,  25),
        "accent_glow": (255,  80, 100),
        "title_color": (255,  25,  55),
        "label_color": (220, 175, 175),
        "value_color": (255, 255, 255),
        "id_color":    (255,  60,  80),
        "divider":     (80,   20,  25),
        "ring_color":  (255,  25,  55),
        "box_bg":      (30,    8,  12),
        "subtitle":    (200, 130, 140),
    },
    {
        "id": "cosmic_purple",
        "bg":          (6,    0,  20),
        "accent":      (150,  40, 255),
        "accent_dark": (80,   10, 160),
        "accent_glow": (190, 100, 255),
        "title_color": (175,  80, 255),
        "label_color": (190, 170, 220),
        "value_color": (255, 255, 255),
        "id_color":    (175,  80, 255),
        "divider":     (55,   20,  90),
        "ring_color":  (150,  40, 255),
        "box_bg":      (18,    5,  40),
        "subtitle":    (180, 140, 220),
    },
]


def _load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _make_circle_mask(size):
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((0, 0, size - 1, size - 1), fill=255)
    return mask


def _draw_brush_strokes(img: Image.Image, theme: dict):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    ac  = theme["accent"]
    acd = theme["accent_dark"]
    bg  = theme["bg"]

    def stroke(pts, color, alpha=200):
        d.polygon(pts, fill=color + (alpha,))

    # Left rising column strokes
    stroke([(0, int(H * 0.45)), (0, H), (70, H), (45, int(H * 0.35))],  acd, 230)
    stroke([(0, int(H * 0.15)), (0, int(H * 0.50)), (110, int(H * 0.38)), (75, int(H * 0.05))], acd, 200)
    stroke([(0, int(H * 0.50)), (0, H), (100, H), (60, int(H * 0.40))], ac, 160)
    stroke([(0, int(H * 0.20)), (0, int(H * 0.55)), (50, int(H * 0.45)), (20, int(H * 0.12))], ac, 100)

    # Left big diagonal slash
    stroke([(85,  H), (260, int(H * 0.08)), (340, int(H * 0.22)), (165, H)], acd, 215)
    stroke([(40,  H), (195, int(H * 0.05)), (270, int(H * 0.20)), (115, H)], ac,  140)
    stroke([(140, H), (310, int(H * 0.12)), (390, int(H * 0.30)), (225, H)], acd, 165)

    # Top-left blot
    stroke([(0, 0), (200, 0), (160, 55), (0, 70)], acd, 180)
    stroke([(0, 0), (130, 0), (95, 38),  (0, 50)], ac,  115)

    # Right edge fringe
    stroke([(W - 60,  0), (W, 0), (W, int(H * 0.35)), (W - 80,  int(H * 0.25))], acd, 185)
    stroke([(W - 100, 0), (W - 55, 0), (W - 35, int(H * 0.25)), (W - 115, int(H * 0.15))], ac, 120)

    # Dark depth slashes
    dark = tuple(max(0, c - 15) for c in bg)
    stroke([(55,  int(H * 0.65)), (85,  int(H * 0.60)), (175, H), (135, H)], dark, 200)
    stroke([(235, int(H * 0.10)), (295, int(H * 0.02)), (365, int(H * 0.22)), (300, int(H * 0.30))], dark, 175)

    img.paste(overlay, mask=overlay.split()[3])


def _draw_profile_box(card: Image.Image, photo_bytes, theme: dict):
    glow_color = theme["accent_glow"]
    ring_color = theme["ring_color"]
    box_bg     = theme["box_bg"]

    box_size = 280
    bx = W - box_size - 38
    by = (H - box_size) // 2

    # Outer glow behind box
    glow = Image.new("RGBA", card.size, (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    for spread in range(22, 0, -1):
        alpha = int(140 * (spread / 22) ** 1.6)
        gd.rounded_rectangle(
            [bx - spread, by - spread, bx + box_size + spread, by + box_size + spread],
            radius=30 + spread, fill=glow_color + (alpha,)
        )
    card.paste(glow, mask=glow.split()[3])

    # Rounded box background
    box_layer = Image.new("RGBA", card.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(box_layer)
    bd.rounded_rectangle([bx, by, bx + box_size, by + box_size],
                         radius=26, fill=box_bg + (255,))
    card.paste(box_layer, mask=box_layer.split()[3])

    # Profile photo circle
    circle_d = 220
    cx = bx + (box_size - circle_d) // 2
    cy = by + (box_size - circle_d) // 2

    if photo_bytes:
        try:
            pfp = Image.open(photo_bytes).convert("RGBA")
            pfp = pfp.resize((circle_d, circle_d), Image.LANCZOS)
        except Exception:
            pfp = None
    else:
        pfp = None

    if pfp is None:
        pfp = Image.new("RGBA", (circle_d, circle_d), (40, 40, 40, 255))
        pd = ImageDraw.Draw(pfp)
        pd.ellipse((0, 0, circle_d - 1, circle_d - 1), fill=(55, 55, 55, 255))

    mask = _make_circle_mask(circle_d)

    # Glow ring layers around circle
    ring_layer = Image.new("RGBA", card.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring_layer)
    for i in range(12, 0, -1):
        a = int(200 * (i / 12) ** 2)
        rd.ellipse(
            [cx - i, cy - i, cx + circle_d + i, cy + circle_d + i],
            outline=glow_color + (a,), width=2
        )
    card.paste(ring_layer, mask=ring_layer.split()[3])

    # White + accent hard ring border
    border_layer = Image.new("RGBA", card.size, (0, 0, 0, 0))
    bld = ImageDraw.Draw(border_layer)
    bld.ellipse([cx - 6, cy - 6, cx + circle_d + 6, cy + circle_d + 6],
                outline=(255, 255, 255, 200), width=5)
    bld.ellipse([cx - 2, cy - 2, cx + circle_d + 2, cy + circle_d + 2],
                outline=ring_color + (255,), width=3)
    card.paste(border_layer, mask=border_layer.split()[3])

    # Paste profile photo with circle mask
    pfp_layer = Image.new("RGBA", card.size, (0, 0, 0, 0))
    pfp_layer.paste(pfp, (cx, cy), mask=mask)
    card.paste(pfp_layer, mask=pfp_layer.split()[3])


def _draw_stats_text(card: Image.Image, user, stats: dict, theme: dict):
    d = ImageDraw.Draw(card)

    f_huge  = _load_font(FONT_BOLD_PATH, 40)
    f_large = _load_font(FONT_BOLD_PATH, 28)
    f_med   = _load_font(FONT_BOLD_PATH, 20)
    f_small = _load_font(FONT_REG_PATH,  17)
    f_tiny  = _load_font(FONT_REG_PATH,  13)

    pad_x = 34

    # Player ID badge
    uid_text = f"#PLAYER ID: {user.id}"
    d.rounded_rectangle([pad_x - 2, 13, pad_x + 18, 33], radius=4, fill=theme["accent"])
    d.text((pad_x + 24, 16), uid_text, font=f_small, fill=theme["id_color"])

    # Player name (large)
    name_upper = (user.first_name or "Player").upper()
    d.text((pad_x, 44), name_upper, font=f_huge, fill=theme["title_color"])

    # Rank / Title subtitle
    try:
        from plugins.utilities.userinfo import calculate_rank, calculate_title
        score, tier = calculate_rank(stats)
        title_str   = calculate_title(stats)
    except Exception:
        score, tier, title_str = 0, "—", "—"

    sub = title_str if title_str != "—" else tier
    d.text((pad_x, 93), sub.upper(), font=f_med, fill=theme["subtitle"])

    # Stat rows
    runs      = stats.get("runs", 0)
    wickets   = stats.get("wickets", 0)
    matches   = stats.get("matches", 0)
    fifties   = stats.get("fifties", 0)
    centuries = stats.get("centuries", 0)
    balls     = stats.get("balls_faced", 0)
    highest   = stats.get("highest_score", 0)
    sr        = round(runs / balls * 100, 1) if balls > 0 else 0.0

    rows = [
        ("MATCHES",       str(matches)),
        ("RUNS",          str(runs)),
        ("WICKETS",       str(wickets)),
        ("50s / 100s",    f"{fifties} / {centuries}"),
        ("STRIKE RATE",   str(sr)),
        ("HIGHEST SCORE", str(highest)),
    ]

    row_y  = 132
    row_h  = 58
    col2_x = 295

    for i, (label, value) in enumerate(rows):
        y = row_y + i * row_h
        if i > 0:
            d.line([(pad_x, y - 1), (col2_x + 130, y - 1)],
                   fill=theme["divider"], width=1)
        d.text((pad_x, y + 8), label, font=f_med, fill=theme["label_color"])
        d.text((col2_x, y + 5), value, font=f_large, fill=theme["value_color"])

    # Bottom footer tag
    tag = f"#CricketLegacy  •  Perf Score: {score}"
    d.text((pad_x, H - 34), tag, font=f_tiny, fill=theme["subtitle"])


def generate_card(photo_bytes, user, stats: dict) -> io.BytesIO:
    theme = random.choice(THEMES)

    card = Image.new("RGB", (W, H), theme["bg"])
    _draw_brush_strokes(card, theme)

    # Right-side subtle dark vignette to contrast stats text
    vignette = Image.new("RGBA", card.size, (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    for i in range(200, 0, -1):
        a = int(110 * (1 - i / 200) ** 2)
        x0 = W // 2 - 40 + (200 - i) // 2
        vd.rectangle([x0, 0, x0 + 1, H], fill=(0, 0, 0, a))
    card.paste(vignette, mask=vignette.split()[3])

    card = card.convert("RGBA")
    _draw_profile_box(card, photo_bytes, theme)
    card = card.convert("RGB")
    _draw_stats_text(card, user, stats, theme)

    buf = io.BytesIO()
    card.save(buf, format="PNG")
    buf.seek(0)
    return buf


async def download_user_photo(client, user_id: int):
    try:
        photos = await client.get_profile_photos(user_id, limit=1)
        if not photos:
            return None
        data = await client.download_media(photos[0], in_memory=True)
        if data:
            return io.BytesIO(bytes(data.getbuffer()))
        return None
    except Exception:
        return None
