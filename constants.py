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
ROLE_OWNER = 1575225137542733954          # [O] Owner.
ROLE_CO_OWNER = 1575225368577704116       # [Co-O] Co-Owner.
ROLE_DEVELOPER = 1575233518265700353      # [D] Developer.
ROLE_CM = 1575225624837099631             # [CM] Community Manager.
ROLE_SOH = 1575225697406947418            # [SOH] Staff OverHead.
ROLE_SA = 1575225917368705104             # [SA] Senior Administrator.
ROLE_ADMIN = 1575226137003687976          # [A] Administrator.
ROLE_ADMIN_GENERIC = 1575233276556214343  # Admin
ROLE_HM = 1575226359939211446             # [HM] Head Moderator
ROLE_SM = 1575226502490882340             # [SM] Senior Moderator.
ROLE_JM = 1575226571076411515             # [JM] Junior Moderator.
ROLE_MOD = 1575226626378039426            # [MOD] Moderator.
ROLE_STAFF = 1575233247598870568          # Staff
ROLE_TM = 1575226667537010718             # [TM] Trial Moderator.
ROLE_CONTRIBUTOR = 1575227506443812964    # [C] Contributor.
ROLE_TESTER = 1575227735914061924         # [T] Tester.
ROLE_MEDIA_PARTNER = 1575231719945281677  # [MP] Media Partner.
ROLE_FACTION_GUIDE = 1575228996801663207  # [FG] Faction Guide.
ROLE_FACTION_MEMBER = 1575228851653443604 # [FM] Faction Member.
ROLE_HONORED_MEMBER = 1575229161176567828 # [HMB] Honored Member.
ROLE_MEMBER = 1575231657638764766         # [M] Member.

ROLE_STAFF_TEAM = ROLE_STAFF
ROLE_ADMIN_TEAM = ROLE_ADMIN_GENERIC

STAFF_HIERARCHY: list[int] = [
    ROLE_OWNER,
    ROLE_CO_OWNER,
    ROLE_CM,
    ROLE_SOH,
    ROLE_SA,
    ROLE_ADMIN,
    ROLE_ADMIN_GENERIC,
    ROLE_HM,
    ROLE_SM,
    ROLE_JM,
    ROLE_MOD,
    ROLE_STAFF,
    ROLE_TM,
]

STAFF_HIERARCHY_NAMES: dict[int, str] = {
    ROLE_OWNER: "[O] Owner.",
    ROLE_CO_OWNER: "[Co-O] Co-Owner.",
    ROLE_CM: "[CM] Community Manager.",
    ROLE_SOH: "[SOH] Staff OverHead.",
    ROLE_SA: "[SA] Senior Administrator.",
    ROLE_ADMIN: "[A] Administrator.",
    ROLE_ADMIN_GENERIC: "Admin",
    ROLE_HM: "[HM] Head Moderator",
    ROLE_SM: "[SM] Senior Moderator.",
    ROLE_JM: "[JM] Junior Moderator.",
    ROLE_MOD: "[MOD] Moderator.",
    ROLE_STAFF: "Staff",
    ROLE_TM: "[TM] Trial Moderator.",
}

SENIOR_STAFF_ROLES: set[int] = {
    ROLE_OWNER,
    ROLE_CO_OWNER,
    ROLE_CM,
    ROLE_SOH,
    ROLE_SA,
    ROLE_ADMIN,
    ROLE_ADMIN_GENERIC,
}

FIRE_ALLOWED_ROLES: set[int] = {
    ROLE_OWNER,
    ROLE_CO_OWNER,
    ROLE_CM,
    ROLE_SOH,
}

# ── Faction Roles ─────────────────────────────────────────────────────────────
ROLE_FO_GENERIC = 1575227864784175185   # [FO] Faction Overseer.
ROLE_SOO = 1575227909897986108          # [SOO} Sanguis Order Overseer.
ROLE_ETO = 1575227971965423756          # [ETO] Eldritch Thorn Overseer.
ROLE_SVO = 1575228298416496650          # [SVO] SilverVenom Overseer.

ROLE_FL_GENERIC = 1575250992935735467   # [FL] Faction Leader
ROLE_SOL = 1575228479006449797          # [SOL] Sanguis Order Leader.
ROLE_ETL = 1575228561881571481          # [ETL] Eldritch Thorn Leader.
ROLE_SVL = 1575228378850525287          # [SVL] SilverVenom Leader.
ROLE_SCL = 1575228640507990096          # [SCL] Seraphine Coven Leader.

ROLE_SOM = 1575232569455280329          # [SOM] Sanguis Order Member.
ROLE_ETM = 1575232880555200693          # [ETM] Eldritch Thorn Member.
ROLE_SVM = 1575232935555112970          # [SVM] SilverVenom Member.
ROLE_SCM = 1575232712543965324          # [SCM] Seraphine Coven Member.

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
    "Sanguis Order": {ROLE_SOM, ROLE_SOL, ROLE_SOO},
    "Eldritch Thorn": {ROLE_ETM, ROLE_ETL, ROLE_ETO},
    "SilverVenom": {ROLE_SVM, ROLE_SVL, ROLE_SVO},
    "Seraphine Coven": {ROLE_SCM, ROLE_SCL},
}

ALL_FACTION_ROLES: set[int] = (
    FACTION_MEMBER_ROLES["Sanguis Order"]
    | FACTION_MEMBER_ROLES["Eldritch Thorn"]
    | FACTION_MEMBER_ROLES["SilverVenom"]
    | FACTION_MEMBER_ROLES["Seraphine Coven"]
    | {ROLE_FACTION_MEMBER, ROLE_FACTION_GUIDE, ROLE_FL_GENERIC, ROLE_FO_GENERIC}
)

FACTION_LEADER_ROLES: set[int] = {
    ROLE_SOL,
    ROLE_ETL,
    ROLE_SVL,
    ROLE_SCL,
    ROLE_FL_GENERIC,
}

FACTION_LEADERS: set[int] = FACTION_LEADER_ROLES
FACTION_LEADER_MAIN_ROLE: int = ROLE_FL_GENERIC

FACTION_OVERSEER_ROLES: set[int] = {
    ROLE_SOO,
    ROLE_ETO,
    ROLE_SVO,
    ROLE_FO_GENERIC,
}

# Map each faction-specific Leader / Overseer role ID -> exact faction name
# Seraphine Coven is handled explicitly in helpers so any overseer can manage it
# (alongside Owner, Co-Owner, and CM), while faction leaders (including SCL) cannot.
ROLE_TO_MANAGED_FACTION: dict[int, str] = {
    ROLE_SOL: "Sanguis Order",
    ROLE_SOO: "Sanguis Order",
    ROLE_ETL: "Eldritch Thorn",
    ROLE_ETO: "Eldritch Thorn",
    ROLE_SVL: "SilverVenom",
    ROLE_SVO: "SilverVenom",
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
    return bool(_role_ids(member) & (set(STAFF_HIERARCHY) | FIRE_ALLOWED_ROLES | {ROLE_DEVELOPER}))


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
    Seraphine Coven can be managed by any overseer, Owner, Co-Owner, or CM (not leaders).
    Other factions can be managed by their own faction's leaders/overseers.
    """
    role_ids = _role_ids(member)
    if not role_ids:
        return False
    if role_ids & TOP_FACTION_MGMT_ROLES:
        return True
    if target_faction == "Seraphine Coven":
        return bool(role_ids & FACTION_OVERSEER_ROLES)
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
    if role_ids & FACTION_OVERSEER_ROLES:
        managed = [
            ROLE_TO_MANAGED_FACTION[rid]
            for rid in role_ids
            if rid in ROLE_TO_MANAGED_FACTION
        ]
        return True, managed[0] if managed else "Seraphine Coven"
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


def can_review_inactivity(member: discord.abc.User | discord.Member) -> bool:
    return bool(_role_ids(member) & SENIOR_STAFF_ROLES)
```[cite: 2]

To also clear the `cogs.activity` import error (`get_player_playtime` in `utils/roblox.py`), paste `utils/roblox.py` (or `cogs/activity.py`) and I'll match them up for you.
