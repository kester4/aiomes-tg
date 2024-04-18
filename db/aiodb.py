from asyncio import run
import json
from typing import Dict
import aiosqlite
import pickle


class UsersDB:
    def __init__(self):
        run(self.start())

    async def run_query(self, method, *args):
        async with aiosqlite.connect('users.db') as db:
            await db.execute(method, parameters=args)
            await db.commit()

    async def start(self):
        await self.run_query('''CREATE TABLE IF NOT EXISTS users (
                            user_id INTEGER PRIMARY KEY,
                            instance BLOB,
                            is_short_schedule BOOLEAN DEFAULT 1,
                            short_schedule TEXT,
                            remember BOOLEAN DEFAULT 0)''')

    async def add_user(self, user_id, obj):
        obj = pickle.dumps(obj)
        await self.run_query("INSERT OR IGNORE INTO users (user_id, instance) VALUES (?, ?)", user_id, obj)

    async def get_users(self) -> Dict:
        async with aiosqlite.connect('users.db') as db:
            cur = await db.execute("SELECT user_id, instance FROM users")
            result = await cur.fetchall()
            return {
                user_id: pickle.loads(obj) for user_id, obj in result
            }

    async def get_user_settings(self, user_id):
        async with aiosqlite.connect('users.db') as db:
            cur = await db.execute("SELECT remember, is_short_schedule FROM users WHERE user_id=?", (user_id,))
            result = await cur.fetchall()
            return result[0]

    async def change_user_settings(self, user_id, setting, new_setting):
        await self.run_query(f"UPDATE users SET {setting}=? WHERE user_id=?", new_setting, user_id)

    async def insert_short_schedule(self, short_schedule, user_id):
        await self.run_query("UPDATE users SET short_schedule=? WHERE user_id=?", json.dumps(short_schedule), user_id)

    async def get_short_schedule(self):
        async with aiosqlite.connect('users.db') as db:
            cur = await db.execute("SELECT user_id, short_schedule FROM users")
            data = await cur.fetchall()
            result = {}
            for user_id, obj in data:
                if obj is None:
                    continue
                result[user_id] = json.loads(obj)
            return result

    async def delete_user(self, user_id):
        await self.run_query("DELETE FROM users WHERE user_id=?", user_id)

    async def bullshit_cleanup(self):
        await self.run_query("DELETE FROM users WHERE remember=0")
