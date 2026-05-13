"""
Super Over — triggered on match tie when super_over setting is enabled.

Flow:
  1. trigger_super_over(client, match) called from end_match on tie
  2. Batting captain picks their STRIKER (batter 1) via inline buttons
  3. Batting captain picks their NON-STRIKER (batter 2) from remaining players
  4. Bowling captain picks their bowler
  5. 1-over innings plays: bowler DMs number, batter replies 0-6 in group
  6. If striker is OUT → non-striker becomes striker (1 wicket used, can continue)
  7. If that batter is also OUT → innings ends (2 wickets, over)
  8. 6 balls completed → innings ends regardless
  9. Innings 2 → same setup for opposing teams
 10. Winner declared; double-tie → Tie result
"""

import asyncio
import html
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

from plugins.game.team import ACTIVE_MATCHES


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _m(uid: int, match: dict) -> str:
    name = match.get("user_cache", {}).get(uid, "Player")
    return f"<a href='tg://user?id={uid}'>{html.escape(name)}</a>"


def _back_btn(chat_id: int) -> InlineKeyboardMarkup:
    clean = str(chat_id).replace("-100", "")
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🏏 Back to Group", url=f"https://t.me/c/{clean}/999999999")
    ]])


def _make_player_buttons(match, batting_team, cb_prefix, exclude_uid=None):
    """Build player selection buttons excluding exclude_uid."""
    players = match.get("teams", {}).get(batting_team, {}).get("players", [])
    cache   = match.get("user_cache", {})
    buttons, row = [], []
    idx_map = {}  # real_idx → uid (for skip handling)
    btn_idx = 0
    for real_idx, uid in enumerate(players):
        if uid == exclude_uid:
            continue
        name = html.escape(cache.get(uid, f"P{real_idx+1}"))[:20]
        row.append(InlineKeyboardButton(name, callback_data=f"{cb_prefix}_{real_idx}"))
        idx_map[real_idx] = uid
        btn_idx += 1
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return buttons


# ─── Entry ────────────────────────────────────────────────────────────────────

async def trigger_super_over(client, match: dict):
    chat_id = match["chat_id"]
    teams   = match.get("teams", {})

    so_bat_1 = match.get("batting_team", "B")
    so_bat_2 = match.get("bowling_team", "A")

    match["super_over"] = {
        "active":           True,
        "bat_order":        [so_bat_1, so_bat_2],
        "current_innings":  1,
        "scores":           {so_bat_1: 0, so_bat_2: 0},
        "wickets":          {so_bat_1: 0, so_bat_2: 0},   # max 2
        "striker":          {so_bat_1: None, so_bat_2: None},
        "non_striker":      {so_bat_1: None, so_bat_2: None},
        "bowler":           {so_bat_1: None, so_bat_2: None},
        "balls":            {so_bat_1: [], so_bat_2: []},
        "bowled":           False,
        "batted":           False,
        "last_bowl":        None,
        "prompt_dispatched": False,
    }
    match["phase"] = "SUPER_OVER"

    a_runs = teams.get("A", {}).get("runs", 0)
    b_runs = teams.get("B", {}).get("runs", 0)

    try:
        await client.send_message(
            chat_id,
            (
                "🔥 <b>IT'S A TIE!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🅰️ <b>Team A:</b> {a_runs}  🆚  🅱️ <b>Team B:</b> {b_runs}\n\n"
                "⚡ <b>SUPER OVER!</b>\n"
                "┄ 1 over each  •  2 batters each  •  2 wickets\n"
                "┄ Highest score wins!\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏏 <b>Team {so_bat_1}</b> bats first in the Super Over"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        print(f"SO announce error: {e}")

    await asyncio.sleep(1)
    await _ask_so_striker(client, match, so_bat_1)


# ─── Setup: Striker ───────────────────────────────────────────────────────────

async def _ask_so_striker(client, match: dict, batting_team: str):
    chat_id  = match["chat_id"]
    cap_id   = match.get("teams", {}).get(batting_team, {}).get("captain_id")
    cache    = match.get("user_cache", {})
    cap_name = html.escape(cache.get(cap_id, "Captain"))
    buttons  = _make_player_buttons(match, batting_team, f"so_str_{match['chat_id']}")

    try:
        await client.send_message(
            chat_id,
            (
                "⚡ <b>SUPER OVER SETUP — Pick Striker</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏏 <b>Team {batting_team}</b> — Who opens the batting?\n"
                f"🧢 <a href='tg://user?id={cap_id}'>{cap_name}</a>, choose your striker:"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
        )
    except Exception as e:
        print(f"SO ask striker error: {e}")


# ─── Setup: Non-striker ───────────────────────────────────────────────────────

async def _ask_so_non_striker(client, match: dict, batting_team: str):
    chat_id   = match["chat_id"]
    so        = match["super_over"]
    striker   = so["striker"][batting_team]
    cap_id    = match.get("teams", {}).get(batting_team, {}).get("captain_id")
    cache     = match.get("user_cache", {})
    cap_name  = html.escape(cache.get(cap_id, "Captain"))
    buttons   = _make_player_buttons(match, batting_team, f"so_nst_{match['chat_id']}", exclude_uid=striker)

    try:
        await client.send_message(
            chat_id,
            (
                "⚡ <b>SUPER OVER SETUP — Pick Non-Striker</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏏 <b>Team {batting_team}</b> — Who is at the non-striker end?\n"
                f"🧢 <a href='tg://user?id={cap_id}'>{cap_name}</a>, choose your second batter:"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
        )
    except Exception as e:
        print(f"SO ask non-striker error: {e}")


# ─── Setup: Bowler ────────────────────────────────────────────────────────────

async def _ask_so_bowler(client, match: dict, bowling_team: str):
    chat_id  = match["chat_id"]
    cap_id   = match.get("teams", {}).get(bowling_team, {}).get("captain_id")
    players  = match.get("teams", {}).get(bowling_team, {}).get("players", [])
    cache    = match.get("user_cache", {})
    cap_name = html.escape(cache.get(cap_id, "Captain"))

    buttons, row = [], []
    for i, uid in enumerate(players):
        name = html.escape(cache.get(uid, f"P{i+1}"))[:20]
        row.append(InlineKeyboardButton(name, callback_data=f"so_bowl_{match['chat_id']}_{i}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    try:
        await client.send_message(
            chat_id,
            (
                "⚡ <b>SUPER OVER SETUP — Pick Bowler</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 <b>Team {bowling_team}</b> — Who will bowl the super over?\n"
                f"🧢 <a href='tg://user?id={cap_id}'>{cap_name}</a>, choose your bowler:"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
        )
    except Exception as e:
        print(f"SO ask bowler error: {e}")


# ─── Callbacks ────────────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^so_str_-?\d+_\d+$"))
async def so_striker_pick(client, query):
    parts    = query.data.split("_")
    chat_id  = int(parts[2])
    real_idx = int(parts[3])

    match = ACTIVE_MATCHES.get(chat_id)
    if not match:
        return await query.answer("No active match.", show_alert=True)

    so = match.get("super_over", {})
    if not so.get("active"):
        return await query.answer("Super over not active.", show_alert=True)

    innings      = so["current_innings"]
    batting_team = so["bat_order"][innings - 1]
    bowling_team = so["bat_order"][innings % 2]
    cap_id       = match.get("teams", {}).get(batting_team, {}).get("captain_id")

    if query.from_user.id != cap_id:
        return await query.answer("Only the batting captain can pick!", show_alert=True)
    if so["striker"][batting_team] is not None:
        return await query.answer("Striker already chosen!", show_alert=True)

    players = match.get("teams", {}).get(batting_team, {}).get("players", [])
    if real_idx >= len(players):
        return await query.answer("Invalid choice.", show_alert=True)

    uid  = players[real_idx]
    name = html.escape(match.get("user_cache", {}).get(uid, "Player"))
    so["striker"][batting_team] = uid

    try:
        await query.message.edit_text(
            f"🏏 <b>{name}</b> will open the batting (Striker) for Team {batting_team}!",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass
    await query.answer(f"{name} selected as Striker!")
    await _ask_so_non_striker(client, match, batting_team)


@Client.on_callback_query(filters.regex(r"^so_nst_-?\d+_\d+$"))
async def so_non_striker_pick(client, query):
    parts    = query.data.split("_")
    chat_id  = int(parts[2])
    real_idx = int(parts[3])

    match = ACTIVE_MATCHES.get(chat_id)
    if not match:
        return await query.answer("No active match.", show_alert=True)

    so = match.get("super_over", {})
    if not so.get("active"):
        return await query.answer("Super over not active.", show_alert=True)

    innings      = so["current_innings"]
    batting_team = so["bat_order"][innings - 1]
    cap_id       = match.get("teams", {}).get(batting_team, {}).get("captain_id")

    if query.from_user.id != cap_id:
        return await query.answer("Only the batting captain can pick!", show_alert=True)
    if so["striker"][batting_team] is None:
        return await query.answer("Pick striker first!", show_alert=True)
    if so["non_striker"][batting_team] is not None:
        return await query.answer("Non-striker already chosen!", show_alert=True)

    players = match.get("teams", {}).get(batting_team, {}).get("players", [])
    if real_idx >= len(players):
        return await query.answer("Invalid choice.", show_alert=True)

    uid = players[real_idx]
    if uid == so["striker"][batting_team]:
        return await query.answer("Can't pick the same player as striker!", show_alert=True)

    name = html.escape(match.get("user_cache", {}).get(uid, "Player"))
    so["non_striker"][batting_team] = uid

    bowling_team = so["bat_order"][innings % 2]

    try:
        await query.message.edit_text(
            f"🤝 <b>{name}</b> is at the non-striker end for Team {batting_team}!",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass
    await query.answer(f"{name} selected as Non-Striker!")
    await _ask_so_bowler(client, match, bowling_team)


@Client.on_callback_query(filters.regex(r"^so_bowl_-?\d+_\d+$"))
async def so_bowler_pick(client, query):
    parts    = query.data.split("_")
    chat_id  = int(parts[2])
    idx      = int(parts[3])

    match = ACTIVE_MATCHES.get(chat_id)
    if not match:
        return await query.answer("No active match.", show_alert=True)

    so = match.get("super_over", {})
    if not so.get("active"):
        return await query.answer("Super over not active.", show_alert=True)

    innings      = so["current_innings"]
    batting_team = so["bat_order"][innings - 1]
    bowling_team = so["bat_order"][innings % 2]
    cap_id       = match.get("teams", {}).get(bowling_team, {}).get("captain_id")

    if query.from_user.id != cap_id:
        return await query.answer("Only the bowling captain can pick!", show_alert=True)
    if so["bowler"][batting_team] is not None:
        return await query.answer("Bowler already chosen!", show_alert=True)

    players = match.get("teams", {}).get(bowling_team, {}).get("players", [])
    if idx >= len(players):
        return await query.answer("Invalid choice.", show_alert=True)

    uid  = players[idx]
    name = html.escape(match.get("user_cache", {}).get(uid, "Player"))
    so["bowler"][batting_team] = uid

    try:
        await query.message.edit_text(
            f"🎯 <b>{name}</b> will bowl for Team {bowling_team} in Super Over Innings {innings}!",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass
    await query.answer(f"{name} selected as Bowler!")
    await _start_so_innings(client, match)


# ─── Innings ──────────────────────────────────────────────────────────────────

async def _start_so_innings(client, match: dict):
    so           = match["super_over"]
    innings      = so["current_innings"]
    batting_team = so["bat_order"][innings - 1]
    bowling_team = so["bat_order"][innings % 2]

    striker_id    = so["striker"][batting_team]
    non_striker_id = so["non_striker"][batting_team]
    bowler_id     = so["bowler"][batting_team]

    if not striker_id or not bowler_id:
        return

    so["bowled"]            = False
    so["batted"]            = False
    so["last_bowl"]         = None
    so["prompt_dispatched"] = False
    so["balls"][batting_team] = []

    chat_id = match["chat_id"]
    cache   = match.get("user_cache", {})

    ns_text = f"  |  🤝 {html.escape(cache.get(non_striker_id, 'Non-Striker'))}" if non_striker_id else ""

    try:
        await client.send_message(
            chat_id,
            (
                f"⚡ <b>SUPER OVER — Innings {innings}</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏏 <b>Batting:</b>  Team {batting_team}\n"
                f"   ⚔️ Striker: {html.escape(cache.get(striker_id, 'Striker'))}"
                f"{ns_text}\n"
                f"🎯 <b>Bowling:</b>  Team {bowling_team} "
                f"— {html.escape(cache.get(bowler_id, 'Bowler'))}\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "⚡ <b>2 wickets  •  6 balls  •  Let's go!</b>"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        print(f"SO start innings error: {e}")

    await asyncio.sleep(1)
    await _so_prompt_ball(client, match)


async def _so_prompt_ball(client, match: dict):
    so = match["super_over"]
    if not so.get("active"):
        return

    so["bowled"]            = False
    so["batted"]            = False
    so["prompt_dispatched"] = True

    chat_id      = match["chat_id"]
    innings      = so["current_innings"]
    batting_team = so["bat_order"][innings - 1]
    bowling_team = so["bat_order"][innings % 2]
    striker_id   = so["striker"][batting_team]
    bowler_id    = so["bowler"][batting_team]
    score        = so["scores"][batting_team]
    wickets      = so["wickets"][batting_team]
    ball_no      = len(so["balls"][batting_team]) + 1
    cache        = match.get("user_cache", {})

    if "bot_username" not in match:
        try:
            me = await client.get_me()
            match["bot_username"] = me.username
        except Exception:
            match["bot_username"] = "NexoraCricketBot"

    bot_username = match["bot_username"]

    striker_name = html.escape(cache.get(striker_id, "Striker"))
    bowler_name  = html.escape(cache.get(bowler_id, "Bowler"))
    score_disp   = f"{score}/{wickets}"

    target_note = ""
    if innings == 2:
        t1_score     = so["scores"][so["bat_order"][0]]
        runs_needed  = t1_score + 1 - score
        balls_remain = 6 - (ball_no - 1)
        target_note  = f"\n🎯 Need <b>{max(0, runs_needed)}</b> in <b>{balls_remain}</b> balls"

    group_btn = InlineKeyboardMarkup([[
        InlineKeyboardButton("ᴅᴇʟɪᴠᴇʀ ʙᴀʟʟ ⚾", url=f"https://t.me/{bot_username}")
    ]])

    try:
        await client.send_message(
            chat_id,
            (
                f"⚡ <b>SO Ball {ball_no}/6</b>  |  Score: {score_disp}"
                f"{target_note}\n"
                f"🎯 <a href='tg://user?id={bowler_id}'>{bowler_name}</a> "
                f"→ 🏏 <a href='tg://user?id={striker_id}'>{striker_name}</a>\n"
                "🔢 Bowler, check your PM to deliver!"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=group_btn,
        )
    except Exception as e:
        print(f"SO group prompt error: {e}")

    try:
        await client.send_message(
            bowler_id,
            (
                f"⚡ <b>SUPER OVER — Ball {ball_no}/6</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏏 <b>Striker:</b> {striker_name}\n"
                "🔢 Send a number (<b>1–6</b>) to bowl:"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=_back_btn(chat_id),
        )
    except Exception as e:
        print(f"SO DM bowler error: {e}")


# ─── Ball handlers (called from state.py) ─────────────────────────────────────

async def handle_so_bowl(client, match: dict, bowler_uid: int, bowl_num: int):
    so = match["super_over"]
    if so.get("bowled") or not so.get("prompt_dispatched"):
        return

    innings      = so["current_innings"]
    batting_team = so["bat_order"][innings - 1]
    if so["bowler"][batting_team] != bowler_uid:
        return

    so["last_bowl"] = bowl_num
    so["bowled"]    = True

    chat_id      = match["chat_id"]
    striker_id   = so["striker"][batting_team]
    ball_no      = len(so["balls"][batting_team]) + 1
    striker_name = html.escape(match.get("user_cache", {}).get(striker_id, "Striker"))

    try:
        await client.send_message(
            chat_id,
            (
                f"⚾ <b>SO Ball {ball_no} delivered!</b>\n"
                f"🏏 {_m(striker_id, match)}, send your shot (0–6) in the group!"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        print(f"SO bowl announce error: {e}")


async def handle_so_bat(client, match: dict, batter_uid: int, bat_num: int):
    so = match["super_over"]
    if so.get("batted") or not so.get("bowled"):
        return

    innings      = so["current_innings"]
    batting_team = so["bat_order"][innings - 1]
    if so["striker"][batting_team] != batter_uid:
        return

    so["batted"] = True
    so["bowled"] = False

    chat_id  = match["chat_id"]
    bowl_num = so["last_bowl"]
    is_out   = (bat_num == bowl_num)
    runs     = bat_num if not is_out else 0
    ball_no  = len(so["balls"][batting_team]) + 1

    if is_out:
        so["balls"][batting_team].append("W")
        so["wickets"][batting_team] += 1
        non_striker = so["non_striker"][batting_team]

        # Can the non-striker come in?
        if non_striker and so["wickets"][batting_team] < 2:
            old_striker  = so["striker"][batting_team]
            old_name     = html.escape(match.get("user_cache", {}).get(old_striker, "Batter"))
            new_name     = html.escape(match.get("user_cache", {}).get(non_striker, "Non-Striker"))
            so["striker"][batting_team]     = non_striker
            so["non_striker"][batting_team] = None

            try:
                await client.send_message(
                    chat_id,
                    (
                        f"☝️ <b>OUT!</b> {_m(old_striker, match)} dismissed!\n"
                        f"⚡ Score: <b>{so['scores'][batting_team]}/{so['wickets'][batting_team]}</b>\n\n"
                        f"🏏 <b>{new_name}</b> walks in as the new striker!"
                    ),
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass

            balls_done = len(so["balls"][batting_team])
            if balls_done >= 6:
                await _end_so_innings(client, match)
            else:
                await _so_prompt_ball(client, match)
        else:
            # All wickets gone or no non-striker
            try:
                await client.send_message(
                    chat_id,
                    (
                        f"☝️ <b>ALL OUT!</b> {_m(batter_uid, match)} dismissed!\n"
                        f"⚡ Team {batting_team} innings ends — "
                        f"{so['scores'][batting_team]}/{so['wickets'][batting_team]}"
                    ),
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass
            await _end_so_innings(client, match)
    else:
        so["scores"][batting_team] += runs
        so["balls"][batting_team].append(runs)

        COMMS = {
            0: "Dot ball 🔒", 1: "Quick single!", 2: "Two runs!",
            3: "Three! 🏃",   4: "FOUR! 💥",     5: "FIVE! 😱",
            6: "SIX! 🚀 Maximum!"
        }
        wickets    = so["wickets"][batting_team]
        score_disp = f"{so['scores'][batting_team]}/{wickets}"

        try:
            await client.send_message(
                chat_id,
                (
                    f"🏏 <b>SO Ball {ball_no}:</b>  +{runs}  {COMMS.get(runs, '')}\n"
                    f"⚡ Score: <b>{score_disp}</b>"
                ),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

        # Chase win check
        if innings == 2:
            t1_score = so["scores"][so["bat_order"][0]]
            if so["scores"][batting_team] > t1_score:
                await _end_so_innings(client, match)
                return

        if len(so["balls"][batting_team]) >= 6:
            await _end_so_innings(client, match)
        else:
            await _so_prompt_ball(client, match)


async def _end_so_innings(client, match: dict):
    so           = match["super_over"]
    innings      = so["current_innings"]
    batting_team = so["bat_order"][innings - 1]
    chat_id      = match["chat_id"]
    score        = so["scores"][batting_team]
    wickets      = so["wickets"][batting_team]
    balls        = so["balls"][batting_team]
    balls_str    = " • ".join(str(b) for b in balls) if balls else "—"

    try:
        await client.send_message(
            chat_id,
            (
                f"🏁 <b>Super Over Innings {innings} Complete</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏏 Team <b>{batting_team}</b>: <b>{score}/{wickets}</b> "
                f"({len([b for b in balls if b != 'W'])} balls)\n"
                f"📋 [ {balls_str} ]"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    if innings == 1:
        so["current_innings"] = 2
        batting_team_2 = so["bat_order"][1]
        target = score + 1
        await asyncio.sleep(1)
        try:
            await client.send_message(
                chat_id,
                (
                    f"🎯 <b>Super Over Target</b>\n"
                    f"Team <b>{batting_team_2}</b> needs <b>{target}</b> run(s) to win!\n"
                    "⚡ Setting up Innings 2…"
                ),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
        await asyncio.sleep(1)
        await _ask_so_striker(client, match, batting_team_2)
    else:
        await _end_super_over(client, match)


async def _end_super_over(client, match: dict):
    so      = match["super_over"]
    chat_id = match["chat_id"]
    t1      = so["bat_order"][0]
    t2      = so["bat_order"][1]
    s1      = so["scores"][t1]
    s2      = so["scores"][t2]

    if s1 > s2:
        winner      = t1
        margin_text = f"Team <b>{t1}</b> wins by {s1 - s2} run(s)! 🏆"
    elif s2 > s1:
        winner      = t2
        wkts_left   = 2 - so["wickets"][t2]
        margin_text = f"Team <b>{t2}</b> wins by {wkts_left} wicket(s)! 🏆"
    else:
        winner      = "Tie"
        margin_text = "Super Over also TIED! — Match declared a <b>Tie</b> 🤝"

    so["active"]   = False
    match["phase"] = "finished"

    try:
        await client.send_message(
            chat_id,
            (
                "⚡ <b>SUPER OVER RESULT</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏏 Team {t1}: <b>{s1}</b> runs\n"
                f"🏏 Team {t2}: <b>{s2}</b> runs\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏆 {margin_text}"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    try:
        from plugins.game.team.scorecard import save_match_stats
        asyncio.create_task(save_match_stats(match, winner))
    except Exception as e:
        print(f"SO stats save error: {e}")

    ACTIVE_MATCHES.pop(chat_id, None)

    try:
        from database.connection import db
        await db.db["games"].update_one(
            {"game_id": match.get("game_id")},
            {"$set": {"status": "ended", "winner": winner}},
        )
    except Exception:
        pass
