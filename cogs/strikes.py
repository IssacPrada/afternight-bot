"""
cogs/strikes.py — Faction strike slash commands (/strike, /viewstrike, /clearstrikes)

Staff strikes (/staffstrike, /staffstrikes, /clearstaffstrikes) live in cogs/moderation.py.
"""
import datetime
import discord
from discord import app_commands
from discord.ext import commands
from constants import (
    FACTION_STRIKE_LOG_CHANNEL_ID,
    can_manage_faction_strikes,
    get_member_faction,
)


class StrikesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _post_log(
        self,
        guild: discord.Guild | None,
        channel_id: int,
        embed: discord.Embed
    ):
        if guild:
            channel = guild.get_channel(channel_id)
            if isinstance(channel, discord.TextChannel):
                await channel.send(embed=embed)
                return
        await self.bot.log_action(embed)

    @app_commands.command(
        name="strike",
        description="Issue a strike to a faction member."
    )
    @app_commands.describe(
        user="The faction member receiving the strike",
        reason="Reason for the strike"
    )
    async def strike(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = "No reason provided."
    ):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user
        guild = interaction.guild

        if not isinstance(actor, discord.Member) or not guild or not can_manage_faction_strikes(actor):
            return await interaction.followup.send(
                "❌ Only Owner, Co-Owner, Community Manager, Faction Leaders, or Faction Overseers may manage faction strikes.",
                ephemeral=True
            )

        faction = get_member_faction(user) or "Unknown"

        # Database.add_strike(user_id, guild_id, faction, reason, struck_by) -> total count
        count = await self.bot.db.add_strike(
            str(user.id), str(guild.id), faction, reason, str(actor.id)
        )

        log_embed = discord.Embed(
            title="⚡ Faction Strike Issued",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Target", value=f"{user.mention} (`{user.id}`)", inline=True)
        log_embed.add_field(name="Faction", value=faction, inline=True)
        log_embed.add_field(name="Issued By", value=actor.mention, inline=True)
        log_embed.add_field(name="Total Strikes", value=str(count), inline=True)
        log_embed.add_field(name="Reason", value=reason, inline=False)
        await self._post_log(guild, FACTION_STRIKE_LOG_CHANNEL_ID, log_embed)

        confirm = discord.Embed(
            title="✅ Faction Strike Issued",
            description=(
                f"{user.mention} now has **{count}** faction strike(s).\n"
                f"**Reason:** {reason}"
            ),
            color=discord.Color.orange()
        )
        await interaction.followup.send(embed=confirm, ephemeral=True)

        try:
            dm = discord.Embed(
                title="⚡ Faction Strike Notice",
                description=(
                    f"You have received a faction strike in **{guild.name}**.\n\n"
                    f"**Total Strikes:** {count}\n"
                    f"**Reason:** {reason}"
                ),
                color=discord.Color.orange(),
                timestamp=datetime.datetime.utcnow()
            )
            await user.send(embed=dm)
        except discord.Forbidden:
            pass

    @app_commands.command(
        name="viewstrike",
        description="View faction strikes for a member."
    )
    @app_commands.describe(user="The faction member to check")
    async def viewstrike(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user
        guild = interaction.guild

        if not isinstance(actor, discord.Member) or not guild or not can_manage_faction_strikes(actor):
            return await interaction.followup.send(
                "❌ Only Owner, Co-Owner, Community Manager, Faction Leaders, or Faction Overseers may view faction strikes.",
                ephemeral=True
            )

        strikes = await self.bot.db.get_strikes(str(user.id), str(guild.id))

        embed = discord.Embed(
            title=f"⚡ Faction Strikes — {user.display_name}",
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)

        if not strikes:
            embed.description = f"{user.mention} has no faction strikes on record."
        else:
            lines = []
            for idx, entry in enumerate(strikes, start=1):
                reason = entry.get("reason") or "No reason provided."
                mod_id = entry.get("struck_by")
                mod_text = f"<@{mod_id}>" if mod_id else "Unknown"
                lines.append(f"**{idx}.** {reason} *(by {mod_text})*")
            embed.description = "\n".join(lines)[:4000]
            embed.add_field(name="Total Strikes", value=str(len(strikes)), inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="clearstrikes",
        description="Clear all faction strikes for a member."
    )
    @app_commands.describe(user="The faction member whose strikes will be cleared")
    async def clearstrikes(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user
        guild = interaction.guild

        if not isinstance(actor, discord.Member) or not guild or not can_manage_faction_strikes(actor):
            return await interaction.followup.send(
                "❌ Only Owner, Co-Owner, Community Manager, Faction Leaders, or Faction Overseers may clear faction strikes.",
                ephemeral=True
            )

        cleared = await self.bot.db.clear_strikes(str(user.id), str(guild.id))

        log_embed = discord.Embed(
            title="🧹 Faction Strikes Cleared",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Target", value=f"{user.mention} (`{user.id}`)", inline=True)
        log_embed.add_field(name="Cleared By", value=actor.mention, inline=True)
        log_embed.add_field(name="Strikes Cleared", value=str(cleared), inline=True)
        await self._post_log(guild, FACTION_STRIKE_LOG_CHANNEL_ID, log_embed)

        await interaction.followup.send(
            f"✅ Cleared **{cleared}** faction strike(s) for {user.mention}.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(StrikesCog(bot))
