"""
cogs/faction.py — /factiondemote slash command
"""
import discord
from discord import app_commands
from discord.ext import commands
from constants import (
    FACTION_COLORS, ALL_FACTION_ROLES,
    get_member_faction, can_use_faction_commands
)
from utils.roblox_group import exile_from_group
import datetime


class FactionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="factiondemote",
        description="Kick a faction member out of the Roblox group and remove their roles."
    )
    @app_commands.describe(
        user="The Discord member to remove",
        roblox_username="Their Roblox username"
    )
    async def factiondemote(self, interaction: discord.Interaction,
                             user: discord.Member, roblox_username: str):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user
        allowed, faction_restriction = can_use_faction_commands(actor)

        if not allowed:
            return await interaction.followup.send(
                "❌ Only faction leaders or faction council may use `/factiondemote`.",
                ephemeral=True
            )

        # ── Target must have a faction member role ────────────────────────────
        target_faction = get_member_faction(user)
        if not target_faction:
            return await interaction.followup.send(
                f"❌ {user.mention} does not have a faction member role.",
                ephemeral=True
            )

        # ── If restricted to a faction, enforce it ────────────────────────────
        if faction_restriction and target_faction != faction_restriction:
            return await interaction.followup.send(
                f"❌ {user.mention} is in **{target_faction}**, not **{faction_restriction}**. "
                "You can only demote members of your own faction.",
                ephemeral=True
            )

        faction_color = FACTION_COLORS.get(target_faction, 0xFF0000)
        guild = interaction.guild

        # ── Strip all faction roles ───────────────────────────────────────────
        roles_removed = []
        for role_id in ALL_FACTION_ROLES:
            role = guild.get_role(role_id)
            if role and role in user.roles:
                roles_removed.append(role)

        if roles_removed:
            await user.remove_roles(
                *roles_removed,
                reason=f"Faction demotion by {actor.display_name}"
            )

        # ── Exile from Roblox group ───────────────────────────────────────────
        success, message = await exile_from_group(roblox_username)

        if not success:
            await interaction.followup.send(
                f"⚠️ Discord roles removed but Roblox exile failed: {message}\n"
                f"You may need to manually remove `{roblox_username}` from the group.",
                ephemeral=True
            )
            return

        # ── Confirmation embed ────────────────────────────────────────────────
        removed_names = ", ".join(r.name for r in roles_removed) if roles_removed else "None"

        embed = discord.Embed(
            title="⬇️ Faction Demotion Applied",
            color=faction_color,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Discord Member", value=user.mention, inline=True)
        embed.add_field(name="Roblox Username", value=f"`{roblox_username}`", inline=True)
        embed.add_field(name="Faction", value=target_faction, inline=True)
        embed.add_field(name="Roles Removed", value=removed_names, inline=False)
        embed.add_field(name="Roblox Action", value=message, inline=False)
        embed.set_footer(text=f"Demoted by {actor.display_name}")
        await interaction.followup.send(embed=embed)

        # ── Log to channel ────────────────────────────────────────────────────
        log_embed = discord.Embed(
            title="📋 Faction Demotion",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Discord", value=f"{user.mention} (`{user.id}`)", inline=True)
        log_embed.add_field(name="Roblox", value=f"`{roblox_username}`", inline=True)
        log_embed.add_field(name="Faction", value=target_faction, inline=True)
        log_embed.add_field(name="Done By", value=actor.mention, inline=True)
        log_embed.add_field(name="Roles Removed", value=removed_names, inline=False)
        await self.bot.log_action(log_embed)

        # ── DM the user ───────────────────────────────────────────────────────
        try:
            dm_embed = discord.Embed(
                title="📉 You Have Been Removed from Your Faction",
                color=faction_color,
                timestamp=datetime.datetime.utcnow()
            )
            dm_embed.description = (
                f"You have been removed from **{target_faction}**.\n\n"
                f"• Your faction roles have been removed\n"
                f"• You have been exiled from the Afternight Factions Roblox group\n\n"
                f"If you have questions, contact your faction leader."
            )
            dm_embed.set_footer(text="Afternight Faction System")
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass


async def setup(bot):
    await bot.add_cog(FactionCog(bot))