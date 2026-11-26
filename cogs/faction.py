"""
cogs/faction.py — /faction command group for managing factions, members, ranks, and rosters
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
    FACTION_COLORS,
    FACTION_COUNCIL_GLOBAL,
    FACTION_GUIDE_ROLE,
    FACTION_LEADER_MAIN_ROLE,
    FACTION_LEADERS,
    FACTION_LOG_CHANNEL_ID,
    FACTION_MEMBER_MAIN_ROLE,
    FACTION_MEMBERS,
    FACTION_OVERSEERS,
    FACTION_ROBLOX_RANKS,
    STRIKE_STATUS,
    can_use_faction_commands,
    get_council_faction,
    get_leader_faction,
    get_member_faction,
)
from utils.roblox_group import get_roblox_user_id, get_xcsrf_token

FACTIONS_GROUP_ID = 127271910
COOKIE = os.getenv("ROBLOX_SECURITY_COOKIE")
HEADERS_ROBLOX = {
    "Cookie": f".ROBLOSECURITY={COOKIE}",
    "Content-Type": "application/json",
}

FACTIONS_LIST = [
    "Sanguis Order",
    "Eldritch Thorn",
    "SilverVenom",
    "Seraphine Coven",
]

FACTION_MEMBER_ROLE_BY_NAME: dict[str, int] = {
    "Sanguis Order":   1575232569455280329,  # [SOM] Sanguis Order Member.
    "Eldritch Thorn":  1575232880555200693,  # [ETM] Eldritch Thorn Member.
    "SilverVenom":     1575232935555112970,  # [SVM] SilverVenom Member.
    "Seraphine Coven": 1575232712543965324,  # [SCM] Seraphine Coven Member.
}

FACTION_LEADER_ROLE_BY_NAME: dict[str, int] = {
    name: rid for rid, name in FACTION_LEADERS.items()
}

FACTION_OVERSEER_ROLE_BY_NAME: dict[str, int] = {
    name: rid for rid, name in FACTION_OVERSEERS.items()
}


async def set_roblox_faction_rank(roblox_username: str, faction: str, rank: int) -> tuple[bool, str]:
    """Update a user's rank in the Factions Roblox group if configured."""
    if not COOKIE:
        return False, "ROBLOX_SECURITY_COOKIE not set (skipped Roblox rank sync)"

    user_id = await get_roblox_user_id(roblox_username)
    if not user_id:
        return False, f"Roblox user `{roblox_username}` not found"

    try:
        token = await get_xcsrf_token()
        headers = {**HEADERS_ROBLOX, "x-csrf-token": token}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://groups.roblox.com/v1/groups/{FACTIONS_GROUP_ID}/roles",
                headers=headers
            ) as resp:
                if resp.status != 200:
                    return False, f"Failed to fetch Roblox group roles (HTTP {resp.status})"
                roles_data = await resp.json()

            target_role_id = None
            for r in roles_data.get("roles", []):
                if r.get("rank") == rank:
                    target_role_id = r.get("id")
                    break

            if not target_role_id:
                return False, f"No Roblox role found with rank `{rank}` in group `{FACTIONS_GROUP_ID}`"

            async with session.patch(
                f"https://groups.roblox.com/v1/groups/{FACTIONS_GROUP_ID}/users/{user_id}",
                headers=headers,
                json={"roleId": target_role_id}
            ) as resp:
                if resp.status == 200:
                    return True, f"Roblox rank updated to `{rank}` (`{faction}`)"
                err = await resp.json()
                msg = err.get("errors", [{}])[0].get("message", "Unknown Roblox error")
                return False, f"Roblox API error: {msg}"
    except Exception as e:
        return False, f"Roblox sync error: {e}"


class FactionCog(commands.Cog):
    faction_group = app_commands.Group(
        name="faction",
        description="Manage faction members, ranks, leaders, and rosters."
    )

    def __init__(self, bot):
        self.bot = bot

    async def _post_faction_log(self, guild: discord.Guild, embed: discord.Embed):
        channel = guild.get_channel(FACTION_LOG_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)
        else:
            await self.bot.log_action(embed)

    def _resolve_faction(
        self,
        interaction_member: discord.Member,
        requested_faction: Optional[str] = None
    ) -> tuple[bool, Optional[str], Optional[str]]:
        allowed, scoped_faction = can_use_faction_commands(interaction_member)
        if not allowed:
            return False, None, "❌ You don't have permission to manage factions."

        if scoped_faction:
            if requested_faction and requested_faction.strip().lower() != scoped_faction.lower():
                return False, None, f"❌ You can only manage **{scoped_faction}**."
            return True, scoped_faction, None

        if not requested_faction:
            return False, None, "❌ Please specify a faction."

        for name in FACTIONS_LIST:
            if name.lower() == requested_faction.strip().lower():
                return True, name, None

        return False, None, f"❌ Unknown faction `{requested_faction}`. Choose from: {', '.join(FACTIONS_LIST)}."

    async def _clear_faction_roles(self, member: discord.Member, reason: str):
        to_remove = []
        role_ids = set(ALL_FACTION_ROLES) | {
            FACTION_LEADER_MAIN_ROLE,
            FACTION_GUIDE_ROLE,
            FACTION_MEMBER_MAIN_ROLE,
            *FACTION_LEADERS.keys(),
            *FACTION_OVERSEERS.keys(),
            *FACTION_MEMBERS.keys(),
        }
        for rid in role_ids:
            role = member.guild.get_role(rid)
            if role and role in member.roles:
                to_remove.append(role)
        if to_remove:
            await member.remove_roles(*to_remove, reason=reason)
        return to_remove

    @faction_group.command(name="addmember", description="Add a member to a faction.")
    @app_commands.describe(
        member="Discord user to add",
        faction="Faction name",
        roblox_username="Optional Roblox username for rank sync"
    )
    async def add_member(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        faction: Optional[str] = None,
        roblox_username: Optional[str] = None
    ):
        ok, target_faction, err = self._resolve_faction(interaction.user, faction)
        if not ok:
            return await interaction.response.send_message(err, ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        blacklist_entry = await self.bot.db.is_blacklisted(str(member.id), str(interaction.guild.id))
        if blacklist_entry:
            return await interaction.followup.send(
                f"❌ {member.mention} is blacklisted from **{blacklist_entry['faction']}** "
                f"(Reason: {blacklist_entry['reason']}). Remove the blacklist first.",
                ephemeral=True
            )

        roles_to_add = []
        for rid in (FACTION_MEMBER_MAIN_ROLE, FACTION_MEMBER_ROLE_BY_NAME.get(target_faction)):
            if rid:
                role = interaction.guild.get_role(rid)
                if role and role not in member.roles:
                    roles_to_add.append(role)

        try:
            if roles_to_add:
                await member.add_roles(*roles_to_add, reason=f"Added to {target_faction} by {interaction.user}")
        except discord.Forbidden:
            return await interaction.followup.send(
                "❌ Missing permissions to assign faction roles. Check my role hierarchy.",
                ephemeral=True
            )

        roblox_note = ""
        if roblox_username:
            rank = FACTION_ROBLOX_RANKS.get(target_faction, 1)
            _, r_msg = await set_roblox_faction_rank(roblox_username.strip(), target_faction, rank)
            roblox_note = f"\n**Roblox Sync:** {r_msg}"

        await self.bot.db.log_staff_action(
            action="FACTION_ADD_MEMBER",
            target_id=str(member.id),
            actor_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            note=f"Added to {target_faction}"
        )

        log_embed = discord.Embed(
            title="➕ Faction Member Added",
            color=FACTION_COLORS.get(target_faction, discord.Color.green().value),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Member", value=f"{member.mention} (`{member.id}`)", inline=True)
        log_embed.add_field(name="Faction", value=target_faction, inline=True)
        log_embed.add_field(name="Added By", value=f"{interaction.user.mention}", inline=True)
        if roblox_note:
            log_embed.add_field(name="Roblox", value=roblox_note.strip(), inline=False)
        await self._post_faction_log(interaction.guild, log_embed)

        await interaction.followup.send(
            f"✅ Added {member.mention} to **{target_faction}**{roblox_note}.",
            ephemeral=True
        )

    @faction_group.command(name="removemember", description="Remove a member from faction roles.")
    @app_commands.describe(
        member="Discord user to remove from faction",
        reason="Reason for removal"
    )
    async def remove_member(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Removed from faction"
    ):
        current_faction = (
            get_member_faction(member)
            or get_leader_faction(member)
            or get_council_faction(member)
        )
        ok, target_faction, err = self._resolve_faction(interaction.user, current_faction)
        if not ok:
            return await interaction.response.send_message(err, ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        try:
            removed = await self._clear_faction_roles(
                member,
                reason=f"Removed from {target_faction} by {interaction.user}: {reason}"
            )
        except discord.Forbidden:
            return await interaction.followup.send(
                "❌ Missing permissions to remove faction roles. Check my role hierarchy.",
                ephemeral=True
            )

        removed_names = ", ".join(r.name for r in removed) or "None"
        await self.bot.db.log_staff_action(
            action="FACTION_REMOVE_MEMBER",
            target_id=str(member.id),
            actor_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            note=f"Removed from {target_faction} | Reason: {reason}"
        )

        log_embed = discord.Embed(
            title="➖ Faction Member Removed",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Member", value=f"{member.mention} (`{member.id}`)", inline=True)
        log_embed.add_field(name="Faction", value=target_faction or "Unknown", inline=True)
        log_embed.add_field(name="Removed By", value=f"{interaction.user.mention}", inline=True)
        log_embed.add_field(name="Roles Removed", value=removed_names, inline=False)
        log_embed.add_field(name="Reason", value=reason, inline=False)
        await self._post_faction_log(interaction.guild, log_embed)

        await interaction.followup.send(
            f"✅ Removed {member.mention} from **{target_faction}** ({removed_names}).",
            ephemeral=True
        )

    @faction_group.command(name="promote", description="Promote a faction member to Faction Guide or Faction Leader.")
    @app_commands.describe(
        member="Faction member to promote",
        rank="Target rank (guide or leader)",
        faction="Faction name"
    )
    @app_commands.choices(rank=[
        app_commands.Choice(name="Faction Guide [FG]", value="guide"),
        app_commands.Choice(name="Faction Leader [FL]", value="leader"),
    ])
    async def promote(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        rank: app_commands.Choice[str],
        faction: Optional[str] = None
    ):
        detected_faction = (
            faction
            or get_member_faction(member)
            or get_leader_faction(member)
            or get_council_faction(member)
        )
        ok, target_faction, err = self._resolve_faction(interaction.user, detected_faction)
        if not ok:
            return await interaction.response.send_message(err, ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        roles_to_add = []
        base_member_rid = FACTION_MEMBER_ROLE_BY_NAME.get(target_faction)
        if base_member_rid:
            base_role = interaction.guild.get_role(base_member_rid)
            if base_role and base_role not in member.roles:
                roles_to_add.append(base_role)

        if rank.value == "guide":
            guide_role = interaction.guild.get_role(FACTION_GUIDE_ROLE)
            if guide_role and guide_role not in member.roles:
                roles_to_add.append(guide_role)
            rank_label = "[FG] Faction Guide"
        else:
            for rid in (FACTION_LEADER_MAIN_ROLE, FACTION_LEADER_ROLE_BY_NAME.get(target_faction)):
                if rid:
                    role = interaction.guild.get_role(rid)
                    if role and role not in member.roles:
                        roles_to_add.append(role)
            rank_label = f"[FL] {target_faction} Leader"

        try:
            if roles_to_add:
                await member.add_roles(*roles_to_add, reason=f"Promoted to {rank_label} by {interaction.user}")
        except discord.Forbidden:
            return await interaction.followup.send(
                "❌ Missing permissions to promote member. Check my role hierarchy.",
                ephemeral=True
            )

        await self.bot.db.log_staff_action(
            action="FACTION_PROMOTE",
            target_id=str(member.id),
            actor_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            note=f"Promoted {member.id} to {rank_label} in {target_faction}"
        )

        log_embed = discord.Embed(
            title="⬆️ Faction Promotion",
            color=FACTION_COLORS.get(target_faction, discord.Color.gold().value),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Member", value=f"{member.mention} (`{member.id}`)", inline=True)
        log_embed.add_field(name="Faction", value=target_faction, inline=True)
        log_embed.add_field(name="New Rank", value=rank_label, inline=True)
        log_embed.add_field(name="By", value=f"{interaction.user.mention}", inline=True)
        await self._post_faction_log(interaction.guild, log_embed)

        await interaction.followup.send(
            f"✅ Promoted {member.mention} to **{rank_label}** in **{target_faction}**.",
            ephemeral=True
        )

    @faction_group.command(name="demote", description="Demote a faction leader/guide back to Faction Member.")
    @app_commands.describe(
        member="Faction member to demote",
        faction="Faction name"
    )
    async def demote(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        faction: Optional[str] = None
    ):
        detected_faction = (
            faction
            or get_leader_faction(member)
            or get_member_faction(member)
            or get_council_faction(member)
        )
        ok, target_faction, err = self._resolve_faction(interaction.user, detected_faction)
        if not ok:
            return await interaction.response.send_message(err, ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        remove_ids = [
            FACTION_GUIDE_ROLE,
            FACTION_LEADER_MAIN_ROLE,
            FACTION_LEADER_ROLE_BY_NAME.get(target_faction),
        ]
        to_remove = [
            interaction.guild.get_role(rid)
            for rid in remove_ids
            if rid and interaction.guild.get_role(rid) in member.roles
        ]

        to_add = []
        for rid in (FACTION_MEMBER_MAIN_ROLE, FACTION_MEMBER_ROLE_BY_NAME.get(target_faction)):
            if rid:
                role = interaction.guild.get_role(rid)
                if role and role not in member.roles:
                    to_add.append(role)

        try:
            if to_remove:
                await member.remove_roles(*to_remove, reason=f"Demoted in {target_faction} by {interaction.user}")
            if to_add:
                await member.add_roles(*to_add, reason=f"Set to Faction Member in {target_faction}")
        except discord.Forbidden:
            return await interaction.followup.send(
                "❌ Missing permissions to update faction roles. Check my role hierarchy.",
                ephemeral=True
            )

        await self.bot.db.log_staff_action(
            action="FACTION_DEMOTE",
            target_id=str(member.id),
            actor_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            note=f"Demoted {member.id} to Faction Member in {target_faction}"
        )

        log_embed = discord.Embed(
            title="⬇️ Faction Demotion",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Member", value=f"{member.mention} (`{member.id}`)", inline=True)
        log_embed.add_field(name="Faction", value=target_faction, inline=True)
        log_embed.add_field(name="New Rank", value="[FM] Faction Member", inline=True)
        log_embed.add_field(name="By", value=f"{interaction.user.mention}", inline=True)
        await self._post_faction_log(interaction.guild, log_embed)

        await interaction.followup.send(
            f"✅ Demoted {member.mention} to **[FM] Faction Member** in **{target_faction}**.",
            ephemeral=True
        )

    @faction_group.command(name="roster", description="View the roster for a faction.")
    @app_commands.describe(faction="Faction name")
    async def roster(
        self,
        interaction: discord.Interaction,
        faction: Optional[str] = None
    ):
        ok, target_faction, err = self._resolve_faction(interaction.user, faction)
        if not ok:
            return await interaction.response.send_message(err, ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        leader_rid = FACTION_LEADER_ROLE_BY_NAME.get(target_faction)
        overseer_rid = FACTION_OVERSEER_ROLE_BY_NAME.get(target_faction)
        member_rid = FACTION_MEMBER_ROLE_BY_NAME.get(target_faction)
        guide_role = interaction.guild.get_role(FACTION_GUIDE_ROLE)

        leaders = []
        overseers = []
        guides = []
        members = []

        for m in interaction.guild.members:
            rids = {r.id for r in m.roles}
            if leader_rid and leader_rid in rids:
                leaders.append(m.mention)
            if overseer_rid and overseer_rid in rids:
                overseers.append(m.mention)
            if guide_role and guide_role in m.roles and (
                (member_rid and member_rid in rids)
                or (leader_rid and leader_rid in rids)
                or get_member_faction(m) == target_faction
            ):
                guides.append(m.mention)
            if member_rid and member_rid in rids:
                members.append(m.mention)

        strike_count = await self.bot.db.get_strike_count(str(interaction.user.id), str(interaction.guild.id))
        status_label, _ = STRIKE_STATUS.get(strike_count, ("✅ Normal", discord.Color.green()))

        embed = discord.Embed(
            title=f"🛡️ {target_faction} — Roster",
            color=FACTION_COLORS.get(target_faction, discord.Color.blurple().value),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="👑 Leaders", value=", ".join(leaders) if leaders else "None", inline=False)
        embed.add_field(name="👁️ Overseers", value=", ".join(overseers) if overseers else "None", inline=False)
        embed.add_field(name="📘 Guides [FG]", value=", ".join(guides) if guides else "None", inline=False)
        embed.add_field(
            name=f"⚔️ Members ({len(members)})",
            value=", ".join(members[:40]) + (f" *+{len(members) - 40} more*" if len(members) > 40 else "")
            if members else "None",
            inline=False
        )
        embed.set_footer(text=f"Faction: {target_faction} · Your strike status: {status_label}")

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(FactionCog(bot))
