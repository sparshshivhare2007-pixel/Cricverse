import asyncio
from pyrogram.enums import ParseMode
from database.games import update_team_penalty, increment_user_penalty_count

TIME_LIMIT = 60  # fallback default (seconds)


def mention_user(match, user_id, fallback="Player"):
    name = match.get("user_cache", {}).get(user_id, fallback)
    return f"<a href='tg://user?id={user_id}'>{name}</a>"


async def _get_timeout(match) -> int:
    """Return the configured ball timeout for this match's group, in seconds."""
    chat_id = match.get("chat_id")
    if not chat_id:
        return TIME_LIMIT
    try:
        from database.group_settings import get_setting
        val = await get_setting(chat_id, "ball_timeout")
        if isinstance(val, int) and val > 0:
            return val
    except Exception:
        pass
    return TIME_LIMIT


async def start_timer(match, role):
    client  = match["client"]
    chat_id = match["chat_id"]

    if "timeouts" not in match:
        match["timeouts"] = {
            "bowler": {"fails": 0, "task": None},
            "batter": {"fails": 0, "task": None},
        }

    user_id = match.get("current_bowler") if role == "bowler" else match.get("striker")
    mention = mention_user(match, user_id, role.capitalize())

    total   = await _get_timeout(match)
    stage1  = int(total * 0.50)          # first nudge
    stage2  = int(total * 0.33)          # second nudge
    stage3  = total - stage1 - stage2    # final → timeout

    # Friendly time display for warnings
    def _fmt(s):
        if s >= 60:
            m, sec = divmod(s, 60)
            return f"{m}m{sec:02d}s" if sec else f"{m}m"
        return f"{s}s"

    await asyncio.sleep(stage1)

    if role == "bowler" and match.get("bowled"):         return
    if role == "batter" and (match.get("batted") or not match.get("bowled")): return

    remaining = stage2 + stage3
    await client.send_message(
        chat_id,
        f"⏳ <b>{_fmt(stage1)} gone.</b>\n"
        f"{mention} still thinking like it's chess.\n"
        f"This is cricket 😭  (<b>{_fmt(remaining)}</b> left)",
        parse_mode=ParseMode.HTML
    )

    await asyncio.sleep(stage2)

    if role == "bowler" and match.get("bowled"):         return
    if role == "batter" and (match.get("batted") or not match.get("bowled")): return

    await client.send_message(
        chat_id,
        f"⚠️ <b>{_fmt(stage3)} remaining!</b>\n"
        f"{mention}, play now or let the clock decide.",
        parse_mode=ParseMode.HTML
    )

    await asyncio.sleep(stage3)

    if role == "bowler" and match.get("bowled"):         return
    if role == "batter" and (match.get("batted") or not match.get("bowled")): return

    await handle_timeout(match, role)


async def handle_timeout(match, role):
    client  = match["client"]
    chat_id = match["chat_id"]

    if "timeouts" not in match or match.get("phase") != "LIVE":
        return

    t_info   = match["timeouts"][role]
    team_key = match.get("bowling_team") if role == "bowler" else match.get("batting_team")
    user_id  = match.get("current_bowler") if role == "bowler" else match.get("striker")

    if not team_key or not user_id:
        return

    mention = mention_user(match, user_id, role.capitalize())

    if t_info.get("fails", 0) == 0:
        t_info["fails"] = 1
        match["prompt_dispatched"] = False

        await client.send_message(
            chat_id,
            (
                "🚩 <b>TIME WARNING</b>\n"
                f"{mention} freezing under pressure.\n"
                "The clock doesn't wait for anyone ⏳\n"
                "⚠️ <b>Next delay:</b> -6 runs & instant removal."
            ),
            parse_mode=ParseMode.HTML
        )

        t_info["task"] = asyncio.create_task(start_timer(match, role))
        return

    t_info["fails"] = 0

    if team_key in match.get("teams", {}):
        match["teams"][team_key]["runs"] -= 6
        if match.get("innings") == 2 and role == "bowler":
            if "target" in match:
                match["target"] -= 6

    try:
        await update_team_penalty(match["game_id"], team_key, 6)
        await increment_user_penalty_count(user_id)
    except Exception as e:
        print(f"Penalty DB Error: {e}")

    penalty_msg = (
        "🚫 <b>CLOCK WINS</b>\n\n"
        f"{mention} couldn't beat the timer ⏰\n"
        f"🧮 <b>Team {team_key}</b> punished with <b>-6 runs</b>.\n"
    )

    if role == "batter":
        penalty_msg += "☝️ <b>Batter is OUT</b> — defeated by the clock.\n"
        await client.send_message(chat_id, penalty_msg, parse_mode=ParseMode.HTML)
        from plugins.game.team.over_engine import advance_ball
        await advance_ball(match, "W")

    else:
        match["last_over_bowler"] = user_id
        match["current_bowler"]   = None
        penalty_msg += (
            "🎳 <b>Bowler removed from the attack.</b>\n"
            "🧢 <b>Bowling Captain</b>, pick a new bowler:\n"
            "<code>/bowling &lt;number&gt;</code>"
        )
        match.update({
            "prompt_dispatched": False,
            "bowled": False,
            "batted": False,
            "last_bowl": None
        })
        await client.send_message(chat_id, penalty_msg, parse_mode=ParseMode.HTML)

    for r in ("bowler", "batter"):
        task = match["timeouts"].get(r, {}).get("task")
        if task:
            try:
                task.cancel()
            except Exception:
                pass
