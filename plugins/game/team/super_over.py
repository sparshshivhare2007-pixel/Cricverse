"""
Super Over — 1 over, 1 wicket, group command setup (no DM buttons).

Flow:
  1. trigger_super_over called on tie
  2. Bot shows numbered batting team list in group
  3. Batting captain uses /batting <n> to pick striker
  4. Bot shows numbered bowling team list in group
  5. Bowling captain uses /bowling <n> to pick bowler
  6. Ball-by-ball: bowler DMs 1-6, batter sends 0-6 in group
  7. 1 wicket OR 6 balls → innings ends
  8. Innings 2 → same command-based setup for opposing teams
  9. Winner declared; double-tie → final Tie
"""

import asyncio
import html
from pyrogram.enums import ParseMode

from plugins.game.team import ACTIVE_MATCHES


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _m(uid, match: dict) -> str:
    if not uid:
        return "<b>Player</b>"
    name = match.get("user_cache", {}).get(uid, "Player")
    return f"<a href='tg://user?id={uid}'>{html.escape(str(name))}</a>"


def _tname(match: dict, key: str) -> str:
    name = match.get("teams", {}).get(key, {}).get("name")
    return html.escape(name) if name else f"Team {key}"


def _balls_display(balls: list) -> str:
    parts = []
    for b in balls:
        if b == "W":
            parts.append("❌")
        elif b == 0:
            parts.append("•")
        elif b == 4:
            parts.append("4️⃣")
        elif b == 6:
            parts.append("6️⃣")
        else:
            parts.append(str(b))
    return "  ".join(parts) if parts else "—"


def _player_list_text(match: dict, team: str) -> str:
    players = match.get("teams", {}).get(team, {}).get("players", [])
    cache   = match.get("user_cache", {})
    lines   = []
    for i, uid in enumerate(players, 1):
        name = html.escape(cache.get(uid, f"Player {i}"))
        lines.append(f"  <b>{i}.</b> {name}")
    return "\n".join(lines)


# ─── Entry ────────────────────────────────────────────────────────────────────

async def trigger_super_over(client, match: dict):
    chat_id  = match["chat_id"]
    teams    = match.get("teams", {})
    so_bat_1 = match.get("batting_team", "B")
    so_bat_2 = match.get("bowling_team", "A")

    match["super_over"] = {
        "active":          True,
        "bat_order":       [so_bat_1, so_bat_2],
        "current_innings": 1,
        "scores":          {so_bat_1: 0, so_bat_2: 0},
        "wickets":         {so_bat_1: 0, so_bat_2: 0},
        "striker":         {so_bat_1: None, so_bat_2: None},
        "bowler":          {so_bat_1: None, so_bat_2: None},
        "balls":           {so_bat_1: [], so_bat_2: []},
        "bowled":          False,
        "batted":          False,
        "last_bowl":       None,
        "prompt_dispatched": False,
        "waiting_for":     "striker",
    }
    match["phase"] = "SUPER_OVER"

    a_runs    = teams.get("A", {}).get("runs", 0)
    b_runs    = teams.get("B", {}).get("runs", 0)
    name_bat1 = _tname(match, so_bat_1)
    name_bat2 = _tname(match, so_bat_2)

    try:
        await client.send_message(
            chat_id,
            (
                "🔥 <b>IT'S A TIE!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🅰️ <b>{_tname(match,'A')}:</b> {a_runs}  🆚  "
                f"🅱️ <b>{_tname(match,'B')}:</b> {b_runs}\n\n"
                "⚡ <b>SUPER OVER!</b>\n"
                "┄ 1 over  •  1 wicket  •  Highest score wins!\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏏 <b>{name_bat1}</b> bats first  •  <b>{name_bat2}</b> chases"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        print(f"SO announce error: {e}")

    await asyncio.sleep(1)
    await _ask_batting(client, match)


async def _ask_batting(client, match: dict):
    so           = match["super_over"]
    innings      = so["current_innings"]
    batting_team = so["bat_order"][innings - 1]
    cap_id       = match.get("teams", {}).get(batting_team, {}).get("captain_id")
    cap_name     = html.escape(match.get("user_cache", {}).get(cap_id, "Captain"))
    bat_name     = _tname(match, batting_team)
    player_list  = _player_list_text(match, batting_team)

    try:
        await client.send_message(
            match["chat_id"],
            (
                f"⚡ <b>SUPER OVER — {bat_name} to bat</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"{player_list}\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🧢 <b>{cap_name}</b>, pick your striker:\n"
                f"<code>/batting &lt;number&gt;</code>"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        print(f"SO ask batting error: {e}")


async def _ask_bowling(client, match: dict):
    so           = match["super_over"]
    innings      = so["current_innings"]
    batting_team = so["bat_order"][innings - 1]
    bowling_team = so["bat_order"][innings % 2]
    cap_id       = match.get("teams", {}).get(bowling_team, {}).get("captain_id")
    cap_name     = html.escape(match.get("user_cache", {}).get(cap_id, "Captain"))
    bow_name     = _tname(match, bowling_team)
    player_list  = _player_list_text(match, bowling_team)
    striker_id   = so["striker"][batting_team]
    striker_name = html.escape(match.get("user_cache", {}).get(striker_id, "?"))

    try:
        await client.send_message(
            match["chat_id"],
            (
                f"✅ <b>Striker set:</b> {striker_name}\n\n"
                f"🎯 <b>{bow_name}</b> — pick your bowler:\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"{player_list}\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🧢 <b>{cap_name}</b>, use:\n"
                f"<code>/bowling &lt;number&gt;</code>"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        print(f"SO ask bowling error: {e}")


# ─── Called from setup.py /batting handler ────────────────────────────────────

async def handle_so_batting_cmd(client, message, match: dict, idx: int):
    so           = match["super_over"]
    innings      = so["current_innings"]
    batting_team = so["bat_order"][innings - 1]
    cap_id       = match.get("teams", {}).get(batting_team, {}).get("captain_id")
    user         = message.from_user

    if so.get("waiting_for") != "striker":
        return await message.reply_text(
            "⚠️ <b>Not waiting for a striker right now.</b>",
            parse_mode=ParseMode.HTML,
        )

    if user.id != cap_id:
        return await message.reply_text(
            "🚫 Only the <b>batting captain</b> can pick the Super Over striker.",
            parse_mode=ParseMode.HTML,
        )

    players = match.get("teams", {}).get(batting_team, {}).get("players", [])
    if idx < 0 or idx >= len(players):
        return await message.reply_text(
            f"❌ Invalid number. Choose between 1 and {len(players)}.",
            parse_mode=ParseMode.HTML,
        )

    striker_id = players[idx]
    try:
        user_obj = await client.get_users(striker_id)
        match["user_cache"][striker_id] = user_obj.first_name
    except Exception:
        pass

    so["striker"][batting_team] = striker_id
    so["waiting_for"]           = "bowler"

    await message.reply_text(
        f"🏏 <b>Striker locked:</b> {_m(striker_id, match)}",
        parse_mode=ParseMode.HTML,
    )
    await asyncio.sleep(0.5)
    await _ask_bowling(client, match)


# ─── Called from setup.py /bowling handler ────────────────────────────────────

async def handle_so_bowling_cmd(client, message, match: dict, idx: int):
    so           = match["super_over"]
    innings      = so["current_innings"]
    batting_team = so["bat_order"][innings - 1]
    bowling_team = so["bat_order"][innings % 2]
    cap_id       = match.get("teams", {}).get(bowling_team, {}).get("captain_id")
    user         = message.from_user

    if so.get("waiting_for") != "bowler":
        return await message.reply_text(
            "⚠️ <b>Not waiting for a bowler right now.</b>",
            parse_mode=ParseMode.HTML,
        )

    if user.id != cap_id:
        return await message.reply_text(
            "🚫 Only the <b>bowling captain</b> can pick the Super Over bowler.",
            parse_mode=ParseMode.HTML,
        )

    players = match.get("teams", {}).get(bowling_team, {}).get("players", [])
    if idx < 0 or idx >= len(players):
        return await message.reply_text(
            f"❌ Invalid number. Choose between 1 and {len(players)}.",
            parse_mode=ParseMode.HTML,
        )

    bowler_id = players[idx]
    try:
        user_obj = await client.get_users(bowler_id)
        match["user_cache"][bowler_id] = user_obj.first_name
    except Exception:
        pass

    so["bowler"][batting_team] = bowler_id
    so["waiting_for"]          = "playing"

    await message.reply_text(
        f"🎯 <b>Bowler locked:</b> {_m(bowler_id, match)}\n\n⚡ Super Over starting — watch this space!",
        parse_mode=ParseMode.HTML,
    )
    await asyncio.sleep(0.5)
    await _start_so_innings(client, match)


# ─── Innings Start ────────────────────────────────────────────────────────────

async def _start_so_innings(client, match: dict):
    so           = match["super_over"]
    innings      = so["current_innings"]
    batting_team = so["bat_order"][innings - 1]
    bowling_team = so["bat_order"][innings % 2]

    striker_id = so["striker"][batting_team]
    bowler_id  = so["bowler"][batting_team]

    if not striker_id or not bowler_id:
        print(f"SO _start_so_innings: striker or bowler is None — aborting")
        return

    so["bowled"]            = False
    so["batted"]            = False
    so["last_bowl"]         = None
    so["prompt_dispatched"] = False
    so["balls"][batting_team] = []

    chat_id      = match["chat_id"]
    cache        = match.get("user_cache", {})
    bat_name     = _tname(match, batting_team)
    bow_name     = _tname(match, bowling_team)
    striker_name = html.escape(cache.get(striker_id, "Striker"))
    bowler_name  = html.escape(cache.get(bowler_id, "Bowler"))

    target_note = ""
    if innings == 2:
        t1_score    = so["scores"][so["bat_order"][0]]
        target_note = f"\n🎯 <b>Target: {t1_score + 1} run(s)</b>"

    try:
        await client.send_message(
            chat_id,
            (
                f"⚡ <b>SUPER OVER — Innings {innings}</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏏 <b>Batting:</b>  {bat_name}\n"
                f"   ⚔️ Striker:  <b>{striker_name}</b>\n\n"
                f"🎯 <b>Bowling:</b>  {bow_name}\n"
                f"   🎳 Bowler:   <b>{bowler_name}</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ 6 balls  •  1 wicket  •  Let's go!{target_note}"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        print(f"SO start innings error: {e}")

    await asyncio.sleep(1)
    await _so_prompt_ball(client, match)


# ─── Ball Prompt ──────────────────────────────────────────────────────────────

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
    balls_done   = len(so["balls"][batting_team])
    ball_no      = balls_done + 1
    cache        = match.get("user_cache", {})

    if "bot_username" not in match:
        try:
            me = await client.get_me()
            match["bot_username"] = me.username
        except Exception:
            match["bot_username"] = "NexoraCricketBot"

    bot_username  = match["bot_username"]
    striker_name  = html.escape(cache.get(striker_id, "Striker")) if striker_id else "?"
    bowler_name   = html.escape(cache.get(bowler_id, "Bowler")) if bowler_id else "?"
    score_disp    = f"{score}/{wickets}"
    bat_name      = _tname(match, batting_team)
    balls_display = _balls_display(so["balls"][batting_team])

    target_note = ""
    if innings == 2:
        t1_score    = so["scores"][so["bat_order"][0]]
        runs_needed = t1_score + 1 - score
        balls_left  = 6 - balls_done
        target_note = f"\n🎯 Need <b>{max(0, runs_needed)}</b> off <b>{balls_left}</b> balls"

    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    group_btn = InlineKeyboardMarkup([[
        InlineKeyboardButton("ᴅᴇʟɪᴠᴇʀ ʙᴀʟʟ ⚾", url=f"https://t.me/{bot_username}")
    ]])

    bowler_mention  = f"<a href='tg://user?id={bowler_id}'>{bowler_name}</a>" if bowler_id else f"<b>{bowler_name}</b>"
    striker_mention = f"<a href='tg://user?id={striker_id}'>{striker_name}</a>" if striker_id else f"<b>{striker_name}</b>"
    balls_line      = f"📋 [ {balls_display} ]" if so["balls"][batting_team] else ""

    try:
        await client.send_message(
            chat_id,
            (
                f"⚡ <b>SO Ball {ball_no}/6</b>  │  <b>{bat_name}:</b> {score_disp}{target_note}\n"
                f"{balls_line}\n"
                f"🎳 {bowler_mention}  →  🏏 {striker_mention}\n"
                "🔢 Bowler, go to bot DM to deliver!"
            ).strip(),
            parse_mode=ParseMode.HTML,
            reply_markup=group_btn,
        )
    except Exception as e:
        print(f"SO group prompt error: {e}")

    # DM the bowler
    try:
        await client.send_message(
            bowler_id,
            (
                f"⚡ <b>SUPER OVER — Ball {ball_no}/6</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏏 <b>Striker:</b>  {striker_name}\n"
                f"📊 <b>Score:</b>    {score_disp}{target_note}\n"
                f"{f'📋 Balls: [ {balls_display} ]' if so['balls'][batting_team] else ''}\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "🔢 Send a number (<b>1–6</b>) to bowl:"
            ).strip(),
            parse_mode=ParseMode.HTML,
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

    striker_id = so["striker"][batting_team]
    if not striker_id:
        print("SO handle_so_bowl: striker_id is None — cannot notify batter")
        return

    so["last_bowl"] = bowl_num
    so["bowled"]    = True

    chat_id  = match["chat_id"]
    ball_no  = len(so["balls"][batting_team]) + 1

    try:
        await client.send_message(
            chat_id,
            (
                f"⚾ <b>Ball {ball_no} delivered!</b>\n"
                f"🏏 {_m(striker_id, match)} — send your shot (<b>0–6</b>) in the group!"
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
    bat_name = _tname(match, batting_team)

    COMMS = {
        0: "Dot ball 🔒",
        1: "Quick single! 🏃",
        2: "Two runs! ✌️",
        3: "Three! Great running 🏃‍♂️",
        4: "FOUR! 💥 Boundary!",
        5: "FIVE! 😱",
        6: "SIX! 🚀 Maximum!",
    }

    if is_out:
        so["balls"][batting_team].append("W")
        so["wickets"][batting_team] += 1
        score_disp    = f"{so['scores'][batting_team]}/{so['wickets'][batting_team]}"
        balls_display = _balls_display(so["balls"][batting_team])
        batter_name   = html.escape(match.get("user_cache", {}).get(batter_uid, "Batter"))

        try:
            await client.send_message(
                chat_id,
                (
                    f"🎯 <b>WICKET!</b>  {batter_name} is OUT!\n"
                    f"📊 {bat_name}: <b>{score_disp}</b>\n"
                    f"📋 [ {balls_display} ]\n\n"
                    "⚡ <b>Innings over — 1 wicket used!</b>"
                ),
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            print(f"SO wicket announce error: {e}")

        await asyncio.sleep(1)
        await _end_so_innings(client, match)
        return

    # Runs scored
    so["scores"][batting_team] += runs
    so["balls"][batting_team].append(runs)

    score_disp    = f"{so['scores'][batting_team]}/{so['wickets'][batting_team]}"
    balls_done    = len(so["balls"][batting_team])
    balls_display = _balls_display(so["balls"][batting_team])
    comm          = COMMS.get(runs, f"{runs} runs")

    # Check innings-2 chase finish
    if innings == 2:
        t1_score = so["scores"][so["bat_order"][0]]
        if so["scores"][batting_team] > t1_score:
            try:
                await client.send_message(
                    chat_id,
                    (
                        f"🏏 <b>Ball {ball_no}:</b>  {runs}  •  {comm}\n"
                        f"📊 {bat_name}: <b>{score_disp}</b>\n"
                        f"📋 [ {balls_display} ]\n\n"
                        "🎉 <b>Target chased! Innings over!</b>"
                    ),
                    parse_mode=ParseMode.HTML,
                )
            except Exception as e:
                print(f"SO chase result error: {e}")
            await asyncio.sleep(1)
            await _end_so_innings(client, match)
            return

    try:
        await client.send_message(
            chat_id,
            (
                f"🏏 <b>Ball {ball_no}:</b>  {runs}  •  {comm}\n"
                f"📊 {bat_name}: <b>{score_disp}</b>\n"
                f"📋 [ {balls_display} ]"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        print(f"SO ball result error: {e}")

    if balls_done >= 6:
        await asyncio.sleep(1)
        await _end_so_innings(client, match)
        return

    await asyncio.sleep(0.5)
    so["batted"] = False
    so["bowled"] = False
    await _so_prompt_ball(client, match)


# ─── End of Innings ───────────────────────────────────────────────────────────

async def _end_so_innings(client, match: dict):
    so      = match["super_over"]
    innings = so["current_innings"]

    if innings == 1:
        so["current_innings"] = 2
        so["waiting_for"]     = "striker"
        so["prompt_dispatched"] = False

        next_bat  = so["bat_order"][1]
        next_bowl = so["bat_order"][0]
        prev_bat  = so["bat_order"][0]
        t1_score  = so["scores"][prev_bat]

        prev_balls = _balls_display(so["balls"][prev_bat])

        try:
            await client.send_message(
                match["chat_id"],
                (
                    f"📋 <b>Innings 1 Summary</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🏏 <b>{_tname(match, prev_bat)}:</b>  {t1_score}/{so['wickets'][prev_bat]}\n"
                    f"Balls: [ {prev_balls} ]\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🎯 <b>{_tname(match, next_bat)}</b> need <b>{t1_score + 1}</b> to win!"
                ),
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            print(f"SO innings summary error: {e}")

        await asyncio.sleep(1)
        await _ask_batting(client, match)

    else:
        await _declare_so_result(client, match)


async def _declare_so_result(client, match: dict):
    so       = match["super_over"]
    team1    = so["bat_order"][0]
    team2    = so["bat_order"][1]
    score1   = so["scores"][team1]
    score2   = so["scores"][team2]
    wickets1 = so["wickets"][team1]
    wickets2 = so["wickets"][team2]
    balls1   = _balls_display(so["balls"][team1])
    balls2   = _balls_display(so["balls"][team2])
    name1    = _tname(match, team1)
    name2    = _tname(match, team2)

    so["active"] = False
    match["phase"] = "ENDED"

    if score1 > score2:
        winner_line = f"🏆 <b>{name1} WIN the Super Over!</b>  (+{score1 - score2} runs)"
    elif score2 > score1:
        winner_line = f"🏆 <b>{name2} WIN the Super Over!</b>  (+{score2 - score1} runs)"
    else:
        winner_line = "🤝 <b>DOUBLE TIE — Match declared a Tie!</b>"

    try:
        await client.send_message(
            match["chat_id"],
            (
                "⚡ <b>SUPER OVER RESULT</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏏 <b>{name1}:</b>  {score1}/{wickets1}\n"
                f"   [ {balls1} ]\n\n"
                f"🎯 <b>{name2}:</b>  {score2}/{wickets2}\n"
                f"   [ {balls2} ]\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"{winner_line}"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        print(f"SO result error: {e}")

    # Clean up ACTIVE_MATCHES
    chat_id = match.get("chat_id")
    if chat_id and chat_id in ACTIVE_MATCHES:
        try:
            ACTIVE_MATCHES.pop(chat_id, None)
        except Exception:
            pass
