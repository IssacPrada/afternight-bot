"""
constants.py — Role IDs, faction config, and shared helpers.
"""
import discord
from typing import Optional

# ─── Staff Hierarchy (ordered lowest → highest) ───────────────────────────────
STAFF_HIERARCHY: list[int] = [
    1458302361843007541,   # Trial Moderator
    1458302463953207347,   # Moderator
    1458302642978816104,   # Senior Moderator
    1458302648657645679,   # Lead Moderator
    1458302715212992615,   # Administrator
    1458302729377153208,   # Senior Administrator
    1458302734536278227,   # Lead Administrator
]

STAFF_HIERARCHY_NAMES: dict[int, str] = {
    1458302361843007541: "Trial Moderator",
    1458302463953207347: "Moderator",
    1458302642978816104: "Senior Moderator",
    1458302648657645679: "Lead Moderator",
    1458302715212992615: "Administrator",
    1458302729377153208: "Senior Administrator",
    1458302734536278227: "Lead Administrator",
}

# ─── Staff Team Roles ─────────────────────────────────────────────────────────
ROLE_STAFF_TEAM        = 1458304077136920668
ROLE_ADMIN_TEAM        = 1458303682180284681

# ─── Privileged Roles (can use /fire, /promote, /demote) ─────────────────────
FIRE_ALLOWED_ROLES: set[int] = {
    1458302854887510210,   # Overseer of Staff
    1458302857764802683,   # Community Manager
    1387649282139754587,   # [C] Creators
}

# ─── Faction Leader Roles ─────────────────────────────────────────────────────
FACTION_LEADERS: dict[int, str] = {
    1458305854611914866: "Sanguis Order",
    1458305860739661916: "Eldritch Thorn",
    1458305839113830528: "Silver Venom",
    1458305866565554249: "Sepharine Coven",
}

# ─── Faction Member Roles ─────────────────────────────────────────────────────
FACTION_MEMBERS: dict[int, str] = {
    1458305856297893932: "Sanguis Order",    # Sanguis Order Vampire
    1458305862748868619: "Eldritch Thorn",   # Eldritch Thorn Witch
    1458305842372673639: "Silver Venom",     # Silver Venom Werewolf
    1458305868495065262: "Sepharine Coven",  # Sepharine Werewitch
}

# ─── Roblox Group Rank IDs per faction ───────────────────────────────────────
FACTION_ROBLOX_RANKS: dict[str, int] = {
    "Sanguis Order":   10,
    "Eldritch Thorn":  20,
    "Silver Venom":    30,
    "Sepharine Coven": 40,
}

# ─── Faction Colors ───────────────────────────────────────────────────────────
FACTION_COLORS: dict[str, int] = {
    "Sanguis Order":   0x710000,
    "Eldritch Thorn":  0x702794,
    "Silver Venom":    0x236A00,
    "Sepharine Coven": 0xECBF66,
}

# ─── Strike thresholds ────────────────────────────────────────────────────────
STRIKE_STATUS = {
    0: ("✅ Normal",        discord.Color.green()),
    1: ("⚠️ Warning",       discord.Color.yellow()),
    2: ("🔴 At Risk",       discord.Color.orange()),
    3: ("💀 Final Warning", discord.Color.red()),
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_member_rank_index(member: discord.Member) -> int:
    """Return the index of the member's highest staff rank, or -1 if none."""
    member_role_ids = {r.id for r in member.roles}
    best = -1
    for i, role_id in enumerate(STAFF_HIERARCHY):
        if role_id in member_role_ids:
            best = i
    return best

def get_member_faction(member: discord.Member) -> Optional[str]:
    """
    Return faction name if member holds a faction leader OR member role.
    Checks member roles first, then leader roles.
    """
    member_role_ids = {r.id for r in member.roles}
    # Check member roles
    for role_id, faction in FACTION_MEMBERS.items():
        if role_id in member_role_ids:
            return faction
    # Check leader roles
    for role_id, faction in FACTION_LEADERS.items():
        if role_id in member_role_ids:
            return faction
    return None

def get_leader_faction(member: discord.Member) -> Optional[str]:
    """Return faction name only if the member holds a LEADER role."""
    member_role_ids = {r.id for r in member.roles}
    for role_id, faction in FACTION_LEADERS.items():
        if role_id in member_role_ids:
            return faction
    return None

def has_fire_permission(member: discord.Member) -> bool:
    member_role_ids = {r.id for r in member.roles}
    return bool(member_role_ids & FIRE_ALLOWED_ROLES)

def is_staff(member: discord.Member) -> bool:
    return get_member_rank_index(member) >= 0

def fmt_duration(seconds: int) -> str:
    """Format seconds into a human-readable string."""
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m {s}s"