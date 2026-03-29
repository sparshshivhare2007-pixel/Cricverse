import asyncio
from pyrogram.enums import ParseMode


async def start_solo_timer(match, role):
    client = match.get("client")
    chat_id = match.get("chat_id")
    if not client or not chat_id:
        return

    user_id = match.get("current_bowler") if role == "bowler" else match.get("current_batter")
    name = match.get("user_cache", {}).get(user_id, role.capitalize())
    mention = f"<a href='tg://user?id={user_id}'>{name}</a>"

    await asyncio.sleep(30)
    if _already_played(match, role):
        return
    try:
        await client.send_message(
            chat_id,
            f"⏳ <b>30 seconds gone.</b>\n{mention} still thinking… This is cricket 😭",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await asyncio.sleep(20)
    if _already_played(match, role):
        return
    try:
        await client.send_message(
            chat_id,
            f"⚠️ <b>10 seconds left!</b>\n{mention}, play NOW or face consequences!",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await asyncio.sleep(10)
    if _already_played(match, role):
        return

    await _handle_solo_timeout(match, role)


def _already_played(match, role):
    if role == "bowler":
        return match.get("bowled", False)
    return match.get("batted", False) or not match.get("bowled", False)


async def _handle_solo_timeout(match, role):
    client = match.get("client")
    chat_id = match.get("chat_id")
    if not client or not chat_id or match.get("phase") != "LIVE":
        return

    if "timeouts" not in match:
        return

    t_info = match["timeouts"][role]
    user_id = match.get("current_bowler") if role == "bowler" else match.get("current_batter")
    if not user_id:
        return

    name = match.get("user_cache", {}).get(user_id, role.capitalize())
    mention = f"<a href='tg://user?id={user_id}'>{name}</a>"
    fails = t_info.get("fails", 0)

    # First warning — chance 1 left
    if fails == 0:
        t_info["fails"] = 1
        match["prompt_dispatched"] = False
        try:
            await client.send_message(
                chat_id,
                (
                    "🚩 <b>TIME WARNING #1</b>\n"
                    f"{mention} is freezing under pressure.\n"
                    "⚠️ <b>1 more chance</b> before penalty kicks in!"
                ),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
        t_info["task"] = asyncio.create_task(start_solo_timer(match, role))
        return

    # Second warning — last chance
    if fails == 1:
        t_info["fails"] = 2
        match["prompt_dispatched"] = False
        try:
            await client.send_message(
                chat_id,
                (
                    "🚨 <b>TIME WARNING #2 — FINAL WARNING</b>\n"
                    f"{mention} is still not playing!\n"
                    "💀 <b>Next timeout = -6 runs penalty & action taken.</b>"
                ),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
        t_info["task"] = asyncio.create_task(start_solo_timer(match, role))
        return

    # Third strike — apply penalty
    t_info["fails"] = 0
    match["total_runs"] = max(0, match.get("total_runs", 0) - 6)

    penalty_msg = (
        "🚫 <b>CLOCK WINS</b>\n\n"
        f"{mention} couldn't beat the timer ⏰\n"
        "🧮 <b>-6 runs</b> penalty applied.\n"
    )

    if role == "batter":
        # Track batter timeout eliminations
        if "timeout_strikes" not in match:
            match["timeout_strikes"] = {}
        match["timeout_strikes"][user_id] = match["timeout_strikes"].get(user_id, 0) + 1
        strike_count = match["timeout_strikes"][user_id]

        if strike_count >= 2:
            from plugins.game.solo import ban_solo_user, ban_remaining_seconds, SOLO_BAN_MINUTES
            ban_solo_user(chat_id, user_id, SOLO_BAN_MINUTES)
            penalty_msg += (
                f"☝️ <b>Batter is OUT</b> — defeated by the clock again! (No bowler credit)\n\n"
                f"🔴 <b>TIMEOUT BAN:</b> {mention} has been eliminated from this match "
                f"and is <b>banned for {SOLO_BAN_MINUTES} minutes</b> from all solo games in this group!"
            )
            try:
                await client.send_message(chat_id, penalty_msg, parse_mode=ParseMode.HTML)
            except Exception:
                pass
            # Remove them from the players list so they can't bat or bowl
            if user_id in match["players"]:
                match["players"].remove(user_id)
            from plugins.game.solo.engine import solo_advance_ball
            await solo_advance_ball(match, "W", credit_bowler=False)
        else:
            penalty_msg += (
                "☝️ <b>Batter is OUT</b> — defeated by the clock. (No bowler credit)\n"
                f"⚠️ <b>Strike {strike_count}/2</b> — one more timeout = 15-min group ban!"
            )
            try:
                await client.send_message(chat_id, penalty_msg, parse_mode=ParseMode.HTML)
            except Exception:
                pass
            from plugins.game.solo.engine import solo_advance_ball
            await solo_advance_ball(match, "W", credit_bowler=False)

    else:
        penalty_msg += "🎳 <b>Bowler skipped.</b> Next bowler steps in."
        match.update({"bowled": False, "batted": False, "prompt_dispatched": False, "last_bowl": None})
        match["balls_in_spell"] = 0
        from plugins.game.solo import get_next_solo_bowler
        from plugins.game.solo.state import send_solo_ball_prompt
        next_b = get_next_solo_bowler(match)
        match["current_bowler"] = next_b
        try:
            await client.send_message(chat_id, penalty_msg, parse_mode=ParseMode.HTML)
        except Exception:
            pass
        await send_solo_ball_prompt(client, match)
