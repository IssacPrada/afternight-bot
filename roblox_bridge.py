"""
roblox_bridge.py — FastAPI bridge for Roblox HTTPService → Discord Bot.
Deploy this separately from the bot (Railway, Render, VPS etc.)

Roblox Lua example:
    local HttpService = game:GetService("HttpService")
    local URL = "https://your-bridge.com"
    local KEY = "your-secret-key"

    -- On player join
    game.Players.PlayerAdded:Connect(function(player)
        local faction = getFaction(player) -- your own logic
        local res = HttpService:PostAsync(
            URL .. "/session/start",
            HttpService:JSONEncode({ roblox_user = player.Name, faction = faction }),
            Enum.HttpContentType.ApplicationJson,
            false,
            { ["x-auth-key"] = KEY }
        )
        local data = HttpService:JSONDecode(res)
        player:SetAttribute("SessionId", data.session_id)
    end)

    -- On player leave
    game.Players.PlayerRemoving:Connect(function(player)
        local sid = player:GetAttribute("SessionId")
        if sid then
            HttpService:PostAsync(
                URL .. "/session/end",
                HttpService:JSONEncode({ session_id = sid }),
                Enum.HttpContentType.ApplicationJson,
                false,
                { ["x-auth-key"] = KEY }
            )
        end
    end)
"""
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
import aiosqlite
import os
import datetime

app = FastAPI(title="Afternight Roblox Bridge", version="1.0.0")

DB_PATH  = os.getenv("DB_PATH", "data/afternight.db")
AUTH_KEY = os.getenv("ROBLOX_BRIDGE_KEY", "change-this-secret-key")


# ─── Auth ──────────────────────────────────────────────────────────────────────

def verify_key(x_auth_key: str = Header(...)):
    if x_auth_key != AUTH_KEY:
        raise HTTPException(status_code=403, detail="Invalid auth key")


# ─── Models ────────────────────────────────────────────────────────────────────

class SessionStart(BaseModel):
    roblox_user: str
    faction: str

class SessionEnd(BaseModel):
    session_id: int


# ─── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.datetime.utcnow().isoformat()}


@app.post("/session/start", dependencies=[Depends(verify_key)])
async def session_start(body: SessionStart):
    """Called when a player joins the Roblox game."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO sessions (roblox_user, faction, joined_at) "
            "VALUES (?, ?, datetime('now'))",
            (body.roblox_user, body.faction)
        )
        await db.commit()
        return {"session_id": cur.lastrowid, "status": "started"}


@app.post("/session/end", dependencies=[Depends(verify_key)])
async def session_end(body: SessionEnd):
    """Called when a player leaves the Roblox game."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sessions "
            "SET left_at = datetime('now'), "
            "duration_s = CAST((julianday('now') - julianday(joined_at)) * 86400 AS INTEGER) "
            "WHERE id = ?",
            (body.session_id,)
        )
        await db.commit()

        async with db.execute(
            "SELECT duration_s, roblox_user, faction FROM sessions WHERE id = ?",
            (body.session_id,)
        ) as cur:
            row = await cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": body.session_id,
        "roblox_user": row[1],
        "faction": row[2],
        "duration_s": row[0],
        "status": "ended"
    }


@app.get("/player/{roblox_username}/stats", dependencies=[Depends(verify_key)])
async def player_stats(roblox_username: str, days: int = 7):
    """Pull a single player's stats."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT joined_at, left_at, duration_s FROM sessions "
            "WHERE roblox_user = ? AND joined_at >= datetime('now', ? || ' days') "
            "ORDER BY joined_at DESC",
            (roblox_username, f"-{days}")
        ) as cur:
            rows = await cur.fetchall()

    total = sum(r["duration_s"] or 0 for r in rows)
    last = rows[0]["joined_at"] if rows else None

    return {
        "roblox_user": roblox_username,
        "days": days,
        "total_seconds": total,
        "session_count": len(rows),
        "last_seen": last,
        "sessions": [dict(r) for r in rows]
    }


@app.get("/faction/{faction}/stats", dependencies=[Depends(verify_key)])
async def faction_stats(faction: str, days: int = 7):
    """Pull full faction stats."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT roblox_user, SUM(duration_s) as total_s, "
            "MAX(joined_at) as last_seen, COUNT(*) as session_count "
            "FROM sessions "
            "WHERE faction = ? AND joined_at >= datetime('now', ? || ' days') "
            "GROUP BY roblox_user ORDER BY total_s DESC",
            (faction, f"-{days}")
        ) as cur:
            rows = await cur.fetchall()

    return {
        "faction": faction,
        "days": days,
        "members": [dict(r) for r in rows]
    }