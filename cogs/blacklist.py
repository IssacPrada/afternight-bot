"""
cogs/blacklist.py — /blacklist, /unblacklist slash commands
"""
import discord
from discord import app_commands
from discord.ext import commands
from constants import (
    FACTION_COLORS, ALL_FACTION_ROLES,
    BLACKLIST_CHANNEL_ID,
    can_use_blacklist
)
from utils.roblox_group import exile_from_group, get_roblox_user_id, get_xcsrf_token, HEADERS, GROUP_ID
import aiohttp
import datetime


async def unban_from_group(roblox_username: str) -> tuple[bool, str]:
    """Unban a user from the Roblox group."""
    user_id = await get_roblox_user_id(roblox_username)
    if not user_id:
        return False, f"Could not find Roblox user: `{roblox_username}`"
    try:
        token = await get_xcsrf_token()
        headers = {**HEADERS, "x-csrf-token": token}
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"https://groups.roblox.com/v1/groups/{GROUP_ID}/bans/{user_id}",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    return True, f"✅ `{roblox_username}` has been unbanned from the group."
                else:
                    error = await resp.json()
                    msg = error.get("errors", [{}])[0].get("message", "Unknown error")
                    return False, f"❌ Roblox API error: {msg}"
    except Exception as e:
        return False, f"❌ Exception: {str(e)}"


async def ban_from_group(roblox_username: str) -> tuple[bool, str]:
    """Ban a user from the Roblox group."""
    user_id = await get_roblox_user_id(roblox_username)
    if not user_id:
        return False, f"Could not find Roblox user: `{roblox_username}`"
    try:
        token = await get_xcsrf_token()
        headers = {**HEADERS, "x-csrf-token": token}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://groups.roblox.com/v1/groups/{GROUP_ID}/bans/{user_id}",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    return True, f"✅ `{roblox_username}` has been banned from the group."
                else:
                    error = await resp.json()
                    msg = error.get("errors", [{}])[0].get("message", "Unknown error")
                    return False, f"❌ Roblox API error: {msg}"
    except Exception as e:
        return False, f"❌ Exception: {str(e)}"


def build_blacklist_embed(entries: list, guild: discord.Guild) -> discord.Embed:
    """Build the blacklist tracking embed."""
    embed = discord.Embed(
        title="🚫 Faction Blacklist",
        description="Members blacklisted from all Afternight Factions.",
        color=discord.Color.dark_red(),
        timestamp=datetime.datetime.utcnow()
    )

    if not entries:
        embed.add_field(name="No Blacklisted Members", value="The blacklist is currently empty.", inline=False)
        return embed

    for entry in entries:
        user = guild.get_member(int(entry["user_id"]))
        user_str = user.mention if user else f"<@{entry['user_id']}>"
        roblox = entry.get("roblox_username") or "N/A"
        date = entry.get("created_at", "")[:10]
        by = guild.get_member(int(entry["blacklisted_by"]))
        by_str = by.display_name if by else f"ID: {entry['blacklisted_by']}"

        embed.add_field(
            name=f"🔴 {user_str} — {entry['faction']}",
            value=(
                f"**Roblox:** `{roblox}`\n"
                f"**Reason:** {entry['reason']}\n"
                f"**Blacklisted by:** {by_str}\n"
                f"**Date:** {date}"
            ),
            inline=False
        )

    embed.set_footer(text=f"Total blacklisted: {len(entries)}")
    return embed


class BlacklistCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _update_blacklist_channel(self, guild: discord.Guild):
        """Rebuild and update the blacklist embed in the tracking channel."""
        channel = guild.get_channel(BLACKLIST_CHANNEL_ID)
        if not channel:
            return

        entries = await self.bot.db.get_all_blacklisted(str(guild.id))
        embed = build_blacklist_embed(entries, guild)

        # Try to find and edit the existing pinned message
        async for message in channel.history(limit=20):
            if message.author == self.bot.user and message.embeds:
                if message.embeds[0].title == "🚫 Faction Blacklist":
                    await message.edit(embed=embed)
                    return

        # No existing message found — send a new one
        await channel.send(embed=embed)

    # ── /blacklist ────────────────────────────────────────────────────────────

    @app_commands.command(
        name="blacklist",
        description="Blacklist a member from a faction and ban them from the Roblox group."
    )
    @app_commands.describe(
        user="The Discord member to blacklist",
        reason="Reason for the blacklist",
        roblox_username="Their Roblox username (to ban from group)"
    )
    async def blacklist(self, interaction: discord.Interaction,
                        user: discord.Member, reason: str,
                        roblox_username: str = None):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user
        allowed, actor_faction = can_use_blacklist(actor)

        if not allowed:
            return await interaction.followup.send(
                "❌ Only faction leaders or faction council may use `/blacklist`.",
                ephemeral=True
            )

        # ── Check if already blacklisted ──────────────────────────────────────
        existing = await self.bot.db.is_blacklisted(str(user.id), str(interaction.guild.id))
        if existing:
            return await interaction.followup.send(
                f"❌ {user.mention} is already blacklisted from **{existing['faction']}**.",
                ephemeral=True
            )

        # ── Determine which faction this is for ───────────────────────────────
        # If actor oversees a specific faction, use that
        # If general council (actor_faction is None), use target's current faction
        target_faction = actor_faction
        if not target_faction:
            from constants import get_member_faction
            target_faction = get_member_faction(user)
            if not target_faction:
                # If they have no faction role just ask for clarification
                return await interaction.followup.send(
                    f"❌ {user.mention} has no faction role. Please specify which "
                    "faction they are being blacklisted from by assigning them the "
                    "faction role first.",
                    ephemeral=True
                )

        faction_color = FACTION_COLORS.get(target_faction, 0xFF0000)
        guild = interaction.guild

        # ── Remove all faction roles ──────────────────────────────────────────
        roles_removed = []
        for role_id in ALL_FACTION_ROLES:
            role = guild.get_role(role_id)
            if role and role in user.roles:
                roles_removed.append(role)

        if roles_removed:
            await user.remove_roles(
                *roles_removed,
                reason=f"Blacklisted by {actor.display_name}: {reason}"
            )

        # ── Ban from Roblox group ─────────────────────────────────────────────
        roblox_result = "No Roblox username provided."
        if roblox_username:
            # First exile them (kick) then ban
            await exile_from_group(roblox_username)
            success, roblox_result = await ban_from_group(roblox_username)

        # ── Save to database ──────────────────────────────────────────────────
        bl_id = await self.bot.db.add_blacklist(
            str(user.id), str(guild.id), target_faction,
            reason, str(actor.id), roblox_username
        )

        # ── DM the user ───────────────────────────────────────────────────────
        try:
            dm_embed = discord.Embed(
                title="🚫 You Have Been Blacklisted",
                color=discord.Color.dark_red(),
                timestamp=datetime.datetime.utcnow()
            )
            dm_embed.description = (
                f"You have been **blacklisted** from **{target_faction}** "
                f"in Afternight Factions.\n\n"
                f"**Reason:** {reason}\n\n"
                f"**What this means:**\n"
                f"• You have been removed from the faction\n"
                f"• You have been banned from the Afternight Factions Roblox group\n"
                f"• Any faction roles will be automatically removed if re-acquired\n\n"
                f"**How to Appeal:**\n"
                f"Contact your **Faction Council** or **Faction Leader** to submit "
                f"an appeal. Once they are available, they will review your case and "
                f"get back to you."
            )
            dm_embed.set_footer(text="Afternight Faction System")
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        # ── Confirmation embed ────────────────────────────────────────────────
        removed_names = ", ".join(r.name for r in roles_removed) if roles_removed else "None"
        embed = discord.Embed(
            title="🚫 Member Blacklisted",
            color=discord.Color.dark_red(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Member", value=user.mention, inline=True)
        embed.add_field(name="Faction", value=target_faction, inline=True)
        embed.add_field(name="Blacklisted By", value=actor.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Roles Removed", value=removed_names, inline=False)
        embed.add_field(name="Roblox Action", value=roblox_result, inline=False)
        await interaction.followup.send(embed=embed)

        # ── Update blacklist channel ──────────────────────────────────────────
        await self._update_blacklist_channel(guild)

        # ── Log to log channel ────────────────────────────────────────────────
        log_embed = discord.Embed(
            title="📋 Member Blacklisted",
            color=discord.Color.dark_red(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Target", value=f"{user.mention} (`{user.id}`)", inline=True)
        log_embed.add_field(name="By", value=actor.mention, inline=True)
        log_embed.add_field(name="Faction", value=target_faction, inline=True)
        log_embed.add_field(name="Roblox", value=f"`{roblox_username or 'N/A'}`", inline=True)
        log_embed.add_field(name="Reason", value=reason, inline=False)
        await self.bot.log_action(log_embed)

    # ── /unblacklist ──────────────────────────────────────────────────────────

    @app_commands.command(
        name="unblacklist",
        description="Remove a member from the blacklist and unban from the Roblox group."
    )
    @app_commands.describe(user="The Discord member to unblacklist")
    async def unblacklist(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user
        allowed, actor_faction = can_use_blacklist(actor)

        if not allowed:
            return await interaction.followup.send(
                "❌ Only faction leaders or faction council may use `/unblacklist`.",
                ephemeral=True
            )

        guild = interaction.guild

        # ── Check if actually blacklisted ─────────────────────────────────────
        entry = await self.bot.db.is_blacklisted(str(user.id), str(guild.id))
        if not entry:
            return await interaction.followup.send(
                f"❌ {user.mention} is not currently blacklisted.",
                ephemeral=True
            )

        # ── Council overseers can only unblacklist their own faction ──────────
        if actor_faction and entry["faction"] != actor_faction:
            return await interaction.followup.send(
                f"❌ {user.mention} is blacklisted from **{entry['faction']}**, "
                f"not **{actor_faction}**.",
                ephemeral=True
            )

        # ── Unban from Roblox group ───────────────────────────────────────────
        roblox_result = "No Roblox username on record."
        roblox_username = entry.get("roblox_username")
        if roblox_username:
            success, roblox_result = await unban_from_group(roblox_username)

        # ── Remove from database ──────────────────────────────────────────────
        await self.bot.db.remove_blacklist(str(user.id), str(guild.id))

        # ── DM the user ───────────────────────────────────────────────────────
        faction_color = FACTION_COLORS.get(entry["faction"], 0x00FF00)
        try:
            dm_embed = discord.Embed(
                title="✅ Blacklist Removed",
                color=discord.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            dm_embed.description = (
                f"Your blacklist from **{entry['faction']}** has been lifted.\n\n"
                f"• You are no longer banned from the Afternight Factions Roblox group\n"
                f"• You may now rejoin the faction if invited\n\n"
                f"Welcome back to Afternight."
            )
            dm_embed.set_footer(text="Afternight Faction System")
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        # ── Confirmation ──────────────────────────────────────────────────────
        embed = discord.Embed(
            title="✅ Blacklist Removed",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Member", value=user.mention, inline=True)
        embed.add_field(name="Faction", value=entry["faction"], inline=True)
        embed.add_field(name="Removed By", value=actor.mention, inline=True)
        embed.add_field(name="Roblox Action", value=roblox_result, inline=False)
        await interaction.followup.send(embed=embed)

        # ── Update blacklist channel ──────────────────────────────────────────
        await self._update_blacklist_channel(guild)

        # ── Log ───────────────────────────────────────────────────────────────
        log_embed = discord.Embed(
            title="📋 Blacklist Removed",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Target", value=f"{user.mention} (`{user.id}`)", inline=True)
        log_embed.add_field(name="By", value=actor.mention, inline=True)
        log_embed.add_field(name="Faction", value=entry["faction"], inline=True)
        log_embed.add_field(name="Roblox", value=f"`{roblox_username or 'N/A'}`", inline=True)
        await self.bot.log_action(log_embed)

    # ── Auto-remove faction roles on role add ─────────────────────────────────

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """
        If a blacklisted member somehow gets a faction role,
        remove it instantly.
        """
        added_roles = set(after.roles) - set(before.roles)
        if not added_roles:
            return

        entry = await self.bot.db.is_blacklisted(str(after.id), str(after.guild.id))
        if not entry:
            return

        faction_role_ids = set(ALL_FACTION_ROLES)
        roles_to_strip = [r for r in added_roles if r.id in faction_role_ids]

        if roles_to_strip:
            await after.remove_roles(
                *roles_to_strip,
                reason="Blacklisted — faction roles auto-removed"
            )
            try:
                dm_embed = discord.Embed(
                    title="🚫 Role Removed — Blacklisted",
                    color=discord.Color.dark_red()
                )
                dm_embed.description = (
                    f"You are blacklisted from **{entry['faction']}** and cannot "
                    f"hold faction roles. The role was automatically removed.\n\n"
                    f"To appeal, contact your **Faction Council** or **Faction Leader**."
                )
                await after.send(embed=dm_embed)
            except discord.Forbidden:
                pass


async def setup(bot):
    await bot.add_cog(BlacklistCog(bot))