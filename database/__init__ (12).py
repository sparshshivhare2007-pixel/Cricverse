import asyncio
from database.connection import db
from database.migrate import migrate

async def initialize_database():
    """Call this inside your main bot startup function."""
    await db.connect()
    await migrate()
    print("✅ Database connected & tables ready")