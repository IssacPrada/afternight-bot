"""
cogs/strikes.py — Faction Strikes & Staff Strikes slash commands
"""
import datetime
import discord
from discord import app_commands
from discord.ext import commands
from constants import (
    FACTION_STRIKE_LOG_CHANNEL_ID,
    MOD_LOG_CHANNEL_ID,
    can_use_faction_strike,
    has_fire_permission,
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

    # ── Faction Strikes ───────────────────────────────────────────────────────

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

        if not isinstance(actor, discord.Member) or not guild or not can_use_faction_strike(actor):
            return await interaction.followup.send(
                "❌ You do not have permission to issue faction strikes.",
                ephemeral=True
            )

        count = await self.bot.db.add_faction_strike(
            str(user.id), str(actor.id), str(guild.id), reason
        )

        log_embed = discord.Embed(
            title="⚡ Faction Strike Issued",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Target", value=f"{user.mention} (`{user.id}`)", inline=True)
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

        guild = interaction.guild
        if not guild:
            return await interaction.followup.send(
                "❌ This command can only be used inside a server.",
                ephemeral=True
            )

        strikes = await self.bot.db.get_faction_strikes(str(user.id), str(guild.id))

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
                reason = entry.get("reason", "No reason provided.")
                mod_id = entry.get("moderator_id") or entry.get("actor_id")
                mod_text = f"<@{mod_id}>" if mod_id else "Unknown"
                lines.append(f"**{idx}.** {reason} *(by {mod_text})*")
            embed.description = "\n".join(lines)
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

        if not isinstance(actor, discord.Member) or not guild or not can_use_faction_strike(actor):
            return await interaction.followup.send(
                "❌ You do not have permission to clear faction strikes.",
                ephemeral=True
            )

        cleared = await self.bot.db.clear_faction_strikes(str(user.id), str(guild.id))

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

    # ── Staff Strikes ─────────────────────────────────────────────────────────

    @app_commands.command(
        name="staffstrike",
        description="Issue a strike to a staff member."
    )
    @app_commands.describe(
        user="The staff member receiving the strike",
        reason="Reason for the strike"
    )
    async def staffstrike(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = "No reason provided."
    ):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user
        guild = interaction.guild

        if not isinstance(actor, discord.Member) or not guild or not has_fire_permission(actor):
            return await interaction.followup.send(
                "❌ You do not have permission to issue staff strikes.",
                ephemeral=True
            )

        count = await self.bot.db.add_staff_strike(
            str(user.id), str(actor.id), str(guild.id), reason
        )

        log_embed = discord.Embed(
            title="📋 Staff Strike Issued",
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Target", value=f"{user.mention} (`{user.id}`)", inline=True)
        log_embed.add_field(name="Issued By", value=actor.mention, inline=True)
        log_embed.add_field(name="Total Staff Strikes", value=str(count), inline=True)
        log_embed.add_field(name="Reason", value=reason, inline=False)
        await self._post_log(guild, MOD_LOG_CHANNEL_ID, log_embed)

        confirm = discord.Embed(
            title="✅ Staff Strike Issued",
            description=(
                f"{user.mention} now has **{count}** staff strike(s).\n"
                f"**Reason:** {reason}"
            ),
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=confirm, ephemeral=True)

        try:
            dm = discord.Embed(
                title="📋 Staff Strike Notice",
                description=(
                    f"You have received a staff strike in **{guild.name}**.\n\n"
                    f"**Total Strikes:** {count}\n"
                    f"**Reason:** {reason}"
                ),
                color=discord.Color.red(),
                timestamp=datetime.datetime.utcnow()
            )
            await user.send(embed=dm)
        except discord.Forbidden:
            pass

    @app_commands.command(
        name="viewstaffstrikes",
        description="View staff strikes for a staff member."
    )
    @app_commands.describe(user="The staff member to check")
    async def viewstaffstrikes(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if not guild:
            return await interaction.followup.send(
                "❌ This command can only be used inside a server.",
                ephemeral=True
            )

        strikes = await self.bot.db.get_staff_strikes(str(user.id), str(guild.id))

        embed = discord.Embed(
            title=f"📋 Staff Strikes — {user.display_name}",
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)

        if not strikes:
            embed.description = f"{user.mention} has no staff strikes on record."
        else:
            lines = []
            for idx, entry in enumerate(strikes, start=1):
                reason = entry.get("reason", "No reason provided.")
                mod_id = entry.get("moderator_id") or entry.get("actor_id")
                mod_text = f"<@{mod_id}>" if mod_id else "Unknown"
                lines.append(f"**{idx}.** {reason} *(by {mod_text})*")
            embed.description = "\n".join(lines)
            embed.add_field(name="Total Strikes", value=str(len(strikes)), inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="clearstaffstrikes",
        description="Clear all staff strikes for a staff member."
    )
    @app_commands.describe(user="The staff member whose strikes will be cleared")
    async def clearstaffstrikes(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user
        guild = interaction.guild

        if not isinstance(actor, discord.Member) or not guild or not has_fire_permission(actor):
            return await interaction.followup.send(
                "❌ You do not have permission to clear staff strikes.",
                ephemeral=True
            )

        cleared = await self.bot.db.clear_staff_strikes(str(user.id), str(guild.id))

        log_embed = discord.Embed(
            title="🧹 Staff Strikes Cleared",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Target", value=f"{user.mention} (`{user.id}`)", inline=True)
        log_embed.add_field(name="Cleared By", value=actor.mention, inline=True)
        log_embed.add_field(name="Strikes Cleared", value=str(cleared), inline=True)
        await self._post_log(guild, MOD_LOG_CHANNEL_ID, log_embed)

        await interaction.followup.send(
            f"✅ Cleared **{cleared}** staff strike(s) for {user.mention}.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(StrikesCog(bot))
