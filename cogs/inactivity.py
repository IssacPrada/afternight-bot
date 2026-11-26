"""
cogs/inactivity.py — /inactivitynotice and /endinactivity with [IN] nickname tracking
"""
import discord
from discord import app_commands
from discord.ext import commands, tasks
from constants import (
    INACTIVITY_REVIEW_CHANNEL_ID,
    INACTIVITY_APPROVED_CHANNEL_ID,
    can_review_inactivity,
    is_staff,
)
import datetime

IN_PREFIX = "[IN] "


def format_in_nickname(current_name: str) -> str:
    """Prefix nickname with '[IN] ' while respecting Discord's 32-char limit."""
    clean = current_name.removeprefix(IN_PREFIX).strip() or "Member"
    prefixed = f"{IN_PREFIX}{clean}"
    if len(prefixed) > 32:
        max_base = 32 - len(IN_PREFIX)
        prefixed = f"{IN_PREFIX}{clean[:max_base]}"
    return prefixed


def parse_end_date(date_str: str) -> datetime.datetime:
    """Parse human-readable end date into a naive UTC datetime (end of day)."""
    clean = date_str.strip().rstrip(".")
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%m %d, %Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            dt = datetime.datetime.strptime(clean, fmt)
            return dt.replace(hour=23, minute=59, second=59)
        except ValueError:
            continue
    return datetime.datetime.utcnow() + datetime.timedelta(days=7)


async def restore_member_nickname(guild: discord.Guild, notice: dict) -> str:
    """Restore a member's nickname prior to '[IN] ' if possible."""
    member = guild.get_member(int(notice["user_id"]))
    if not member:
        return "Member left server"
    restore_to = notice.get("previous_nick") or notice.get("original_nick") or member.name
    restore_to = restore_to.removeprefix(IN_PREFIX).strip()[:32]
    try:
        await member.edit(nick=restore_to, reason="Inactivity ended — restored nickname")
        return f"Restored nickname to `{restore_to}`"
    except discord.Forbidden:
        return "Missing permissions to change nickname (check bot role position)"
    except Exception as e:
        return f"Could not restore nickname: {e}"


# ── Persistent Approval View ──────────────────────────────────────────────────

class InactivityView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def _extract_notice_id(self, interaction: discord.Interaction) -> int | None:
        embed = interaction.message.embeds[0] if interaction.message.embeds else None
        if not embed or not embed.footer or not embed.footer.text:
            return None
        parts = embed.footer.text.split("Notice ID:")
        if len(parts) < 2:
            return None
        try:
            return int(parts[1].strip().split()[0])
        except ValueError:
            return None

    @discord.ui.button(
        label="✅ Approve",
        style=discord.ButtonStyle.green,
        custom_id="inactivity_approve_v2"
    )
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not can_review_inactivity(interaction.user):
            return await interaction.response.send_message(
                "❌ You don't have permission to approve inactivity notices.",
                ephemeral=True
            )

        notice_id = await self._extract_notice_id(interaction)
        notice = await self.bot.db.get_inactivity_notice(notice_id) if notice_id else None
        if not notice:
            return await interaction.response.send_message(
                "❌ Could not find this inactivity notice in the database.",
                ephemeral=True
            )
        if notice["status"] != "pending":
            return await interaction.response.send_message(
                f"❌ This notice is already marked as **{notice['status']}**.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        submitter = guild.get_member(int(notice["user_id"]))
        nick_status = "Member not in server"
        prev_nick = notice.get("original_nick") or ""

        if submitter:
            prev_nick = submitter.nick or submitter.display_name
            new_nick = format_in_nickname(prev_nick)
            try:
                await submitter.edit(nick=new_nick, reason=f"Approved inactivity #{notice_id}")
                nick_status = f"Nickname updated → `{new_nick}`"
            except discord.Forbidden:
                nick_status = "⚠️ Could not change nickname (check bot role position)"

        await self.bot.db.update_inactivity_status(
            notice_id,
            status="approved",
            reviewed_by=str(interaction.user.id),
            previous_nick=prev_nick
        )

        # Disable buttons & update review embed
        for child in self.children:
            child.disabled = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = f"📋 Inactivity Notice — Approved (#{notice_id})"
        embed.add_field(
            name="✅ Approved By",
            value=f"{interaction.user.mention} ({nick_status})",
            inline=False
        )
        await interaction.message.edit(embed=embed, view=self)

        # Post approved notice & log to INACTIVITY_APPROVED_CHANNEL_ID
        approved_channel = guild.get_channel(INACTIVITY_APPROVED_CHANNEL_ID)
        mention = submitter.mention if submitter else f"<@{notice['user_id']}>"
        if approved_channel:
            approved_embed = discord.Embed(
                title="📋 Inactivity Notice Approved & Logged",
                color=discord.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            approved_embed.description = (
                f"{mention}\n\n"
                f"📅 **Starting:** {notice['date_start']}\n"
                f"📅 **Returning:** {notice['date_end']}\n"
                f"🏷️ **Nickname Status:** {nick_status}\n\n"
                f"**Reason:** {notice['reason']}"
            )
            approved_embed.set_footer(text=f"Notice #{notice_id} · Approved by {interaction.user.display_name}")
            await approved_channel.send(embed=approved_embed)

        # DM submitter
        if submitter:
            try:
                dm_embed = discord.Embed(
                    title="✅ Inactivity Notice Approved",
                    color=discord.Color.green(),
                    timestamp=datetime.datetime.utcnow()
                )
                dm_embed.description = (
                    f"Your inactivity notice has been **approved**!\n\n"
                    f"📅 **Starting:** {notice['date_start']}\n"
                    f"📅 **Returning:** {notice['date_end']}\n"
                    f"🏷️ **Nickname:** {nick_status}\n\n"
                    f"Your name will automatically revert when your inactivity ends."
                )
                await submitter.send(embed=dm_embed)
            except discord.Forbidden:
                pass

        await interaction.followup.send(
            f"✅ Notice **#{notice_id}** approved and logged in <#{INACTIVITY_APPROVED_CHANNEL_ID}>. {nick_status}.",
            ephemeral=True
        )

    @discord.ui.button(
        label="❌ Deny",
        style=discord.ButtonStyle.red,
        custom_id="inactivity_deny_v2"
    )
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not can_review_inactivity(interaction.user):
            return await interaction.response.send_message(
                "❌ You don't have permission to deny inactivity notices.",
                ephemeral=True
            )

        notice_id = await self._extract_notice_id(interaction)
        notice = await self.bot.db.get_inactivity_notice(notice_id) if notice_id else None
        if not notice:
            return await interaction.response.send_message(
                "❌ Could not find this inactivity notice in the database.",
                ephemeral=True
            )
        if notice["status"] != "pending":
            return await interaction.response.send_message(
                f"❌ This notice is already marked as **{notice['status']}**.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        await self.bot.db.update_inactivity_status(
            notice_id,
            status="denied",
            reviewed_by=str(interaction.user.id)
        )

        for child in self.children:
            child.disabled = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = f"📋 Inactivity Notice — Denied (#{notice_id})"
        embed.add_field(
            name="❌ Denied By",
            value=f"{interaction.user.mention}",
            inline=False
        )
        await interaction.message.edit(embed=embed, view=self)

        submitter = interaction.guild.get_member(int(notice["user_id"]))
        if submitter:
            try:
                dm_embed = discord.Embed(
                    title="❌ Inactivity Notice Denied",
                    color=discord.Color.red(),
                    timestamp=datetime.datetime.utcnow()
                )
                dm_embed.description = (
                    f"Your inactivity notice has been **denied**.\n\n"
                    f"📅 **Starting:** {notice['date_start']}\n"
                    f"📅 **Returning:** {notice['date_end']}"
                )
                await submitter.send(embed=dm_embed)
            except discord.Forbidden:
                pass

        await interaction.followup.send(
            f"❌ Notice **#{notice_id}** denied and logged.",
            ephemeral=True
        )


# ── Cog ───────────────────────────────────────────────────────────────────────

class InactivityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_inactivity_end.start()

    def cog_unload(self):
        self.check_inactivity_end.cancel()

    async def cog_load(self):
        # Re-register persistent view so buttons keep working after restarts
        self.bot.add_view(InactivityView(self.bot))

    @tasks.loop(minutes=30)
    async def check_inactivity_end(self):
        await self.bot.wait_until_ready()
        try:
            expired = await self.bot.db.get_expired_inactivity_notices(datetime.datetime.utcnow())
            for notice in expired:
                guild = self.bot.get_guild(int(notice["guild_id"]))
                if not guild:
                    continue
                status_msg = await restore_member_nickname(guild, notice)
                await self.bot.db.complete_inactivity_notice(notice["id"])

                approved_channel = guild.get_channel(INACTIVITY_APPROVED_CHANNEL_ID)
                if approved_channel:
                    embed = discord.Embed(
                        title="🔄 Inactivity Ended",
                        description=(
                            f"<@{notice['user_id']}>'s inactivity period ended (**{notice['date_end']}**).\n"
                            f"**Status:** {status_msg}"
                        ),
                        color=discord.Color.blurple(),
                        timestamp=datetime.datetime.utcnow()
                    )
                    await approved_channel.send(embed=embed)
        except Exception:
            pass

    @check_inactivity_end.before_loop
    async def before_check_inactivity_end(self):
        await self.bot.wait_until_ready()

    @app_commands.command(
        name="inactivitynotice",
        description="Submit an inactivity notice for review and logging."
    )
    @app_commands.describe(
        start_month="Month you go inactive (e.g. November)",
        start_day="Day you go inactive (e.g. 26)",
        start_year="Year you go inactive (e.g. 2026)",
        end_month="Month you return (e.g. December)",
        end_day="Day you return (e.g. 3)",
        end_year="Year you return (e.g. 2026)",
        reason="Reason for inactivity"
    )
    async def inactivitynotice(
        self, interaction: discord.Interaction,
        start_month: str, start_day: str, start_year: str,
        end_month: str, end_day: str, end_year: str,
        reason: str
    ):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user
        if not is_staff(actor):
            return await interaction.followup.send(
                "❌ Only staff members may submit inactivity notices.",
                ephemeral=True
            )

        date_start = f"{start_month} {start_day}, {start_year}"
        date_end   = f"{end_month} {end_day}, {end_year}"
        end_dt     = parse_end_date(date_end)

        review_channel = interaction.guild.get_channel(INACTIVITY_REVIEW_CHANNEL_ID)
        if not review_channel:
            return await interaction.followup.send(
                "❌ Inactivity channel not found. Check `INACTIVITY_REVIEW_CHANNEL_ID`.",
                ephemeral=True
            )

        current_name = actor.nick or actor.display_name
        notice_id = await self.bot.db.create_inactivity_notice(
            user_id=str(actor.id),
            guild_id=str(interaction.guild.id),
            original_nick=current_name,
            date_start=date_start,
            date_end=date_end,
            end_date_dt=end_dt,
            reason=reason
        )

        embed = discord.Embed(
            title=f"📋 Inactivity Notice — Pending Review (#{notice_id})",
            color=discord.Color.yellow(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=actor.display_avatar.url)
        embed.add_field(name="Staff Member", value=f"{actor.mention} (`{actor.id}`)", inline=True)
        embed.add_field(name="Current Name", value=f"`{current_name}`", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="📅 Starting", value=date_start, inline=True)
        embed.add_field(name="📅 Returning", value=date_end, inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.set_footer(text=f"Notice ID: {notice_id} · Approve or Deny below")

        sent_msg = await review_channel.send(embed=embed, view=InactivityView(self.bot))
        await self.bot.db.set_inactivity_message(
            notice_id, str(review_channel.id), str(sent_msg.id)
        )

        await interaction.followup.send(
            f"📨 Inactivity notice **#{notice_id}** sent to <#{INACTIVITY_REVIEW_CHANNEL_ID}> for approval and logging.",
            ephemeral=True
        )

    @app_commands.command(
        name="endinactivity",
        description="End your active inactivity early and restore your previous nickname."
    )
    async def endinactivity(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        notice = await self.bot.db.get_active_inactivity_for_user(
            str(interaction.user.id), str(interaction.guild.id)
        )
        if not notice:
            return await interaction.followup.send(
                "❌ You don't have an active approved inactivity notice.",
                ephemeral=True
            )

        status_msg = await restore_member_nickname(interaction.guild, notice)
        await self.bot.db.complete_inactivity_notice(notice["id"])

        approved_channel = interaction.guild.get_channel(INACTIVITY_APPROVED_CHANNEL_ID)
        if approved_channel:
            embed = discord.Embed(
                title="🔄 Inactivity Ended Early",
                description=(
                    f"{interaction.user.mention} ended their inactivity early (Notice **#{notice['id']}**).\n"
                    f"**Status:** {status_msg}"
                ),
                color=discord.Color.blurple(),
                timestamp=datetime.datetime.utcnow()
            )
            await approved_channel.send(embed=embed)

        await interaction.followup.send(
            f"✅ Inactivity ended. {status_msg}.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(InactivityCog(bot))
