"""
roblox_bridge.py — FastAPI bridge for Roblox HTTPService → Discord Bot.
Now uses shared Postgres database via Supabase.
"""
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
import asyncpg
import os
import datetime

DATABASE_URL = os.getenv("DATABASE_URL")
AUTH_KEY     = os.getenv("ROBLOX_BRIDGE_KEY", "change-this-secret-key")

app = FastAPI(title="Afternight Roblox Bridge", version="1.0.0")

# Global connection pool
pool = None


@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id          SERIAL PRIMARY KEY,
                roblox_user TEXT      NOT NULL,
                faction     TEXT,
                joined_at   TIMESTAMP NOT NULL DEFAULT NOW(),
                left_at     TIMESTAMP,
                duration_s  INTEGER   DEFAULT 0
            );
        """)


@app.on_event("shutdown")
async def shutdown():
    global pool
    if pool:
        await pool.close()


# ── Auth ──────────────────────────────────────────────────────────────────────

def verify_key(x_auth_key: str = Header(...)):
    if x_auth_key != AUTH_KEY:
        raise HTTPException(status_code=403, detail="Invalid auth key")


# ── Models ────────────────────────────────────────────────────────────────────

class SessionStart(BaseModel):
    roblox_user: str
    faction: str

class SessionEnd(BaseModel):
    session_id: int


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.datetime.utcnow().isoformat()}


@app.post("/session/start", dependencies=[Depends(verify_key)])
async def session_start(body: SessionStart):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO sessions (roblox_user, faction) "
            "VALUES ($1, $2) RETURNING id",
            body.roblox_user, body.faction
        )
        return {"session_id": row["id"], "status": "started"}


@app.post("/session/end", dependencies=[Depends(verify_key)])
async def session_end(body: SessionEnd):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE sessions SET left_at=NOW(), "
            "duration_s = EXTRACT(EPOCH FROM (NOW() - joined_at))::INTEGER "
            "WHERE id=$1",
            body.session_id
        )
        row = await conn.fetchrow(
            "SELECT duration_s, roblox_user, faction FROM sessions WHERE id=$1",
            body.session_id
        )

    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id":  body.session_id,
        "roblox_user": row["roblox_user"],
        "faction":     row["faction"],
        "duration_s":  row["duration_s"],
        "status":      "ended"
    }


@app.get("/player/{roblox_username}/stats", dependencies=[Depends(verify_key)])
async def player_stats(roblox_username: str, days: int = 7):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT joined_at, left_at, duration_s FROM sessions "
            "WHERE roblox_user=$1 AND joined_at >= NOW() - ($2 || ' days')::INTERVAL "
            "ORDER BY joined_at DESC",
            roblox_username, str(days)
        )

    total = sum(r["duration_s"] or 0 for r in rows)
    last  = rows[0]["joined_at"] if rows else None

    return {
        "roblox_user":   roblox_username,
        "days":          days,
        "total_seconds": total,
        "session_count": len(rows),
        "last_seen":     str(last) if last else None,
        "sessions":      [dict(r) for r in rows]
    }
