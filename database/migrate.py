from database.connection import db

async def migrate():
    async with db.pool.acquire() as conn:
        await conn.execute("CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, name TEXT, coins BIGINT DEFAULT 1000, games_played INT DEFAULT 0, notify_enabled BOOLEAN DEFAULT TRUE, created_at TIMESTAMP DEFAULT NOW());")
        await conn.execute("CREATE TABLE IF NOT EXISTS bot_mods (user_id BIGINT PRIMARY KEY, added_by BIGINT, added_at TIMESTAMP DEFAULT NOW());")
        await conn.execute("CREATE TABLE IF NOT EXISTS user_bans (user_id BIGINT PRIMARY KEY, first_name TEXT, reason TEXT, banned_by BIGINT, banned_at TIMESTAMP DEFAULT NOW());")
        await conn.execute("CREATE TABLE IF NOT EXISTS group_bans (chat_id BIGINT PRIMARY KEY, title TEXT, reason TEXT, banned_by BIGINT, banned_at TIMESTAMP DEFAULT NOW());")
        await conn.execute("CREATE TABLE IF NOT EXISTS achievement_meta (key TEXT PRIMARY KEY, value INT NOT NULL);")
        await conn.execute("INSERT INTO achievement_meta (key, value) VALUES ('generation_count', 0) ON CONFLICT DO NOTHING;")
        await conn.execute("CREATE TABLE IF NOT EXISTS mods (user_id BIGINT PRIMARY KEY, tier INT NOT NULL DEFAULT 1, added_by BIGINT, added_at TIMESTAMP DEFAULT NOW());")
        
        await conn.execute("CREATE TABLE IF NOT EXISTS games (game_id UUID PRIMARY KEY, chat_id BIGINT, title TEXT, mode TEXT, host_id BIGINT, phase TEXT DEFAULT 'waiting', status TEXT, winner TEXT, team_a_runs INT DEFAULT 0, team_b_runs INT DEFAULT 0, team_a_wickets INT DEFAULT 0, team_b_wickets INT DEFAULT 0, team_a_balls INT DEFAULT 0, team_b_balls INT DEFAULT 0, team_a_penalty INT DEFAULT 0, team_b_penalty INT DEFAULT 0, target INT, innings INT DEFAULT 1, motm BIGINT, toss_winner BIGINT, batting_team CHAR(1), bowling_team CHAR(1), overs INT DEFAULT 0, created_at TIMESTAMP DEFAULT NOW());")
        await conn.execute("CREATE TABLE IF NOT EXISTS game_players (id SERIAL PRIMARY KEY, game_id UUID REFERENCES games(game_id) ON DELETE CASCADE, user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE, team CHAR(1), is_out BOOLEAN DEFAULT FALSE, is_captain BOOLEAN DEFAULT FALSE, role TEXT, joined_at TIMESTAMP DEFAULT NOW());")
        await conn.execute("CREATE TABLE IF NOT EXISTS team_shifts (game_id UUID REFERENCES games(game_id) ON DELETE CASCADE, user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE, shifts INT DEFAULT 0, PRIMARY KEY (game_id, user_id));")
        await conn.execute("CREATE TABLE IF NOT EXISTS user_stats (user_id BIGINT PRIMARY KEY, username TEXT, first_name TEXT, matches INT DEFAULT 0, wins INT DEFAULT 0, losses INT DEFAULT 0, runs INT DEFAULT 0, balls_faced INT DEFAULT 0, highest_score INT DEFAULT 0, fours INT DEFAULT 0, sixes INT DEFAULT 0, centuries INT DEFAULT 0, fifties INT DEFAULT 0, ducks INT DEFAULT 0, wickets INT DEFAULT 0, balls_bowled INT DEFAULT 0, runs_conceded INT DEFAULT 0, hat_tricks INT DEFAULT 0, moms INT DEFAULT 0, best_partnership INT DEFAULT 0, penalties_received INT DEFAULT 0, created_at TIMESTAMP DEFAULT NOW());")
        
        await conn.execute("CREATE TABLE IF NOT EXISTS achievements (id SERIAL PRIMARY KEY, code TEXT UNIQUE, title TEXT, description TEXT, condition JSONB, rarity TEXT, is_dynamic BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT NOW());")
        await conn.execute("CREATE TABLE IF NOT EXISTS user_achievements (user_id BIGINT, achievement_id INT REFERENCES achievements(id) ON DELETE CASCADE, unlocked_at TIMESTAMP DEFAULT NOW(), PRIMARY KEY (user_id, achievement_id));")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_user_achievements_user ON user_achievements(user_id);")

        print("🏆 Achievements tables ready.")

        await conn.execute("ALTER TABLE games ADD COLUMN IF NOT EXISTS title TEXT;")
        await conn.execute("ALTER TABLE games ADD COLUMN IF NOT EXISTS target INT;")
        await conn.execute("ALTER TABLE games ADD COLUMN IF NOT EXISTS innings INT DEFAULT 1;")
        await conn.execute("ALTER TABLE games ADD COLUMN IF NOT EXISTS winner TEXT;")
        await conn.execute("ALTER TABLE games ADD COLUMN IF NOT EXISTS team_a_penalty INT DEFAULT 0;")
        await conn.execute("ALTER TABLE games ADD COLUMN IF NOT EXISTS team_b_penalty INT DEFAULT 0;")
        await conn.execute("ALTER TABLE achievements ADD COLUMN IF NOT EXISTS difficulty INT DEFAULT 0;")

        stats_columns = [
            ("matches", "INT DEFAULT 0"),
            ("wins", "INT DEFAULT 0"),
            ("losses", "INT DEFAULT 0"),
            ("moms", "INT DEFAULT 0"),
            ("highest_score", "INT DEFAULT 0"),
            ("best_partnership", "INT DEFAULT 0"),
            ("centuries", "INT DEFAULT 0"),
            ("fifties", "INT DEFAULT 0"),
            ("ducks", "INT DEFAULT 0"),
            ("fours", "INT DEFAULT 0"),
            ("sixes", "INT DEFAULT 0"),
            ("balls_faced", "INT DEFAULT 0"),
            ("balls_bowled", "INT DEFAULT 0"),
            ("runs_conceded", "INT DEFAULT 0"),
            ("penalties_received", "INT DEFAULT 0")
        ]

        for col_name, col_type in stats_columns:
            await conn.execute(f"ALTER TABLE user_stats ADD COLUMN IF NOT EXISTS {col_name} {col_type};")

        await conn.execute("CREATE INDEX IF NOT EXISTS idx_games_chat_status ON games(chat_id, status);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_players_user ON game_players(user_id);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_players_game ON game_players(game_id);")

        print("✅ Database migration complete. All tables and career milestones are ready.")
        
