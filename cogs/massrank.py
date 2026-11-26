"""
cogs/massrank.py — Bulk role assignment/removal and Roblox group mass-ranking commands
"""
import datetime
import os
from typing import Optional
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from constants import (
    FACTION_COLORS,
    FACTION_LEADER_MAIN_ROLE,
    FACTION_MEMBER_MAIN_ROLE,
    FACTION_ROBLOX_RANKS,
    MOD_LOG_CHANNEL_ID,
    ROLE_MEMBER,
    has_fire_permission,
)
from utils.roblox_group import get_roblox_user_id, get_xcsrf_token

LEGACIES_GROUP_ID = 1024076883
FACTIONS_GROUP_ID = 127271910
COOKIE = os.getenv("ROBLOX_SECURITY_COOKIE")
HEADERS_ROBLOX = {
    "Cookie": f".ROBLOSECURITY={COOKIE}",
    "Content-Type": "application/json",
}

ROLE_PRESETS: dict[str, int] = {
    "member": ROLE_MEMBER,
    "faction_member": FACTION_MEMBER_MAIN_ROLE,
    "faction_leader": FACTION_LEADER_MAIN_ROLE,
}


async def _set_roblox_group_rank(group_id: int, roblox_username: str, rank: int) -> tuple[bool, str]:
    if not COOKIE:
        return False, "ROBLOX_SECURITY_COOKIE not configured"

    user_id = await get_roblox_user_id(roblox_username)
    if not user_id:
        return False, f"User `{roblox_username}` not found"

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
                    return True, f"Updated `{roblox_username}` to rank `{rank}`"
                err = await resp.json()
                msg = err.get("errors", [{}])[0].get("message", "Unknown Roblox error")
                return False, f"`{roblox_username}`: {msg}"
    except Exception as e:
        return False, f"`{roblox_username}`: {e}"


class MassRankCog(commands.Cog):
    massrank_group = app_commands.Group(
        name="massrank",
        description="Perform bulk Discord role or Roblox group rank updates."
    )

    def __init__(self, bot):
        self.bot = bot

    async def _post_log(self, guild: discord.Guild, embed: discord.Embed):
        channel = guild.get_channel(MOD_LOG_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)
        else:
            await self.bot.log_action(embed)

    def _resolve_discord_role(
        self,
        guild: discord.Guild,
        role: Optional[discord.Role],
        preset: Optional[str]
    ) -> tuple[Optional[discord.Role], Optional[str]]:
        if role:
            return role, None
        if preset:
            key = preset.strip().lower()
            if key not in ROLE_PRESETS:
                return None, f"❌ Unknown preset `{preset}`. Available: {', '.join(ROLE_PRESETS)}."
            resolved = guild.get_role(ROLE_PRESETS[key])
            if not resolved:
                return None, f"❌ Preset role for `{key}` was not found in this server."
            return resolved, None
        return None, "❌ Provide either a `role` or a `preset`."

    @massrank_group.command(
        name="addrole",
        description="Add a Discord role to members with a source role or to all server members."
    )
    @app_commands.describe(
        role="Target Discord role to add",
        source_role="Optional role to filter target members (leave empty for all members)",
        preset="Optional role preset (member, faction_member, faction_leader)",
        reason="Reason for the mass role addition"
    )
    async def add_role(
        self,
        interaction: discord.Interaction,
        role: Optional[discord.Role] = None,
        source_role: Optional[discord.Role] = None,
        preset: Optional[str] = None,
        reason: str = "Mass role add"
    ):
        if not has_fire_permission(interaction.user):
            return await interaction.response.send_message(
                "❌ You don't have permission to use mass-rank commands.",
                ephemeral=True
            )

        target_role, err = self._resolve_discord_role(interaction.guild, role, preset)
        if err:
            return await interaction.response.send_message(err, ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        candidates = [
            m for m in interaction.guild.members
            if not m.bot
            and target_role not in m.roles
            and (source_role is None or source_role in m.roles)
        ]

        updated = 0
        failed = 0
        for member in candidates:
            try:
                await member.add_roles(target_role, reason=f"{reason} (by {interaction.user})")
                updated += 1
            except discord.Forbidden:
                failed += 1
            except discord.HTTPException:
                failed += 1

        await self.bot.db.log_staff_action(
            action="MASSRANK_ADD_ROLE",
            target_id=str(target_role.id),
            actor_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            note=f"Added {target_role.name} to {updated} members (failed: {failed}) | {reason}"
        )

        log_embed = discord.Embed(
            title="📦 Mass Role Add",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Target Role", value=target_role.mention, inline=True)
        log_embed.add_field(
            name="Filter",
            value=source_role.mention if source_role else "All non-bot members",
            inline=True
        )
        log_embed.add_field(name="By", value=f"{interaction.user.mention}", inline=True)
        log_embed.add_field(name="Result", value=f"✅ Updated: **{updated}** · ❌ Failed: **{failed}**", inline=False)
        log_embed.add_field(name="Reason", value=reason, inline=False)
        await self._post_log(interaction.guild, log_embed)

        await interaction.followup.send(
            f"✅ Added {target_role.mention} to **{updated}** member(s) (failed: **{failed}**).",
            ephemeral=True
        )

    @massrank_group.command(
        name="removerole",
        description="Remove a Discord role from members who currently have it."
    )
    @app_commands.describe(
        role="Target Discord role to remove",
        source_role="Optional additional filter role",
        preset="Optional role preset (member, faction_member, faction_leader)",
        reason="Reason for the mass role removal"
    )
    async def remove_role(
        self,
        interaction: discord.Interaction,
        role: Optional[discord.Role] = None,
        source_role: Optional[discord.Role] = None,
        preset: Optional[str] = None,
        reason: str = "Mass role removal"
    ):
        if not has_fire_permission(interaction.user):
            return await interaction.response.send_message(
                "❌ You don't have permission to use mass-rank commands.",
                ephemeral=True
            )

        target_role, err = self._resolve_discord_role(interaction.guild, role, preset)
        if err:
            return await interaction.response.send_message(err, ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        candidates = [
            m for m in interaction.guild.members
            if not m.bot
            and target_role in m.roles
            and (source_role is None or source_role in m.roles)
        ]

        updated = 0
        failed = 0
        for member in candidates:
            try:
                await member.remove_roles(target_role, reason=f"{reason} (by {interaction.user})")
                updated += 1
            except discord.Forbidden:
                failed += 1
            except discord.HTTPException:
                failed += 1

        await self.bot.db.log_staff_action(
            action="MASSRANK_REMOVE_ROLE",
            target_id=str(target_role.id),
            actor_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            note=f"Removed {target_role.name} from {updated} members (failed: {failed}) | {reason}"
        )

        log_embed = discord.Embed(
            title="📦 Mass Role Remove",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Target Role", value=target_role.mention, inline=True)
        log_embed.add_field(
            name="Filter",
            value=source_role.mention if source_role else "All members with role",
            inline=True
        )
        log_embed.add_field(name="By", value=f"{interaction.user.mention}", inline=True)
        log_embed.add_field(name="Result", value=f"✅ Removed: **{updated}** · ❌ Failed: **{failed}**", inline=False)
        log_embed.add_field(name="Reason", value=reason, inline=False)
        await self._post_log(interaction.guild, log_embed)

        await interaction.followup.send(
            f"✅ Removed {target_role.mention} from **{updated}** member(s) (failed: **{failed}**).",
            ephemeral=True
        )

    @massrank_group.command(
        name="roblox",
        description="Set a Roblox group rank for comma-separated Roblox usernames."
    )
    @app_commands.describe(
        usernames="Comma-separated Roblox usernames (e.g. PlayerOne, PlayerTwo)",
        rank="Target Roblox group rank number (or use faction preset)",
        group="Target Roblox group (factions or legacies)",
        faction="Optional faction name to auto-pick rank (Sanguis Order, Eldritch Thorn, SilverVenom, Seraphine Coven)"
    )
    @app_commands.choices(group=[
        app_commands.Choice(name="Factions Group", value="factions"),
        app_commands.Choice(name="Legacies Group", value="legacies"),
    ])
    async def roblox_massrank(
        self,
        interaction: discord.Interaction,
        usernames: str,
        rank: Optional[int] = None,
        group: str = "factions",
        faction: Optional[str] = None
    ):
        if not has_fire_permission(interaction.user):
            return await interaction.response.send_message(
                "❌ You don't have permission to use mass-rank commands.",
                ephemeral=True
            )

        target_rank = rank
        if faction and target_rank is None:
            for f_name, f_rank in FACTION_ROBLOX_RANKS.items():
                if f_name.lower() == faction.strip().lower():
                    target_rank = f_rank
                    break

        if target_rank is None:
            return await interaction.response.send_message(
                "❌ Provide a `rank` number or a valid `faction` name.",
                ephemeral=True
            )

        user_list = [u.strip() for u in usernames.split(",") if u.strip()]
        if not user_list:
            return await interaction.response.send_message(
                "❌ Provide at least one valid Roblox username.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        group_id = FACTIONS_GROUP_ID if group == "factions" else LEGACIES_GROUP_ID
        successes = 0
        failures: list[str] = []

        for u in user_list[:50]:
            ok, msg = await _set_roblox_group_rank(group_id, u, target_rank)
            if ok:
                successes += 1
            else:
                failures.append(msg)

        await self.bot.db.log_staff_action(
            action="MASSRANK_ROBLOX",
            target_id=str(group_id),
            actor_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            note=f"Group {group} ({group_id}) rank {target_rank}: {successes} ok, {len(failures)} failed"
        )

        color = FACTION_COLORS.get(faction, discord.Color.blurple().value) if faction else discord.Color.blurple()
        log_embed = discord.Embed(
            title="🎮 Roblox Mass Rank",
            color=color,
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Group", value=f"{group.title()} (`{group_id}`)", inline=True)
        log_embed.add_field(name="Target Rank", value=str(target_rank), inline=True)
        log_embed.add_field(name="By", value=f"{interaction.user.mention}", inline=True)
        log_embed.add_field(
            name="Summary",
            value=f"✅ Succeeded: **{successes}** · ❌ Failed: **{len(failures)}**",
            inline=False
        )
        if failures:
            log_embed.add_field(
                name="Errors",
                value="\n".join(failures[:10])[:1024],
                inline=False
            )
        await self._post_log(interaction.guild, log_embed)

        reply = f"✅ Updated **{successes}** Roblox user(s) to rank **{target_rank}** (`{group}`)."
        if failures:
            reply += f"\n❌ **{len(failures)}** failed: " + ", ".join(failures[:5])
        await interaction.followup.send(reply, ephemeral=True)


async def setup(bot):
    await bot.add_cog(MassRankCog(bot))
