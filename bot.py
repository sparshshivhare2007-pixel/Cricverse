import asyncio
from pyrogram import Client, idle
from config import Config
from database.connection import db
import asyncio
from database.migrate import migrate


async def start_nexora():
    # 1. Initialize Database inside the running loop
    # This fixes: RuntimeError: no running event loop
    try:
        await initialize_database()
    except Exception as e:
        print(f"❌ Database Initialization Failed: {e}")
        return

    # 2. Initialize the Bot
    bot = Client(
        "bot",
        bot_token=Config.BOT_TOKEN,
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        workers=80,
        plugins=dict(root="plugins")
    )

    # 3. Start the Client
    await bot.start()
    print("🚀 Nexora Cricket Bot is Online!")
    # 🔌 GLOBAL CLIENT FALLBACK (ENGINE SAFETY)
    from plugins.game.team.init import ACTIVE_MATCHES

    for m in ACTIVE_MATCHES.values():
        if not m.get("client"):
            m["client"] = bot


    # 4. Keep it running
    await idle()

    # 5. Graceful Shutdown
    await bot.stop()
    await db.close()

if __name__ == "__main__":
    # This creates the event loop and starts the async function
    try:
        asyncio.run(start_nexora())
    except KeyboardInterrupt:
        print("👋 Bot stopped manually.")
