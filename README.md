# Afternight Faction & Staff Bot

A Python Discord bot for **Afternight Factions** featuring slash commands for staff management, faction discipline, and Roblox activity tracking.

---

## Features

| Module | Commands |
|--------|----------|
| **Staff** | `/promote` `/demote` `/fire` |
| **Strikes** | `/strike` `/viewstrike` `/clearstrikes` |
| **Activity** | `/getplayertime` `/getfactiontime` `/logsession` |
| **Roblox Bridge** | FastAPI HTTP server for live Roblox integration |

---

## Quick Start

### 1. Clone & Install

```bash
git clone <your-repo>
cd discord-bot
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and fill in:
#   DISCORD_TOKEN   — your bot token
#   LOG_CHANNEL_ID  — channel ID for action logs
#   ROBLOX_BRIDGE_KEY — shared secret with Roblox
```

### 3. Run the Bot

```bash
python bot.py
```

### 4. (Optional) Run the Roblox Bridge

```bash
uvicorn roblox_bridge:app --host 0.0.0.0 --port 8000
```

---

## Project Structure

```
discord-bot/
├── bot.py              # Entry point, bot setup, cog loader
├── database.py         # SQLite async database layer
├── constants.py        # Role IDs, faction config, helpers
├── roblox_bridge.py    # FastAPI HTTP bridge for Roblox HTTPService
├── requirements.txt
├── .env.example
├── cogs/
│   ├── staff.py        # /promote /demote /fire
│   ├── strikes.py      # /strike /viewstrike /clearstrikes
│   └── activity.py     # /getplayertime /getfactiontime /logsession
└── utils/
    └── roblox.py       # Roblox API helpers (profile + avatar fetch)
```

---

## Command Reference

### Staff Commands

#### `/promote @user`
- Promotes user one rank up in the staff hierarchy
- Cannot exceed Lead Administrator
- Requires caller to be higher rank than target
- Sends DM to promoted user & logs action

#### `/demote @user`
- Demotes user one rank down
- Cannot go below Trial Moderator
- Requires caller to be higher rank than target

#### `/fire @user [reason]`
- Removes **all** staff roles (hierarchy + Staff Team + Administrative Team)
- **Restricted to:** Overseer of Staff, Community Manager, [C] Creators

---

### Strike Commands

#### `/strike @user reason:"text"`
- Adds +1 strike (max 3)
- Sends DM to user with faction & reason
- At 3 strikes, posts a public notice in the channel
- Faction leaders only see their own faction; staff can strike anyone

#### `/viewstrike @user`
```
STRIKES — Username
3/3
1. Inactive for 2 weeks (2025-01-01)
2. Missed event (2025-01-08)
3. No response to leader (2025-01-15)
```

#### `/clearstrikes @user`
- Wipes all strikes for that user
- Useful after removal or after a member reforms

---

### Activity Commands

#### `/getplayertime roblox_username: [days: 7]`
- Shows sessions, total time, last session info
- Fetches live Roblox profile picture & link
- Shows strike count

#### `/getfactiontime [faction] [days: 7]`
- Shows all active members, total time, session count
- **Faction leaders automatically see only their own faction**
- Staff can select any faction

#### `/logsession roblox_username faction duration_minutes`
- Admin-only manual session logger
- Used for testing or manual correction

---

## Staff Hierarchy

| Rank | Role ID |
|------|---------|
| Lead Administrator | 1458302734536278227 |
| Senior Administrator | 1458302729377153208 |
| Administrator | 1458302715212992615 |
| Lead Moderator | 1458302648657645679 |
| Senior Moderator | 1458302642978816104 |
| Moderator | 1458302463953207347 |
| Trial Moderator | 1458302361843007541 |

**Administrative Team role** (1458303682180284681) is automatically granted at Administrator+ and removed below.

---

## Factions

| Faction | Leader Role ID | Color |
|---------|---------------|-------|
| Sanguis Order | 1458305854611914866 | #710000 |
| Eldritch Thorn | 1458305860739661916 | #702794 |
| Silver Venom | 1458305839113830528 | #236a00 |
| Sepharine Coven | 1458305866565554249 | #ecbf66 |

---

## Roblox Bridge (HTTPService)

The bridge runs as a separate FastAPI server. Roblox game scripts POST to it using `HttpService:PostAsync`.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/session/start` | Player joins server |
| POST | `/session/end` | Player leaves server |
| POST | `/session/full` | Log complete session at once |
| GET | `/faction/{name}/stats` | Pull faction stats |

### Example Roblox Script (Lua)

```lua
local HttpService = game:GetService("HttpService")
local BRIDGE_URL = "https://your-bridge.com"
local AUTH_KEY   = "your-secret-key"

local function postSession(path, data)
    local success, result = pcall(function()
        return HttpService:PostAsync(
            BRIDGE_URL .. path,
            HttpService:JSONEncode(data),
            Enum.HttpContentType.ApplicationJson,
            false,
            { ["x-auth-key"] = AUTH_KEY }
        )
    end)
    if success then
        return HttpService:JSONDecode(result)
    end
end

-- When player joins
game.Players.PlayerAdded:Connect(function(player)
    local faction = getFaction(player)  -- your faction detection logic
    local result = postSession("/session/start", {
        roblox_user = player.Name,
        faction     = faction
    })
    player:SetAttribute("SessionId", result.session_id)
end)

-- When player leaves
game.Players.PlayerRemoving:Connect(function(player)
    local sessionId = player:GetAttribute("SessionId")
    if sessionId then
        postSession("/session/end", { session_id = sessionId })
    end
end)
```

---

## Bot Permissions Required

- `Manage Roles` — for promote/demote/fire
- `Send Messages` — for responses
- `Embed Links` — for rich embeds
- `Read Message History` — for context
- `Use Application Commands` — for slash commands

---

## Tech Stack

- Python 3.11+
- discord.py 2.3+
- aiosqlite (SQLite, upgradable to PostgreSQL)
- FastAPI + uvicorn (Roblox bridge)
- aiohttp (Roblox API calls)
