import io
import random
from datetime import date
from PIL import Image, ImageDraw, ImageFont
from pyrogram import Client, filters
from pyrogram.enums import ParseMode

FONT = "Assets/fonts.ttf"
NAME_FONT = "Assets/namefont.ttf"


def _load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _cx(draw, text, cx, y, font, fill, stroke_fill=None, stroke_width=0):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text((cx - w // 2, y), text, font=font, fill=fill,
              stroke_fill=stroke_fill, stroke_width=stroke_width)


def _box(draw, x, y, w, h, fill, radius=12, outline=None, ow=2):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=fill,
                            outline=outline, width=ow)


def generate_solo_mvp_poster(
    mvp_name: str,
    runs: int,
    balls: int,
    wickets: int,
    balls_bowled: int,
    runs_conceded: int,
    fours: int,
    sixes: int,
    total_match_runs: int,
    total_overs: str,
    player_count: int,
) -> io.BytesIO:
    W, H = 800, 1020

    BG       = (8, 12, 24)
    CARD     = (15, 22, 42)
    CARD2    = (20, 28, 55)
    GOLD     = (255, 215, 0)
    GOLD_DIM = (180, 140, 0)
    GREEN    = (16, 185, 129)
    WHITE    = (240, 245, 255)
    SILVER   = (148, 163, 184)
    BLUE_H   = (30, 64, 175)
    RED_H    = (153, 27, 27)
    INDIGO   = (79, 70, 229)

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    f_96  = _load_font(FONT, 96)
    f_72  = _load_font(FONT, 72)
    f_48  = _load_font(FONT, 48)
    f_36  = _load_font(FONT, 36)
    f_28  = _load_font(FONT, 28)
    f_22  = _load_font(FONT, 22)
    f_nm  = _load_font(NAME_FONT, 60)
    f_nm2 = _load_font(NAME_FONT, 34)

    # ── Top border ────────────────────────────────────────────────────────────
    draw.rectangle([0, 0, W, 6], fill=GOLD)
    draw.rectangle([0, 6, W, 10], fill=GOLD_DIM)

    # ── Header ────────────────────────────────────────────────────────────────
    _cx(draw, "CRICKET  LEGACY", W // 2, 18, f_22, SILVER)
    _cx(draw, "✦  MAN OF THE MATCH  ✦", W // 2, 48, f_48, GOLD,
        stroke_fill=(100, 80, 0), stroke_width=2)
    draw.rectangle([60, 112, W - 60, 115], fill=GOLD)
    draw.rectangle([90, 115, W - 90, 117], fill=GOLD_DIM)

    # ── MVP Card ──────────────────────────────────────────────────────────────
    _box(draw, 30, 125, W - 60, 125, CARD, radius=16, outline=GOLD, ow=2)

    _box(draw, 50, 142, 76, 30, GOLD, radius=8)
    draw.text((60, 144), "MVP", font=f_28, fill=BG)

    draw.text((148, 136), mvp_name, font=f_nm, fill=WHITE)
    draw.text((W - 76, 138), "⭐", font=f_48, fill=GOLD)

    draw.text((150, 202), f"Solo Cricket  •  {player_count} Players", font=f_22, fill=SILVER)

    # ── Divider ───────────────────────────────────────────────────────────────
    draw.rectangle([60, 264, W - 60, 267], fill=INDIGO)

    # ── Match Banner ──────────────────────────────────────────────────────────
    _box(draw, 30, 276, W - 60, 52, CARD2, radius=10)
    _cx(draw, f"MATCH TOTAL: {total_match_runs} runs  │  OVERS: {total_overs}",
        W // 2, 290, f_28, SILVER)

    # ── Batting Card ──────────────────────────────────────────────────────────
    _box(draw, 30, 342, W - 60, 230, CARD, radius=16, outline=BLUE_H, ow=2)
    _box(draw, 30, 342, W - 60, 42, BLUE_H, radius=16)
    draw.rectangle([30, 360, 30 + W - 60, 384], fill=BLUE_H)
    draw.text((55, 350), "🏏  BATTING", font=f_28, fill=WHITE)

    draw.text((55, 390), str(runs), font=f_96, fill=GOLD,
              stroke_fill=(80, 60, 0), stroke_width=2)
    draw.text((55, 490), "RUNS", font=f_22, fill=SILVER)

    draw.text((215, 405), f"({balls} balls)", font=f_48, fill=WHITE)

    sr = round((runs / balls) * 100, 1) if balls > 0 else 0.0
    sr_col = GREEN if sr >= 150 else (GOLD if sr >= 100 else WHITE)
    draw.text((215, 462), f"SR  {sr}", font=f_36, fill=sr_col)

    _box(draw, W - 250, 395, 95, 60, CARD2, radius=10)
    _cx(draw, "4s", W - 202, 398, f_22, SILVER)
    _cx(draw, str(fours), W - 202, 422, f_48, WHITE)

    _box(draw, W - 145, 395, 95, 60, CARD2, radius=10)
    _cx(draw, "6s", W - 97, 398, f_22, SILVER)
    _cx(draw, str(sixes), W - 97, 422, f_48, GOLD)

    if runs >= 100:
        _box(draw, W - 250, 464, 200, 34, (120, 80, 0), radius=8)
        _cx(draw, "💯 CENTURY!", W - 150, 471, f_28, WHITE)
    elif runs >= 50:
        _box(draw, W - 250, 464, 200, 34, (40, 80, 20), radius=8)
        _cx(draw, "⭐ HALF CENTURY", W - 150, 471, f_28, WHITE)

    # ── Bowling Card ──────────────────────────────────────────────────────────
    _box(draw, 30, 588, W - 60, 200, CARD, radius=16, outline=RED_H, ow=2)
    _box(draw, 30, 588, W - 60, 42, RED_H, radius=16)
    draw.rectangle([30, 606, 30 + W - 60, 630], fill=RED_H)
    draw.text((55, 596), "⚾  BOWLING", font=f_28, fill=WHITE)

    draw.text((55, 636), str(wickets), font=f_96, fill=(239, 68, 68),
              stroke_fill=(80, 10, 10), stroke_width=2)
    draw.text((55, 736), "WICKETS", font=f_22, fill=SILVER)

    eco = round((runs_conceded / (balls_bowled / 6)), 2) if balls_bowled > 0 else 0.0
    eco_col = GREEN if eco <= 6 else (GOLD if eco <= 9 else (239, 68, 68))

    col_y = 645
    for lbl, val, col, bx in [
        ("ECONOMY", str(eco), eco_col, 205),
        ("BALLS", str(balls_bowled), WHITE, 390),
        ("CONCEDED", str(runs_conceded), WHITE, 575),
    ]:
        _box(draw, bx, col_y, 165, 72, CARD2, radius=10)
        _cx(draw, lbl, bx + 82, col_y + 5, f_22, SILVER)
        _cx(draw, val, bx + 82, col_y + 32, f_48, col)

    if wickets >= 3:
        _box(draw, 205, 727, 535, 32, (80, 15, 15), radius=8)
        _cx(draw, "🎩 TRIPLE STRIKE — MATCH BREAKER!", W // 2, 733, f_28, WHITE)

    # ── Awards Row ────────────────────────────────────────────────────────────
    _box(draw, 30, 804, W - 60, 70, CARD2, radius=14, outline=GOLD, ow=1)
    _cx(draw, "⚡ PLAYER OF THE MATCH  —  OUTSTANDING PERFORMANCE ⚡",
        W // 2, 820, f_28, GOLD)
    _cx(draw, f"Runs: {runs}  •  Wkts: {wickets}  •  SR: {sr}  •  Eco: {eco}",
        W // 2, 852, f_22, SILVER)

    # ── Footer ────────────────────────────────────────────────────────────────
    draw.rectangle([0, 892, W, 895], fill=INDIGO)
    _cx(draw, "#CricketLegacy  •  Nexora Bot", W // 2, 905, f_28, SILVER)
    _cx(draw, str(date.today()), W // 2, 940, f_22, (70, 85, 110))
    draw.rectangle([0, 1012, W, 1020], fill=GOLD)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


@Client.on_message(filters.command("testsolo"))
async def testsolo_cmd(client, message):
    runs         = random.randint(18, 145)
    balls        = runs + random.randint(3, 35)
    wickets      = random.randint(1, 6)
    balls_bowled = random.randint(12, 30)
    r_conceded   = random.randint(18, 72)
    fours        = random.randint(0, max(1, runs // 10))
    sixes        = random.randint(0, max(1, runs // 15))
    total_runs   = runs + random.randint(35, 130)
    total_b      = random.randint(60, 132)
    total_overs  = f"{total_b // 6}.{total_b % 6}"
    players      = random.randint(3, 7)

    wait = await message.reply_text("🎨 <b>Generating MVP poster...</b>", parse_mode=ParseMode.HTML)

    try:
        poster = generate_solo_mvp_poster(
            mvp_name=message.from_user.first_name,
            runs=runs,
            balls=balls,
            wickets=wickets,
            balls_bowled=balls_bowled,
            runs_conceded=r_conceded,
            fours=fours,
            sixes=sixes,
            total_match_runs=total_runs,
            total_overs=total_overs,
            player_count=players,
        )
        poster.name = "solo_mvp.png"
        caption = (
            f"⭐ <b>Solo Match MVP Poster</b>\n"
            f"────┈┄┄╌╌╌╌┄┄┈────\n"
            f"👤 <b>MVP:</b> {message.from_user.first_name}\n"
            f"🏏 Runs: <b>{runs}</b> ({balls}b)  •  SR: <b>{round(runs/balls*100,1) if balls else 0}</b>\n"
            f"⚾ Wickets: <b>{wickets}</b>  •  Eco: <b>{round(r_conceded/(balls_bowled/6),2) if balls_bowled else 0}</b>\n"
            f"6️⃣ Sixes: <b>{sixes}</b>  •  4️⃣ Fours: <b>{fours}</b>\n"
            f"<i>Test poster with random stats</i>"
        )
        await wait.delete()
        await message.reply_photo(photo=poster, caption=caption, parse_mode=ParseMode.HTML)
    except Exception as e:
        await wait.edit_text(f"❌ Poster generation failed: {e}")
