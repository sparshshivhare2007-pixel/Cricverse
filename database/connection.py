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
                min_size=10,
                max_size=85 
            )
            print("✅ Database Pool Created (PRO MODE: 85 Max Connections).")

db = Database()
