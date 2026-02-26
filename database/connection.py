import asyncpg
from config import Config

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        if not self.pool:
            print("🗄️ Connecting to PostgreSQL...")
            self.pool = await asyncpg.create_pool(
                dsn=Config.DATABASE_URL,
                min_size=5,
                max_size=30
            )
            print("✅ Database Pool Created.")

db = Database()
