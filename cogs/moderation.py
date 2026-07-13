"""
cogs/moderation.py — /warn, /viewwarns, /clearwarns, /ban commands
"""
import discord
from discord import app_commands
from discord.ext import commands
from constants import is_staff, get_member_rank_index
import datetime
from discord.ext import tasks

# ── Config ────────────────────────────────────────────────────────────────────
WARN_LOG_CHANNEL = 1388022887725924372
BAN_LOG_CHANNEL  = 1388022794729558077
APPEAL_SERVER    = "https://discord.gg/dQAbatSEcw"
ADMIN_RANK_INDEX = 4


def is_admin_plus(member: discord.Member) -> bool:
    return get_member_rank_index(member) >= ADMIN_RANK_INDEX


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_unbans.start()

    def cog_unload(self):
        self.check_unbans.cancel()

    # ── Auto unban checker ────────────────────────────────────────────────────

    @tasks.loop(minutes=30)
    async def check_unbans(self):
        await self.bot.wait_until_ready()
        try:
            expired = await self.bot.db.get_expired_temp_bans()
            for ban in expired:
                guild = self.bot.get_guild(int(ban["guild_id"]))
                if not guild:
                    continue
                try:
                    user = await self.bot.fetch_user(int(ban["user_id"]))
                    await guild.unban(user, reason="Temporary ban expired")
                    await self.bot.db.mark_temp_ban_expired(ban["id"])

                    try:
                        dm_embed = discord.Embed(
                            title="✅ You Have Been Unbanned",
                            color=discord.Color.green(),
                            timestamp=datetime.datetime.utcnow()
                        )
                        dm_embed.description = (
                            f"Your temporary ban from **Afternight Legacies** has expired "
                            f"and you have been unbanned.\n\n"
                            f"You may rejoin the server. Please follow the rules.\n\n"
                            f"If you believe your ban was unfair, you may still appeal:\n"
                            f"{APPEAL_SERVER}"
                        )
                        await user.send(embed=dm_embed)
                    except discord.Forbidden:
                        pass

                    log_channel = guild.get_channel(BAN_LOG_CHANNEL)
                    if log_channel:
                        log_embed = discord.Embed(
                            title="✅ Temp Ban Expired — Auto Unbanned",
                            color=discord.Color.green(),
                            timestamp=datetime.datetime.utcnow()
                        )
                        log_embed.add_field(
                            name="Discord ID",
                            value=f"{user.mention} (`{user.id}`)",
                            inline=False
                        )
                        log_embed.add_field(
                            name="Reason",
                            value="Temporary ban duration expired.",
                            inline=False
                        )
                        await log_channel.send(embed=log_embed)

                except Exception:
                    pass
        except Exception:
            pass

    @check_unbans.before_loop
    async def before_check_unbans(self):
        await self.bot.wait_until_ready()

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
                "❌ Only staff members may issue warnings.", ephemeral=True
            )
        if user.bot:
            return await interaction.followup.send(
                "❌ You cannot warn a bot.", ephemeral=True
            )
        if user == actor:
            return await interaction.followup.send(
                "❌ You cannot warn yourself.", ephemeral=True
            )

        guild = interaction.guild
        await self.bot.db.add_warn(
            str(user.id), str(guild.id), reason, evidence, str(actor.id)
        )

        warns      = await self.bot.db.get_warns(str(user.id), str(guild.id))
        warn_count = len(warns)

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

        log_channel = guild.get_channel(WARN_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        confirm_embed = discord.Embed(
            title="✅ Warning Issued Successfully",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        confirm_embed.add_field(name="Member",         value=user.mention,    inline=True)
        confirm_embed.add_field(name="Reason",         value=reason,          inline=True)
        confirm_embed.add_field(name="Total Warnings", value=f"{warn_count}", inline=True)
        await interaction.followup.send(embed=confirm_embed, ephemeral=True)

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
                "❌ Only staff members may view warnings.", ephemeral=True
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
        embed.add_field(name="Total Warnings", value=f"**{count}**", inline=True)
        embed.add_field(name="Discord ID",     value=f"`{user.id}`", inline=True)

        if warns:
            for i, w in enumerate(warns, 1):
                date       = str(w.get("created_at", ""))[:10]
                issuer     = guild.get_member(int(w["warned_by"]))
                issuer_str = issuer.display_name if issuer else f"ID: {w['warned_by']}"
                evidence   = w.get("evidence", "None provided")
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
                "❌ Only staff members may clear warnings.", ephemeral=True
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

        log_channel = guild.get_channel(WARN_LOG_CHANNEL)
        if log_channel:
            log_embed = discord.Embed(
                title="🗑️ Warnings Cleared",
                color=discord.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            log_embed.add_field(
                name="Discord ID",
                value=f"{user.mention} (`{user.id}`)",
                inline=False
            )
            log_embed.add_field(name="Cleared By", value=actor.mention,            inline=True)
            log_embed.add_field(name="Removed",    value=f"{removed} warning(s)",  inline=True)
            await log_channel.send(embed=log_embed)

    # ── /ban ──────────────────────────────────────────────────────────────────

    @app_commands.command(
        name="ban",
        description="Ban a member from the server."
    )
    @app_commands.describe(
        user="The member to ban",
        reason="Reason for the ban",
        evidence="Evidence link or description (optional)",
        temporary="Is this a temporary ban?",
        unban_date="If temporary, when they get unbanned (e.g. July 20 2026)",
        delete_days="Number of days of messages to delete (0-7, default 0)"
    )
    @app_commands.choices(temporary=[
        app_commands.Choice(name="Yes — Temporary Ban", value="yes"),
        app_commands.Choice(name="No — Permanent Ban",  value="no"),
    ])
    async def ban(self, interaction: discord.Interaction,
                  user: discord.Member,
                  reason: str,
                  temporary: str,
                  evidence: str = "None provided",
                  unban_date: str = None,
                  delete_days: int = 0):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user

        if not is_admin_plus(actor):
            return await interaction.followup.send(
                "❌ Only Administrators or above may use `/ban`.",
                ephemeral=True
            )

        if user == actor:
            return await interaction.followup.send(
                "❌ You cannot ban yourself.", ephemeral=True
            )

        if user.top_role >= interaction.guild.me.top_role:
            return await interaction.followup.send(
                "❌ I cannot ban this user — their role is higher than mine.",
                ephemeral=True
            )

        if temporary == "yes" and not unban_date:
            return await interaction.followup.send(
                "❌ Please provide an unban date for a temporary ban.",
                ephemeral=True
            )

        if delete_days < 0 or delete_days > 7:
            return await interaction.followup.send(
                "❌ Delete days must be between 0 and 7.",
                ephemeral=True
            )

        guild        = interaction.guild
        is_temp      = temporary == "yes"
        ban_type_str = f"Temporary — Unban: **{unban_date}**" if is_temp else "Permanent"

        # ── DM before ban ─────────────────────────────────────────────────────
        try:
            dm_embed = discord.Embed(
                title="🔨 You Have Been Banned",
                color=discord.Color.red(),
                timestamp=datetime.datetime.utcnow()
            )
            dm_embed.description = (
                f"You have been **{'temporarily' if is_temp else 'permanently'} banned** "
                f"from **Afternight Legacies**.\n\n"
                f"**Reason:** {reason}\n"
            )
            if is_temp:
                dm_embed.description += f"**Unban Date:** {unban_date}\n\n"
            else:
                dm_embed.description += "\n"
            dm_embed.description += (
                f"If you believe this was a mistake, you may appeal here:\n"
                f"{APPEAL_SERVER}"
            )
            dm_embed.set_footer(text="Afternight Moderation")
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        # ── Execute ban ───────────────────────────────────────────────────────
        await guild.ban(
            user,
            reason=f"{reason} | Banned by {actor}",
            delete_message_days=delete_days
        )

        # ── Save temp ban to database ─────────────────────────────────────────
        if is_temp:
            await self.bot.db.add_temp_ban(
                str(user.id), str(guild.id), unban_date, reason, str(actor.id)
            )

        # ── Log embed ─────────────────────────────────────────────────────────
        log_embed = discord.Embed(
            title="🔨 Member Banned",
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.set_thumbnail(url=user.display_avatar.url)
        log_embed.add_field(
            name="Discord ID",
            value=f"{user.mention} (`{user.id}`)",
            inline=False
        )
        log_embed.add_field(name="Reason",              value=reason,        inline=False)
        log_embed.add_field(name="Temporary Or Perm",   value=ban_type_str,  inline=False)
        log_embed.add_field(name="Evidence",            value=evidence,      inline=False)
        log_embed.add_field(
            name="Banned By",
            value=f"{actor.mention} (`{actor.id}`)",
            inline=True
        )
        log_embed.add_field(
            name="Messages Deleted",
            value=f"{delete_days} day(s)",
            inline=True
        )
        log_embed.set_footer(text=f"User ID: {user.id}")

        log_channel = guild.get_channel(BAN_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        # ── Confirmation ──────────────────────────────────────────────────────
        confirm_embed = discord.Embed(
            title="✅ Member Banned",
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )
        confirm_embed.add_field(name="Member",  value=user.mention,  inline=True)
        confirm_embed.add_field(name="Reason",  value=reason,        inline=True)
        confirm_embed.add_field(name="Type",    value=ban_type_str,  inline=True)
        await interaction.followup.send(embed=confirm_embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ModerationCog(bot))
