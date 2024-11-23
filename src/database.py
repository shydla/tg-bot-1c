import aiosqlite
from typing import List, Optional

class Database:
    def __init__(self, db_path: str = "data/bot.db"):
        self.db_path = db_path

    async def create_tables(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    status TEXT DEFAULT 'pending', -- pending, approved, blocked
                    blocked_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def add_user(self, user_id: int, username: str, full_name: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR IGNORE INTO users 
                   (user_id, username, full_name) VALUES (?, ?, ?)""",
                (user_id, username, full_name)
            )
            await db.commit()

    async def get_user(self, user_id: int) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ) as cursor:
                result = await cursor.fetchone()
                if result:
                    return {
                        "user_id": result[0],
                        "username": result[1],
                        "full_name": result[2],
                        "status": result[3],
                        "blocked_reason": result[4],
                        "created_at": result[5]
                    }
                return None

    async def update_user_status(self, user_id: int, status: str, blocked_reason: str = None) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            if blocked_reason:
                await db.execute(
                    """UPDATE users SET status = ?, blocked_reason = ? 
                       WHERE user_id = ?""",
                    (status, blocked_reason, user_id)
                )
            else:
                await db.execute(
                    "UPDATE users SET status = ? WHERE user_id = ?",
                    (status, user_id)
                )
            await db.commit()

    async def get_users_by_status(self, status: str = None) -> List[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            if status:
                query = "SELECT * FROM users WHERE status = ? ORDER BY created_at DESC"
                params = (status,)
            else:
                query = "SELECT * FROM users ORDER BY created_at DESC"
                params = ()

            async with db.execute(query, params) as cursor:
                results = await cursor.fetchall()
                return [
                    {
                        "user_id": row[0],
                        "username": row[1],
                        "full_name": row[2],
                        "status": row[3],
                        "blocked_reason": row[4],
                        "created_at": row[5]
                    }
                    for row in results
                ]