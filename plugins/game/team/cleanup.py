import asyncio
import time
from pyrogram.enums import ParseMode
from plugins.game.team import ACTIVE_MATCHES
from database.connection import db

async def auto_clean_matches(client):
    """Background task to kill inactive matches and free stuck players"""
    print("🧹 Match Garbage Collector Started...")
    
    while True:
        await asyncio.sleep(60)
        
        now = time.time()
        stale_chats = []

        for chat_id, match in list(ACTIVE_MATCHES.items()):
            if "last_active" not in match:
                match["last_active"] = now
            
            if now - match["last_active"] > 600:
                stale_chats.append(chat_id)

        for chat_id in stale_chats:
            match = ACTIVE_MATCHES.pop(chat_id, None)
            if not match: 
                continue

            game_id = match.get("game_id")
            print(f"☠️ Killed Zombie Match {game_id} in chat {chat_id}")

            try:
                await client.send_message(
                    chat_id,
                    "⚠️ <b>MATCH ABORTED!</b>\n\n"
                    "No activity for 10 minutes. The match has been automatically ended and all players are now free to play elsewhere.",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass

            if game_id:
                try:
                    async with db.pool.acquire() as conn:
                        await conn.execute("UPDATE games SET status='ended' WHERE game_id=$1", game_id)
                except Exception as e:
                    print("❌ GC DB Cleanup Error:", e)


