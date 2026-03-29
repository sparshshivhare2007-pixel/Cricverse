import asyncio
import random
from pyrogram import Client
from pyrogram.enums import ParseMode
from database.connection import db

NUDGE_INTERVAL = 3600 * 6
INACTIVITY_DAYS = 3

NUDGE_MESSAGES = [
    "🏏 <b>The pitch misses you, Captain!</b>\nYou haven't played in a while. Your rank is gathering dust 😤\nHead to your group and smash some runs! 🔥",
    "⚡ <b>Your rivals are grinding!</b>\nWhile you're away, others are climbing the leaderboard 📈\nCome back and reclaim your spot — the crease is calling! 🏟️",
    "🦆 <b>Don't let your legacy fade!</b>\nIt's been {days} days since your last match. Every day idle is a day your rivals get stronger 💀\nBack to the pitch! 🏏",
    "🌟 <b>You've been inactive for {days} days!</b>\nYour Cricket DNA is waiting to evolve — but only if you play 🧬\nCome join a match and show what you're made of! ⚔️",
    "🔥 <b>ALERT: Rank under threat!</b>\n{days} days without a match? Someone might just overtake you soon 👀\nLog in and defend your legacy! 🏆",
]

async def _run_nudge_loop(client: Client):
    await asyncio.sleep(60)
    while True:
        try:
            await _send_nudges(client)
        except Exception as e:
            print(f"Nudge loop error: {e}")
        await asyncio.sleep(NUDGE_INTERVAL)


async def _send_nudges(client: Client):
    try:
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=INACTIVITY_DAYS)
        rows = await db.db["user_stats"].find(
            {
                "last_played_at": {"$lt": cutoff, "$ne": None},
                "matches": {"$gt": 0},
            },
            {"user_id": 1, "first_name": 1, "last_played_at": 1}
        ).limit(50).to_list(None)

        notify_off = set()
        user_docs = await db.db["users"].find(
            {"notify_enabled": False}, {"user_id": 1}
        ).to_list(None)
        for u in user_docs:
            notify_off.add(u["user_id"])

        rows = [r for r in rows if r.get("user_id") not in notify_off]
    except Exception as e:
        print(f"Nudge DB fetch error: {e}")
        return

    sent = 0
    for row in rows:
        from datetime import datetime
        lp = row.get("last_played_at")
        days = (datetime.utcnow() - lp).days if lp else INACTIVITY_DAYS
        uid = row["user_id"]
        name = row.get("first_name") or "Captain"

        msg = random.choice(NUDGE_MESSAGES).format(days=days, name=name)

        try:
            await client.send_message(uid, msg, parse_mode=ParseMode.HTML)
            sent += 1
            await asyncio.sleep(0.5)
        except Exception:
            pass

    if sent:
        print(f"✅ Nudge: Sent {sent} inactivity reminders.")


def start_nudge_task(client: Client):
    asyncio.create_task(_run_nudge_loop(client))
    print("✅ Inactivity nudge task started.")
