"""
cogs/moderation.py — Moderation, warnings, tempbans, staff strikes, promotions, demotions, and firing
"""
import datetime
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands, tasks
from constants import (
    FIRE_ALLOWED_ROLES,
    MOD_LOG_CHANNEL_ID,
    ROLE_ADMIN_TEAM,
    ROLE_STAFF_TEAM,
    SENIOR_STAFF_ROLES,
    STAFF_HIERARCHY,
    STAFF_HIERARCHY_NAMES,
    get_member_rank_index,
    has_fire_permission,
    is_staff,
)


def parse_unban_date(date_str: str) -> datetime.datetime:
    """Parse a tempban unban date into a naive UTC datetime (end of day)."""
    clean = date_str.strip().rstrip(".")
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%m %d, %Y"):
        try:
            dt = datetime.datetime.strptime(clean, fmt)
            return dt.replace(hour=23, minute=59, second=59)
        except ValueError:
            continue
    return datetime.datetime.utcnow() + datetime.timedelta(days=7)


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_temp_bans.start()

    def cog_unload(self):
        self.check_temp_bans.cancel()

    async def _post_mod_log(self, guild: discord.Guild, embed: discord.Embed):
        channel = guild.get_channel(MOD_LOG_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)
        else:
            await self.bot.log_action(embed)

    def _can_manage_staff_ranks(self, member: discord.Member) -> bool:
        role_ids = {r.id for r in member.roles}
        return bool(role_ids & set(SENIOR_STAFF_ROLES)) or has_fire_permission(member)

    async def _sync_team_roles(self, member: discord.Member, rank_index: int, reason: str):
        """Ensure Staff / Admin team roles match the member's rank in STAFF_HIERARCHY."""
        staff_role = member.guild.get_role(ROLE_STAFF_TEAM)
        admin_role = member.guild.get_role(ROLE_ADMIN_TEAM)

        # Indices 0..4 are [TM]..[HM], indices 5..6 are [A]..[SA]
        should_have_staff = rank_index >= 0
        should_have_admin = rank_index >= 5

        if staff_role:
            if should_have_staff and staff_role not in member.roles:
                await member.add_roles(staff_role, reason=reason)
            elif not should_have_staff and staff_role in member.roles:
                await member.remove_roles(staff_role, reason=reason)

        if admin_role:
            if should_have_admin and admin_role not in member.roles:
                await member.add_roles(admin_role, reason=reason)
            elif not should_have_admin and admin_role in member.roles:
                await member.remove_roles(admin_role, reason=reason)

    @tasks.loop(minutes=30)
    async def check_temp_bans(self):
        await self.bot.wait_until_ready()
        try:
            active_bans = await self.bot.db.get_expired_temp_bans()
            now = datetime.datetime.utcnow()
            for ban in active_bans:
                unban_dt = parse_unban_date(ban["unban_date"])
                if now < unban_dt:
                    continue

                guild = self.bot.get_guild(int(ban["guild_id"]))
                if guild:
                    user = discord.Object(id=int(ban["user_id"]))
                    try:
                        await guild.unban(user, reason=f"Temp ban #{ban['id']} expired")
                    except discord.NotFound:
                        pass
                    except discord.Forbidden:
                        pass

                    embed = discord.Embed(
                        title="🔓 Temp Ban Expired",
                        description=f"<@{ban['user_id']}>'s temporary ban (**{ban['unban_date']}**) has expired.",
                        color=discord.Color.green(),
                        timestamp=now
                    )
                    await self._post_mod_log(guild, embed)

                await self.bot.db.mark_temp_ban_expired(ban["id"])
        except Exception:
            pass

    @check_temp_bans.before_loop
    async def before_check_temp_bans(self):
        await self.bot.wait_until_ready()

    # ── Warnings ──────────────────────────────────────────────────────────────

    @app_commands.command(name="warn", description="Issue a warning to a member.")
    @app_commands.describe(
        member="Member to warn",
        reason="Reason for the warning",
        evidence="Optional link or proof"
    )
    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
        evidence: Optional[str] = None
    ):
        if not is_staff(interaction.user):
            return await interaction.response.send_message(
                "❌ Only staff members can issue warnings.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)
        clean_evidence = evidence.strip() if evidence else "None provided"

        await self.bot.db.add_warn(
            user_id=str(member.id),
            guild_id=str(interaction.guild.id),
            reason=reason,
            evidence=clean_evidence,
            warned_by=str(interaction.user.id)
        )
        warns = await self.bot.db.get_warns(str(member.id), str(interaction.guild.id))
        warn_num = len(warns)

        await self.bot.db.log_staff_action(
            action="WARN",
            target_id=str(member.id),
            actor_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            note=f"#{warn_num}: {reason}"
        )

        log_embed = discord.Embed(
            title=f"⚠️ Member Warned (#{warn_num})",
            color=discord.Color.yellow(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Member", value=f"{member.mention} (`{member.id}`)", inline=True)
        log_embed.add_field(name="Warned By", value=f"{interaction.user.mention}", inline=True)
        log_embed.add_field(name="Total Warns", value=str(warn_num), inline=True)
        log_embed.add_field(name="Reason", value=reason, inline=False)
        log_embed.add_field(name="Evidence", value=clean_evidence, inline=False)
        await self._post_mod_log(interaction.guild, log_embed)

        try:
            dm = discord.Embed(
                title=f"⚠️ Warning Issued in {interaction.guild.name}",
                description=f"**Reason:** {reason}\n**Total Warnings:** {warn_num}",
                color=discord.Color.yellow(),
                timestamp=datetime.datetime.utcnow()
            )
            await member.send(embed=dm)
        except discord.Forbidden:
            pass

        await interaction.followup.send(
            f"✅ Warned {member.mention} (Warning **#{warn_num}**).",
            ephemeral=True
        )

    @app_commands.command(name="warns", description="View warnings for a member.")
    @app_commands.describe(member="Member to check warnings for")
    async def warns(self, interaction: discord.Interaction, member: discord.Member):
        if not is_staff(interaction.user):
            return await interaction.response.send_message(
                "❌ Only staff members can view warnings.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)
        entries = await self.bot.db.get_warns(str(member.id), str(interaction.guild.id))
        if not entries:
            return await interaction.followup.send(
                f"📭 {member.mention} has no warnings.",
                ephemeral=True
            )

        embed = discord.Embed(
            title=f"⚠️ Warnings for {member.display_name} ({len(entries)})",
            color=discord.Color.yellow(),
            timestamp=datetime.datetime.utcnow()
        )
        for idx, w in enumerate(entries[:25], start=1):
            embed.add_field(
                name=f"Warn #{idx} — By <@{w['warned_by']}>",
                value=f"**Reason:** {w['reason']}\n**Evidence:** {w.get('evidence') or 'None'}",
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="removewarn", description="Remove a specific warning by number (1-based).")
    @app_commands.describe(member="Member to remove warning from", number="Warning number to remove")
    async def removewarn(self, interaction: discord.Interaction, member: discord.Member, number: int):
        if not is_staff(interaction.user):
            return await interaction.response.send_message(
                "❌ Only staff members can remove warnings.",
                ephemeral=True
            )
        if number < 1:
            return await interaction.response.send_message(
                "❌ Warning number must be 1 or higher.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)
        removed = await self.bot.db.delete_warn_by_index(
            str(member.id), str(interaction.guild.id), number - 1
        )
        if not removed:
            return await interaction.followup.send(
                f"❌ Warning **#{number}** not found for {member.mention}.",
                ephemeral=True
            )

        await self.bot.db.log_staff_action(
            action="REMOVE_WARN",
            target_id=str(member.id),
            actor_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            note=f"Removed warn #{number}"
        )

        log_embed = discord.Embed(
            title="🗑️ Warning Removed",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Member", value=f"{member.mention} (`{member.id}`)", inline=True)
        log_embed.add_field(name="Warning #", value=str(number), inline=True)
        log_embed.add_field(name="Removed By", value=f"{interaction.user.mention}", inline=True)
        await self._post_mod_log(interaction.guild, log_embed)

        await interaction.followup.send(
            f"✅ Removed warning **#{number}** from {member.mention}.",
            ephemeral=True
        )

    @app_commands.command(name="clearwarns", description="Clear all warnings for a member.")
    @app_commands.describe(member="Member to clear warnings for")
    async def clearwarns(self, interaction: discord.Interaction, member: discord.Member):
        if not is_staff(interaction.user):
            return await interaction.response.send_message(
                "❌ Only staff members can clear warnings.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)
        count = await self.bot.db.clear_warns(str(member.id), str(interaction.guild.id))
        await self.bot.db.log_staff_action(
            action="CLEAR_WARNS",
            target_id=str(member.id),
            actor_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            note=f"Cleared {count} warns"
        )

        log_embed = discord.Embed(
            title="🧹 Warnings Cleared",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Member", value=f"{member.mention} (`{member.id}`)", inline=True)
        log_embed.add_field(name="Cleared Count", value=str(count), inline=True)
        log_embed.add_field(name="Cleared By", value=f"{interaction.user.mention}", inline=True)
        await self._post_mod_log(interaction.guild, log_embed)

        await interaction.followup.send(
            f"✅ Cleared **{count}** warning(s) for {member.mention}.",
            ephemeral=True
        )

    # ── Temp Ban ──────────────────────────────────────────────────────────────

    @app_commands.command(name="tempban", description="Temporarily ban a member until a specified date.")
    @app_commands.describe(
        member="Member to temporarily ban",
        unban_date="Date to unban (e.g. December 5, 2026)",
        reason="Reason for the temporary ban"
    )
    async def tempban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        unban_date: str,
        reason: str
    ):
        if not is_staff(interaction.user):
            return await interaction.response.send_message(
                "❌ Only staff members can issue temporary bans.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        try:
            await interaction.guild.ban(member, reason=f"Temp ban until {unban_date}: {reason}")
        except discord.Forbidden:
            return await interaction.followup.send(
                "❌ Missing permissions to ban this member. Check my role hierarchy.",
                ephemeral=True
            )

        await self.bot.db.add_temp_ban(
            user_id=str(member.id),
            guild_id=str(interaction.guild.id),
            unban_date=unban_date,
            reason=reason,
            banned_by=str(interaction.user.id)
        )
        await self.bot.db.log_staff_action(
            action="TEMPBAN",
            target_id=str(member.id),
            actor_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            note=f"Until {unban_date} | Reason: {reason}"
        )

        log_embed = discord.Embed(
            title="⏳ Temporary Ban Issued",
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Member", value=f"{member.mention} (`{member.id}`)", inline=True)
        log_embed.add_field(name="Banned By", value=f"{interaction.user.mention}", inline=True)
        log_embed.add_field(name="Unban Date", value=unban_date, inline=True)
        log_embed.add_field(name="Reason", value=reason, inline=False)
        await self._post_mod_log(interaction.guild, log_embed)

        await interaction.followup.send(
            f"✅ Temporarily banned {member.mention} until **{unban_date}**.",
            ephemeral=True
        )

    # ── Staff Strikes ─────────────────────────────────────────────────────────

    @app_commands.command(name="staffstrike", description="Issue a strike to a staff member.")
    @app_commands.describe(
        member="Staff member to strike",
        reason="Reason for the staff strike",
        evidence="Optional link or evidence"
    )
    async def staffstrike(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
        evidence: Optional[str] = None
    ):
        if not self._can_manage_staff_ranks(interaction.user):
            return await interaction.response.send_message(
                "❌ You don't have permission to issue staff strikes.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)
        clean_evidence = evidence.strip() if evidence else "None provided"

        await self.bot.db.add_staff_strike(
            user_id=str(member.id),
            guild_id=str(interaction.guild.id),
            reason=reason,
            evidence=clean_evidence,
            issued_by=str(interaction.user.id)
        )
        strikes = await self.bot.db.get_staff_strikes(str(member.id), str(interaction.guild.id))
        count = len(strikes)

        await self.bot.db.log_staff_action(
            action="STAFF_STRIKE",
            target_id=str(member.id),
            actor_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            note=f"#{count}: {reason}"
        )

        log_embed = discord.Embed(
            title=f"⚡ Staff Strike Issued (#{count})",
            color=discord.Color.dark_red(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Staff Member", value=f"{member.mention} (`{member.id}`)", inline=True)
        log_embed.add_field(name="Issued By", value=f"{interaction.user.mention}", inline=True)
        log_embed.add_field(name="Total Strikes", value=str(count), inline=True)
        log_embed.add_field(name="Reason", value=reason, inline=False)
        log_embed.add_field(name="Evidence", value=clean_evidence, inline=False)
        await self._post_mod_log(interaction.guild, log_embed)

        await interaction.followup.send(
            f"✅ Issued staff strike **#{count}** to {member.mention}.",
            ephemeral=True
        )

    @app_commands.command(name="staffstrikes", description="View staff strikes for a staff member.")
    @app_commands.describe(member="Staff member to check")
    async def staffstrikes(self, interaction: discord.Interaction, member: discord.Member):
        if not is_staff(interaction.user):
            return await interaction.response.send_message(
                "❌ Only staff members can view staff strikes.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)
        entries = await self.bot.db.get_staff_strikes(str(member.id), str(interaction.guild.id))
        if not entries:
            return await interaction.followup.send(
                f"📭 {member.mention} has no staff strikes.",
                ephemeral=True
            )

        embed = discord.Embed(
            title=f"⚡ Staff Strikes for {member.display_name} ({len(entries)})",
            color=discord.Color.dark_red(),
            timestamp=datetime.datetime.utcnow()
        )
        for idx, s in enumerate(entries[:25], start=1):
            embed.add_field(
                name=f"Strike #{idx} — By <@{s['issued_by']}>",
                value=f"**Reason:** {s['reason']}\n**Evidence:** {s.get('evidence') or 'None'}",
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="clearstaffstrikes", description="Clear all staff strikes for a member.")
    @app_commands.describe(member="Staff member to clear strikes for")
    async def clearstaffstrikes(self, interaction: discord.Interaction, member: discord.Member):
        if not self._can_manage_staff_ranks(interaction.user):
            return await interaction.response.send_message(
                "❌ You don't have permission to clear staff strikes.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)
        count = await self.bot.db.clear_staff_strikes(str(member.id), str(interaction.guild.id))
        await self.bot.db.log_staff_action(
            action="CLEAR_STAFF_STRIKES",
            target_id=str(member.id),
            actor_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            note=f"Cleared {count} staff strikes"
        )

        log_embed = discord.Embed(
            title="🧹 Staff Strikes Cleared",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Staff Member", value=f"{member.mention} (`{member.id}`)", inline=True)
        log_embed.add_field(name="Cleared Count", value=str(count), inline=True)
        log_embed.add_field(name="Cleared By", value=f"{interaction.user.mention}", inline=True)
        await self._post_mod_log(interaction.guild, log_embed)

        await interaction.followup.send(
            f"✅ Cleared **{count}** staff strike(s) for {member.mention}.",
            ephemeral=True
        )



async def setup(bot):
    await bot.add_cog(ModerationCog(bot))
