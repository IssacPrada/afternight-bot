"""
constants.py — Centralized configuration, role mappings, and permission helpers
"""
import discord

# ── Server & Log Channels ─────────────────────────────────────────────────────
RESIGN_LOG_CHANNEL_ID = 1575223632408350760
INACTIVITY_REVIEW_CHANNEL_ID = 1575292981739524137
INACTIVITY_APPROVED_CHANNEL_ID = 1575223603593617530
BLACKLIST_CHANNEL_ID = 1575314707978391692
SUGGESTION_CHANNEL_ID = 1575220167900926163
FACTION_LOG_CHANNEL_ID = 1575315278751998093
FACTION_STRIKE_LOG_CHANNEL_ID = 1575315278751998093
MOD_LOG_CHANNEL_ID = 1575292898986172436
AUTOMOD_LOG_CHANNEL_ID = 1575223771466436719
TESTING_CHANNEL_ID = 1575319593621258400
FEEDBACK_CHANNEL_ID = 1575319889755906159

# ── Leadership & Staff Roles ──────────────────────────────────────────────────
ROLE_OWNER = 1575225137542733954       # [O] Owner.
ROLE_CO_OWNER = 1575225368577704116    # [Co-O] Co-Owner.
ROLE_CM = 1575225624837099631          # [CM] Community Manager.
ROLE_SOH = 1575225697406947418         # [SOH] Staff OverHead.
ROLE_SA = 1575225917368705104          # [SA] Senior Administrator.
ROLE_ADMIN = 1575226137003687976       # [A] Administrator.
ROLE_ADMIN_GENERIC = 1575233276556214343
ROLE_TESTER = 1575227735914061924

ROLE_STAFF_TEAM = 0
ROLE_ADMIN_TEAM = 0

STAFF_HIERARCHY: list[int] = [
    ROLE_OWNER,
    ROLE_CO_OWNER,
    ROLE_CM,
    ROLE_SOH,
    ROLE_SA,
    ROLE_ADMIN,
    ROLE_ADMIN_GENERIC,
]

STAFF_HIERARCHY_NAMES: dict[int, str] = {
    ROLE_OWNER: "[O] Owner.",
    ROLE_CO_OWNER: "[Co-O] Co-Owner.",
    ROLE_CM: "[CM] Community Manager.",
    ROLE_SOH: "[SOH] Staff OverHead.",
    ROLE_SA: "[SA] Senior Administrator.",
    ROLE_ADMIN: "[A] Administrator.",
    ROLE_ADMIN_GENERIC: "Admin",
}

FIRE_ALLOWED_ROLES: set[int] = {
    ROLE_OWNER,
    ROLE_CO_OWNER,
    ROLE_CM,
    ROLE_SOH,
}

# ── Faction Config (Replace 0 placeholders with migrated role IDs) ────────────
FACTION_NAMES: tuple[str, ...] = (
    "Sanguis Order",
    "Eldritch Thorn",
    "SilverVenom",
    "Seraphine Coven",
)

FACTION_COLORS: dict[str, int] = {
    "Sanguis Order": 0x990000,
    "Eldritch Thorn": 0x2E8B57,
    "SilverVenom": 0x708090,
    "Seraphine Coven": 0x9B59B6,
}

# Map faction name -> set of role IDs belonging to that faction
FACTION_MEMBER_ROLES: dict[str, set[int]] = {
    "Sanguis Order": set(),
    "Eldritch Thorn": set(),
    "SilverVenom": set(),
    "Seraphine Coven": set(),
}

ALL_FACTION_ROLES: set[int] = (
    FACTION_MEMBER_ROLES["Sanguis Order"]
    | FACTION_MEMBER_ROLES["Eldritch Thorn"]
    | FACTION_MEMBER_ROLES["SilverVenom"]
    | FACTION_MEMBER_ROLES["Seraphine Coven"]
)

FACTION_LEADER_ROLES: set[int] = {
    0,  # Sanguis Order Leader
    0,  # Eldritch Thorn Leader
    0,  # SilverVenom Leader
    0,  # Seraphine Coven Leader
}

FACTION_OVERSEER_ROLES: set[int] = {
    0,  # Sanguis Order Overseer
    0,  # Eldritch Thorn Overseer
    0,  # SilverVenom Overseer
    0,  # Seraphine Coven Overseer
}

# Map each Faction Leader / Faction Overseer role ID -> exact faction name
ROLE_TO_MANAGED_FACTION: dict[int, str] = {
    # Example:
    # 123456789012345678: "Sanguis Order",
}

# ── Permission Role Groups ────────────────────────────────────────────────────
TOP_FACTION_MGMT_ROLES: set[int] = {
    ROLE_OWNER,
    ROLE_CO_OWNER,
    ROLE_CM,
}

ACTIVITY_ALLOWED_ROLES: set[int] = (
    TOP_FACTION_MGMT_ROLES | FACTION_LEADER_ROLES | FACTION_OVERSEER_ROLES
)

FACTION_STRIKE_ALLOWED_ROLES: set[int] = (
    TOP_FACTION_MGMT_ROLES | FACTION_LEADER_ROLES | FACTION_OVERSEER_ROLES
)

STAFF_STRIKE_ALLOWED_ROLES: set[int] = {
    ROLE_OWNER,
    ROLE_CO_OWNER,
    ROLE_CM,
    ROLE_SOH,
}


# ── Permission & Lookup Helpers ───────────────────────────────────────────────
def _role_ids(member: discord.abc.User | discord.Member) -> set[int]:
    if not isinstance(member, discord.Member):
        return set()
    return {role.id for role in member.roles}


def is_staff(member: discord.abc.User | discord.Member) -> bool:
    return bool(_role_ids(member) & (set(STAFF_HIERARCHY) | FIRE_ALLOWED_ROLES))


def get_member_faction(member: discord.abc.User | discord.Member) -> str | None:
    role_ids = _role_ids(member)
    for faction_name, f_roles in FACTION_MEMBER_ROLES.items():
        if role_ids & f_roles:
            return faction_name
    return None


def can_view_activity(member: discord.abc.User | discord.Member) -> bool:
    return bool(_role_ids(member) & ACTIVITY_ALLOWED_ROLES)


def can_manage_faction_strikes(member: discord.abc.User | discord.Member) -> bool:
    return bool(_role_ids(member) & FACTION_STRIKE_ALLOWED_ROLES)


def can_manage_staff_strikes(member: discord.abc.User | discord.Member) -> bool:
    return bool(_role_ids(member) & STAFF_STRIKE_ALLOWED_ROLES)


def can_faction_demote(member: discord.abc.User | discord.Member, target_faction: str) -> bool:
    """
    Owner, Co-Owner, and Community Manager can demote in any faction.
    Faction Leaders and Faction Overseers can only demote in their own faction.
    """
    role_ids = _role_ids(member)
    if not role_ids:
        return False
    if role_ids & TOP_FACTION_MGMT_ROLES:
        return True
    managed_factions = {
        ROLE_TO_MANAGED_FACTION[rid]
        for rid in role_ids
        if rid in ROLE_TO_MANAGED_FACTION
    }
    return target_faction in managed_factions


def can_use_faction_commands(member: discord.abc.User | discord.Member) -> tuple[bool, str | None]:
    """
    Returns (allowed, restricted_faction_name).
    restricted_faction_name is None for Owner/Co-Owner/CM, or a faction name if locked to one.
    """
    role_ids = _role_ids(member)
    if not role_ids:
        return False, None
    if role_ids & TOP_FACTION_MGMT_ROLES:
        return True, None
    managed = [
        ROLE_TO_MANAGED_FACTION[rid]
        for rid in role_ids
        if rid in ROLE_TO_MANAGED_FACTION
    ]
    if managed:
        return True, managed[0]
    return False, None


def can_use_blacklist(member: discord.abc.User | discord.Member) -> bool:
    return bool(_role_ids(member) & (TOP_FACTION_MGMT_ROLES | FACTION_LEADER_ROLES | FACTION_OVERSEER_ROLES))


def has_fire_permission(member: discord.abc.User | discord.Member) -> bool:
    return bool(_role_ids(member) & FIRE_ALLOWED_ROLES)
