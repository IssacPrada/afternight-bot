"""
constants.py — Role IDs, channel IDs, faction config, and shared helpers.
"""
import discord
from typing import Optional

# ─── Channels ─────────────────────────────────────────────────────────────────
RESIGN_LOG_CHANNEL_ID        = 1575223632408350760
INACTIVITY_REVIEW_CHANNEL_ID   = 1575292981739524137
INACTIVITY_APPROVED_CHANNEL_ID = 1575223603593617530
BLACKLIST_CHANNEL_ID           = 1575292981739524137  # Update if you have a dedicated blacklist channel ID
SUGGESTION_CHANNEL_ID        = 1575220167900926163
BLACKLIST_CHANNEL_ID           = 1575314707978391692
FACTION_LOG_CHANNEL_ID         = 1575315278751998093
MOD_LOG_CHANNEL_ID             = 1575292898986172436
AUTOMOD_LOG_CHANNEL_ID         = 1575223771466436719
# ─── Core / Leadership Roles ──────────────────────────────────────────────────
ROLE_MEMBER       = 1575231657638764766  # [M] Member.
ROLE_HONORED      = 1575229161176567828  # [HMB] Honored Member.
ROLE_TESTER       = 1575227735914061924  # [T] Tester.
ROLE_CONTRIBUTOR  = 1575227506443812964  # [C] Contributor.
ROLE_MEDIA        = 1575231719945281677  # [MP] Media Partner.

ROLE_STAFF_TEAM   = 1575233247598870568  # Staff
ROLE_ADMIN_TEAM   = 1575233276556214343  # Admin
ROLE_SOH          = 1575225697406947418  # [SOH] Staff OverHead.
ROLE_CM           = 1575225624837099631  # [CM] Community Manager.
ROLE_DEV          = 1575233518265700353  # [D] Developer.
ROLE_CO_OWNER     = 1575225368577704116  # [Co-O] Co-Owner.
ROLE_OWNER        = 1575225137542733954  # [O] Owner.

# ─── Staff Hierarchy (ordered lowest → highest) ───────────────────────────────
STAFF_HIERARCHY: list[int] = [
    1575226667537010718,  # [TM] Trial Moderator.
    1575226626378039426,  # [MOD] Moderator.
    1575226571076411515,  # [JM] Junior Moderator
    1575226502490882340,  # [SM] Senior Moderator.
    1575226359939211446,  # [HM] Head Moderator
    1575226137003687976,  # [A] Administrator.
    1575225917368705104,  # [SA] Senior Administrator.
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

SENIOR_STAFF_ROLES: list[int] = [
    ROLE_SOH,
    ROLE_CM,
    ROLE_DEV,
    ROLE_CO_OWNER,
    ROLE_OWNER,
]

# ─── Privileged Roles ─────────────────────────────────────────────────────────
FIRE_ALLOWED_ROLES: set[int] = {
    ROLE_SOH,
    ROLE_CM,
    ROLE_DEV,
    ROLE_CO_OWNER,
    ROLE_OWNER,
}

INACTIVITY_REVIEWER_ROLES: set[int] = {
    ROLE_SOH,
    ROLE_CM,
    ROLE_DEV,
    ROLE_CO_OWNER,
    ROLE_OWNER,
}

# ─── Faction Roles ────────────────────────────────────────────────────────────
FACTION_LEADER_MAIN_ROLE = 1575250992935735467  # [FL] Faction Leader
FACTION_GUIDE_ROLE       = 1575228996801663207  # [FG] Faction Guide.
FACTION_MEMBER_MAIN_ROLE = 1575228851653443604  # [FM] Faction Member.
FACTION_COUNCIL_GLOBAL   = 1575227864784175185  # [FO] Faction Overseer.

FACTION_LEADERS: dict[int, str] = {
    1575228479006449797: "Sanguis Order",   # [SOL] Sanguis Order Leader.
    1575228561881571481: "Eldritch Thorn",  # [ETL] Eldritch Thorn Leader.
    1575228378850525287: "SilverVenom",     # [SVL] SilverVenom Leader.
    1575228640507990096: "Seraphine Coven", # [SCL] Seraphine Coven Leader.
}

FACTION_OVERSEERS: dict[int, str] = {
    1575227909897986108: "Sanguis Order",   # [SOO} Sanguis Order Overseer.
    1575227971965423756: "Eldritch Thorn",  # [ETO] Eldritch Thorn Overseer.
    1575228298416496650: "SilverVenom",     # [SVO] SilverVenom Overseer.
}

FACTION_MEMBERS: dict[int, str] = {
    1575232569455280329: "Sanguis Order",   # [SOM] Sanguis Order Member.
    1575232880555200693: "Eldritch Thorn",  # [ETM] Eldritch Thorn Member.
    1575232935555112970: "SilverVenom",     # [SVM] SilverVenom Member.
    1575232712543965324: "Seraphine Coven", # [SCM] Seraphine Coven Member.
}

ALL_FACTION_ROLES: list[int] = [
    1575232569455280329,  # [SOM]
    1575232880555200693,  # [ETM]
    1575232935555112970,  # [SVM]
    1575232712543965324,  # [SCM]
    FACTION_LEADER_MAIN_ROLE,
    FACTION_GUIDE_ROLE,
    FACTION_MEMBER_MAIN_ROLE,
]

FACTION_ROBLOX_RANKS: dict[str, int] = {
    "Sanguis Order":   10,
    "Eldritch Thorn":  20,
    "SilverVenom":     30,
    "Seraphine Coven": 40,
}

FACTION_COLORS: dict[str, int] = {
    "Sanguis Order":   0x710000,
    "Eldritch Thorn":  0x702794,
    "SilverVenom":     0x236A00,
    "Seraphine Coven": 0xECBF66,
}

STRIKE_STATUS = {
    0: ("✅ Normal",        discord.Color.green()),
    1: ("⚠️ Warning",       discord.Color.yellow()),
    2: ("🔴 At Risk",       discord.Color.orange()),
    3: ("💀 Final Warning", discord.Color.red()),
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_member_rank_index(member: discord.Member) -> int:
    member_role_ids = {r.id for r in member.roles}
    best = -1
    for i, role_id in enumerate(STAFF_HIERARCHY):
        if role_id in member_role_ids:
            best = i
    return best

def get_member_faction(member: discord.Member) -> Optional[str]:
    member_role_ids = {r.id for r in member.roles}
    for role_id, faction in FACTION_MEMBERS.items():
        if role_id in member_role_ids:
            return faction
    for role_id, faction in FACTION_LEADERS.items():
        if role_id in member_role_ids:
            return faction
    return None

def get_leader_faction(member: discord.Member) -> Optional[str]:
    member_role_ids = {r.id for r in member.roles}
    for role_id, faction in FACTION_LEADERS.items():
        if role_id in member_role_ids:
            return faction
    return None

def get_council_faction(member: discord.Member) -> Optional[str]:
    member_role_ids = {r.id for r in member.roles}
    for role_id, faction in FACTION_OVERSEERS.items():
        if role_id in member_role_ids:
            return faction
    return None

def can_use_faction_commands(member: discord.Member) -> tuple[bool, Optional[str]]:
    member_role_ids = {r.id for r in member.roles}

    if FACTION_COUNCIL_GLOBAL in member_role_ids or (member_role_ids & FIRE_ALLOWED_ROLES):
        return True, None

    overseer_faction = get_council_faction(member)
    if overseer_faction:
        return True, overseer_faction

    leader_faction = get_leader_faction(member)
    if leader_faction:
        return True, leader_faction

    return False, None

def can_use_blacklist(member: discord.Member) -> tuple[bool, Optional[str]]:
    return can_use_faction_commands(member)

def has_fire_permission(member: discord.Member) -> bool:
    member_role_ids = {r.id for r in member.roles}
    return bool(member_role_ids & FIRE_ALLOWED_ROLES)

def can_review_inactivity(member: discord.Member) -> bool:
    member_role_ids = {r.id for r in member.roles}
    return bool(member_role_ids & INACTIVITY_REVIEWER_ROLES)

def is_staff(member: discord.Member) -> bool:
    member_role_ids = {r.id for r in member.roles}
    return (
        get_member_rank_index(member) >= 0
        or ROLE_STAFF_TEAM in member_role_ids
        or ROLE_ADMIN_TEAM in member_role_ids
        or bool(member_role_ids & FIRE_ALLOWED_ROLES)
    )

def fmt_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m {s}s"
