"""
cogs/resign.py — /resign slash command for staff and faction resignations
"""
import datetime
import os
from typing import Optional
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from constants import (
    ALL_FACTION_ROLES,
    FACTION_GUIDE_ROLE,
    FACTION_LEADER_MAIN_ROLE,
    FACTION_LEADERS,
    FACTION_MEMBER_MAIN_ROLE,
    FACTION_MEMBERS,
    FACTION_OVERSEERS,
    RESIGN_LOG_CHANNEL_ID,
    ROLE_ADMIN_TEAM,
    ROLE_STAFF_TEAM,
    STAFF_HIERARCHY,
    STAFF_HIERARCHY_NAMES,
    get_council_faction,
    get_leader_faction,
    get_member_faction,
    get_member_rank_index,
    is_staff,
)
from utils.roblox_group import get_roblox_user_id, get_xcsrf_token

LEGACIES_GROUP_ID = 1024076883
FACTIONS_GROUP_ID = 127271910
COOKIE = os.getenv("ROBLOX_SECURITY_COOKIE")
HEADERS_ROBLOX = {
    "Cookie": f".ROBLOSECURITY={COOKIE}",
    "Content-Type": "application/json",
}


async def _reset_roblox_rank(group_id: int, roblox_username: str, rank: int = 1) -> tuple[bool, str]:
    if not COOKIE:
        return False, "ROBLOX_SECURITY_COOKIE not set"

    user_id = await get_roblox_user_id(roblox_username)
    if not user_id:
        return False, f"Roblox user `{roblox_username}` not found"

    try:
        token = await get_xcsrf_token()
        headers = {**HEADERS_ROBLOX, "x-csrf-token": token}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://groups.roblox.com/v1/groups/{group_id}/roles",
                headers=headers
            ) as resp:
                if resp.status != 200:
                    return False, f"Failed to fetch roles (HTTP {resp.status})"
                roles_data = await resp.json()

            target_role_id = None
            for r in roles_data.get("roles", []):
                if r.get("rank") == rank:
                    target_role_id = r.get("id")
                    break

            if not target_role_id:
                return False, f"Rank `{rank}` not found in group `{group_id}`"

            async with session.patch(
                f"https://groups.roblox.com/v1/groups/{group_id}/users/{user_id}",
                headers=headers,
                json={"roleId": target_role_id}
            ) as resp:
                if resp.status == 200:
                    return True, f"Rank set to `{rank}` in group `{group_id}`"
                err = await resp.json()
                msg = err.get("errors", [{}])[0].get("message", "Unknown Roblox error")
                return False, f"Roblox API error: {msg}"
    except Exception as e:
        return False, f"Roblox sync error: {e}"


class ResignModal(discord.ui.Modal, title="Submit Resignation"):
    reason_input = discord.ui.TextInput(
        label="Reason for Resignation",
        style=discord.TextStyle.long,
        placeholder="Explain why you are stepping down...",
        min_length=5,
        max_length=1000
    )

    roblox_input = discord.ui.TextInput(
        label="Roblox Username (Optional)",
        style=discord.TextStyle.short,
        placeholder="Leave blank if not syncing Roblox rank",
        required=False,
        max_length=50
    )

    def __init__(self, bot, scope: str):
        super().__init__()
        self.bot = bot
        self.scope = scope

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        guild = interaction.guild
        reason = self.reason_input.value.strip()
        roblox_username = self.roblox_input.value.strip() if self.roblox_input.value else None

        rank_idx = get_member_rank_index(member)
        staff_rank_label = STAFF_HIERARCHY_NAMES.get(STAFF_HIERARCHY[rank_idx], "Staff") if rank_idx >= 0 else None
        faction_name = (
            get_leader_faction(member)
            or get_member_faction(member)
            or get_council_faction(member)
        )

        removed_roles: list[discord.Role] = []

        if self.scope in ("staff", "both"):
            staff_ids = set(STAFF_HIERARCHY) | {ROLE_STAFF_TEAM, ROLE_ADMIN_TEAM}
            for rid in staff_ids:
                role = guild.get_role(rid)
                if role and role in member.roles:
                    removed_roles.append(role)

        if self.scope in ("faction", "both"):
            faction_ids = set(ALL_FACTION_ROLES) | {
                FACTION_LEADER_MAIN_ROLE,
                FACTION_GUIDE_ROLE,
                FACTION_MEMBER_MAIN_ROLE,
                *FACTION_LEADERS.keys(),
                *FACTION_OVERSEERS.keys(),
                *FACTION_MEMBERS.keys(),
            }
            for rid in faction_ids:
                role = guild.get_role(rid)
                if role and role in member.roles and role not in removed_roles:
                    removed_roles.append(role)

        role_cleanup_note = "No roles removed"
        if removed_roles:
            try:
                await member.remove_roles(
                    *removed_roles,
                    reason=f"Resignation ({self.scope}): {reason}"
                )
                role_cleanup_note = ", ".join(r.name for r in removed_roles)
            except discord.Forbidden:
                role_cleanup_note = "Missing permissions to remove one or more roles"
            except discord.HTTPException:
                role_cleanup_note = "Failed to remove roles due to Discord error"

        roblox_notes: list[str] = []
        if roblox_username:
            if self.scope in ("staff", "both"):
                _, msg = await _reset_roblox_rank(LEGACIES_GROUP_ID, roblox_username, rank=1)
                roblox_notes.append(f"Legacies: {msg}")
            if self.scope in ("faction", "both"):
                _, msg = await _reset_roblox_rank(FACTIONS_GROUP_ID, roblox_username, rank=1)
                roblox_notes.append(f"Factions: {msg}")

        await self.bot.db.log_staff_action(
            action="RESIGN",
            target_id=str(member.id),
            actor_id=str(member.id),
            guild_id=str(guild.id),
            note=f"Scope: {self.scope} | Roles: {role_cleanup_note} | Reason: {reason}"
        )

        log_embed = discord.Embed(
            title="🏳️ Resignation Submitted",
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.set_thumbnail(url=member.display_avatar.url)
        log_embed.add_field(name="Member", value=f"{member.mention} (`{member.id}`)", inline=True)
        log_embed.add_field(name="Scope", value=self.scope.upper(), inline=True)
        if staff_rank_label:
            log_embed.add_field(name="Previous Staff Rank", value=staff_rank_label, inline=True)
        if faction_name:
            log_embed.add_field(name="Faction", value=faction_name, inline=True)
        if roblox_username:
            log_embed.add_field(name="Roblox Username", value=f"`{roblox_username}`", inline=True)
        log_embed.add_field(name="Reason", value=reason, inline=False)
        log_embed.add_field(name="Removed Roles", value=role_cleanup_note[:1024], inline=False)
        if roblox_notes:
            log_embed.add_field(name="Roblox Rank Reset", value="\n".join(roblox_notes), inline=False)

        log_channel = guild.get_channel(RESIGN_LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(embed=log_embed)
        else:
            await self.bot.log_action(log_embed)

        await interaction.followup.send(
            f"✅ Your resignation (**{self.scope}**) has been recorded and logged in <#{RESIGN_LOG_CHANNEL_ID}>.",
            ephemeral=True
        )


class ResignCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="resign",
        description="Submit a resignation from staff, a faction, or both."
    )
    @app_commands.describe(
        scope="Whether you are resigning from staff, faction, or both"
    )
    @app_commands.choices(scope=[
        app_commands.Choice(name="Staff", value="staff"),
        app_commands.Choice(name="Faction", value="faction"),
        app_commands.Choice(name="Both (Staff & Faction)", value="both"),
    ])
    async def resign(
        self,
        interaction: discord.Interaction,
        scope: Optional[app_commands.Choice[str]] = None
    ):
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "❌ This command can only be used inside a server.",
                ephemeral=True
            )

        selected_scope = scope.value if scope else ("staff" if is_staff(interaction.user) else "faction")
        await interaction.response.send_modal(ResignModal(bot=self.bot, scope=selected_scope))


async def setup(bot):
    await bot.add_cog(ResignCog(bot))
