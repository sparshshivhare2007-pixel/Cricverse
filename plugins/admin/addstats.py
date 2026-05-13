"""
/addstats — Owner-only command to manually add stats to a player.

Usage:
  1. Reply mode (reply to a CricQuest-style profile message):
       /addstats @username
       Parses stats from the replied message — shows a confirmation first.

  2. Direct mode (no reply needed):
       /addstats @username <field> <value>
       e.g. /addstats @player runs 50

  3. Field menu:
       /addstats fields
       Lists all supported field names.
"""

import re
import time
import html
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import Config
from database.connection import db

OWNER_FILTER = filters.user(list(Config.OWNER_IDS))

# ──────────────────────── Pending store (in-memory) ────────────────────────
# key → {"user_id": int, "target_id": int, "target_name": str, "additions": dict, "ts": float}
_PENDING: dict = {}
_PENDING_TTL = 120  # seconds

def _clean_pending():
    now = time.time()
    for k in list(_PENDING.keys()):
        if now - _PENDING[k]["ts"] > _PENDING_TTL:
            del _PENDING[k]

def _pending_key(user_id: int) -> str:
    return f"as_{user_id}"


# ──────────────────────── Field registry ────────────────────────

NUMERIC_FIELDS = {
    "matches":          ("🎮 Matches",           False),
    "wins":             ("✅ Wins",               False),
    "losses":           ("❌ Losses",             False),
    "runs":             ("🏃 Runs",               False),
    "balls_faced":      ("⚾ Balls Faced",         False),
    "balls_bowled":     ("🎳 Balls Bowled",        False),
    "runs_conceded":    ("💨 Runs Conceded",       False),
    "fours":            ("4️⃣ Fours",              False),
    "sixes":            ("6️⃣ Sixes",              False),
    "wickets":          ("🎯 Wickets",            False),
    "moms":             ("🏆 Man of the Match",    False),
    "centuries":        ("💯 Centuries",           False),
    "fifties":          ("⭐ Fifties",             False),
    "ducks":            ("🦆 Ducks",              False),
    "hat_tricks":       ("🎩 Hat-Tricks",          False),
    "highest_score":    ("🔥 Highest Score",       True),
    "best_partnership": ("🤝 Best Partnership",    True),
    "captain_wins":     ("🧢 Captain Wins",        False),
    "captain_losses":   ("🧢 Captain Losses",      False),
    "not_outs":         ("🛡 Not Outs",            False),
    "penalties_received": ("⚠️ Penalties",         False),
}

ALIASES = {
    "match": "matches", "mom": "moms", "run": "runs",
    "balls": "balls_faced", "ball": "balls_faced",
    "balls_bowl": "balls_bowled", "overs": "balls_bowled",
    "four": "fours", "six": "sixes",
    "century": "centuries", "hundred": "centuries",
    "hundreds": "centuries", "100s": "centuries",
    "50s": "fifties", "fifty": "fifties",
    "duck": "ducks", "hat_trick": "hat_tricks",
    "hattrick": "hat_tricks", "hattricks": "hat_tricks",
    "hs": "highest_score", "highest": "highest_score",
    "partner": "best_partnership", "partnership": "best_partnership",
    "cap_wins": "captain_wins", "cap_losses": "captain_losses",
    "captain_win": "captain_wins", "captain_loss": "captain_losses",
    "not_out": "not_outs", "penalty": "penalties_received",
    "penalties": "penalties_received", "wicket": "wickets",
    "win": "wins", "loss": "losses",
    "rc": "runs_conceded", "bb": "balls_bowled", "bf": "balls_faced",
}


def _resolve_field(name: str):
    name = name.lower().strip()
    if name in NUMERIC_FIELDS:
        return name
    return ALIASES.get(name)


def _fields_text():
    lines = ["📋 <b>ADDSTATS — SUPPORTED FIELD NAMES</b>\n"]
    for key, (label, is_max) in NUMERIC_FIELDS.items():
        note = " <i>(max, not add)</i>" if is_max else ""
        lines.append(f"• <code>{key}</code> — {label}{note}")
    lines.append(
        "\n<i>Tip: Overs in profile messages are auto-converted to balls_bowled.</i>"
    )
    return "\n".join(lines)


# ──────────────────────── Profile message parser ────────────────────────

def _overs_to_balls(overs_str: str) -> int:
    try:
        parts = str(overs_str).split(".")
        whole = int(parts[0])
        rem = int(parts[1]) if len(parts) > 1 else 0
        return whole * 6 + rem
    except Exception:
        return 0


def _parse_profile_message(text: str) -> dict:
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
    ]
    for field, pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                parsed[field] = int(m.group(1))
            except ValueError:
                pass

    m = re.search(r"Overs\s*[:\-]\s*([\d.]+)", text, re.IGNORECASE)
    if m:
        parsed["balls_bowled"] = _overs_to_balls(m.group(1))

    m = re.search(r"(\d+)[×x]\s*Man of the Match", text, re.IGNORECASE)
    if m:
        val = int(m.group(1))
        if val > parsed.get("moms", 0):
            parsed["moms"] = val

    return parsed


# ──────────────────────── DB helpers ────────────────────────

async def _get_existing(user_id: int) -> dict:
    await db.ensure_pool()
    return (await db.db["user_stats"].find_one({"user_id": user_id})) or {}


async def _apply_stats(user_id: int, additions: dict) -> dict:
    await db.ensure_pool()
    col = db.db["user_stats"]
    existing = await col.find_one({"user_id": user_id}) or {}

    inc_ops, max_ops, changes = {}, {}, {}
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


# ──────────────────────── Formatters ────────────────────────

def _preview_text(target_user, existing: dict, additions: dict) -> str:
    name = html.escape(target_user.first_name)
    uid = target_user.id
    lines = [
        f"📋 <b>Confirm Stats Update</b>",
        f"👤 <a href='tg://user?id={uid}'>{name}</a>",
        "━━━━━━━━━━━━━━━━",
        "<b>Field</b>  |  <b>Before → After</b>",
    ]
    for field, value in additions.items():
        info = NUMERIC_FIELDS.get(field)
        if info is None:
            continue
        label, is_max = info
        old = existing.get(field, 0)
        new = max(old, value) if is_max else old + value
        diff = new - old
        diff_str = f"(+{diff})" if diff > 0 else f"({diff})" if diff < 0 else "(no change)"
        lines.append(f"• {label}: <code>{old}</code> → <code>{new}</code> {diff_str}")
    lines.append("━━━━━━━━━━━━━━━━")
    lines.append("⚠️ Do you want to apply these changes?")
    return "\n".join(lines)


def _result_text(target_user, changes: dict, source: str) -> str:
    name = html.escape(target_user.first_name)
    uid = target_user.id
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


def _confirm_kb(key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, Apply", callback_data=f"as_confirm:{key}"),
            InlineKeyboardButton("❌ Cancel",      callback_data=f"as_cancel:{key}"),
        ]
    ])


# ──────────────────────── Command handler ────────────────────────

@Client.on_message(
    filters.command("addstats") & OWNER_FILTER & (filters.private | filters.group)
)
async def addstats_cmd(client: Client, message: Message):
    args = message.command[1:]

    # ── /addstats fields ──
    if args and args[0].lower() == "fields":
        return await message.reply_text(
            _fields_text(), parse_mode=ParseMode.HTML,
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
            "• Reply to profile message: <code>/addstats @username</code>\n"
            "• Direct: <code>/addstats @username runs 50</code>\n"
            "• Field list: <code>/addstats fields</code>",
            parse_mode=ParseMode.HTML,
        )

    # ── Mode A: reply to profile message → confirmation ──
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
                "Make sure it's a valid stats/profile message.",
                parse_mode=ParseMode.HTML,
            )

        existing = await _get_existing(target_user.id)
        _clean_pending()
        key = _pending_key(message.from_user.id)
        _PENDING[key] = {
            "user_id":     message.from_user.id,
            "target_id":   target_user.id,
            "target_name": target_user.first_name,
            "additions":   parsed,
            "source":      "profile message",
            "ts":          time.time(),
        }
        return await message.reply_text(
            _preview_text(target_user, existing, parsed),
            parse_mode=ParseMode.HTML,
            reply_markup=_confirm_kb(key),
        )

    # ── Mode B: direct field + value → instant confirmation ──
    field_args = args[1:]
    if len(field_args) < 2:
        return await message.reply_text(
            "❌ <b>Missing field or value.</b>\n\n"
            "<b>Direct:</b> <code>/addstats @username &lt;field&gt; &lt;value&gt;</code>\n"
            "<b>Reply:</b> Reply to a profile message with <code>/addstats @username</code>\n"
            "<b>Fields:</b> <code>/addstats fields</code>",
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

    existing = await _get_existing(target_user.id)
    additions = {field: value}
    _clean_pending()
    key = _pending_key(message.from_user.id)
    _PENDING[key] = {
        "user_id":     message.from_user.id,
        "target_id":   target_user.id,
        "target_name": target_user.first_name,
        "additions":   additions,
        "source":      "manual",
        "ts":          time.time(),
    }
    return await message.reply_text(
        _preview_text(target_user, existing, additions),
        parse_mode=ParseMode.HTML,
        reply_markup=_confirm_kb(key),
    )


# ──────────────────────── Confirm / Cancel callbacks ────────────────────────

@Client.on_callback_query(filters.regex(r"^as_confirm:") & OWNER_FILTER)
async def addstats_confirm_cb(client: Client, cb: CallbackQuery):
    key = cb.data.split(":", 1)[1]
    pending = _PENDING.get(key)
    if not pending:
        return await cb.answer("⏰ This confirmation expired. Send the command again.", show_alert=True)

    await cb.answer("Applying…")
    del _PENDING[key]

    try:
        target_user = await client.get_users(pending["target_id"])
    except Exception:
        return await cb.message.edit_text("❌ Could not fetch target user. Aborted.")

    changes = await _apply_stats(pending["target_id"], pending["additions"])
    await cb.message.edit_text(
        _result_text(target_user, changes, pending["source"]),
        parse_mode=ParseMode.HTML,
    )


@Client.on_callback_query(filters.regex(r"^as_cancel:") & OWNER_FILTER)
async def addstats_cancel_cb(client: Client, cb: CallbackQuery):
    key = cb.data.split(":", 1)[1]
    _PENDING.pop(key, None)
    await cb.answer("Cancelled.")
    try:
        await cb.message.edit_text("❌ <b>Stats update cancelled.</b>", parse_mode=ParseMode.HTML)
    except Exception:
        pass
