"""
IPL Team Selection — after both captains are confirmed, each captain is DM'd
with buttons to pick their IPL team (2 per row). Once both pick (or 60s timeout),
announces the choices in the group and proceeds to toss.

Duplicate guard: once a captain locks a team it is added to TAKEN_TEAMS[chat_id].
If the other captain tries the same team they get an alert and must pick again.
"""

import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

from plugins.game.team import ACTIVE_MATCHES

IPL_TEAMS = [
    ("🟡 CSK", "CSK"),   ("💙 MI", "MI"),
    ("🔴 RCB", "RCB"),   ("💜 KKR", "KKR"),
    ("🔵 DC", "DC"),     ("🟠 SRH", "SRH"),
    ("🩷 PBKS", "PBKS"), ("🩵 RR", "RR"),
    ("🟢 LSG", "LSG"),   ("🔵 GT", "GT"),
]

# user_id  → {"future": asyncio.Future, "chat_id": int}
PENDING_IPL: dict = {}

# chat_id → set of already-claimed IPL codes for this game
TAKEN_TEAMS: dict = {}


def build_ipl_buttons():
    buttons = []
    row = []
    for label, code in IPL_TEAMS:
        row.append(InlineKeyboardButton(label, callback_data=f"ipl_pick_{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


async def _ask_one_captain_ipl(client, cap_uid: int, team_key: str, chat_id: int):
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    PENDING_IPL[cap_uid] = {"future": future, "chat_id": chat_id}

    try:
        await client.send_message(
            cap_uid,
            (
                f"🏏 <b>Pick Your IPL Team!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"You are captaining <b>Team {team_key}</b>.\n"
                "Choose your IPL franchise below 👇\n"
                "<i>(You have 60 seconds)</i>"
            ),
            reply_markup=build_ipl_buttons(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        PENDING_IPL.pop(cap_uid, None)
        return None

    try:
        pick = await asyncio.wait_for(asyncio.shield(future), timeout=60)
        return pick
    except asyncio.TimeoutError:
        return None
    finally:
        PENDING_IPL.pop(cap_uid, None)


async def ask_ipl_teams(client, match: dict, chat_id: int, game_id: str, capA_uid: int, capB_uid: int):
    TAKEN_TEAMS[chat_id] = set()

    try:
        pick_a, pick_b = await asyncio.gather(
            _ask_one_captain_ipl(client, capA_uid, "A", chat_id),
            _ask_one_captain_ipl(client, capB_uid, "B", chat_id),
        )
    finally:
        TAKEN_TEAMS.pop(chat_id, None)

    match = ACTIVE_MATCHES.get(chat_id, match)

    if pick_a:
        match["teams"]["A"]["ipl_team"] = pick_a
    if pick_b:
        match["teams"]["B"]["ipl_team"] = pick_b

    na = pick_a or "—"
    nb = pick_b or "—"

    try:
        await client.send_message(
            chat_id,
            (
                "🏆 <b>IPL TEAMS CHOSEN!</b>\n"
                "────┈┄┄╌╌╌╌┄┄┈────\n"
                f"🌊 <b>Team A:</b> {na}\n"
                f"🔥 <b>Team B:</b> {nb}\n"
                "────┈┄┄╌╌╌╌┄┄┈────"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    from plugins.game.team.setup import send_toss
    await send_toss(client, chat_id, game_id)


@Client.on_callback_query(filters.regex(r"^ipl_pick_"))
async def ipl_pick_handler(client, query):
    uid = query.from_user.id
    entry = PENDING_IPL.get(uid)

    if entry is None or entry["future"].done():
        return await query.answer("No pending team selection or already picked.", show_alert=True)

    code = query.data[len("ipl_pick_"):]
    chat_id = entry["chat_id"]
    taken = TAKEN_TEAMS.get(chat_id, set())

    if code in taken:
        return await query.answer(
            f"❌ {code} is already taken by the other captain!\nPick a different team.",
            show_alert=True,
        )

    taken.add(code)
    TAKEN_TEAMS[chat_id] = taken

    entry["future"].set_result(code)
    PENDING_IPL.pop(uid, None)

    await query.message.edit_text(
        f"✅ <b>IPL Team selected:</b> <b>{code}</b> 🎉\n"
        "Your choice has been locked in!",
        parse_mode=ParseMode.HTML,
    )
    await query.answer(f"✅ {code} locked in!")
