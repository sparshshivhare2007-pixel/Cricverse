import random
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from database.connection import db

DNA_PROFILES = {
    "Powerhouse 💪": {
        "tagline": "Run-machine. The scoreboard belongs to you.",
        "trait":   "Unstoppable batting dominance.",
        "tip":     "Keep piling runs — centuries are your calling card.",
        "color":   "🔴",
    },
    "Aggressive ⚔️": {
        "tagline": "Big swings, bigger boundaries. Fear is your rival's problem.",
        "trait":   "High-octane strike rate with explosive hitting.",
        "tip":     "Channel the aggression — six every over is the goal.",
        "color":   "🟠",
    },
    "Spin Wizard 🌀": {
        "tagline": "Batters can't read you. That's the point.",
        "trait":   "Low economy, high wickets — bowling is your art.",
        "tip":     "Stay patient, vary pace, and watch them crumble.",
        "color":   "🟣",
    },
    "Strategic 🧠": {
        "tagline": "Calculated, composed, and always one step ahead.",
        "trait":   "High average, consistent performer, rarely ducks out.",
        "tip":     "Play the long game — patience is your superpower.",
        "color":   "🔵",
    },
    "Finisher 🏆": {
        "tagline": "Best when the match is on the line. Clutch is your mode.",
        "trait":   "Top win rate and Man of the Match performances.",
        "tip":     "Keep delivering in pressure moments.",
        "color":   "🟡",
    },
    "Lucky Charm 🍀": {
        "tagline": "Unpredictable, chaotic, but somehow it always works.",
        "trait":   "Rising star — personality still forming.",
        "tip":     "Play more matches to unlock your true potential.",
        "color":   "🟢",
    },
}

ALL_DNA = list(DNA_PROFILES.keys())


def get_personality(stats: dict) -> str:
    runs          = int(stats.get("runs") or 0)
    wickets       = int(stats.get("wickets") or 0)
    balls_faced   = int(stats.get("balls_faced") or 0)
    balls_bowled  = int(stats.get("balls_bowled") or 0)
    runs_conceded = int(stats.get("runs_conceded") or 0)
    matches       = max(int(stats.get("matches") or 1), 1)
    wins          = int(stats.get("wins") or 0)
    sixes         = int(stats.get("sixes") or 0)
    fours         = int(stats.get("fours") or 0)
    centuries     = int(stats.get("centuries") or 0)
    moms          = int(stats.get("moms") or 0)
    ducks         = int(stats.get("ducks") or 0)

    sr       = (runs / balls_faced * 100) if balls_faced > 0 else 0.0
    eco      = (runs_conceded / (balls_bowled / 6)) if balls_bowled > 0 else 99.0
    avg      = runs / matches
    win_rate = wins / matches * 100

    if matches < 3:
        return "Lucky Charm 🍀"

    scores = {
        "Powerhouse 💪": (runs / 80) + (centuries * 6) + (sixes * 0.4),
        "Aggressive ⚔️": (sr / 8) + (sixes * 1.8) + (fours * 0.5),
        "Spin Wizard 🌀": (wickets * 3.5) + max(0.0, (9 - eco) * 5),
        "Strategic 🧠":  (avg * 1.5) + max(0.0, (6 - ducks) * 4) + max(0.0, (8 - eco) * 1.5),
        "Finisher 🏆":   (win_rate * 0.9) + (moms * 9),
        "Lucky Charm 🍀": 4.0,
    }

    return max(scores, key=scores.get)


def get_dna_info(dna_name: str) -> dict:
    return DNA_PROFILES.get(dna_name, DNA_PROFILES["Lucky Charm 🍀"])


@Client.on_message(filters.command("personality") & filters.group)
async def personality_cmd(client, message):
    user = message.from_user
    uid = user.id

    async with db.pool.acquire() as conn:
        stats = await conn.fetchrow("SELECT * FROM user_stats WHERE user_id=$1", uid)

    if not stats:
        dna = "Lucky Charm 🍀"
        info = DNA_PROFILES[dna]
        return await message.reply_text(
            f"🧬 <b>Cricket DNA — {user.first_name}</b>\n\n"
            f"{info['color']} <b>{dna}</b>\n"
            f"<i>{info['tagline']}</i>\n\n"
            "📊 Play some matches to evolve your identity!",
            parse_mode=ParseMode.HTML,
        )

    dna = get_personality(dict(stats))
    info = DNA_PROFILES[dna]

    runs          = int(stats["runs"] or 0)
    wickets       = int(stats["wickets"] or 0)
    matches       = int(stats["matches"] or 0)
    wins          = int(stats["wins"] or 0)
    balls_faced   = int(stats["balls_faced"] or 0)
    balls_bowled  = int(stats["balls_bowled"] or 0)
    runs_conceded = int(stats["runs_conceded"] or 0)
    sixes         = int(stats["sixes"] or 0)
    centuries     = int(stats["centuries"] or 0)
    moms          = int(stats["moms"] or 0)

    sr     = f"{runs / balls_faced * 100:.1f}" if balls_faced > 0 else "—"
    eco    = f"{runs_conceded / (balls_bowled / 6):.2f}" if balls_bowled > 0 else "—"
    wr     = f"{wins / max(matches, 1) * 100:.0f}%"
    winstr = f"{wins}/{matches}"

    text = (
        f"🧬 <b>Cricket DNA ❖ {user.first_name}</b>\n"
        "────┈┄┄╌╌╌╌┄┄┈────\n\n"
        f"{info['color']} <b>{dna}</b>\n"
        f"<i>{info['tagline']}</i>\n\n"
        f"⚡ <b>Trait:</b> {info['trait']}\n"
        f"💡 <b>Tip:</b> {info['tip']}\n\n"
        "📊 <b>Your Numbers:</b>\n"
        f"➥ 🏃 Runs: <b>{runs}</b>  |  Wickets: <b>{wickets}</b>\n"
        f"➥ ⚡ SR: <b>{sr}</b>  |  Eco: <b>{eco}</b>\n"
        f"➥ 💯 Centuries: <b>{centuries}</b>  |  MOMs: <b>{moms}</b>\n"
        f"➥ 🔥 Sixes: <b>{sixes}</b>  |  Win Rate: <b>{wr}</b> ({winstr})\n\n"
        "────┈┄┄╌╌╌╌┄┄┈────\n"
        "✨ <i>DNA evolves with every match you play.</i>"
    )

    await message.reply_text(text, parse_mode=ParseMode.HTML)
