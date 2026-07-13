"""
cogs/moderation.py — /warn, /viewwarns, /clearwarns commands
"""
import discord
from discord import app_commands
from discord.ext import commands
from constants import is_staff
import datetime

# ── Config ────────────────────────────────────────────────────────────────────
WARN_LOG_CHANNEL  = 1388022887725924372
APPEAL_SERVER     = "https://discord.gg/dQAbatSEcw"


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── /warn ─────────────────────────────────────────────────────────────────

    @app_commands.command(
        name="warn",
        description="Warn a community member."
    )
    @app_commands.describe(
        user="The member to warn",
        reason="Reason for the warning",
        evidence="Evidence link or description (optional)"
    )
    async def warn(self, interaction: discord.Interaction,
                   user: discord.Member,
                   reason: str,
                   evidence: str = "None provided"):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user

        if not is_staff(actor):
            return await interaction.followup.send(
                "❌ Only staff members may issue warnings.",
                ephemeral=True
            )

        if user.bot:
            return await interaction.followup.send(
                "❌ You cannot warn a bot.",
                ephemeral=True
            )

        if user == actor:
            return await interaction.followup.send(
                "❌ You cannot warn yourself.",
                ephemeral=True
            )

        guild = interaction.guild

        # ── Add warn to database ──────────────────────────────────────────────
        await self.bot.db.add_warn(
            str(user.id), str(guild.id), reason, evidence, str(actor.id)
        )

        # ── Get all warns for this user ───────────────────────────────────────
        warns = await self.bot.db.get_warns(str(user.id), str(guild.id))
        warn_count = len(warns)

        # ── Log embed ─────────────────────────────────────────────────────────
        log_embed = discord.Embed(
            title="⚠️ Warning Issued",
            color=discord.Color.yellow(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.set_thumbnail(url=user.display_avatar.url)
        log_embed.add_field(
            name="Discord ID",
            value=f"{user.mention} (`{user.id}`)",
            inline=False
        )
        log_embed.add_field(name="Reason",   value=reason,   inline=False)
        log_embed.add_field(name="Evidence", value=evidence, inline=False)
        log_embed.add_field(
            name="Warned By",
            value=f"{actor.mention} (`{actor.id}`)",
            inline=True
        )
        log_embed.add_field(
            name="Total Warnings",
            value=f"**{warn_count}** warning(s)",
            inline=True
        )
        log_embed.set_footer(text=f"User ID: {user.id}")

        # ── Previous warnings ─────────────────────────────────────────────────
        if warn_count > 1:
            prev_text = ""
            for i, w in enumerate(warns[:-1], 1):
                date = str(w.get("created_at", ""))[:10]
                prev_text += f"**{i}.** {w['reason']} *({date})*\n"
            log_embed.add_field(
                name=f"Previous Warnings ({warn_count - 1})",
                value=prev_text[:1024],
                inline=False
            )

        # ── Send to log channel ───────────────────────────────────────────────
        log_channel = guild.get_channel(WARN_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        # ── Confirmation to staff ─────────────────────────────────────────────
        confirm_embed = discord.Embed(
            title="✅ Warning Issued Successfully",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        confirm_embed.add_field(name="Member",   value=user.mention,  inline=True)
        confirm_embed.add_field(name="Reason",   value=reason,        inline=True)
        confirm_embed.add_field(
            name="Total Warnings",
            value=f"{warn_count} warning(s)",
            inline=True
        )
        await interaction.followup.send(embed=confirm_embed, ephemeral=True)

        # ── DM the user ───────────────────────────────────────────────────────
        try:
            dm_embed = discord.Embed(
                title="⚠️ You Have Been Warned",
                color=discord.Color.yellow(),
                timestamp=datetime.datetime.utcnow()
            )
            dm_embed.description = (
                f"You have been warned in **Afternight Legacies** for **{reason}**.\n\n"
                f"If this is a mistake you are free to open a ticket in our appeal server.\n"
                f"{APPEAL_SERVER}"
            )
            dm_embed.set_footer(text="Afternight Moderation")
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass

    # ── /viewwarns ────────────────────────────────────────────────────────────

    @app_commands.command(
        name="viewwarns",
        description="View warnings for a member."
    )
    @app_commands.describe(user="The member to check")
    async def viewwarns(self, interaction: discord.Interaction,
                        user: discord.Member):
        await interaction.response.defer()

        if not is_staff(interaction.user):
            return await interaction.followup.send(
                "❌ Only staff members may view warnings.",
                ephemeral=True
            )

        guild = interaction.guild
        warns = await self.bot.db.get_warns(str(user.id), str(guild.id))
        count = len(warns)

        embed = discord.Embed(
            title=f"⚠️ Warnings — {user.display_name}",
            color=discord.Color.yellow() if count > 0 else discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(
            name="Total Warnings",
            value=f"**{count}** warning(s)",
            inline=True
        )
        embed.add_field(
            name="Discord ID",
            value=f"`{user.id}`",
            inline=True
        )

        if warns:
            for i, w in enumerate(warns, 1):
                date     = str(w.get("created_at", ""))[:10]
                issuer   = guild.get_member(int(w["warned_by"]))
                issuer_str = issuer.display_name if issuer else f"ID: {w['warned_by']}"
                evidence = w.get("evidence", "None provided")
                embed.add_field(
                    name=f"Warning {i} — {date}",
                    value=(
                        f"**Reason:** {w['reason']}\n"
                        f"**Evidence:** {evidence}\n"
                        f"**Issued by:** {issuer_str}"
                    ),
                    inline=False
                )
        else:
            embed.add_field(
                name="No Warnings",
                value="This member has no warnings.",
                inline=False
            )

        embed.set_footer(text=f"User ID: {user.id}")
        await interaction.followup.send(embed=embed)

    # ── /clearwarns ───────────────────────────────────────────────────────────

    @app_commands.command(
        name="clearwarns",
        description="Clear all warnings for a member."
    )
    @app_commands.describe(user="The member whose warnings to clear")
    async def clearwarns(self, interaction: discord.Interaction,
                         user: discord.Member):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user

        if not is_staff(actor):
            return await interaction.followup.send(
                "❌ Only staff members may clear warnings.",
                ephemeral=True
            )

        guild   = interaction.guild
        removed = await self.bot.db.clear_warns(str(user.id), str(guild.id))

        embed = discord.Embed(
            title="✅ Warnings Cleared",
            description=f"Cleared **{removed}** warning(s) from {user.mention}.",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text=f"Cleared by {actor.display_name}")
        await interaction.followup.send(embed=embed)

        # ── Log ───────────────────────────────────────────────────────────────
        log_channel = guild.get_channel(WARN_LOG_CHANNEL)
        if log_channel:
            log_embed = discord.Embed(
                title="🗑️ Warnings Cleared",
                color=discord.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            log_embed.add_field(
                name="Member",
                value=f"{user.mention} (`{user.id}`)",
                inline=True
            )
            log_embed.add_field(name="Cleared By", value=actor.mention,    inline=True)
            log_embed.add_field(name="Removed",    value=f"{removed} warning(s)", inline=True)
            await log_channel.send(embed=log_embed)


async def setup(bot):
    await bot.add_cog(ModerationCog(bot))
