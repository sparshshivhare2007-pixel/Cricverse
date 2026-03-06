import asyncio
from pyrogram import Client, idle
from config import Config
from database.connection import db
from database.migrate import migrate

async def initialize_database():
    await db.connect()
    await migrate()
    print("✅ Database connected & tables ready")

async def start_nexora():
    bot = Client(
        "bot",
        bot_token=Config.BOT_TOKEN,
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        workers=80,
        plugins=dict(root="plugins")
    )

    await bot.start()
    print("🚀 Nexora Cricket Bot is Online!")

    try:
        await initialize_database()
    except Exception as e:
        print(f"❌ Database Initialization Failed: {e}")

    from plugins.game.team import ACTIVE_MATCHES
    for m in ACTIVE_MATCHES.values():
        if not m.get("client"):
            m["client"] = bot

    from plugins.game.team.cleanup import auto_clean_matches
    asyncio.create_task(auto_clean_matches(bot))
    print("🧹 Background Garbage Collector is active!")

    await idle()

    print("🛑 Shutting down...")
    await bot.stop()
    await db.close()

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(start_nexora())
    except KeyboardInterrupt:
        print("👋 Bot stopped manually.")
        
