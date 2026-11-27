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

# ─── Privileged Roles (can use /fire, /promote, /demote, /shout) ─────────────
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

# ─── Faction Council Roles ────────────────────────────────────────────────────
FACTION_COUNCIL_GLOBAL = 1487512441373065327  # General Faction Council role

FACTION_OVERSEERS: dict[int, str] = {
    1487867888592490606: "Sanguis Order",    # Sanguis Order Overseer
    1487867988446154925: "Eldritch Thorn",   # Eldritch Thorn Overseer
    1487868098492104767: "Silver Venom",     # Silvervenom Overseer
    # Sepharine Coven has no overseer
}

# ─── Faction Member Roles ─────────────────────────────────────────────────────
FACTION_MEMBERS: dict[int, str] = {
    1458305856297893932: "Sanguis Order",    # Sanguis Order Vampire
    1458305862748868619: "Eldritch Thorn",   # Eldritch Thorn Witch
    1458305842372673639: "Silver Venom",     # Silver Venom Werewolf
    1458305868495065262: "Sepharine Coven",  # Sepharine Werewitch
}

# ─── All faction roles to strip on blacklist/demotion ─────────────────────────
ALL_FACTION_ROLES: list[int] = [
    1458305856297893932,  # Sanguis Order Vampire
    1458305862748868619,  # Eldritch Thorn Witch
    1458305842372673639,  # Silver Venom Werewolf
    1458305868495065262,  # Sepharine Werewitch
    1458305763306111092,  # Faction Member
    1458305760839864422,  # Faction Elder
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
```[cite: 2]

---

### `automod.py`

```python
"""
cogs/automod.py — Auto moderation for slurs
"""
import discord
from discord import app_commands
from discord.ext import commands
import datetime
import json
import os

# ── Config ────────────────────────────────────────────────────────────────────
AUTOMOD_LOG_CHANNEL = 1575223771466436719
SLURS_FILE          = "data/slurs.json"

IMMUNE_ROLES: set[int] = {
    1387649282139754587,  # [C] Creators
}

ALLOWED_TO_MANAGE: set[int] = {
    1458302857764802683,  # Community Manager
    1458302854887510210,  # Overseer of Staff
    1387649282139754587,  # [C] Creators
}

APPEAL_SERVER = "https://discord.gg/dQAbatSEcw"


def load_slurs() -> list[str]:
    try:
        if not os.path.exists(SLURS_FILE):
            return []
        with open(SLURS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_slurs(slurs: list[str]):
    try:
        os.makedirs(os.path.dirname(SLURS_FILE), exist_ok=True)
        with open(SLURS_FILE, "w") as f:
            json.dump(slurs, f)
    except Exception:
        pass


def contains_slur(content: str, slurs: list[str]) -> bool:
    content_lower = content.lower()
    for slur in slurs:
        if slur.lower() in content_lower:
            return True
    return False


class AutoModCog(commands.Cog):
    def __init__(self, bot):
        self.bot   = bot
        self.slurs = load_slurs()

    # ── Message listener ──────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return

        member_role_ids = {r.id for r in message.author.roles}
        if member_role_ids & IMMUNE_ROLES:
            return

        if not self.slurs:
            return

        if not contains_slur(message.content, self.slurs):
            return

        # ── Delete message ────────────────────────────────────────────────────
        try:
            await message.delete()
        except discord.Forbidden:
            pass

        # ── Auto warn ─────────────────────────────────────────────────────────
        guild = message.guild
        try:
            await self.bot.db.add_warn(
                str(message.author.id),
                str(guild.id),
                "Slur usage",
                f"Auto-detected slur in #{message.channel.name}",
                str(self.bot.user.id)
            )
            warns      = await self.bot.db.get_warns(str(message.author.id), str(guild.id))
            warn_count = len(warns)
        except Exception:
            warn_count = 1

        # ── Warn message in channel ───────────────────────────────────────────
        try:
            await message.channel.send(
                f"{message.author.mention} you have been warned for slur usage.",
                delete_after=10
            )
        except discord.Forbidden:
            pass

        # ── DM the user ───────────────────────────────────────────────────────
        try:
            dm = discord.Embed(
                title="⚠️ You Have Been Warned",
                color=discord.Color.yellow(),
                timestamp=discord.utils.utcnow()
            )
            dm.description = (
                f"You have been warned in **Afternight Legacies** for **slur usage**.\n\n"
                f"**Warning Count:** {warn_count}\n\n"
                f"If you believe this was a mistake, open a ticket:\n{APPEAL_SERVER}"
            )
            dm.set_footer(text="Afternight Auto Moderation")
            await message.author.send(embed=dm)
        except discord.Forbidden:
            pass

        # ── Log ───────────────────────────────────────────────────────────────
        log_channel = guild.get_channel(AUTOMOD_LOG_CHANNEL)
        if log_channel:
            log_embed = discord.Embed(
                title="🤖 AutoMod — Slur Detected",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            log_embed.set_thumbnail(url=message.author.display_avatar.url)
            log_embed.add_field(
                name="User",
                value=f"{message.author.mention} (`{message.author.id}`)",
                inline=True
            )
            log_embed.add_field(name="Channel",       value=message.channel.mention, inline=True)
            log_embed.add_field(name="Warning Count", value=f"{warn_count}",         inline=True)
            log_embed.add_field(name="Action",        value="Message deleted + Auto warned", inline=False)
            log_embed.set_footer(text=f"User ID: {message.author.id}")
            await log_channel.send(embed=log_embed)

    # ── /addslur ──────────────────────────────────────────────────────────────

    @app_commands.command(name="addslur", description="Add a word to the automod slur list.")
    @app_commands.describe(word="The word to add")
    async def addslur(self, interaction: discord.Interaction, word: str):
        await interaction.response.defer(ephemeral=True)

        if not {r.id for r in interaction.user.roles} & ALLOWED_TO_MANAGE:
            return await interaction.followup.send(
                "❌ Only Community Manager, Overseer of Staff, or Creators may manage the slur list.",
                ephemeral=True
            )

        word = word.lower().strip()
        if word in self.slurs:
            return await interaction.followup.send(
                f"❌ `{word}` is already in the slur list.", ephemeral=True
            )

        self.slurs.append(word)
        save_slurs(self.slurs)

        await interaction.followup.send(
            f"✅ Added `{word}` to the automod slur list. Total: **{len(self.slurs)}** word(s).",
            ephemeral=True
        )

    # ── /removeslur ───────────────────────────────────────────────────────────

    @app_commands.command(name="removeslur", description="Remove a word from the automod slur list.")
    @app_commands.describe(word="The word to remove")
    async def removeslur(self, interaction: discord.Interaction, word: str):
        await interaction.response.defer(ephemeral=True)

        if not {r.id for r in interaction.user.roles} & ALLOWED_TO_MANAGE:
            return await interaction.followup.send(
                "❌ Only Community Manager, Overseer of Staff, or Creators may manage the slur list.",
                ephemeral=True
            )

        word = word.lower().strip()
        if word not in self.slurs:
            return await interaction.followup.send(
                f"❌ `{word}` is not in the slur list.", ephemeral=True
            )

        self.slurs.remove(word)
        save_slurs(self.slurs)

        await interaction.followup.send(
            f"✅ Removed `{word}` from the automod slur list. Total: **{len(self.slurs)}** word(s).",
            ephemeral=True
        )

    # ── /viewslurs ────────────────────────────────────────────────────────────

    @app_commands.command(name="viewslurs", description="View all words in the automod slur list.")
    async def viewslurs(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not {r.id for r in interaction.user.roles} & ALLOWED_TO_MANAGE:
            return await interaction.followup.send(
                "❌ Only Community Manager, Overseer of Staff, or Creators may view the slur list.",
                ephemeral=True
            )

        # ── Reload from file in case another instance updated it ──────────────
        self.slurs = load_slurs()

        if not self.slurs:
            return await interaction.followup.send(
                "The slur list is currently empty.", ephemeral=True
            )

        embed = discord.Embed(
            title="🤖 AutoMod Slur List",
            description="\n".join(f"`{s}`" for s in self.slurs),
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"Total: {len(self.slurs)} word(s)")
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AutoModCog(bot))
```[cite: 9]

---

### `backup.py`

```python
"""
cogs/backup.py — /generatebackupcode and /transferroles slash commands
"""
import discord
from discord import app_commands
from discord.ext import commands
from constants import (
    STAFF_HIERARCHY, STAFF_HIERARCHY_NAMES,
    ROLE_STAFF_TEAM, ROLE_ADMIN_TEAM,
    FIRE_ALLOWED_ROLES, is_staff
)
import datetime
import secrets
import string

# ── Config ────────────────────────────────────────────────────────────────────
TRANSFER_LOG_CHANNEL = 1575292898986172436

NOTIFY_ROLES: set[int] = {
    1458302854887510210,  # Overseer of Staff
    1458302857764802683,  # Community Manager
    1387649282139754587,  # [C] Creators
}


def generate_code() -> str:
    """Generate a random 16-character alphanumeric code."""
    chars = string.ascii_uppercase + string.digits
    return "-".join(
        "".join(secrets.choice(chars) for _ in range(4))
        for _ in range(4)
    )


class BackupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # In-memory store: code -> {user_id, guild_id, roles, created_at}
        self.backup_codes: dict[str, dict] = {}

    # ── /generatebackupcode ───────────────────────────────────────────────────

    @app_commands.command(
        name="generatebackupcode",
        description="Generate a backup code to transfer your roles if your account is compromised."
    )
    async def generatebackupcode(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        member = interaction.user

        if not is_staff(member):
            return await interaction.followup.send(
                "❌ Only staff members may generate a backup code.",
                ephemeral=True
            )

        # ── Check if they already have a code ─────────────────────────────────
        existing = next(
            (code for code, data in self.backup_codes.items()
             if data["user_id"] == member.id and data["guild_id"] == interaction.guild.id),
            None
        )

        if existing:
            # Show their existing code
            data = self.backup_codes[existing]
            embed = discord.Embed(
                title="🔑 Your Existing Backup Code",
                color=discord.Color.yellow(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.description = (
                f"You already have a backup code. Keep it safe!\n\n"
                f"```{existing}```\n\n"
                f"⚠️ **Never share this code with anyone.**\n"
                f"If you believe it has been compromised, use `/generatebackupcode` "
                f"again to generate a new one."
            )
            embed.add_field(
                name="Roles Stored",
                value=", ".join(data["role_names"]) or "None",
                inline=False
            )
            embed.set_footer(text="Store this somewhere safe — it never expires.")
            return await interaction.followup.send(embed=embed, ephemeral=True)

        # ── Store their current staff roles ───────────────────────────────────
        staff_role_ids = []
        staff_role_names = []
        member_role_ids = {r.id for r in member.roles}

        for role_id in STAFF_HIERARCHY:
            if role_id in member_role_ids:
                staff_role_ids.append(role_id)
                staff_role_names.append(STAFF_HIERARCHY_NAMES.get(role_id, "Unknown"))

        for rid in [ROLE_STAFF_TEAM, ROLE_ADMIN_TEAM]:
            if rid in member_role_ids:
                staff_role_ids.append(rid)

        # Also store privileged roles
        for rid in FIRE_ALLOWED_ROLES:
            if rid in member_role_ids:
                staff_role_ids.append(rid)

        if not staff_role_ids:
            return await interaction.followup.send(
                "❌ You don't have any staff roles to back up.",
                ephemeral=True
            )

        # ── Generate code ─────────────────────────────────────────────────────
        code = generate_code()
        while code in self.backup_codes:
            code = generate_code()

        self.backup_codes[code] = {
            "user_id":    member.id,
            "guild_id":   interaction.guild.id,
            "role_ids":   staff_role_ids,
            "role_names": staff_role_names,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "used":       False
        }

        # ── Send code via DM ──────────────────────────────────────────────────
        try:
            dm_embed = discord.Embed(
                title="🔑 Your Backup Code",
                color=discord.Color.blurple(),
                timestamp=datetime.datetime.utcnow()
            )
            dm_embed.description = (
                f"Here is your backup code. **Store it somewhere safe.**\n\n"
                f"```{code}```\n\n"
                f"⚠️ **Never share this with anyone.**\n\n"
                f"If your account is ever compromised, join the server on your new "
                f"account and use `/transferroles` with this code to transfer your roles."
            )
            dm_embed.add_field(
                name="Roles Stored",
                value=", ".join(staff_role_names) or "None",
                inline=False
            )
            dm_embed.set_footer(text="This code never expires — keep it safe.")
            await member.send(embed=dm_embed)

            await interaction.followup.send(
                "✅ Your backup code has been sent to your DMs! Keep it safe.",
                ephemeral=True
            )
        except discord.Forbidden:
            # DMs closed — show in ephemeral
            embed = discord.Embed(
                title="🔑 Your Backup Code",
                color=discord.Color.blurple(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.description = (
                f"⚠️ Could not DM you. Here is your code — **copy it now, "
                f"this message will disappear.**\n\n"
                f"```{code}```\n\n"
                f"**Never share this with anyone.**"
            )
            embed.add_field(
                name="Roles Stored",
                value=", ".join(staff_role_names) or "None",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /transferroles ────────────────────────────────────────────────────────

    @app_commands.command(
        name="transferroles",
        description="Transfer your staff roles to this account using your backup code."
    )
    @app_commands.describe(
        code="Your backup code (format: XXXX-XXXX-XXXX-XXXX)",
        old_account="Your old Discord account (mention or ID)"
    )
    async def transferroles(self, interaction: discord.Interaction,
                             code: str, old_account: discord.Member):
        await interaction.response.defer(ephemeral=True)

        new_member = interaction.user
        guild      = interaction.guild
        code       = code.strip().upper()

        # ── Validate code ─────────────────────────────────────────────────────
        if code not in self.backup_codes:
            return await interaction.followup.send(
                "❌ Invalid backup code. Double check and try again.",
                ephemeral=True
            )

        data = self.backup_codes[code]

        # ── Check guild matches ───────────────────────────────────────────────
        if data["guild_id"] != guild.id:
            return await interaction.followup.send(
                "❌ This code was not generated in this server.",
                ephemeral=True
            )

        # ── Check old account matches ─────────────────────────────────────────
        if data["user_id"] != old_account.id:
            return await interaction.followup.send(
                "❌ That code does not belong to the old account you specified.",
                ephemeral=True
            )

        # ── Check code not already used ───────────────────────────────────────
        if data["used"]:
            return await interaction.followup.send(
                "❌ This backup code has already been used.",
                ephemeral=True
            )

        # ── Check new account doesn't already have staff roles ────────────────
        if is_staff(new_member):
            return await interaction.followup.send(
                "❌ Your new account already has staff roles.",
                ephemeral=True
            )

        # ── Transfer roles ────────────────────────────────────────────────────
        roles_added   = []
        roles_removed = []

        # Add roles to new account
        for role_id in data["role_ids"]:
            role = guild.get_role(role_id)
            if role:
                try:
                    await new_member.add_roles(role, reason=f"Role transfer from {old_account}")
                    roles_added.append(role)
                except discord.Forbidden:
                    pass

        # Remove roles from old account
        for role_id in data["role_ids"]:
            role = guild.get_role(role_id)
            if role and role in old_account.roles:
                try:
                    await old_account.remove_roles(role, reason=f"Role transfer to {new_member}")
                    roles_removed.append(role)
                except discord.Forbidden:
                    pass

        # Mark code as used
        self.backup_codes[code]["used"] = True

        # ── Notify log channel ────────────────────────────────────────────────
        log_channel = guild.get_channel(TRANSFER_LOG_CHANNEL)

        # Ping all notify roles
        pings = []
        for role_id in NOTIFY_ROLES:
            role = guild.get_role(role_id)
            if role:
                pings.append(role.mention)
        ping_str = " ".join(pings)

        log_embed = discord.Embed(
            title="🔄 Staff Role Transfer",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(
            name="Old Account",
            value=f"{old_account.mention} (`{old_account.id}`)",
            inline=True
        )
        log_embed.add_field(
            name="New Account",
            value=f"{new_member.mention} (`{new_member.id}`)",
            inline=True
        )
        log_embed.add_field(
            name="Roles Transferred",
            value=", ".join(r.name for r in roles_added) or "None",
            inline=False
        )
        log_embed.add_field(
            name="Roles Removed from Old Account",
            value=", ".join(r.name for r in roles_removed) or "None",
            inline=False
        )
        log_embed.set_footer(text="Please verify this transfer is legitimate.")

        if log_channel:
            await log_channel.send(content=ping_str, embed=log_embed)

        # ── Also log to main log channel ──────────────────────────────────────
        await self.bot.log_action(log_embed)

        # ── DM old account ────────────────────────────────────────────────────
        try:
            old_dm = discord.Embed(
                title="🔄 Roles Transferred Away",
                color=discord.Color.red(),
                timestamp=datetime.datetime.utcnow()
            )
            old_dm.description = (
                f"Your staff roles have been transferred to a new account.\n\n"
                f"**Roles Removed:** {', '.join(r.name for r in roles_removed) or 'None'}\n\n"
                f"If you did not authorize this transfer contact an Overseer of Staff "
                f"or Community Manager immediately."
            )
            await old_account.send(embed=old_dm)
        except discord.Forbidden:
            pass

        # ── Confirm to new account ────────────────────────────────────────────
        confirm_embed = discord.Embed(
            title="✅ Roles Successfully Transferred",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        confirm_embed.description = (
            f"Your staff roles have been transferred to this account.\n\n"
            f"**Roles Added:** {', '.join(r.name for r in roles_added) or 'None'}\n\n"
            f"Leadership has been notified of this transfer."
        )
        await interaction.followup.send(embed=confirm_embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(BackupCog(bot))
```[cite: 10]

---

### `inactivity.py`

```python
"""
cogs/inactivity.py — /inactivitynotice slash command
"""
import discord
from discord import app_commands
from discord.ext import commands
from constants import is_staff, FIRE_ALLOWED_ROLES
import datetime

# ── Config ────────────────────────────────────────────────────────────────────
REVIEW_CHANNEL_ID   = 1575292981739524137  # Where notices are reviewed
APPROVED_CHANNEL_ID = 1575223603593617530  # Where approved notices are posted

REVIEWER_ROLES: set[int] = {
    1458302854887510210,  # Overseer of Staff
    1458302857764802683,  # Community Manager
    1387649282139754587,  # [C] Creators
}


def can_review(member: discord.Member) -> bool:
    return bool({r.id for r in member.roles} & REVIEWER_ROLES)


# ── Approval View ─────────────────────────────────────────────────────────────

class InactivityView(discord.ui.View):
    def __init__(self, submitter_id: int, date_start: str, date_end: str, reason: str):
        super().__init__(timeout=None)
        self.submitter_id = submitter_id
        self.date_start   = date_start
        self.date_end     = date_end
        self.reason       = reason

    @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.green, custom_id="inactivity_approve")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not can_review(interaction.user):
            return await interaction.response.send_message(
                "❌ You don't have permission to approve inactivity notices.",
                ephemeral=True
            )

        # ── Disable buttons ───────────────────────────────────────────────────
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

        # ── Update review embed ───────────────────────────────────────────────
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(
            name="✅ Approved By",
            value=f"{interaction.user.mention} — {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
            inline=False
        )
        await interaction.message.edit(embed=embed, view=self)

        # ── Post to approved channel ──────────────────────────────────────────
        approved_channel = interaction.guild.get_channel(APPROVED_CHANNEL_ID)
        submitter = interaction.guild.get_member(self.submitter_id)
        mention   = submitter.mention if submitter else f"<@{self.submitter_id}>"

        approved_embed = discord.Embed(
            title="📋 Inactivity Notice Approved",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        approved_embed.description = (
            f"{mention}\n\n"
            f"📅 **Starting:** {self.date_start}\n"
            f"📅 **Returning:** {self.date_end}\n\n"
            f"**Reason:** {self.reason}"
        )
        approved_embed.set_footer(text=f"Approved by {interaction.user.display_name}")

        if approved_channel:
            await approved_channel.send(embed=approved_embed)

        # ── DM submitter ──────────────────────────────────────────────────────
        if submitter:
            try:
                dm_embed = discord.Embed(
                    title="✅ Inactivity Notice Approved",
                    color=discord.Color.green(),
                    timestamp=datetime.datetime.utcnow()
                )
                dm_embed.description = (
                    f"Your inactivity notice has been **approved**!\n\n"
                    f"📅 **Starting:** {self.date_start}\n"
                    f"📅 **Returning:** {self.date_end}\n\n"
                    f"Enjoy your time off!"
                )
                await submitter.send(embed=dm_embed)
            except discord.Forbidden:
                pass

        await interaction.response.send_message(
            f"✅ Inactivity notice approved and posted to <#{APPROVED_CHANNEL_ID}>.",
            ephemeral=True
        )

    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.red, custom_id="inactivity_deny")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not can_review(interaction.user):
            return await interaction.response.send_message(
                "❌ You don't have permission to deny inactivity notices.",
                ephemeral=True
            )

        # ── Disable buttons ───────────────────────────────────────────────────
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

        # ── Update review embed ───────────────────────────────────────────────
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(
            name="❌ Denied By",
            value=f"{interaction.user.mention} — {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
            inline=False
        )
        await interaction.message.edit(embed=embed, view=self)

        # ── DM submitter ──────────────────────────────────────────────────────
        submitter = interaction.guild.get_member(self.submitter_id)
        if submitter:
            try:
                dm_embed = discord.Embed(
                    title="❌ Inactivity Notice Denied",
                    color=discord.Color.red(),
                    timestamp=datetime.datetime.utcnow()
                )
                dm_embed.description = (
                    f"Your inactivity notice has been **denied**.\n\n"
                    f"📅 **Starting:** {self.date_start}\n"
                    f"📅 **Returning:** {self.date_end}\n\n"
                    f"Please contact the **Overseer of Staff**, **Community Manager**, "
                    f"or **Creators** to ask why it was denied."
                )
                await submitter.send(embed=dm_embed)
            except discord.Forbidden:
                pass

        await interaction.response.send_message(
            "❌ Inactivity notice denied. The submitter has been notified via DM.",
            ephemeral=True
        )


# ── Cog ───────────────────────────────────────────────────────────────────────

class InactivityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="inactivitynotice",
        description="Submit an inactivity notice for staff review."
    )
    @app_commands.describe(
        start_month="Month you go inactive (e.g. July)",
        start_day="Day you go inactive (e.g. 10)",
        start_year="Year you go inactive (e.g. 2026)",
        end_month="Month you return (e.g. July)",
        end_day="Day you return (e.g. 20)",
        end_year="Year you return (e.g. 2026)",
        reason="Reason for inactivity"
    )
    async def inactivitynotice(self, interaction: discord.Interaction,
                                start_month: str, start_day: str, start_year: str,
                                end_month: str, end_day: str, end_year: str,
                                reason: str):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user

        # ── Staff only ────────────────────────────────────────────────────────
        if not is_staff(actor):
            return await interaction.followup.send(
                "❌ Only staff members may submit inactivity notices.",
                ephemeral=True
            )

        date_start = f"{start_month} {start_day}, {start_year}"
        date_end   = f"{end_month} {end_day}, {end_year}"

        # ── Send to review channel ────────────────────────────────────────────
        review_channel = interaction.guild.get_channel(REVIEW_CHANNEL_ID)
        if not review_channel:
            return await interaction.followup.send(
                "❌ Review channel not found. Contact an admin.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="📋 Inactivity Notice — Pending Review",
            color=discord.Color.yellow(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=actor.display_avatar.url)
        embed.add_field(name="Staff Member", value=actor.mention, inline=True)
        embed.add_field(name="Submitted", value=datetime.datetime.utcnow().strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="📅 Starting", value=date_start, inline=True)
        embed.add_field(name="📅 Returning", value=date_end, inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.set_footer(text="Use the buttons below to approve or deny")

        view = InactivityView(
            submitter_id=actor.id,
            date_start=date_start,
            date_end=date_end,
            reason=reason
        )

        await review_channel.send(embed=embed, view=view)

        # ── Confirm to submitter ──────────────────────────────────────────────
        confirm = discord.Embed(
            title="📨 Inactivity Notice Submitted",
            color=discord.Color.yellow(),
            description=(
                f"Your inactivity notice has been submitted for review.\n\n"
                f"📅 **Starting:** {date_start}\n"
                f"📅 **Returning:** {date_end}\n\n"
                f"You will be notified via DM once it has been reviewed."
            )
        )
        await interaction.followup.send(embed=confirm, ephemeral=True)


async def setup(bot):
    await bot.add_cog(InactivityCog(bot))
```[cite: 14]

---

### `moderation.py`

```python
"""
cogs/moderation.py — Full moderation suite (slash commands only)
"""
import discord
from discord import app_commands
from discord.ext import commands
import datetime
from discord.ext import tasks

# ── Role IDs ──────────────────────────────────────────────────────────────────
ROLE_STAFF    = 1458304077136920668
ROLE_ADMIN    = 1458303682180284681
ROLE_CM       = 1458302857764802683
ROLE_OVERSEER = 1458302854887510210
ROLE_CREATOR  = 1387649282139754587

# ── Log Channels ──────────────────────────────────────────────────────────────
WARN_LOG_CHANNEL         = 1575683752430928012
BAN_LOG_CHANNEL          = 1575683719274954842
KICK_LOG_CHANNEL         = 1575223771466436719
MUTE_LOG_CHANNEL         = 1575223771466436719
LOCKDOWN_LOG_CHANNEL     = 1575292898986172436
UNBAN_LOG_CHANNEL        = 1575292898986172436
STAFF_STRIKE_LOG_CHANNEL = 1575292898986172436

APPEAL_SERVER = "https://discord.gg/dQAbatSEcw"

LOCKDOWN_TEXT_CHANNELS = [
    1575220072505671921,
    1575220129246093434,
    1575220150200828105,
    1575220167900926163,
    1575220259898523740,
    1575220353880297492,
]
LOCKDOWN_VOICE_CHANNELS = [
    1575684643884114090,
    1575684690126446592,
    1575684718949568532,
]

ALL_STAFF_ROLES = [
    ROLE_STAFF,
    ROLE_ADMIN,
    ROLE_CM,
    ROLE_OVERSEER,
]


# ── Permission helpers ────────────────────────────────────────────────────────

def get_role_ids(member: discord.Member) -> set[int]:
    return {r.id for r in member.roles}


def is_staff(member: discord.Member) -> bool:
    return bool(get_role_ids(member) & {ROLE_STAFF, ROLE_ADMIN, ROLE_CM, ROLE_OVERSEER, ROLE_CREATOR})


def is_admin(member: discord.Member) -> bool:
    return bool(get_role_ids(member) & {ROLE_ADMIN, ROLE_CM, ROLE_OVERSEER, ROLE_CREATOR})


def is_head(member: discord.Member) -> bool:
    return bool(get_role_ids(member) & {ROLE_CM, ROLE_OVERSEER, ROLE_CREATOR})


def parse_duration(duration: str) -> datetime.timedelta | None:
    duration = duration.lower().strip()
    try:
        if duration.endswith("m"):
            return datetime.timedelta(minutes=int(duration[:-1]))
        elif duration.endswith("h"):
            return datetime.timedelta(hours=int(duration[:-1]))
        elif duration.endswith("d"):
            return datetime.timedelta(days=int(duration[:-1]))
    except ValueError:
        pass
    return None


def format_evidence(evidence: str, attachments: list) -> str:
    parts = []
    if evidence and evidence != "None provided":
        parts.append(evidence)
    for att in attachments:
        parts.append(att.url)
    return "\n".join(parts) if parts else "None provided"


# ── Clear Warns Dropdown ──────────────────────────────────────────────────────

class WarnSelect(discord.ui.Select):
    def __init__(self, warns: list, user: discord.Member, bot):
        self.warn_list = warns
        self.target    = user
        self.bot       = bot

        options = [
            discord.SelectOption(
                label=f"Warning {i + 1} — {str(w.get('created_at', ''))[:10]}",
                description=w["reason"][:100],
                value=str(i)
            )
            for i, w in enumerate(warns[:24])
        ]
        options.insert(0, discord.SelectOption(
            label="⚠️ Clear ALL warnings",
            description="Remove every warning for this user",
            value="all"
        ))

        super().__init__(
            placeholder="Select a warning to remove...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        if self.values[0] == "all":
            removed = await self.bot.db.clear_warns(str(self.target.id), str(guild.id))
            await interaction.followup.send(
                f"✅ Cleared all **{removed}** warning(s) from {self.target.mention}.",
                ephemeral=True
            )
        else:
            index   = int(self.values[0])
            warn    = self.warn_list[index]
            removed = await self.bot.db.delete_warn_by_index(
                str(self.target.id), str(guild.id), index
            )
            if removed:
                await interaction.followup.send(
                    f"✅ Removed warning {index + 1} from {self.target.mention}:\n"
                    f"**Reason:** {warn['reason']}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send("❌ Could not remove that warning.", ephemeral=True)

        for item in self.view.children:
            item.disabled = True
        await interaction.message.edit(view=self.view)


class WarnSelectView(discord.ui.View):
    def __init__(self, warns: list, user: discord.Member, bot):
        super().__init__(timeout=60)
        self.add_item(WarnSelect(warns, user, bot))


# ── Cog ───────────────────────────────────────────────────────────────────────

class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_unbans.start()

    def cog_unload(self):
        self.check_unbans.cancel()

    # ── Auto unban ────────────────────────────────────────────────────────────

    @tasks.loop(minutes=30)
    async def check_unbans(self):
        await self.bot.wait_until_ready()
        try:
            expired = await self.bot.db.get_expired_temp_bans()
            for ban in expired:
                guild = self.bot.get_guild(int(ban["guild_id"]))
                if not guild:
                    continue
                try:
                    user = await self.bot.fetch_user(int(ban["user_id"]))
                    await guild.unban(user, reason="Temporary ban expired")
                    await self.bot.db.mark_temp_ban_expired(ban["id"])
                    try:
                        dm = discord.Embed(
                            title="✅ You Have Been Unbanned",
                            color=discord.Color.green(),
                            timestamp=discord.utils.utcnow()
                        )
                        dm.description = (
                            f"Your temporary ban from **Afternight Legacies** has expired.\n\n"
                            f"You may rejoin the server. Please follow the rules.\n\n"
                            f"If you believe your ban was unfair:\n{APPEAL_SERVER}"
                        )
                        await user.send(embed=dm)
                    except discord.Forbidden:
                        pass
                    log_channel = guild.get_channel(BAN_LOG_CHANNEL)
                    if log_channel:
                        e = discord.Embed(
                            title="✅ Temp Ban Expired",
                            color=discord.Color.green(),
                            timestamp=discord.utils.utcnow()
                        )
                        e.add_field(name="Discord ID", value=f"{user.mention} (`{user.id}`)", inline=False)
                        e.add_field(name="Reason",     value="Temporary ban duration expired.", inline=False)
                        await log_channel.send(embed=e)
                except Exception:
                    pass
        except Exception:
            pass

    @check_unbans.before_loop
    async def before_check_unbans(self):
        await self.bot.wait_until_ready()

    # ── /warn ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="warn", description="Warn a community member.")
    @app_commands.describe(
        user="The member to warn",
        reason="Reason for the warning",
        evidence="Evidence link(s) — separate multiple with commas",
        attachment1="Evidence attachment (optional)",
        attachment2="Second evidence attachment (optional)"
    )
    async def warn(self, interaction: discord.Interaction,
                   user: discord.Member, reason: str,
                   evidence: str = "None provided",
                   attachment1: discord.Attachment = None,
                   attachment2: discord.Attachment = None):
        await interaction.response.defer()

        actor = interaction.user
        if not is_staff(actor):
            return await interaction.followup.send("❌ Only staff members may warn.", ephemeral=True)
        if user.bot:
            return await interaction.followup.send("❌ You cannot warn a bot.", ephemeral=True)
        if user == actor:
            return await interaction.followup.send("❌ You cannot warn yourself.", ephemeral=True)

        attachments   = [a for a in [attachment1, attachment2] if a]
        evidence_full = format_evidence(evidence, attachments)

        guild = interaction.guild
        await self.bot.db.add_warn(str(user.id), str(guild.id), reason, evidence_full, str(actor.id))
        warns      = await self.bot.db.get_warns(str(user.id), str(guild.id))
        warn_count = len(warns)

        log_embed = discord.Embed(title="⚠️ Warning Issued", color=discord.Color.yellow(), timestamp=discord.utils.utcnow())
        log_embed.set_thumbnail(url=user.display_avatar.url)
        log_embed.add_field(name="Discord ID",     value=f"{user.mention} (`{user.id}`)", inline=False)
        log_embed.add_field(name="Reason",         value=reason,                          inline=False)
        log_embed.add_field(name="Evidence",       value=evidence_full,                   inline=False)
        log_embed.add_field(name="Warned By",      value=f"{actor.mention} (`{actor.id}`)", inline=True)
        log_embed.add_field(name="Total Warnings", value=f"**{warn_count}** warning(s)",  inline=True)
        log_embed.set_footer(text=f"User ID: {user.id}")

        if warn_count > 1:
            prev_text = ""
            for i, w in enumerate(warns[:-1], 1):
                date = str(w.get("created_at", ""))[:10]
                prev_text += f"**{i}.** {w['reason']} *({date})*\n"
            log_embed.add_field(name=f"Previous Warnings ({warn_count - 1})", value=prev_text[:1024], inline=False)

        log_channel = guild.get_channel(WARN_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        confirm = discord.Embed(title="✅ Warning Issued", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        confirm.add_field(name="Member",         value=user.mention,    inline=True)
        confirm.add_field(name="Reason",         value=reason,          inline=True)
        confirm.add_field(name="Total Warnings", value=f"{warn_count}", inline=True)
        await interaction.followup.send(embed=confirm)

        try:
            dm = discord.Embed(title="⚠️ You Have Been Warned", color=discord.Color.yellow(), timestamp=discord.utils.utcnow())
            dm.description = (
                f"You have been warned in **Afternight Legacies** for **{reason}**.\n\n"
                f"If this is a mistake open a ticket:\n{APPEAL_SERVER}"
            )
            dm.set_footer(text="Afternight Moderation")
            await user.send(embed=dm)
        except discord.Forbidden:
            pass

    # ── /viewwarns ────────────────────────────────────────────────────────────

    @app_commands.command(name="viewwarns", description="View warnings for a member.")
    @app_commands.describe(user="The member to check")
    async def viewwarns(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer()

        if not is_staff(interaction.user):
            return await interaction.followup.send("❌ Only staff may view warnings.", ephemeral=True)

        guild = interaction.guild
        warns = await self.bot.db.get_warns(str(user.id), str(guild.id))
        count = len(warns)

        embed = discord.Embed(
            title=f"⚠️ Warnings — {user.display_name}",
            color=discord.Color.yellow() if count > 0 else discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Total Warnings", value=f"**{count}**", inline=True)
        embed.add_field(name="Discord ID",     value=f"`{user.id}`", inline=True)

        if warns:
            for i, w in enumerate(warns, 1):
                date       = str(w.get("created_at", ""))[:10]
                issuer     = guild.get_member(int(w["warned_by"]))
                issuer_str = issuer.display_name if issuer else f"ID: {w['warned_by']}"
                embed.add_field(
                    name=f"Warning {i} — {date}",
                    value=f"**Reason:** {w['reason']}\n**Evidence:** {w.get('evidence', 'None')}\n**By:** {issuer_str}",
                    inline=False
                )
        else:
            embed.add_field(name="No Warnings", value="This member has no warnings.", inline=False)

        embed.set_footer(text=f"User ID: {user.id}")
        await interaction.followup.send(embed=embed)

    # ── /clearwarns ───────────────────────────────────────────────────────────

    @app_commands.command(name="clearwarns", description="Clear one or all warnings for a member.")
    @app_commands.describe(user="The member whose warnings to manage")
    async def clearwarns(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)

        if not is_admin(interaction.user):
            return await interaction.followup.send("❌ Only Admins or above may clear warnings.", ephemeral=True)

        guild = interaction.guild
        warns = await self.bot.db.get_warns(str(user.id), str(guild.id))

        if not warns:
            return await interaction.followup.send(f"❌ {user.mention} has no warnings.", ephemeral=True)

        embed = discord.Embed(
            title=f"🗑️ Clear Warnings — {user.display_name}",
            description=f"{user.mention} has **{len(warns)}** warning(s). Select which to remove:",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        view = WarnSelectView(warns, user, self.bot)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    # ── /ban ──────────────────────────────────────────────────────────────────

    @app_commands.command(name="ban", description="Ban a member from the server.")
    @app_commands.describe(
        user="The member to ban",
        reason="Reason for the ban",
        evidence="Evidence link(s)",
        temporary="Is this a temporary ban?",
        unban_date="If temporary, when they get unbanned (e.g. July 20 2026)",
        delete_days="Number of days of messages to delete (0-7)",
        attachment1="Evidence attachment (optional)",
        attachment2="Second evidence attachment (optional)"
    )
    @app_commands.choices(temporary=[
        app_commands.Choice(name="Yes — Temporary Ban", value="yes"),
        app_commands.Choice(name="No — Permanent Ban",  value="no"),
    ])
    async def ban(self, interaction: discord.Interaction,
                  user: discord.Member, reason: str, temporary: str,
                  evidence: str = "None provided", unban_date: str = None,
                  delete_days: int = 0,
                  attachment1: discord.Attachment = None,
                  attachment2: discord.Attachment = None):
        await interaction.response.defer()

        actor = interaction.user
        if not is_admin(actor):
            return await interaction.followup.send("❌ Only Admins or above may ban.", ephemeral=True)
        if user == actor:
            return await interaction.followup.send("❌ You cannot ban yourself.", ephemeral=True)
        if user.top_role >= interaction.guild.me.top_role:
            return await interaction.followup.send("❌ I cannot ban this user.", ephemeral=True)
        if temporary == "yes" and not unban_date:
            return await interaction.followup.send("❌ Provide an unban date for a temp ban.", ephemeral=True)
        if not 0 <= delete_days <= 7:
            return await interaction.followup.send("❌ Delete days must be 0-7.", ephemeral=True)

        attachments   = [a for a in [attachment1, attachment2] if a]
        evidence_full = format_evidence(evidence, attachments)
        guild         = interaction.guild
        is_temp       = temporary == "yes"
        ban_type_str  = f"Temporary — Unban: **{unban_date}**" if is_temp else "Permanent"

        try:
            dm = discord.Embed(title="🔨 You Have Been Banned", color=discord.Color.red(), timestamp=discord.utils.utcnow())
            dm.description = (
                f"You have been **{'temporarily' if is_temp else 'permanently'} banned** from **Afternight Legacies**.\n\n"
                f"**Reason:** {reason}\n"
            )
            if is_temp:
                dm.description += f"**Unban Date:** {unban_date}\n\n"
            else:
                dm.description += "\n"
            dm.description += f"Appeal here:\n{APPEAL_SERVER}"
            dm.set_footer(text="Afternight Moderation")
            await user.send(embed=dm)
        except discord.Forbidden:
            pass

        await guild.ban(user, reason=f"{reason} | Banned by {actor}", delete_message_days=delete_days)

        if is_temp:
            await self.bot.db.add_temp_ban(str(user.id), str(guild.id), unban_date, reason, str(actor.id))

        log_embed = discord.Embed(title="🔨 Member Banned", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        log_embed.set_thumbnail(url=user.display_avatar.url)
        log_embed.add_field(name="Discord ID",        value=f"{user.mention} (`{user.id}`)", inline=False)
        log_embed.add_field(name="Reason",            value=reason,                          inline=False)
        log_embed.add_field(name="Temporary Or Perm", value=ban_type_str,                    inline=False)
        log_embed.add_field(name="Evidence",          value=evidence_full,                   inline=False)
        log_embed.add_field(name="Banned By",         value=f"{actor.mention} (`{actor.id}`)", inline=True)
        log_embed.add_field(name="Messages Deleted",  value=f"{delete_days} day(s)",         inline=True)
        log_embed.set_footer(text=f"User ID: {user.id}")

        log_channel = guild.get_channel(BAN_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        confirm = discord.Embed(title="✅ Member Banned", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        confirm.add_field(name="Member", value=user.mention,  inline=True)
        confirm.add_field(name="Reason", value=reason,        inline=True)
        confirm.add_field(name="Type",   value=ban_type_str,  inline=True)
        await interaction.followup.send(embed=confirm)

    # ── /kick ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="kick", description="Kick a member from the server.")
    @app_commands.describe(
        user="The member to kick",
        reason="Reason for the kick",
        evidence="Evidence link(s)",
        attachment1="Evidence attachment (optional)",
        attachment2="Second evidence attachment (optional)"
    )
    async def kick(self, interaction: discord.Interaction,
                   user: discord.Member, reason: str,
                   evidence: str = "None provided",
                   attachment1: discord.Attachment = None,
                   attachment2: discord.Attachment = None):
        await interaction.response.defer()

        actor = interaction.user
        if not is_staff(actor):
            return await interaction.followup.send("❌ Only staff may kick.", ephemeral=True)
        if user == actor:
            return await interaction.followup.send("❌ You cannot kick yourself.", ephemeral=True)
        if user.top_role >= interaction.guild.me.top_role:
            return await interaction.followup.send("❌ I cannot kick this user.", ephemeral=True)

        attachments   = [a for a in [attachment1, attachment2] if a]
        evidence_full = format_evidence(evidence, attachments)
        guild         = interaction.guild

        try:
            dm = discord.Embed(title="👢 You Have Been Kicked", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
            dm.description = (
                f"You have been **kicked** from **Afternight Legacies**.\n\n"
                f"**Reason:** {reason}\n\nAppeal here:\n{APPEAL_SERVER}"
            )
            dm.set_footer(text="Afternight Moderation")
            await user.send(embed=dm)
        except discord.Forbidden:
            pass

        await guild.kick(user, reason=f"{reason} | Kicked by {actor}")

        log_embed = discord.Embed(title="👢 Member Kicked", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        log_embed.set_thumbnail(url=user.display_avatar.url)
        log_embed.add_field(name="Discord ID", value=f"{user.mention} (`{user.id}`)", inline=False)
        log_embed.add_field(name="Reason",     value=reason,                          inline=False)
        log_embed.add_field(name="Evidence",   value=evidence_full,                   inline=False)
        log_embed.add_field(name="Kicked By",  value=f"{actor.mention} (`{actor.id}`)", inline=False)
        log_embed.set_footer(text=f"User ID: {user.id}")

        log_channel = guild.get_channel(KICK_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        confirm = discord.Embed(title="✅ Member Kicked", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        confirm.add_field(name="Member", value=user.mention, inline=True)
        confirm.add_field(name="Reason", value=reason,       inline=True)
        await interaction.followup.send(embed=confirm)

    # ── /mute ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="mute", description="Timeout (mute) a member.")
    @app_commands.describe(
        user="The member to mute",
        reason="Reason",
        duration="Duration (10m, 1h, 1d — max 28 days)",
        evidence="Evidence link(s)",
        attachment1="Evidence attachment (optional)",
        attachment2="Second evidence attachment (optional)"
    )
    async def mute(self, interaction: discord.Interaction,
                   user: discord.Member, reason: str, duration: str,
                   evidence: str = "None provided",
                   attachment1: discord.Attachment = None,
                   attachment2: discord.Attachment = None):
        await interaction.response.defer()

        actor = interaction.user
        if not is_staff(actor):
            return await interaction.followup.send("❌ Only staff may mute.", ephemeral=True)
        if user == actor:
            return await interaction.followup.send("❌ You cannot mute yourself.", ephemeral=True)
        if user.top_role >= interaction.guild.me.top_role:
            return await interaction.followup.send("❌ I cannot mute this user.", ephemeral=True)

        delta = parse_duration(duration)
        if not delta:
            return await interaction.followup.send("❌ Invalid duration. Use `10m`, `1h`, `1d` etc.", ephemeral=True)
        if delta > datetime.timedelta(days=28):
            return await interaction.followup.send("❌ Maximum mute duration is 28 days.", ephemeral=True)

        attachments   = [a for a in [attachment1, attachment2] if a]
        evidence_full = format_evidence(evidence, attachments)

        until     = discord.utils.utcnow() + delta
        until_str = until.strftime("%B %d, %Y at %I:%M %p UTC")

        try:
            dm = discord.Embed(title="🔇 You Have Been Muted", color=discord.Color.dark_grey(), timestamp=discord.utils.utcnow())
            dm.description = (
                f"You have been **muted** in **Afternight Legacies**.\n\n"
                f"**Reason:** {reason}\n**Duration:** {duration}\n**Unmuted:** {until_str}\n\n"
                f"Appeal here:\n{APPEAL_SERVER}"
            )
            dm.set_footer(text="Afternight Moderation")
            await user.send(embed=dm)
        except discord.Forbidden:
            pass

        await user.timeout(until, reason=f"{reason} | Muted by {actor}")

        log_embed = discord.Embed(title="🔇 Member Muted", color=discord.Color.dark_grey(), timestamp=discord.utils.utcnow())
        log_embed.set_thumbnail(url=user.display_avatar.url)
        log_embed.add_field(name="Discord ID", value=f"{user.mention} (`{user.id}`)", inline=False)
        log_embed.add_field(name="Reason",     value=reason,                          inline=False)
        log_embed.add_field(name="Duration",   value=duration,                        inline=True)
        log_embed.add_field(name="Unmuted",    value=until_str,                       inline=True)
        log_embed.add_field(name="Evidence",   value=evidence_full,                   inline=False)
        log_embed.add_field(name="Muted By",   value=f"{actor.mention} (`{actor.id}`)", inline=False)
        log_embed.set_footer(text=f"User ID: {user.id}")

        log_channel = interaction.guild.get_channel(MUTE_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        confirm = discord.Embed(title="✅ Member Muted", color=discord.Color.dark_grey(), timestamp=discord.utils.utcnow())
        confirm.add_field(name="Member",   value=user.mention, inline=True)
        confirm.add_field(name="Duration", value=duration,     inline=True)
        confirm.add_field(name="Reason",   value=reason,       inline=True)
        await interaction.followup.send(embed=confirm)

    # ── /unmute ───────────────────────────────────────────────────────────────

    @app_commands.command(name="unmute", description="Remove a timeout from a member.")
    @app_commands.describe(user="The member to unmute", reason="Reason (optional)")
    async def unmute(self, interaction: discord.Interaction,
                     user: discord.Member, reason: str = "Mute lifted by staff"):
        await interaction.response.defer()

        if not is_staff(interaction.user):
            return await interaction.followup.send("❌ Only staff may unmute.", ephemeral=True)
        if not user.is_timed_out():
            return await interaction.followup.send(f"❌ {user.mention} is not muted.", ephemeral=True)

        actor = interaction.user
        await user.timeout(None, reason=f"{reason} | Unmuted by {actor}")

        try:
            dm = discord.Embed(title="🔊 You Have Been Unmuted", color=discord.Color.green(), timestamp=discord.utils.utcnow())
            dm.description = f"Your mute in **Afternight Legacies** has been lifted.\n\n**Reason:** {reason}"
            dm.set_footer(text="Afternight Moderation")
            await user.send(embed=dm)
        except discord.Forbidden:
            pass

        log_embed = discord.Embed(title="🔊 Member Unmuted", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        log_embed.set_thumbnail(url=user.display_avatar.url)
        log_embed.add_field(name="Discord ID", value=f"{user.mention} (`{user.id}`)", inline=False)
        log_embed.add_field(name="Reason",     value=reason,                          inline=False)
        log_embed.add_field(name="Unmuted By", value=f"{actor.mention} (`{actor.id}`)", inline=False)
        log_embed.set_footer(text=f"User ID: {user.id}")

        log_channel = interaction.guild.get_channel(MUTE_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        confirm = discord.Embed(title="✅ Member Unmuted", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        confirm.add_field(name="Member", value=user.mention, inline=True)
        confirm.add_field(name="Reason", value=reason,       inline=True)
        await interaction.followup.send(embed=confirm)

    # ── /unban ────────────────────────────────────────────────────────────────

    @app_commands.command(name="unban", description="Unban a user from the server.")
    @app_commands.describe(user_id="The Discord ID to unban", reason="Reason")
    async def unban(self, interaction: discord.Interaction,
                    user_id: str, reason: str = "No reason provided"):
        await interaction.response.defer()

        if not is_admin(interaction.user):
            return await interaction.followup.send("❌ Only Admins or above may unban.", ephemeral=True)

        guild = interaction.guild
        try:
            user = await self.bot.fetch_user(int(user_id))
        except (ValueError, discord.NotFound):
            return await interaction.followup.send("❌ Could not find that user ID.", ephemeral=True)

        try:
            await guild.unban(user, reason=f"{reason} | Unbanned by {interaction.user}")
        except discord.NotFound:
            return await interaction.followup.send(f"❌ {user} is not banned.", ephemeral=True)

        try:
            expired = await self.bot.db.get_expired_temp_bans()
            for ban in expired:
                if ban["user_id"] == str(user.id) and ban["guild_id"] == str(guild.id):
                    await self.bot.db.mark_temp_ban_expired(ban["id"])
        except Exception:
            pass

        try:
            dm = discord.Embed(title="✅ You Have Been Unbanned", color=discord.Color.green(), timestamp=discord.utils.utcnow())
            dm.description = f"You have been **unbanned** from **Afternight Legacies**.\n\n**Reason:** {reason}"
            dm.set_footer(text="Afternight Moderation")
            await user.send(embed=dm)
        except discord.Forbidden:
            pass

        log_embed = discord.Embed(title="✅ Member Unbanned", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        log_embed.add_field(name="Discord ID",  value=f"{user.mention} (`{user.id}`)", inline=False)
        log_embed.add_field(name="Reason",      value=reason,                          inline=False)
        log_embed.add_field(name="Unbanned By", value=interaction.user.mention,        inline=False)
        log_embed.set_footer(text=f"User ID: {user.id}")

        log_channel = guild.get_channel(UNBAN_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        confirm = discord.Embed(title="✅ Member Unbanned", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        confirm.add_field(name="User",   value=f"{user} (`{user.id}`)", inline=True)
        confirm.add_field(name="Reason", value=reason,                  inline=True)
        await interaction.followup.send(embed=confirm)

    # ── /lockdownserver ───────────────────────────────────────────────────────

    @app_commands.command(name="lockdownserver", description="Lock specific channels.")
    @app_commands.describe(reason="Reason for the lockdown")
    async def lockdownserver(self, interaction: discord.Interaction,
                              reason: str = "No reason provided"):
        await interaction.response.defer()

        if not is_head(interaction.user):
            return await interaction.followup.send(
                "❌ Only CM/Overseer/Creators may lockdown.", ephemeral=True
            )

        actor      = interaction.user
        guild      = interaction.guild
        staff_role = guild.get_role(ROLE_STAFF)
        admin_role = guild.get_role(ROLE_ADMIN)
        locked     = 0
        failed     = 0

        lockdown_embed = discord.Embed(
            title="🔒 Server Lockdown",
            description=(
                f"The server is currently under **lockdown**.\n\n"
                f"**Reason:** {reason}\n\n"
                f"Only staff members may speak during this time."
            ),
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        lockdown_embed.set_footer(text=f"Lockdown initiated by {actor.display_name}")

        for channel_id in LOCKDOWN_TEXT_CHANNELS:
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            try:
                ow = channel.overwrites_for(guild.default_role)
                ow.send_messages = False
                await channel.set_permissions(guild.default_role, overwrite=ow, reason=f"Lockdown by {actor}: {reason}")
                for role in [staff_role, admin_role]:
                    if role:
                        sow = channel.overwrites_for(role)
                        sow.send_messages = True
                        await channel.set_permissions(role, overwrite=sow, reason="Lockdown — staff override")
                await channel.send(embed=lockdown_embed)
                locked += 1
            except Exception:
                failed += 1

        for channel_id in LOCKDOWN_VOICE_CHANNELS:
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            try:
                ow = channel.overwrites_for(guild.default_role)
                ow.connect = False
                await channel.set_permissions(guild.default_role, overwrite=ow, reason=f"Lockdown by {actor}: {reason}")
                for role in [staff_role, admin_role]:
                    if role:
                        sow = channel.overwrites_for(role)
                        sow.connect = True
                        await channel.set_permissions(role, overwrite=sow, reason="Lockdown — staff override")
                locked += 1
            except Exception:
                failed += 1

        log_embed = discord.Embed(title="🔒 Server Lockdown Initiated", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        log_embed.add_field(name="By",     value=actor.mention,          inline=True)
        log_embed.add_field(name="Reason", value=reason,                 inline=True)
        log_embed.add_field(name="Locked", value=f"{locked} channel(s)", inline=True)
        log_channel = guild.get_channel(LOCKDOWN_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        confirm = discord.Embed(title="🔒 Server Locked Down", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        confirm.add_field(name="Reason", value=reason,              inline=True)
        confirm.add_field(name="Locked", value=f"{locked} channels", inline=True)
        await interaction.followup.send(embed=confirm)

    # ── /unlockdownserver ─────────────────────────────────────────────────────

    @app_commands.command(name="unlockdownserver", description="Unlock all channels after a lockdown.")
    @app_commands.describe(reason="Reason for ending the lockdown")
    async def unlockdownserver(self, interaction: discord.Interaction,
                                reason: str = "Lockdown lifted"):
        await interaction.response.defer()

        if not is_head(interaction.user):
            return await interaction.followup.send(
                "❌ Only CM/Overseer/Creators may unlock.", ephemeral=True
            )

        actor    = interaction.user
        guild    = interaction.guild
        unlocked = 0
        failed   = 0

        unlock_embed = discord.Embed(
            title="🔓 Server Unlocked",
            description=(
                f"The server lockdown has been **lifted**.\n\n"
                f"**Reason:** {reason}\n\n"
                f"You may now speak freely. Please follow the server rules."
            ),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        unlock_embed.set_footer(text=f"Unlocked by {actor.display_name}")

        for channel_id in LOCKDOWN_TEXT_CHANNELS:
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            try:
                ow = channel.overwrites_for(guild.default_role)
                ow.send_messages = None
                await channel.set_permissions(guild.default_role, overwrite=ow, reason=f"Lockdown lifted by {actor}: {reason}")
                msg = await channel.send(embed=unlock_embed)
                await msg.delete(delay=15)
                unlocked += 1
            except Exception:
                failed += 1

        for channel_id in LOCKDOWN_VOICE_CHANNELS:
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            try:
                ow = channel.overwrites_for(guild.default_role)
                ow.connect = None
                await channel.set_permissions(guild.default_role, overwrite=ow, reason=f"Lockdown lifted by {actor}: {reason}")
                unlocked += 1
            except Exception:
                failed += 1

        log_embed = discord.Embed(title="🔓 Server Lockdown Lifted", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        log_embed.add_field(name="By",       value=actor.mention,            inline=True)
        log_embed.add_field(name="Reason",   value=reason,                   inline=True)
        log_embed.add_field(name="Unlocked", value=f"{unlocked} channel(s)", inline=True)
        log_channel = guild.get_channel(LOCKDOWN_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        confirm = discord.Embed(title="🔓 Server Unlocked", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        confirm.add_field(name="Reason",   value=reason,               inline=True)
        confirm.add_field(name="Unlocked", value=f"{unlocked} channels", inline=True)
        await interaction.followup.send(embed=confirm)

    # ── /staffstrike ──────────────────────────────────────────────────────────

    @app_commands.command(name="staffstrike", description="Issue a strike to a staff member.")
    @app_commands.describe(user="The staff member", reason="Reason", evidence="Evidence (optional)")
    async def staffstrike(self, interaction: discord.Interaction,
                          user: discord.Member, reason: str,
                          evidence: str = "None provided"):
        await interaction.response.defer()

        actor = interaction.user
        if not is_head(actor):
            return await interaction.followup.send("❌ Only CM/Overseer/Creators may strike staff.", ephemeral=True)
        if not is_staff(user):
            return await interaction.followup.send(f"❌ {user.mention} is not a staff member.", ephemeral=True)
        if user == actor:
            return await interaction.followup.send("❌ You cannot strike yourself.", ephemeral=True)

        guild = interaction.guild
        await self.bot.db.add_staff_strike(str(user.id), str(guild.id), reason, evidence, str(actor.id))
        strikes      = await self.bot.db.get_staff_strikes(str(user.id), str(guild.id))
        strike_count = len(strikes)

        log_embed = discord.Embed(title="⚡ Staff Strike Issued", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        log_embed.set_thumbnail(url=user.display_avatar.url)
        log_embed.add_field(name="Staff Member",  value=f"{user.mention} (`{user.id}`)", inline=False)
        log_embed.add_field(name="Reason",        value=reason,                          inline=False)
        log_embed.add_field(name="Evidence",      value=evidence,                        inline=False)
        log_embed.add_field(name="Issued By",     value=f"{actor.mention} (`{actor.id}`)", inline=True)
        log_embed.add_field(name="Total Strikes", value=f"**{strike_count}/3**",         inline=True)
        log_embed.set_footer(text=f"User ID: {user.id}")

        if strike_count > 1:
            prev_text = ""
            for i, s in enumerate(strikes[:-1], 1):
                date = str(s.get("created_at", ""))[:10]
                prev_text += f"**{i}.** {s['reason']} *({date})*\n"
            log_embed.add_field(name=f"Previous Strikes ({strike_count - 1})", value=prev_text[:1024], inline=False)

        log_channel = guild.get_channel(STAFF_STRIKE_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        try:
            dm = discord.Embed(title="⚡ You Have Received a Staff Strike", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
            dm.description = (
                f"You have received a **staff strike** in **Afternight Legacies**.\n\n"
                f"**Reason:** {reason}\n**Strike Count:** {strike_count}/3\n\n"
            )
            if strike_count >= 3:
                dm.description += "⚠️ You have reached **3/3 strikes** and have been **automatically removed from staff**."
            else:
                dm.description += "Reaching **3 strikes** will result in automatic removal from staff."
            dm.set_footer(text="Afternight Staff System")
            await user.send(embed=dm)
        except discord.Forbidden:
            pass

        if strike_count >= 3:
            roles_removed = []
            for role_id in ALL_STAFF_ROLES:
                role = guild.get_role(role_id)
                if role and role in user.roles:
                    roles_removed.append(role)
            if roles_removed:
                await user.remove_roles(*roles_removed, reason="Auto-fired: 3 staff strikes")
            fire_embed = discord.Embed(
                title="🔥 Staff Member Auto-Fired",
                description=(
                    f"{user.mention} has reached **3/3 staff strikes** and has been automatically removed.\n\n"
                    f"**Roles Removed:** {', '.join(r.name for r in roles_removed) or 'None'}"
                ),
                color=discord.Color.dark_red(),
                timestamp=discord.utils.utcnow()
            )
            if log_channel:
                await log_channel.send(embed=fire_embed)

        confirm = discord.Embed(title="✅ Staff Strike Issued", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        confirm.add_field(name="Staff Member",  value=user.mention,        inline=True)
        confirm.add_field(name="Strike Count",  value=f"{strike_count}/3", inline=True)
        confirm.add_field(name="Reason",        value=reason,              inline=False)
        if strike_count >= 3:
            confirm.add_field(name="⚠️ Auto Action", value="Staff member has been fired.", inline=False)
        await interaction.followup.send(embed=confirm)

    # ── /viewstaffstrikes ─────────────────────────────────────────────────────

    @app_commands.command(name="viewstaffstrikes", description="View staff strikes for a staff member.")
    @app_commands.describe(user="The staff member to check")
    async def viewstaffstrikes(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer()

        if not is_head(interaction.user):
            return await interaction.followup.send("❌ Only CM/Overseer/Creators may view staff strikes.", ephemeral=True)

        guild   = interaction.guild
        strikes = await self.bot.db.get_staff_strikes(str(user.id), str(guild.id))
        count   = len(strikes)

        embed = discord.Embed(
            title=f"⚡ Staff Strikes — {user.display_name}",
            color=discord.Color.orange() if count > 0 else discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Total Strikes", value=f"**{count}/3**", inline=True)
        embed.add_field(name="Discord ID",    value=f"`{user.id}`",   inline=True)

        if strikes:
            for i, s in enumerate(strikes, 1):
                date       = str(s.get("created_at", ""))[:10]
                issuer     = guild.get_member(int(s["issued_by"]))
                issuer_str = issuer.display_name if issuer else f"ID: {s['issued_by']}"
                embed.add_field(
                    name=f"Strike {i} — {date}",
                    value=f"**Reason:** {s['reason']}\n**Evidence:** {s.get('evidence', 'None')}\n**By:** {issuer_str}",
                    inline=False
                )
        else:
            embed.add_field(name="No Strikes", value="This staff member has no strikes.", inline=False)

        embed.set_footer(text=f"User ID: {user.id}")
        await interaction.followup.send(embed=embed)

    # ── /clearstaffstrikes ────────────────────────────────────────────────────

    @app_commands.command(name="clearstaffstrikes", description="Clear all staff strikes for a staff member.")
    @app_commands.describe(user="The staff member whose strikes to clear")
    async def clearstaffstrikes(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)

        if not is_head(interaction.user):
            return await interaction.followup.send("❌ Only CM/Overseer/Creators may clear staff strikes.", ephemeral=True)

        guild   = interaction.guild
        removed = await self.bot.db.clear_staff_strikes(str(user.id), str(guild.id))

        embed = discord.Embed(
            title="✅ Staff Strikes Cleared",
            description=f"Cleared **{removed}** strike(s) from {user.mention}.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        await interaction.followup.send(embed=embed)

        log_channel = guild.get_channel(STAFF_STRIKE_LOG_CHANNEL)
        if log_channel:
            e = discord.Embed(title="🗑️ Staff Strikes Cleared", color=discord.Color.green(), timestamp=discord.utils.utcnow())
            e.add_field(name="Staff Member", value=f"{user.mention} (`{user.id}`)", inline=True)
            e.add_field(name="Cleared By",   value=interaction.user.mention,        inline=True)
            e.add_field(name="Removed",      value=f"{removed} strike(s)",          inline=True)
            await log_channel.send(embed=e)


async def setup(bot):
    await bot.add_cog(ModerationCog(bot))
```[cite: 16]

---

### `suggestions.py`

```python
"""
cogs/suggestions.py — /suggest slash command
"""
import discord
from discord import app_commands
from discord.ext import commands
import datetime

SUGGESTION_CHANNEL_ID = 1575220167900926163


class SuggestionModal(discord.ui.Modal, title="Submit a Suggestion"):
    suggestion = discord.ui.TextInput(
        label="Your Suggestion",
        style=discord.TextStyle.long,
        placeholder="Describe your suggestion in detail...",
        min_length=10,
        max_length=1000
    )

    def __init__(self, attachments: list[discord.Attachment]):
        super().__init__()
        self.attachments = attachments

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        channel = interaction.guild.get_channel(SUGGESTION_CHANNEL_ID)
        if not channel:
            return await interaction.followup.send(
                "❌ Suggestion channel not found. Contact an admin.", ephemeral=True
            )

        author = interaction.user

        # ── Sort attachments ──────────────────────────────────────────────────
        image_attachments = []
        video_attachments = []
        for att in self.attachments:
            if att.content_type and att.content_type.startswith("image/"):
                image_attachments.append(att)
            elif att.content_type and att.content_type.startswith("video/"):
                video_attachments.append(att)

        # ── Main suggestion embed ─────────────────────────────────────────────
        embed = discord.Embed(
            description=f"## 💡 New Suggestion\n\n{self.suggestion.value}",
            color=discord.Color.from_rgb(88, 101, 242),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_author(
            name=author.display_name,
            icon_url=author.display_avatar.url
        )
        embed.set_footer(text=f"User ID: {author.id}")

        # First image goes into the main embed
        if image_attachments:
            embed.set_image(url=image_attachments[0].url)

        # ── Send main embed ───────────────────────────────────────────────────
        suggestion_msg = await channel.send(embed=embed)

        # ── Send second image as follow up embed ──────────────────────────────
        for att in image_attachments[1:]:
            extra = discord.Embed(color=discord.Color.from_rgb(88, 101, 242))
            extra.set_image(url=att.url)
            await channel.send(embed=extra)

        # ── Send videos as plain links ────────────────────────────────────────
        for att in video_attachments:
            await channel.send(content=f"🎥 **Video Reference:** {att.url}")

        # ── Add vote reactions ────────────────────────────────────────────────
        await suggestion_msg.add_reaction("👍")
        await suggestion_msg.add_reaction("👎")

        # ── Confirm to user ───────────────────────────────────────────────────
        confirm = discord.Embed(
            title="✅ Suggestion Submitted!",
            description=(
                f"Your suggestion has been sent to {channel.mention}.\n\n"
                f"Thank you for helping improve Afternight!"
            ),
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=confirm, ephemeral=True)


class SuggestionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="suggest",
        description="Submit a suggestion for Afternight."
    )
    @app_commands.describe(
        reference1="First image or video reference (optional)",
        reference2="Second image or video reference (optional)"
    )
    async def suggest(self, interaction: discord.Interaction,
                      reference1: discord.Attachment = None,
                      reference2: discord.Attachment = None):

        # ── Collect attachments ───────────────────────────────────────────────
        attachments = [a for a in [reference1, reference2] if a is not None]

        # ── Validate file types ───────────────────────────────────────────────
        for att in attachments:
            if att.content_type and not (
                att.content_type.startswith("image/") or
                att.content_type.startswith("video/")
            ):
                return await interaction.response.send_message(
                    f"❌ `{att.filename}` is not a valid image or video file.",
                    ephemeral=True
                )

            if att.size > 50 * 1024 * 1024:
                return await interaction.response.send_message(
                    f"❌ `{att.filename}` is too large. Max file size is 50MB.",
                    ephemeral=True
                )

        # ── Open the modal ────────────────────────────────────────────────────
        await interaction.response.send_modal(SuggestionModal(attachments=attachments))


async def setup(bot):
    await bot.add_cog(SuggestionCog(bot))
```[cite: 22]

---

### `testing.py`

```python
"""
cogs/testing.py — Auto-rank to Tester + /testingsession command
"""
import discord
from discord import app_commands
from discord.ext import commands
from utils.roblox import fetch_roblox_user
from utils.roblox_group import get_roblox_user_id, get_xcsrf_token, HEADERS
import aiohttp
import datetime
import os

# ── Config ────────────────────────────────────────────────────────────────────
TESTING_CHANNEL_ID    = 1575319593621258400
FEEDBACK_CHANNEL_ID   = 1575319889755906159
GAME_TESTER_ROLE_ID   = 1458302213368840458
LEGACIES_GROUP_ID     = 1024076883
TESTER_RANK           = 40

ALLOWED_ROLES: set[int] = {
    1458303507659624683,  # Programmer
    1387649282139754587,  # Creators
}

GAME_LINK = "https://www.roblox.com/games/92315559992414/Afternight-Legacies-TESTING"
COOKIE    = os.getenv("ROBLOX_SECURITY_COOKIE")

HEADERS_LEGACIES = {
    "Cookie": f".ROBLOSECURITY={COOKIE}",
    "Content-Type": "application/json",
}


# ── Roblox helpers ────────────────────────────────────────────────────────────

async def get_legacies_role_id(rank: int) -> int | None:
    """Get the roleId for a given rank in the Legacies group."""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://groups.roblox.com/v1/groups/{LEGACIES_GROUP_ID}/roles",
            headers=HEADERS_LEGACIES
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            for role in data.get("roles", []):
                if role["rank"] == rank:
                    return role["id"]
    return None


async def rank_to_tester(roblox_username: str) -> tuple[bool, str]:
    """Rank a user to Tester in the Legacies group."""
    if not COOKIE:
        return False, "ROBLOX_SECURITY_COOKIE is not set."

    # Get user ID
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://users.roblox.com/v1/usernames/users",
            json={"usernames": [roblox_username], "excludeBannedUsers": False},
            headers=HEADERS_LEGACIES
        ) as resp:
            if resp.status != 200:
                return False, f"Could not find Roblox user: `{roblox_username}`"
            data = await resp.json()
            users = data.get("data", [])
            if not users:
                return False, f"Roblox user `{roblox_username}` does not exist."
            user_id = users[0]["id"]

    # Get role ID for tester rank
    role_id = await get_legacies_role_id(TESTER_RANK)
    if not role_id:
        return False, "Could not find the Tester role in the Legacies group."

    # Get XCSRF token
    try:
        token = await get_xcsrf_token()
        headers = {**HEADERS_LEGACIES, "x-csrf-token": token}

        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f"https://groups.roblox.com/v1/groups/{LEGACIES_GROUP_ID}/users/{user_id}",
                headers=headers,
                json={"roleId": role_id}
            ) as resp:
                if resp.status == 200:
                    return True, f"✅ `{roblox_username}` has been ranked to **Tester** in Afternight Legacies."
                else:
                    error = await resp.json()
                    msg = error.get("errors", [{}])[0].get("message", "Unknown error")
                    return False, f"❌ Roblox API error: {msg}"

    except Exception as e:
        return False, f"❌ Exception: {str(e)}"


class TestingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── Auto-rank listener ────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id != TESTING_CHANNEL_ID:
            return
        if message.channel.id != TESTING_CHANNEL_ID:
            return

        # DEBUG - remove after testing
        print(f"[DEBUG] {message.author} roles: {[r.id for r in message.author.roles]}")
        print(f"[DEBUG] Looking for role: {GAME_TESTER_ROLE_ID}")
        print(f"[DEBUG] Tester role found: {message.guild.get_role(GAME_TESTER_ROLE_ID)}")

        # ── Prevent duplicate ranking ─────────────────────────────────────────────
        async for msg in message.channel.history(limit=100):
            if msg.author == self.bot.user and msg.reference:
                ref = msg.reference.resolved
                if ref and ref.author == message.author and "Tester Rank Granted" in (
                msg.embeds[0].title if msg.embeds else ""):
                    await message.reply(
                        "⚠️ You have already been ranked to Tester!",
                        delete_after=10
                    )
                    return

        # ── Only Game Testers can use this channel ────────────────────────────
        tester_role = message.guild.get_role(GAME_TESTER_ROLE_ID)
        if tester_role not in message.author.roles:
            await message.reply(
                "❌ Only Game Testers may submit their username here.",
                delete_after=10
            )
            return

        roblox_username = message.content.strip()

        # Basic validation — no spaces, reasonable length
        if " " in roblox_username or len(roblox_username) > 20 or len(roblox_username) < 1:
            await message.reply(
                "❌ Please send just your Roblox username with no spaces.",
                delete_after=10
            )
            return

        # Show typing indicator while we process
        async with message.channel.typing():
            roblox_data = await fetch_roblox_user(roblox_username)
            if not roblox_data:
                await message.reply(
                    f"❌ Could not find Roblox user `{roblox_username}`. "
                    "Please double check your username and try again.",
                    delete_after=15
                )
                return

            success, result_msg = await rank_to_tester(roblox_username)

        if success:
            embed = discord.Embed(
                title="🎮 Tester Rank Granted!",
                color=discord.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.set_thumbnail(url=roblox_data.get("avatar_url") or message.author.display_avatar.url)
            embed.add_field(name="Discord", value=message.author.mention, inline=True)
            embed.add_field(name="Roblox", value=f"`{roblox_username}`", inline=True)
            embed.add_field(
                name="Game Link",
                value=f"[Click to join]({GAME_LINK})",
                inline=False
            )
            embed.set_footer(text="Afternight Legacies Testing")
            await message.reply(embed=embed)
        else:
            await message.reply(f"❌ Failed to rank: {result_msg}", delete_after=15)

            # Rank them to tester
            success, result_msg = await rank_to_tester(roblox_username)

        if success:
            embed = discord.Embed(
                title="🎮 Tester Rank Granted!",
                color=discord.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.set_thumbnail(url=roblox_data.get("avatar_url") or message.author.display_avatar.url)
            embed.add_field(name="Discord", value=message.author.mention, inline=True)
            embed.add_field(name="Roblox", value=f"`{roblox_username}`", inline=True)
            embed.add_field(
                name="Game Link",
                value=f"[Click to join]({GAME_LINK})",
                inline=False
            )
            embed.set_footer(text="Afternight Legacies Testing")
            await message.reply(embed=embed)
        else:
            await message.reply(f"❌ Failed to rank: {result_msg}", delete_after=15)

    # ── /testingsession ───────────────────────────────────────────────────────

    @app_commands.command(
        name="testingsession",
        description="Announce a testing session and ping all game testers."
    )
    @app_commands.describe(
        channel="Channel to send the announcement to",
        date="Date of the session e.g. July 1st 2026",
        time="Time of the session e.g. 5:00 PM EST",
        testing="What will be tested e.g. combat system, map layout"
    )
    async def testingsession(self, interaction: discord.Interaction,
                              channel: discord.TextChannel,
                              date: str,
                              time: str,
                              testing: str):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user
        actor_role_ids = {r.id for r in actor.roles}

        if not actor_role_ids & ALLOWED_ROLES:
            return await interaction.followup.send(
                "❌ Only Programmers or Creators may use `/testingsession`.",
                ephemeral=True
            )

        guild       = interaction.guild
        tester_role = guild.get_role(GAME_TESTER_ROLE_ID)
        ping_str    = tester_role.mention if tester_role else "@GameTester"

        embed = discord.Embed(
            title="🎮 Testing Session Announcement",
            color=discord.Color.from_rgb(88, 101, 242),
            timestamp=datetime.datetime.utcnow()
        )
        embed.description = (
            f"*We will be conducting a testing session to evaluate **{testing}**. "
            f"This session will help us identify issues, gather feedback, and make "
            f"improvements for the game.*"
        )
        embed.add_field(
            name="Details",
            value=(
                f"📅 **Date:** {date}\n"
                f"⏰ **Time:** {time}\n"
                f"📍 **Link:** [Click to join]({GAME_LINK})"
            ),
            inline=False
        )
        embed.add_field(
            name="Feedback Channel",
            value=f"Please share any feedback, observations, or issues you encounter in <#{FEEDBACK_CHANNEL_ID}>.",
            inline=False
        )
        embed.set_footer(text="Thank you for your participation and support! — Afternight Team")

        await channel.send(content=ping_str, embed=embed)

        await interaction.followup.send(
            f"✅ Testing session announcement sent to {channel.mention}.",
            ephemeral=True
        )

        # ── Log ───────────────────────────────────────────────────────────────
        log_embed = discord.Embed(
            title="📋 Testing Session Announced",
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Announced By", value=actor.mention, inline=True)
        log_embed.add_field(name="Channel", value=channel.mention, inline=True)
        log_embed.add_field(name="Date", value=date, inline=True)
        log_embed.add_field(name="Time", value=time, inline=True)
        log_embed.add_field(name="Testing", value=testing, inline=False)
        await self.bot.log_action(log_embed)


async def setup(bot):
    await bot.add_cog(TestingCog(bot))
```[cite: 23]

---

### Quick Reminder on `LOG_CHANNEL_ID`
`LOG_CHANNEL_ID` is read from your `.env` file (`os.getenv("LOG_CHANNEL_ID", "0")`), so you can set the main action log channel ID directly in `.env` without editing `bot.py`[cite: 1, 5]. *(Also, if you want a separate main log channel ID that wasn't listed above, let me know and I can wire it in.)*
