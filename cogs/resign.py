"""
cogs/resign.py — /resign slash command
"""
import discord
from discord import app_commands
from discord.ext import commands
from constants import (
    ALL_FACTION_ROLES, FACTION_LEADERS, FACTION_MEMBERS,
    FACTION_OVERSEERS, FACTION_COUNCIL_GLOBAL,
    STAFF_HIERARCHY, ROLE_STAFF_TEAM, ROLE_ADMIN_TEAM,
    get_leader_faction, get_member_faction, get_council_faction,
    is_staff
)
from utils.roblox_group import get_roblox_user_id, get_xcsrf_token, HEADERS, GROUP_ID
import aiohttp
import datetime
import os

# ── Config ────────────────────────────────────────────────────────────────────
LEGACIES_GROUP_ID        = 1024076883
FACTIONS_GROUP_ID        = 127271910
FACTION_LEADER_MAIN_ROLE = 1458305745564205198  # Faction Leaders role
FACTION_ELDER_ROLE       = 1458305760839864422  # Faction Elder

LEGACIES_STAFF_RANK   = 50
LEGACIES_ADMIN_RANK   = 60
FACTIONS_COUNCIL_RANK = 61

OWNER_ID_1 = 1487231309318193305
OWNER_ID_2 = 1102725104435220630

COMMUNITY_MANAGER_ROLE = 1458302857764802683
OVERSEER_ROLE          = 1458302854887510210

COOKIE = os.getenv("ROBLOX_SECURITY_COOKIE")

HEADERS_ROBLOX = {
    "Cookie": f".ROBLOSECURITY={COOKIE}",
    "Content-Type": "application/json",
}


# ── Roblox helpers ────────────────────────────────────────────────────────────

async def get_role_id_for_rank(group_id: int, rank: int) -> int | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://groups.roblox.com/v1/groups/{group_id}/roles",
            headers=HEADERS_ROBLOX
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            for role in data.get("roles", []):
                if role["rank"] == rank:
                    return role["id"]
    return None


async def demote_to_member_in_group(group_id: int, roblox_username: str) -> tuple[bool, str]:
    """Demote a user to the lowest rank in a group."""
    user_id = await get_roblox_user_id(roblox_username)
    if not user_id:
        return False, f"Could not find Roblox user: `{roblox_username}`"
    try:
        token    = await get_xcsrf_token()
        headers  = {**HEADERS_ROBLOX, "x-csrf-token": token}
        role_id  = await get_role_id_for_rank(group_id, 1)
        if not role_id:
            role_id = await get_role_id_for_rank(group_id, 2)
        if not role_id:
            return False, "Could not find Member rank in group."

        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f"https://groups.roblox.com/v1/groups/{group_id}/users/{user_id}",
                headers=headers,
                json={"roleId": role_id}
            ) as resp:
                if resp.status == 200:
                    return True, "✅ Demoted to Member in Roblox group."
                else:
                    error = await resp.json()
                    msg = error.get("errors", [{}])[0].get("message", "Unknown error")
                    return False, f"❌ Roblox API error: {msg}"
    except Exception as e:
        return False, f"❌ Exception: {str(e)}"


async def kick_from_factions_group(roblox_username: str) -> tuple[bool, str]:
    """Kick a user from the Factions group."""
    user_id = await get_roblox_user_id(roblox_username)
    if not user_id:
        return False, f"Could not find Roblox user: `{roblox_username}`"
    try:
        token   = await get_xcsrf_token()
        headers = {**HEADERS_ROBLOX, "x-csrf-token": token}
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"https://groups.roblox.com/v1/groups/{FACTIONS_GROUP_ID}/users/{user_id}",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    return True, "✅ Removed from Factions Roblox group."
                else:
                    error = await resp.json()
                    msg   = error.get("errors", [{}])[0].get("message", "Unknown error")
                    return False, f"❌ Roblox API error: {msg}"
    except Exception as e:
        return False, f"❌ Exception: {str(e)}"


# ── Resign Modal ──────────────────────────────────────────────────────────────

class ResignModal(discord.ui.Modal, title="Resignation"):
    reason = discord.ui.TextInput(
        label="Reason for Resignation",
        style=discord.TextStyle.long,
        placeholder="Please provide your reason for resigning...",
        min_length=10,
        max_length=1000
    )

    roblox_username = discord.ui.TextInput(
        label="Your Roblox Username",
        style=discord.TextStyle.short,
        placeholder="Enter your exact Roblox username...",
        min_length=1,
        max_length=20
    )

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        guild  = interaction.guild
        reason = self.reason.value
        roblox = self.roblox_username.value.strip()

        member_role_ids = {r.id for r in member.roles}

        # ── Determine resign type ─────────────────────────────────────────────
        is_community_manager = COMMUNITY_MANAGER_ROLE in member_role_ids
        is_overseer          = OVERSEER_ROLE in member_role_ids
        leader_faction       = get_leader_faction(member)
        council_faction      = get_council_faction(member)
        is_council_global    = FACTION_COUNCIL_GLOBAL in member_role_ids
        member_faction       = get_member_faction(member)
        staff_member         = is_staff(member)

        roles_removed  = []
        roblox_result  = "No Roblox action taken."
        notify_targets = []

        # ── All faction-related roles to always check ─────────────────────────
        ALL_FACTION_RELATED = list(ALL_FACTION_ROLES) + [
            FACTION_LEADER_MAIN_ROLE,
            FACTION_ELDER_ROLE,
        ]
        # Also include all leader role IDs
        for role_id in FACTION_LEADERS:
            if role_id not in ALL_FACTION_RELATED:
                ALL_FACTION_RELATED.append(role_id)

        # ── Community Manager or Overseer of Staff ────────────────────────────
        if is_community_manager or is_overseer:
            for role_id in STAFF_HIERARCHY:
                role = guild.get_role(role_id)
                if role and role in member.roles:
                    roles_removed.append(role)
            for rid in [ROLE_STAFF_TEAM, ROLE_ADMIN_TEAM,
                        COMMUNITY_MANAGER_ROLE, OVERSEER_ROLE]:
                role = guild.get_role(rid)
                if role and role in member.roles:
                    roles_removed.append(role)

            success, roblox_result = await demote_to_member_in_group(
                LEGACIES_GROUP_ID, roblox
            )

            notify_targets.append((OWNER_ID_1, "community_manager_overseer"))
            notify_targets.append((OWNER_ID_2, "community_manager_overseer"))

        # ── Faction Council / Overseer ────────────────────────────────────────
        elif council_faction or is_council_global:
            role = guild.get_role(FACTION_COUNCIL_GLOBAL)
            if role and role in member.roles:
                roles_removed.append(role)
            for role_id in FACTION_OVERSEERS:
                r = guild.get_role(role_id)
                if r and r in member.roles:
                    roles_removed.append(r)

            # Also remove faction leader main role and elder if held
            for rid in [FACTION_LEADER_MAIN_ROLE, FACTION_ELDER_ROLE]:
                role = guild.get_role(rid)
                if role and role in member.roles:
                    roles_removed.append(role)

            success, roblox_result = await kick_from_factions_group(roblox)

            notify_targets.append((OWNER_ID_1, "council"))
            cm_role = guild.get_role(COMMUNITY_MANAGER_ROLE)
            if cm_role:
                for m in cm_role.members:
                    notify_targets.append((m, "council"))

        # ── Faction Leader ────────────────────────────────────────────────────
        elif leader_faction:
            for role_id in ALL_FACTION_RELATED:
                role = guild.get_role(role_id)
                if role and role in member.roles:
                    roles_removed.append(role)

            success, roblox_result = await kick_from_factions_group(roblox)

            if leader_faction == "Sepharine Coven":
                for role_id in FACTION_OVERSEERS:
                    r = guild.get_role(role_id)
                    if r:
                        for m in r.members:
                            notify_targets.append((m, "leader"))
                gc = guild.get_role(FACTION_COUNCIL_GLOBAL)
                if gc:
                    for m in gc.members:
                        notify_targets.append((m, "leader"))
            else:
                for role_id, faction in FACTION_OVERSEERS.items():
                    if faction == leader_faction:
                        r = guild.get_role(role_id)
                        if r:
                            for m in r.members:
                                notify_targets.append((m, "leader"))

        # ── Faction Member ────────────────────────────────────────────────────
        elif member_faction:
            for role_id in ALL_FACTION_RELATED:
                role = guild.get_role(role_id)
                if role and role in member.roles:
                    roles_removed.append(role)

            success, roblox_result = await kick_from_factions_group(roblox)

            for role_id, faction in FACTION_LEADERS.items():
                if faction == member_faction:
                    r = guild.get_role(role_id)
                    if r:
                        for m in r.members:
                            notify_targets.append((m, "member"))

        # ── Staff member ──────────────────────────────────────────────────────
        elif staff_member:
            for role_id in STAFF_HIERARCHY:
                role = guild.get_role(role_id)
                if role and role in member.roles:
                    roles_removed.append(role)
            for rid in [ROLE_STAFF_TEAM, ROLE_ADMIN_TEAM]:
                role = guild.get_role(rid)
                if role and role in member.roles:
                    roles_removed.append(role)

            success, roblox_result = await demote_to_member_in_group(
                LEGACIES_GROUP_ID, roblox
            )

            overseer_role = guild.get_role(OVERSEER_ROLE)
            cm_role       = guild.get_role(COMMUNITY_MANAGER_ROLE)
            if overseer_role:
                for m in overseer_role.members:
                    notify_targets.append((m, "staff"))
            if cm_role:
                for m in cm_role.members:
                    notify_targets.append((m, "staff"))

        else:
            return await interaction.followup.send(
                "❌ You don't have any staff or faction roles to resign from.",
                ephemeral=True
            )

        # ── Remove Discord roles ──────────────────────────────────────────────
        if roles_removed:
            # Deduplicate
            seen_ids      = set()
            unique_roles  = []
            for r in roles_removed:
                if r.id not in seen_ids:
                    seen_ids.add(r.id)
                    unique_roles.append(r)
            roles_removed = unique_roles

            await member.remove_roles(
                *roles_removed,
                reason=f"Resigned: {reason}"
            )

        # ── Build resign embed ────────────────────────────────────────────────
        resign_embed = discord.Embed(
            title="📋 Resignation Notice",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        resign_embed.set_thumbnail(url=member.display_avatar.url)
        resign_embed.add_field(name="Member", value=member.mention, inline=True)
        resign_embed.add_field(name="Roblox", value=f"`{roblox}`",  inline=True)
        resign_embed.add_field(name="\u200b", value="\u200b",       inline=True)
        resign_embed.add_field(
            name="Roles Removed",
            value=", ".join(r.name for r in roles_removed) or "None",
            inline=False
        )
        resign_embed.add_field(name="Roblox Action", value=roblox_result, inline=False)
        resign_embed.add_field(name="Reason",        value=reason,        inline=False)
        resign_embed.set_footer(text="Afternight Resignation System")

        # ── Notify targets ────────────────────────────────────────────────────
        seen = set()
        for target, resign_type in notify_targets:
            if isinstance(target, int):
                try:
                    target = await self.bot.fetch_user(target)
                except Exception:
                    continue

            if target.id in seen or target.id == member.id:
                continue
            seen.add(target.id)

            try:
                notify_embed = discord.Embed(
                    title="📢 Resignation Notice",
                    color=discord.Color.orange(),
                    timestamp=datetime.datetime.utcnow()
                )
                notify_embed.set_thumbnail(url=member.display_avatar.url)
                notify_embed.add_field(
                    name="Who Resigned",
                    value=f"{member.mention} (`{member.display_name}`)",
                    inline=True
                )
                notify_embed.add_field(name="Roblox", value=f"`{roblox}`", inline=True)
                notify_embed.add_field(name="Reason", value=reason,        inline=False)
                notify_embed.add_field(
                    name="Roles Removed",
                    value=", ".join(r.name for r in roles_removed) or "None",
                    inline=False
                )
                notify_embed.add_field(
                    name="Roblox Action",
                    value=roblox_result,
                    inline=False
                )
                notify_embed.set_footer(text="Afternight Resignation System")
                await target.send(embed=notify_embed)
            except discord.Forbidden:
                pass

        # ── DM the resigning member ───────────────────────────────────────────
        try:
            dm_embed = discord.Embed(
                title="✅ Resignation Submitted",
                color=discord.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            dm_embed.description = (
                f"Your resignation has been processed.\n\n"
                f"**Reason:** {reason}\n\n"
                f"**Roles Removed:** {', '.join(r.name for r in roles_removed) or 'None'}\n"
                f"**Roblox:** {roblox_result}\n\n"
                f"Thank you for your time in Afternight. We wish you well!"
            )
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        await interaction.followup.send(
            "✅ Your resignation has been submitted and processed.",
            ephemeral=True
        )

        await self.bot.log_action(resign_embed)


# ── Cog ───────────────────────────────────────────────────────────────────────

class ResignCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="resign",
        description="Resign from your staff or faction role."
    )
    async def resign(self, interaction: discord.Interaction):
        member          = interaction.user
        member_role_ids = {r.id for r in member.roles}

        has_faction  = get_member_faction(member) is not None
        has_leader   = get_leader_faction(member) is not None
        has_council  = get_council_faction(member) is not None or FACTION_COUNCIL_GLOBAL in member_role_ids
        has_staff    = is_staff(member)
        is_cm        = COMMUNITY_MANAGER_ROLE in member_role_ids
        is_os        = OVERSEER_ROLE in member_role_ids

        if not any([has_faction, has_leader, has_council, has_staff, is_cm, is_os]):
            return await interaction.response.send_message(
                "❌ You don't have any staff or faction roles to resign from.",
                ephemeral=True
            )

        await interaction.response.send_modal(ResignModal(bot=self.bot))


async def setup(bot):
    await bot.add_cog(ResignCog(bot))
