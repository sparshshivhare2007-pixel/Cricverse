"""
/addstats — Owner-only command to manually add stats to a player.

Usage:
  1. Reply mode (reply to a CricQuest-style profile message):
       /addstats @username
       Parses stats from the replied message and adds them to the player.

  2. Direct mode (no reply needed):
       /addstats @username <field> <value>
       e.g. /addstats @player runs 50

  3. Field menu:
       /addstats fields
       Lists all supported field names.
"""

import re
import html
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import Config
from database.connection import db

OWNER_FILTER = filters.user(list(Config.OWNER_IDS))

# ──────────────────────── Field registry ────────────────────────

NUMERIC_FIELDS = {
    "matches":          ("🎮 Matches",          False),
    "wins":             ("✅ Wins",              False),
    "losses":           ("❌ Losses",            False),
    "runs":             ("🏃 Runs",              False),
    "balls_faced":      ("⚾ Balls Faced",        False),
    "balls_bowled":     ("🎳 Balls Bowled",       False),
    "runs_conceded":    ("💨 Runs Conceded",      False),
    "fours":            ("4️⃣ Fours",             False),
    "sixes":            ("6️⃣ Sixes",             False),
    "moms":             ("🏆 Man of the Match",   False),
    "centuries":        ("💯 Centuries",          False),
    "fifties":          ("⭐ Fifties",            False),
    "ducks":            ("🦆 Ducks",             False),
    "hat_tricks":       ("🎩 Hat-Tricks",         False),
    "highest_score":    ("🔥 Highest Score",      True),   # True = use $max instead of $inc
    "best_partnership": ("🤝 Best Partnership",   True),
    "captain_wins":     ("🧢 Captain Wins",       False),
    "captain_losses":   ("🧢 Captain Losses",     False),
    "not_outs":         ("🛡 Not Outs",           False),
    "penalties_received": ("⚠️ Penalties",        False),
}

ALIASES = {
    "match": "matches",
    "mom": "moms",
    "run": "runs",
    "balls": "balls_faced",
    "ball": "balls_faced",
    "balls_bowl": "balls_bowled",
    "overs": "balls_bowled",
    "four": "fours",
    "six": "sixes",
    "century": "centuries",
    "hundred": "centuries",
    "hundreds": "centuries",
    "100s": "centuries",
    "50s": "fifties",
    "fifty": "fifties",
    "duck": "ducks",
    "hat_trick": "hat_tricks",
    "hattrick": "hat_tricks",
    "hattricks": "hat_tricks",
    "hs": "highest_score",
    "highest": "highest_score",
    "partner": "best_partnership",
    "partnership": "best_partnership",
    "cap_wins": "captain_wins",
    "cap_losses": "captain_losses",
    "captain_win": "captain_wins",
    "captain_loss": "captain_losses",
    "not_out": "not_outs",
    "penalty": "penalties_received",
    "penalties": "penalties_received",
    "wicket": "wickets",
    "win": "wins",
    "loss": "losses",
    "rc": "runs_conceded",
    "bb": "balls_bowled",
    "bf": "balls_faced",
}

# wickets lives in user_stats too
NUMERIC_FIELDS["wickets"] = ("🎯 Wickets", False)
ALIASES["wicket"] = "wickets"


def _resolve_field(name: str):
    name = name.lower().strip()
    if name in NUMERIC_FIELDS:
        return name
    return ALIASES.get(name)


def _fields_text():
    lines = ["📋 <b>ADDSTATS — FIELD NAMES</b>", ""]
    for key, (label, is_max) in NUMERIC_FIELDS.items():
        note = " <i>(uses max, not add)</i>" if is_max else ""
        lines.append(f"• <code>{key}</code> — {label}{note}")
    lines.append("")
    lines.append("<b>Overs note:</b> when parsing a profile message, overs (e.g. 35.2) are converted to balls bowled automatically.")
    return "\n".join(lines)


# ──────────────────────── Profile message parser ────────────────────────

def _overs_to_balls(overs_str: str) -> int:
    """Convert '35.2' → 212 balls."""
    try:
        parts = str(overs_str).split(".")
        whole = int(parts[0])
        rem = int(parts[1]) if len(parts) > 1 else 0
        return whole * 6 + rem
    except Exception:
        return 0


def _parse_profile_message(text: str) -> dict:
    """Parse a CricQuest/Nexora-style profile text into a stats dict."""
    parsed = {}

    patterns = [
        ("matches",       r"Matches\s*[:\-]\s*(\d+)"),
        ("moms",          r"MOMs?\s*[:\-]\s*(\d+)"),
        ("captain_wins",  r"Captaincy\s*[:\-]\s*(\d+)\s*Wins"),
        ("captain_losses",r"Captaincy\s*.*?(\d+)\s*Losses"),
        ("runs",          r"Runs\s*[:\-]\s*(\d+)"),
        ("balls_faced",   r"Balls\s*[:\-]\s*(\d+)"),
        ("highest_score", r"Highest\s*[:\-]\s*(\d+)"),
        ("sixes",         r"6️⃣\s*[:\-]?\s*(\d+)"),
        ("fours",         r"4️⃣\s*[:\-]?\s*(\d+)"),
        ("fifties",       r"50s\s*[:\-]\s*(\d+)"),
        ("centuries",     r"100s\s*[:\-]\s*(\d+)"),
        ("ducks",         r"Ducks\s*[:\-]\s*(\d+)"),
        ("wickets",       r"Wickets\s*[:\-]\s*(\d+)"),
        ("hat_tricks",    r"Hat[- ]Tricks?\s*[:\-]\s*(\d+)"),
        # overs → balls_bowled handled separately
    ]

    for field, pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                parsed[field] = int(m.group(1))
            except ValueError:
                pass

    # Overs → balls bowled
    m = re.search(r"Overs\s*[:\-]\s*([\d.]+)", text, re.IGNORECASE)
    if m:
        parsed["balls_bowled"] = _overs_to_balls(m.group(1))

    # MOM count from "22× Man of the Match" line (overrides if higher)
    m = re.search(r"(\d+)[×x]\s*Man of the Match", text, re.IGNORECASE)
    if m:
        val = int(m.group(1))
        if val > parsed.get("moms", 0):
            parsed["moms"] = val

    return parsed


# ──────────────────────── DB helpers ────────────────────────

async def _get_stats(user_id: int) -> dict:
    await db.ensure_pool()
    return (await db.db["user_stats"].find_one({"user_id": user_id})) or {}


async def _apply_stats(user_id: int, additions: dict) -> dict:
    """
    Apply additions to user_stats.
    Fields marked as is_max use $max; rest use $inc.
    Returns a dict of {field: (old_value, new_value)}.
    """
    await db.ensure_pool()
    col = db.db["user_stats"]

    existing = await col.find_one({"user_id": user_id}) or {}

    inc_ops = {}
    max_ops = {}
    changes = {}

    for field, value in additions.items():
        info = NUMERIC_FIELDS.get(field)
        if info is None:
            continue
        _, is_max = info
        old_val = existing.get(field, 0)

        if is_max:
            new_val = max(old_val, value)
            max_ops[field] = value
        else:
            new_val = old_val + value
            inc_ops[field] = value

        changes[field] = (old_val, new_val)

    update = {}
    if inc_ops:
        update["$inc"] = inc_ops
    if max_ops:
        update["$max"] = max_ops

    if update:
        await col.update_one({"user_id": user_id}, update, upsert=True)

    return changes


# ──────────────────────── Command handler ────────────────────────

@Client.on_message(
    filters.command("addstats") & OWNER_FILTER & (filters.private | filters.group)
)
async def addstats_cmd(client: Client, message: Message):
    args = message.command[1:]

    # ── /addstats fields ──
    if args and args[0].lower() == "fields":
        return await message.reply_text(
            _fields_text(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )

    # ── Resolve target user ──
    target_user = None

    if args:
        raw = args[0].lstrip("@")
        try:
            target_user = await client.get_users(int(raw) if raw.isdigit() else raw)
        except Exception:
            return await message.reply_text(
                f"❌ Could not find user <code>{html.escape(args[0])}</code>.",
                parse_mode=ParseMode.HTML,
            )

    # If no username in args but there's a reply to a profile message, try parsing user ID from it
    if target_user is None and message.reply_to_message:
        reply_text = message.reply_to_message.text or message.reply_to_message.caption or ""
        uid_match = re.search(r"User\s*ID\s*[:\-]?\s*(\d+)", reply_text, re.IGNORECASE)
        if uid_match:
            try:
                target_user = await client.get_users(int(uid_match.group(1)))
            except Exception:
                pass

    if target_user is None:
        return await message.reply_text(
            "❌ <b>Who?</b>\n\n"
            "Usage:\n"
            "• Reply to a profile message: <code>/addstats @username</code>\n"
            "• Direct: <code>/addstats @username runs 50</code>\n"
            "• Field list: <code>/addstats fields</code>",
            parse_mode=ParseMode.HTML,
        )

    # ── Mode A: reply to profile message ──
    if message.reply_to_message and len(args) <= 1:
        reply_text = (
            message.reply_to_message.text
            or message.reply_to_message.caption
            or ""
        )
        parsed = _parse_profile_message(reply_text)

        if not parsed:
            return await message.reply_text(
                "❌ Could not parse any stats from the replied message.\n"
                "Make sure it's a valid profile/stats message.",
                parse_mode=ParseMode.HTML,
            )

        status = await message.reply_text("⏳ Applying parsed stats…")
        changes = await _apply_stats(target_user.id, parsed)
        await status.edit_text(
            _build_result_text(target_user, changes, source="profile message"),
            parse_mode=ParseMode.HTML,
        )
        return

    # ── Mode B: direct field + value ──
    # args: [username, field, value]  OR  [field, value] if no username (shouldn't happen here)
    field_args = args[1:]  # skip the username

    if len(field_args) < 2:
        # Not enough args — show usage
        return await message.reply_text(
            "❌ <b>Missing field or value.</b>\n\n"
            "<b>Direct usage:</b> <code>/addstats @username &lt;field&gt; &lt;value&gt;</code>\n"
            "<b>Reply usage:</b> Reply to a profile message with <code>/addstats @username</code>\n"
            "<b>Field list:</b> <code>/addstats fields</code>",
            parse_mode=ParseMode.HTML,
        )

    raw_field = field_args[0]
    raw_value = field_args[1]

    field = _resolve_field(raw_field)
    if field is None:
        return await message.reply_text(
            f"❌ Unknown field <code>{html.escape(raw_field)}</code>.\n"
            "Send <code>/addstats fields</code> to see all field names.",
            parse_mode=ParseMode.HTML,
        )

    try:
        value = int(raw_value)
    except ValueError:
        return await message.reply_text(
            f"❌ Value must be a whole number, got <code>{html.escape(raw_value)}</code>.",
            parse_mode=ParseMode.HTML,
        )

    changes = await _apply_stats(target_user.id, {field: value})
    await message.reply_text(
        _build_result_text(target_user, changes, source="manual"),
        parse_mode=ParseMode.HTML,
    )


# ──────────────────────── Result formatter ────────────────────────

def _build_result_text(user, changes: dict, source: str) -> str:
    name = html.escape(user.first_name)
    uid = user.id

    if not changes:
        return f"⚠️ No stats were changed for <a href='tg://user?id={uid}'>{name}</a>."

    lines = [
        f"✅ <b>Stats Updated</b> — <a href='tg://user?id={uid}'>{name}</a>",
        f"<i>Source: {html.escape(source)}</i>",
        "━━━━━━━━━━━━━━━━",
    ]
    for field, (old, new) in changes.items():
        label = NUMERIC_FIELDS.get(field, (field, False))[0]
        diff = new - old
        diff_str = f"+{diff}" if diff >= 0 else str(diff)
        lines.append(f"• {label}: <code>{old}</code> → <code>{new}</code>  (<b>{diff_str}</b>)")

    lines.append("━━━━━━━━━━━━━━━━")
    return "\n".join(lines)
