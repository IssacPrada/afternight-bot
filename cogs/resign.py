"""
cogs/resign.py — /resign slash command
"""
import discord
from discord import app_commands
from discord.ext import commands
from constants import (
    ALL_FACTION_ROLES, FACTION_LEADERS,
    FACTION_LEADER_MAIN_ROLE, FACTION_GUIDE_ROLE,
    STAFF_HIERARCHY, STAFF_TEAM_TAGS, SENIOR_STAFF_ROLES, ROLE_STAFF_TEAM, ROLE_ADMIN_TEAM,
    RESIGN_LOG_CHANNEL_ID,
    has_faction_role,
    is_staff
)
from utils.roblox_group import get_roblox_user_id, get_xcsrf_token
import aiohttp
import datetime
import os

# ── Config ────────────────────────────────────────────────────────────────────
LEGACIES_GROUP_ID = 1024076883
FACTIONS_GROUP_ID = 127271910
COOKIE            = os.getenv("ROBLOX_SECURITY_COOKIE")

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
    user_id = await get_roblox_user_id(roblox_username)
    if not user_id:
        return False, f"Could not find Roblox user: `{roblox_username}`"
    try:
        token   = await get_xcsrf_token()
        headers = {**HEADERS_ROBLOX, "x-csrf-token": token}
        role_id = await get_role_id_for_rank(group_id, 1) or await get_role_id_for_rank(group_id, 2)
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
                error = await resp.json()
                msg = error.get("errors", [{}])[0].get("message", "Unknown error")
                return False, f"❌ Roblox API error: {msg}"
    except Exception as e:
        return False, f"❌ Exception: {str(e)}"


async def kick_from_factions_group(roblox_username: str) -> tuple[bool, str]:
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

        roles_removed = []
        roblox_result = "No Roblox action taken."
        resign_category = "Member"

        all_faction_related = set(ALL_FACTION_ROLES) | {
            FACTION_LEADER_MAIN_ROLE,
            FACTION_GUIDE_ROLE,
            *FACTION_LEADERS,
        }
        all_staff_related = set(STAFF_HIERARCHY) | set(SENIOR_STAFF_ROLES) | STAFF_TEAM_TAGS | {
            ROLE_STAFF_TEAM,
            ROLE_ADMIN_TEAM,
        }

        if has_faction_role(member):
            resign_category = "Faction"
            for rid in all_faction_related:
                role = guild.get_role(rid)
                if role and role in member.roles:
                    roles_removed.append(role)
            _, roblox_result = await kick_from_factions_group(roblox)
        elif is_staff(member):
            resign_category = "Staff"
            for rid in all_staff_related:
                role = guild.get_role(rid)
                if role and role in member.roles:
                    roles_removed.append(role)
            _, roblox_result = await demote_to_member_in_group(LEGACIES_GROUP_ID, roblox)
        else:
            return await interaction.followup.send(
                "❌ You don't have any staff or faction roles to resign from.",
                ephemeral=True
            )

        if roles_removed:
            seen_ids     = set()
            unique_roles = []
            for r in roles_removed:
                if r.id not in seen_ids:
                    seen_ids.add(r.id)
                    unique_roles.append(r)
            try:
                await member.remove_roles(*unique_roles, reason=f"Resigned: {reason}")
            except discord.Forbidden:
                pass
            roles_removed = unique_roles

        removed_str = ", ".join(r.name for r in roles_removed) or "None"

        # ── Post to dedicated Resign Log Channel (no DM spam to staff/owners) ──
        resign_embed = discord.Embed(
            title=f"📋 {resign_category} Resignation Notice",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        resign_embed.set_thumbnail(url=member.display_avatar.url)
        resign_embed.add_field(name="Member",        value=f"{member.mention} (`{member.id}`)", inline=True)
        resign_embed.add_field(name="Roblox",        value=f"`{roblox}`",                      inline=True)
        resign_embed.add_field(name="Category",      value=resign_category,                    inline=True)
        resign_embed.add_field(name="Roles Removed", value=removed_str,                        inline=False)
        resign_embed.add_field(name="Roblox Action", value=roblox_result,                      inline=False)
        resign_embed.add_field(name="Reason",        value=reason,                              inline=False)
        resign_embed.set_footer(text="Afternight Resignation System")

        resign_channel = guild.get_channel(RESIGN_LOG_CHANNEL_ID)
        if resign_channel:
            await resign_channel.send(embed=resign_embed)
        else:
            await self.bot.log_action(resign_embed)

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
                f"**Roles Removed:** {removed_str}\n"
                f"**Roblox:** {roblox_result}\n\n"
                f"Thank you for your time in Afternight. We wish you well!"
            )
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        await interaction.followup.send(
            f"✅ Your resignation has been submitted and logged in <#{RESIGN_LOG_CHANNEL_ID}>.",
            ephemeral=True
        )


class ResignCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="resign",
        description="Resign from your staff or faction role."
    )
    async def resign(self, interaction: discord.Interaction):
        member = interaction.user
        has_role = has_faction_role(member) or is_staff(member)
        if not has_role:
            return await interaction.response.send_message(
                "❌ You don't have any staff or faction roles to resign from.",
                ephemeral=True
            )
        await interaction.response.send_modal(ResignModal(bot=self.bot))


async def setup(bot):
    await bot.add_cog(ResignCog(bot))
