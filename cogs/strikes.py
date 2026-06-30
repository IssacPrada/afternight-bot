"""
cogs/strikes.py — /strike, /viewstrike, /clearstrikes slash commands
"""
import discord
from discord import app_commands
from discord.ext import commands
from constants import (
    FACTION_COLORS, STRIKE_STATUS,
    get_member_faction, can_use_faction_commands
)
from utils.roblox_group import exile_from_group
import datetime


class StrikesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── /strike ───────────────────────────────────────────────────────────────

    @app_commands.command(name="strike", description="Issue a strike to a faction member.")
    @app_commands.describe(
        user="The Discord member to strike",
        reason="Reason for the strike",
        roblox_username="Their Roblox username (required at 3 strikes for group exile)"
    )
    async def strike(self, interaction: discord.Interaction,
                     user: discord.Member, reason: str,
                     roblox_username: str = None):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user
        allowed, faction_restriction = can_use_faction_commands(actor)

        if not allowed:
            return await interaction.followup.send(
                "❌ Only faction leaders or faction council may issue strikes.",
                ephemeral=True
            )

        # ── Target must have a faction member role ────────────────────────────
        target_faction = get_member_faction(user)
        if not target_faction:
            return await interaction.followup.send(
                f"❌ {user.mention} does not have a faction member role and cannot be struck.",
                ephemeral=True
            )

        # ── If restricted to a faction, enforce it ────────────────────────────
        if faction_restriction and target_faction != faction_restriction:
            return await interaction.followup.send(
                f"❌ {user.mention} is in **{target_faction}**, not **{faction_restriction}**. "
                "You can only strike members of your own faction.",
                ephemeral=True
            )

        guild = interaction.guild
        new_count = await self.bot.db.add_strike(
            str(user.id), str(guild.id), target_faction, reason, str(actor.id)
        )

        status_text, status_color = STRIKE_STATUS.get(min(new_count, 3), STRIKE_STATUS[3])
        faction_color = FACTION_COLORS.get(target_faction, 0xFF0000)

        # ── Confirmation embed ────────────────────────────────────────────────
        embed = discord.Embed(
            title="⚡ Strike Issued",
            color=faction_color,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Member", value=user.mention, inline=True)
        embed.add_field(name="Strikes", value=f"**{new_count}/3**", inline=True)
        embed.add_field(name="Status", value=status_text, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Faction", value=target_faction, inline=True)
        embed.set_footer(text=f"Issued by {actor.display_name}")
        await interaction.followup.send(embed=embed)

        # ── Log to channel ────────────────────────────────────────────────────
        log_embed = discord.Embed(
            title="📋 Strike Issued",
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Target", value=f"{user.mention} (`{user.id}`)", inline=True)
        log_embed.add_field(name="Issued By", value=actor.mention, inline=True)
        log_embed.add_field(name="Faction", value=target_faction, inline=True)
        log_embed.add_field(name="Strike Count", value=f"{new_count}/3", inline=True)
        log_embed.add_field(name="Reason", value=reason, inline=False)
        await self.bot.log_action(log_embed)

        # ── DM the user ───────────────────────────────────────────────────────
        try:
            dm_embed = discord.Embed(
                title=f"⚠️ You Have Been Striked — {target_faction}",
                color=faction_color,
                timestamp=datetime.datetime.utcnow()
            )
            dm_embed.description = (
                f"You have been **Striked** in **{target_faction}**.\n\n"
                f"You are now **{new_count}/3** strikes.\n\n"
                f"**Reason:** {reason}\n\n"
                f"If you continue this behavior you may be:\n"
                f"• Striked again\n"
                f"• Removed from this faction\n\n"
                f"If you have questions, contact your faction leader or a faction elder."
            )
            dm_embed.set_footer(text="Afternight Faction System")
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        # ── At 3 strikes → exile from Roblox group ────────────────────────────
        if new_count >= 3:
            warn_embed = discord.Embed(
                title="💀 3 Strikes Reached",
                color=discord.Color.dark_red(),
                timestamp=datetime.datetime.utcnow()
            )

            if roblox_username:
                success, message = await exile_from_group(roblox_username)
                warn_embed.description = (
                    f"{user.mention} has reached **3/3 strikes**.\n\n"
                    f"**Roblox Group Action:** {message}"
                )
                if success:
                    try:
                        exile_dm = discord.Embed(
                            title="🚫 Removed from Afternight Factions",
                            color=discord.Color.dark_red(),
                            timestamp=datetime.datetime.utcnow()
                        )
                        exile_dm.description = (
                            f"You have reached **3/3 strikes** in **{target_faction}** "
                            f"and have been exiled from the Afternight Factions Roblox group.\n\n"
                            f"If you believe this was in error, contact your faction leader."
                        )
                        exile_dm.set_footer(text="Afternight Faction System")
                        await user.send(embed=exile_dm)
                    except discord.Forbidden:
                        pass
            else:
                warn_embed.description = (
                    f"{user.mention} has reached **3/3 strikes** and is eligible for removal.\n\n"
                    f"⚠️ No Roblox username was provided — use `/strike` again with "
                    f"`roblox_username:` filled in to exile them from the group."
                )

            await interaction.channel.send(embed=warn_embed)

    # ── /viewstrike ───────────────────────────────────────────────────────────

    @app_commands.command(name="viewstrike", description="View strikes for a faction member.")
    @app_commands.describe(user="The member to check")
    async def viewstrike(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer()

        actor = interaction.user
        allowed, faction_restriction = can_use_faction_commands(actor)

        if not allowed:
            return await interaction.followup.send(
                "❌ Only faction leaders or faction council may view strikes.",
                ephemeral=True
            )

        target_faction = get_member_faction(user)

        # ── If restricted to a faction, enforce it ────────────────────────────
        if faction_restriction and target_faction != faction_restriction:
            return await interaction.followup.send(
                f"❌ {user.mention} is not in your faction.", ephemeral=True
            )

        guild = interaction.guild
        strikes = await self.bot.db.get_strikes(str(user.id), str(guild.id))
        count = len(strikes)
        status_text, status_color = STRIKE_STATUS.get(min(count, 3), STRIKE_STATUS[3])

        embed = discord.Embed(
            title=f"📋 STRIKES — {user.display_name}",
            color=status_color,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Total Strikes", value=f"**{count}/3**", inline=True)
        embed.add_field(name="Status", value=status_text, inline=True)
        if target_faction:
            embed.add_field(name="Faction", value=target_faction, inline=True)
        else:
            embed.add_field(name="\u200b", value="\u200b", inline=True)

        if strikes:
            reasons_text = ""
            for i, strike in enumerate(strikes[:3], 1):
                date = strike["created_at"][:10]
                reasons_text += f"**{i}.** {strike['reason']} *({date})*\n"
            embed.add_field(name="Reasons", value=reasons_text, inline=False)
        else:
            embed.add_field(name="Reasons", value="None", inline=False)

        embed.set_footer(text=f"User ID: {user.id}")
        await interaction.followup.send(embed=embed)

    # ── /clearstrikes ─────────────────────────────────────────────────────────

    @app_commands.command(name="clearstrikes", description="Clear all strikes for a member.")
    @app_commands.describe(user="The member whose strikes to clear")
    async def clearstrikes(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user
        allowed, faction_restriction = can_use_faction_commands(actor)

        if not allowed:
            return await interaction.followup.send(
                "❌ Only faction leaders or faction council may clear strikes.",
                ephemeral=True
            )

        target_faction = get_member_faction(user)

        # ── If restricted to a faction, enforce it ────────────────────────────
        if faction_restriction and target_faction != faction_restriction:
            return await interaction.followup.send(
                f"❌ {user.mention} is not in your faction.", ephemeral=True
            )

        guild = interaction.guild
        removed = await self.bot.db.clear_strikes(str(user.id), str(guild.id))

        embed = discord.Embed(
            title="✅ Strikes Cleared",
            description=f"Cleared **{removed}** strike(s) from {user.mention}.",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text=f"Cleared by {actor.display_name}")
        await interaction.followup.send(embed=embed)

        log_embed = discord.Embed(
            title="📋 Strikes Cleared",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Target", value=user.mention, inline=True)
        log_embed.add_field(name="Cleared By", value=actor.mention, inline=True)
        log_embed.add_field(name="Removed", value=f"{removed} strike(s)", inline=True)
        await self.bot.log_action(log_embed)


async def setup(bot):
    await bot.add_cog(StrikesCog(bot))