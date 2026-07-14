import os
import datetime
from typing import Optional, List, Dict
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL")

class Database:
    def __init__(self):
        self.pool = None

    async def init(self):
        try:
            self.pool = await asyncpg.create_pool(
                DATABASE_URL,
                ssl="require",
                statement_cache_size=0
            )
            print("✅ Database connected successfully")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise

        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS strikes (
                    id          SERIAL PRIMARY KEY,
                    user_id     TEXT      NOT NULL,
                    guild_id    TEXT      NOT NULL,
                    faction     TEXT,
                    reason      TEXT      NOT NULL,
                    struck_by   TEXT      NOT NULL,
                    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id          SERIAL PRIMARY KEY,
                    roblox_user TEXT      NOT NULL,
                    faction     TEXT,
                    joined_at   TIMESTAMP NOT NULL DEFAULT NOW(),
                    left_at     TIMESTAMP,
                    duration_s  INTEGER   DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS staff_log (
                    id          SERIAL PRIMARY KEY,
                    action      TEXT      NOT NULL,
                    target_id   TEXT      NOT NULL,
                    actor_id    TEXT      NOT NULL,
                    guild_id    TEXT      NOT NULL,
                    note        TEXT,
                    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS blacklist (
                    id                     SERIAL PRIMARY KEY,
                    user_id                TEXT      NOT NULL,
                    guild_id               TEXT      NOT NULL,
                    faction                TEXT      NOT NULL,
                    reason                 TEXT      NOT NULL,
                    blacklisted_by         TEXT      NOT NULL,
                    roblox_username        TEXT,
                    blacklist_embed_msg_id TEXT,
                    created_at             TIMESTAMP NOT NULL DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS warns (
                    id          SERIAL PRIMARY KEY,
                    user_id     TEXT      NOT NULL,
                    guild_id    TEXT      NOT NULL,
                    reason      TEXT      NOT NULL,
                    evidence    TEXT,
                    warned_by   TEXT      NOT NULL,
                    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS temp_bans (
                    id          SERIAL PRIMARY KEY,
                    user_id     TEXT      NOT NULL,
                    guild_id    TEXT      NOT NULL,
                    unban_date  TEXT      NOT NULL,
                    reason      TEXT      NOT NULL,
                    banned_by   TEXT      NOT NULL,
                    expired     BOOLEAN   NOT NULL DEFAULT FALSE,
                    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)

    # ── Strikes ───────────────────────────────────────────────────────────────

    async def add_strike(self, user_id: str, guild_id: str, faction: str,
                         reason: str, struck_by: str) -> int:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO strikes (user_id, guild_id, faction, reason, struck_by) "
                "VALUES ($1, $2, $3, $4, $5)",
                user_id, guild_id, faction, reason, struck_by
            )
        return await self.get_strike_count(user_id, guild_id)

    async def get_strike_count(self, user_id: str, guild_id: str) -> int:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT COUNT(*) FROM strikes WHERE user_id=$1 AND guild_id=$2",
                user_id, guild_id
            )
            return row["count"] if row else 0

    async def get_strikes(self, user_id: str, guild_id: str) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT reason, created_at, struck_by FROM strikes "
                "WHERE user_id=$1 AND guild_id=$2 ORDER BY created_at ASC",
                user_id, guild_id
            )
            return [dict(r) for r in rows]

    async def clear_strikes(self, user_id: str, guild_id: str) -> int:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM strikes WHERE user_id=$1 AND guild_id=$2",
                user_id, guild_id
            )
            return int(result.split()[-1])

    # ── Sessions ──────────────────────────────────────────────────────────────

    async def get_player_sessions(self, roblox_user: str, days: int = 7) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM sessions WHERE roblox_user=$1 "
                "AND joined_at >= NOW() - ($2 || ' days')::INTERVAL "
                "ORDER BY joined_at DESC",
                roblox_user, str(days)
            )
            return [dict(r) for r in rows]

    async def get_faction_sessions(self, faction: str, days: int = 7) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT roblox_user, SUM(duration_s) as total_s, "
                "MAX(joined_at) as last_seen, COUNT(*) as session_count "
                "FROM sessions WHERE faction=$1 "
                "AND joined_at >= NOW() - ($2 || ' days')::INTERVAL "
                "GROUP BY roblox_user ORDER BY total_s DESC",
                faction, str(days)
            )
            return [dict(r) for r in rows]

    # ── Staff Log ─────────────────────────────────────────────────────────────

    async def log_staff_action(self, action: str, target_id: str, actor_id: str,
                                guild_id: str, note: str = ""):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO staff_log (action, target_id, actor_id, guild_id, note) "
                "VALUES ($1, $2, $3, $4, $5)",
                action, target_id, actor_id, guild_id, note
            )

    # ── Blacklist ─────────────────────────────────────────────────────────────

    async def add_blacklist(self, user_id: str, guild_id: str, faction: str,
                             reason: str, blacklisted_by: str,
                             roblox_username: str = None) -> int:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO blacklist (user_id, guild_id, faction, reason, "
                "blacklisted_by, roblox_username) VALUES ($1, $2, $3, $4, $5, $6) "
                "RETURNING id",
                user_id, guild_id, faction, reason, blacklisted_by, roblox_username
            )
            return row["id"]

    async def set_blacklist_embed_msg(self, blacklist_id: int, msg_id: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE blacklist SET blacklist_embed_msg_id=$1 WHERE id=$2",
                msg_id, blacklist_id
            )

    async def is_blacklisted(self, user_id: str, guild_id: str) -> Optional[Dict]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM blacklist WHERE user_id=$1 AND guild_id=$2",
                user_id, guild_id
            )
            return dict(row) if row else None

    async def remove_blacklist(self, user_id: str, guild_id: str) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM blacklist WHERE user_id=$1 AND guild_id=$2",
                user_id, guild_id
            )
            return int(result.split()[-1]) > 0

    async def get_all_blacklisted(self, guild_id: str) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM blacklist WHERE guild_id=$1 ORDER BY created_at DESC",
                guild_id
            )
            return [dict(r) for r in rows]

    # ── Warns ─────────────────────────────────────────────────────────────────

    async def add_warn(self, user_id: str, guild_id: str, reason: str,
                       evidence: str, warned_by: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO warns (user_id, guild_id, reason, evidence, warned_by) "
                "VALUES ($1, $2, $3, $4, $5)",
                user_id, guild_id, reason, evidence, warned_by
            )

    async def get_warns(self, user_id: str, guild_id: str) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT reason, evidence, warned_by, created_at FROM warns "
                "WHERE user_id=$1 AND guild_id=$2 ORDER BY created_at ASC",
                user_id, guild_id
            )
            return [dict(r) for r in rows]

    async def clear_warns(self, user_id: str, guild_id: str) -> int:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM warns WHERE user_id=$1 AND guild_id=$2",
                user_id, guild_id
            )
            return int(result.split()[-1])

    # ── Temp Bans ─────────────────────────────────────────────────────────────

    async def add_temp_ban(self, user_id: str, guild_id: str,
                            unban_date: str, reason: str, banned_by: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO temp_bans (user_id, guild_id, unban_date, reason, banned_by) "
                "VALUES ($1, $2, $3, $4, $5)",
                user_id, guild_id, unban_date, reason, banned_by
            )

    async def get_expired_temp_bans(self) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM temp_bans WHERE expired=FALSE"
            )
            return [dict(r) for r in rows]

    async def mark_temp_ban_expired(self, ban_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE temp_bans SET expired=TRUE WHERE id=$1", ban_id
            )
