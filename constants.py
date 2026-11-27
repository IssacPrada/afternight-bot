"""
constants.py — Role IDs, faction config, and shared helpers.
"""
import discord
from typing import Optional

# ─── Staff Hierarchy (ordered lowest → highest) ───────────────────────────────
STAFF_HIERARCHY: list[int] = [
    1575226667537010718,   # [TM] Trial Moderator
    1575226626378039426,   # [MOD] Moderator
    1575226571076411515,   # [JM] Junior Moderator
    1575226502490882340,   # [SM] Senior Moderator
    1575226359939211446,   # [HM] Head Moderator
    1575226137003687976,   # [A] Administrator
    1575225917368705104,   # [SA] Senior Administrator
]

STAFF_HIERARCHY_NAMES: dict[int, str] = {
    1575226667537010718: "[TM] Trial Moderator",
    1575226626378039426: "[MOD] Moderator",
    1575226571076411515: "[JM] Junior Moderator",
    1575226502490882340: "[SM] Senior Moderator",
    1575226359939211446: "[HM] Head Moderator",
    1575226137003687976: "[A] Administrator",
    1575225917368705104: "[SA] Senior Administrator",
}

# ─── Staff Team Roles ─────────────────────────────────────────────────────────
ROLE_STAFF_TEAM = 1575233247598870568  # Staff
ROLE_ADMIN_TEAM = 1575233276556214343  # Admin

# ─── Privileged Roles (can use /fire, /promote, /demote, /shout) ─────────────
FIRE_ALLOWED_ROLES: set[int] = {
    1575225137542733954,   # [O] Owner.
    1575225368577704116,   # [Co-O] Co-Owner.
    1575225624837099631,   # [CM] Community Manager.
    1575225697406947418,   # [SOH] Staff OverHead
}

# ─── Faction Leader Roles ─────────────────────────────────────────────────────
FACTION_LEADER_MAIN_ROLE = 1575250992935735467  # [FL] Faction Leader

FACTION_LEADERS: dict[int, str] = {
    1575228479006449797: "Sanguis Order",    # [SOL] Sanguis Order Leader.
    1575228561881571481: "Eldritch Thorn",   # [ETL] Eldritch Thorn Leader.
    1575228378850525287: "Silver Venom",     # [SVL] SilverVenom Leader.
    1575228640507990096: "Sepharine Coven",  # [SCL] Sepharine Coven Leader.
}

# ─── Faction Council Roles ────────────────────────────────────────────────────
FACTION_COUNCIL_GLOBAL = 1575227864784175185  # [FO] Faction Overseer.

FACTION_OVERSEERS: dict[int, str] = {
    1575227909897986108: "Sanguis Order",   # [SOO] Sanguis Order Overseer.
    1575227971965423756: "Eldritch Thorn",  # [ETO] Eldritch Thorn Overseer.
    1575228298416496650: "Silver Venom",    # [SVO] SilverVenom Overseer.
}

# ─── Faction Member Roles ─────────────────────────────────────────────────────
FACTION_MEMBERS: dict[int, str] = {
    1575232569455280329: "Sanguis Order",    # [SOM] Sanguis Order Member.
    1575232880555200693: "Eldritch Thorn",   # [ETM] Eldritch Thorn Member.
    1575232935555112970: "Silver Venom",     # [SVM] SilverVenom Member.
    1575232712543965324: "Sepharine Coven",  # [SCM] Sepharine Coven Member.
}

# ─── All faction roles to strip on blacklist/demotion ─────────────────────────
ALL_FACTION_ROLES: list[int] = [
    1575232569455280329,  # [SOM] Sanguis Order Member.
    1575232880555200693,  # [ETM] Eldritch Thorn Member.
    1575232935555112970,  # [SVM] SilverVenom Member.
    1575232712543965324,  # [SCM] Sepharine Coven Member.
    1575228851653443604,  # [FM] Faction Member.
    1575228996801663207,  # [FG] Faction Guide.
    1575250992935735467,  # [FL] Faction Leader
]

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

# ─── Auto-Rank Channels ───────────────────────────────────────────────────────
FACTION_AUTORANK_CHANNEL_ID = 1575222977686143008  # Replace with your Faction username channel ID
FACTIONS_GROUP_ID           = 127271910

# Map faction roles -> (faction_name, roblox_rank_number, label)
# - Faction Leaders map to Leader rank (replace rank numbers with your group's exact Leader rank numbers)
# - Faction Overseers map strictly to basic member rank (never Leader)
FACTION_AUTORANK_ROLE_MAP: dict[int, tuple[str, int, str]] = {
    # Faction Leaders -> Leader rank
    1575228479006449797: ("Sanguis Order",   15, "Leader"),        # [SOL] Sanguis Order Leader.
    1575228561881571481: ("Eldritch Thorn",  25, "Leader"),        # [ETL] Eldritch Thorn Leader.
    1575228378850525287: ("Silver Venom",    35, "Leader"),        # [SVL] SilverVenom Leader.
    1575228640507990096: ("Sepharine Coven", 45, "Leader"),        # [SCL] Sepharine Coven Leader.

    # Faction Members -> basic member rank
    1575232569455280329: ("Sanguis Order",   10, "Basic Member"),  # [SOM] Sanguis Order Member.
    1575232880555200693: ("Eldritch Thorn",  20, "Basic Member"),  # [ETM] Eldritch Thorn Member.
    1575232935555112970: ("Silver Venom",    30, "Basic Member"),  # [SVM] SilverVenom Member.
    1575232712543965324: ("Sepharine Coven", 40, "Basic Member"),  # [SCM] Sepharine Coven Member.

    # Faction Overseers -> basic member rank ONLY (never Leader)
    1575227909897986108: ("Sanguis Order",   10, "Basic Member"),  # [SOO} Sanguis Order Overseer.
    1575227971965423756: ("Eldritch Thorn",  20, "Basic Member"),  # [ETO] Eldritch Thorn Overseer.
    1575228298416496650: ("Silver Venom",    30, "Basic Member"),  # [SVO] SilverVenom Overseer.
}

# ─── Channels ─────────────────────────────────────────────────────────────────
BLACKLIST_CHANNEL_ID = 1575314707978391692

# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_member_rank_index(member: discord.Member) -> int:
    member_role_ids = {r.id for r in member.roles}
    best = -1
    for i, role_id in enumerate(STAFF_HIERARCHY):
        if role_id in member_role_ids:
            best = i
    return best

def get_member_faction(member: discord.Member) -> Optional[str]:
    """Return faction name if member holds a faction leader OR member role."""
    member_role_ids = {r.id for r in member.roles}
    for role_id, faction in FACTION_MEMBERS.items():
        if role_id in member_role_ids:
            return faction
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

def get_council_faction(member: discord.Member) -> Optional[str]:
    """Return faction name if member holds a faction overseer role."""
    member_role_ids = {r.id for r in member.roles}
    for role_id, faction in FACTION_OVERSEERS.items():
        if role_id in member_role_ids:
            return faction
    return None

def can_use_faction_commands(member: discord.Member) -> tuple[bool, Optional[str]]:
    """
    Check if a member can use faction commands (strike, viewstrike, clearstrike,
    factiondemote, blacklist, unblacklist).
    Returns (allowed, faction_restriction).
    - Faction leaders -> only their own faction
    - Faction overseers -> only their assigned faction
    - General faction council -> any faction (None means no restriction)
    """
    member_role_ids = {r.id for r in member.roles}

    # General faction council — no restriction
    if FACTION_COUNCIL_GLOBAL in member_role_ids:
        return True, None

    # Faction-specific overseer — restricted to their faction
    overseer_faction = get_council_faction(member)
    if overseer_faction:
        return True, overseer_faction

    # Faction leader — restricted to their faction
    leader_faction = get_leader_faction(member)
    if leader_faction:
        return True, leader_faction

    return False, None

# Keep this as an alias so blacklist.py doesn't break
def can_use_blacklist(member: discord.Member) -> tuple[bool, Optional[str]]:
    return can_use_faction_commands(member)

def has_fire_permission(member: discord.Member) -> bool:
    member_role_ids = {r.id for r in member.roles}
    return bool(member_role_ids & FIRE_ALLOWED_ROLES)

def is_staff(member: discord.Member) -> bool:
    return get_member_rank_index(member) >= 0

def fmt_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m {s}s"
