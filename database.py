import os
import aiosqlite
import datetime
from typing import Optional, List, Dict

DB_PATH = os.getenv("DB_PATH", "/app/data/afternight.db")

class Database:
    def __init__(self):
        self.path = DB_PATH

    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS strikes (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     TEXT    NOT NULL,
                    guild_id    TEXT    NOT NULL,
                    faction     TEXT,
                    reason      TEXT    NOT NULL,
                    struck_by   TEXT    NOT NULL,
                    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    roblox_user TEXT    NOT NULL,
                    faction     TEXT,
                    joined_at   TEXT    NOT NULL,
                    left_at     TEXT,
                    duration_s  INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS staff_log (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    action      TEXT    NOT NULL,
                    target_id   TEXT    NOT NULL,
                    actor_id    TEXT    NOT NULL,
                    guild_id    TEXT    NOT NULL,
                    note        TEXT,
                    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS blacklist (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id         TEXT    NOT NULL,
                    guild_id        TEXT    NOT NULL,
                    faction         TEXT    NOT NULL,
                    reason          TEXT    NOT NULL,
                    blacklisted_by  TEXT    NOT NULL,
                    roblox_username TEXT,
                    blacklist_embed_msg_id TEXT,
                    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
                );
            """)
            await db.commit()

    # ── Strikes ───────────────────────────────────────────────────────────────

    async def add_strike(self, user_id: str, guild_id: str, faction: str,
                         reason: str, struck_by: str) -> int:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO strikes (user_id, guild_id, faction, reason, struck_by) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, guild_id, faction, reason, struck_by)
            )
            await db.commit()
        return await self.get_strike_count(user_id, guild_id)

    async def get_strike_count(self, user_id: str, guild_id: str) -> int:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM strikes WHERE user_id=? AND guild_id=?",
                (user_id, guild_id)
            ) as cur:
                row = await cur.fetchone()
                return row[0] if row else 0

    async def get_strikes(self, user_id: str, guild_id: str) -> List[Dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT reason, created_at, struck_by FROM strikes "
                "WHERE user_id=? AND guild_id=? ORDER BY created_at ASC",
                (user_id, guild_id)
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def clear_strikes(self, user_id: str, guild_id: str) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "DELETE FROM strikes WHERE user_id=? AND guild_id=?",
                (user_id, guild_id)
            )
            await db.commit()
            return cur.rowcount

    # ── Sessions ──────────────────────────────────────────────────────────────

    async def start_session(self, roblox_user: str, faction: str) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "INSERT INTO sessions (roblox_user, faction, joined_at) VALUES (?, ?, datetime('now'))",
                (roblox_user, faction)
            )
            await db.commit()
            return cur.lastrowid

    async def get_player_sessions(self, roblox_user: str, days: int = 7) -> List[Dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM sessions WHERE roblox_user=? "
                "AND joined_at >= datetime('now', ? || ' days') ORDER BY joined_at DESC",
                (roblox_user, f"-{days}")
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def get_faction_sessions(self, faction: str, days: int = 7) -> List[Dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT roblox_user, SUM(duration_s) as total_s, MAX(joined_at) as last_seen, "
                "COUNT(*) as session_count FROM sessions "
                "WHERE faction=? AND joined_at >= datetime('now', ? || ' days') "
                "GROUP BY roblox_user ORDER BY total_s DESC",
                (faction, f"-{days}")
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    # ── Staff Log ─────────────────────────────────────────────────────────────

    async def log_staff_action(self, action: str, target_id: str, actor_id: str,
                                guild_id: str, note: str = ""):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO staff_log (action, target_id, actor_id, guild_id, note) "
                "VALUES (?, ?, ?, ?, ?)",
                (action, target_id, actor_id, guild_id, note)
            )
            await db.commit()

    # ── Blacklist ─────────────────────────────────────────────────────────────

    async def add_blacklist(self, user_id: str, guild_id: str, faction: str,
                             reason: str, blacklisted_by: str,
                             roblox_username: str = None) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "INSERT INTO blacklist (user_id, guild_id, faction, reason, "
                "blacklisted_by, roblox_username) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, guild_id, faction, reason, blacklisted_by, roblox_username)
            )
            await db.commit()
            return cur.lastrowid

    async def set_blacklist_embed_msg(self, blacklist_id: int, msg_id: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE blacklist SET blacklist_embed_msg_id=? WHERE id=?",
                (msg_id, blacklist_id)
            )
            await db.commit()

    async def is_blacklisted(self, user_id: str, guild_id: str) -> Optional[Dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM blacklist WHERE user_id=? AND guild_id=?",
                (user_id, guild_id)
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def remove_blacklist(self, user_id: str, guild_id: str) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "DELETE FROM blacklist WHERE user_id=? AND guild_id=?",
                (user_id, guild_id)
            )
            await db.commit()
            return cur.rowcount > 0

    async def get_all_blacklisted(self, guild_id: str) -> List[Dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM blacklist WHERE guild_id=? ORDER BY created_at DESC",
                (guild_id,)
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]
