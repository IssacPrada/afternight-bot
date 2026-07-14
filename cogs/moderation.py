"""
cogs/moderation.py — Full moderation suite
"""
import discord
from discord import app_commands
from discord.ext import commands
from constants import is_staff, get_member_rank_index, ROLE_STAFF_TEAM, has_fire_permission
import datetime
from discord.ext import tasks

# ── Config ────────────────────────────────────────────────────────────────────
WARN_LOG_CHANNEL     = 1388022887725924372
BAN_LOG_CHANNEL      = 1388022794729558077
KICK_LOG_CHANNEL     = 1526138824173031545
MUTE_LOG_CHANNEL     = 1388022999986212875
LOCKDOWN_LOG_CHANNEL = 1388022999986212875
UNBAN_LOG_CHANNEL    = 1388022999986212875
APPEAL_SERVER        = "https://discord.gg/dQAbatSEcw"

ADMIN_RANK_INDEX = 4
MOD_RANK_INDEX   = 1

# ── Lockdown targets ──────────────────────────────────────────────────────────
LOCKDOWN_TEXT_CHANNELS = [
    1520278354425675826,
    1458296382178852886,
    1458296167455785185,
    1458296246719484039,
    1392580593727967386,
]

LOCKDOWN_VOICE_CHANNELS = [
    1388025901736005764,
    1388025936728821780,
]


def is_admin_plus(member: discord.Member) -> bool:
    return get_member_rank_index(member) >= ADMIN_RANK_INDEX


def is_mod_plus(member: discord.Member) -> bool:
    return get_member_rank_index(member) >= MOD_RANK_INDEX


def parse_duration(duration: str) -> datetime.timedelta | None:
    duration = duration.lower().strip()
    try:
        if duration.endswith("m"):
            return datetime.timedelta(minutes=int(duration[:-1]))
        elif duration.endswith("h"):
            return datetime.timedelta(hours=int(duration[:-1]))
        elif duration.endswith("d"):
            return datetime.timedelta(days=int(duration[:-1]))
    except ValueError:
        pass
    return None


# ── Clear Warns Select ────────────────────────────────────────────────────────

class WarnSelect(discord.ui.Select):
    def __init__(self, warns: list, user: discord.Member, bot):
        self.warn_list = warns
        self.target    = user
        self.bot       = bot

        options = [
            discord.SelectOption(
                label=f"Warning {i + 1} — {str(w.get('created_at', ''))[:10]}",
                description=w["reason"][:100],
                value=str(i)
            )
            for i, w in enumerate(warns[:25])
        ]
        options.insert(0, discord.SelectOption(
            label="⚠️ Clear ALL warnings",
            description="Remove every warning for this user",
            value="all"
        ))

        super().__init__(
            placeholder="Select a warning to remove...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        if self.values[0] == "all":
            removed = await self.bot.db.clear_warns(str(self.target.id), str(guild.id))
            await interaction.followup.send(
                f"✅ Cleared all **{removed}** warning(s) from {self.target.mention}.",
                ephemeral=True
            )
        else:
            index  = int(self.values[0])
            warn   = self.warn_list[index]
            removed = await self.bot.db.delete_warn_by_index(
                str(self.target.id), str(guild.id), index
            )
            if removed:
                await interaction.followup.send(
                    f"✅ Removed warning {index + 1} from {self.target.mention}:\n"
                    f"**Reason:** {warn['reason']}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ Could not remove that warning.", ephemeral=True
                )

        self.disabled = True
        await interaction.message.edit(view=self.view)


class WarnSelectView(discord.ui.View):
    def __init__(self, warns: list, user: discord.Member, bot):
        super().__init__(timeout=60)
        self.add_item(WarnSelect(warns, user, bot))


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
                        dm = discord.Embed(title="✅ You Have Been Unbanned", color=discord.Color.green(), timestamp=datetime.datetime.utcnow())
                        dm.description = (
                            f"Your temporary ban from **Afternight Legacies** has expired and you have been unbanned.\n\n"
                            f"You may rejoin the server. Please follow the rules.\n\n"
                            f"If you believe your ban was unfair, you may still appeal:\n{APPEAL_SERVER}"
                        )
                        await user.send(embed=dm)
                    except discord.Forbidden:
                        pass
                    log_channel = guild.get_channel(BAN_LOG_CHANNEL)
                    if log_channel:
                        e = discord.Embed(title="✅ Temp Ban Expired — Auto Unbanned", color=discord.Color.green(), timestamp=datetime.datetime.utcnow())
                        e.add_field(name="Discord ID", value=f"{user.mention} (`{user.id}`)", inline=False)
                        e.add_field(name="Reason", value="Temporary ban duration expired.", inline=False)
                        await log_channel.send(embed=e)
                except Exception:
                    pass
        except Exception:
            pass

    @check_unbans.before_loop
    async def before_check_unbans(self):
        await self.bot.wait_until_ready()

    # ── Helper: collect attachments from interaction ───────────────────────────

    def _format_evidence(self, evidence: str, attachments: list[discord.Attachment]) -> str:
        parts = []
        if evidence and evidence != "None provided":
            parts.append(evidence)
        for att in attachments:
            parts.append(att.url)
        return "\n".join(parts) if parts else "None provided"

    # ── /warn ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="warn", description="Warn a community member.")
    @app_commands.describe(
        user="The member to warn",
        reason="Reason for the warning",
        evidence="Evidence link(s) — separate multiple with commas",
        attachment1="Evidence attachment (optional)",
        attachment2="Second evidence attachment (optional)"
    )
    async def warn(self, interaction: discord.Interaction,
                   user: discord.Member, reason: str,
                   evidence: str = "None provided",
                   attachment1: discord.Attachment = None,
                   attachment2: discord.Attachment = None):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user
        if not is_staff(actor):
            return await interaction.followup.send("❌ Only staff members may issue warnings.", ephemeral=True)
        if user.bot:
            return await interaction.followup.send("❌ You cannot warn a bot.", ephemeral=True)
        if user == actor:
            return await interaction.followup.send("❌ You cannot warn yourself.", ephemeral=True)

        attachments   = [a for a in [attachment1, attachment2] if a]
        evidence_full = self._format_evidence(evidence, attachments)

        guild = interaction.guild
        await self.bot.db.add_warn(str(user.id), str(guild.id), reason, evidence_full, str(actor.id))
        warns      = await self.bot.db.get_warns(str(user.id), str(guild.id))
        warn_count = len(warns)

        log_embed = discord.Embed(title="⚠️ Warning Issued", color=discord.Color.yellow(), timestamp=datetime.datetime.utcnow())
        log_embed.set_thumbnail(url=user.display_avatar.url)
        log_embed.add_field(name="Discord ID",     value=f"{user.mention} (`{user.id}`)", inline=False)
        log_embed.add_field(name="Reason",         value=reason,                          inline=False)
        log_embed.add_field(name="Evidence",       value=evidence_full,                   inline=False)
        log_embed.add_field(name="Warned By",      value=f"{actor.mention} (`{actor.id}`)", inline=True)
        log_embed.add_field(name="Total Warnings", value=f"**{warn_count}** warning(s)",  inline=True)
        log_embed.set_footer(text=f"User ID: {user.id}")

        if warn_count > 1:
            prev_text = ""
            for i, w in enumerate(warns[:-1], 1):
                date = str(w.get("created_at", ""))[:10]
                prev_text += f"**{i}.** {w['reason']} *({date})*\n"
            log_embed.add_field(name=f"Previous Warnings ({warn_count - 1})", value=prev_text[:1024], inline=False)

        log_channel = guild.get_channel(WARN_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        confirm = discord.Embed(title="✅ Warning Issued", color=discord.Color.green(), timestamp=datetime.datetime.utcnow())
        confirm.add_field(name="Member",         value=user.mention,    inline=True)
        confirm.add_field(name="Reason",         value=reason,          inline=True)
        confirm.add_field(name="Total Warnings", value=f"{warn_count}", inline=True)
        await interaction.followup.send(embed=confirm, ephemeral=True)

        try:
            dm = discord.Embed(title="⚠️ You Have Been Warned", color=discord.Color.yellow(), timestamp=datetime.datetime.utcnow())
            dm.description = (
                f"You have been warned in **Afternight Legacies** for **{reason}**.\n\n"
                f"If this is a mistake you are free to open a ticket in our appeal server.\n{APPEAL_SERVER}"
            )
            dm.set_footer(text="Afternight Moderation")
            await user.send(embed=dm)
        except discord.Forbidden:
            pass

    # ── /viewwarns ────────────────────────────────────────────────────────────

    @app_commands.command(name="viewwarns", description="View warnings for a member.")
    @app_commands.describe(user="The member to check")
    async def viewwarns(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer()

        if not is_staff(interaction.user):
            return await interaction.followup.send("❌ Only staff members may view warnings.", ephemeral=True)

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
                embed.add_field(
                    name=f"Warning {i} — {date}",
                    value=f"**Reason:** {w['reason']}\n**Evidence:** {w.get('evidence', 'None')}\n**Issued by:** {issuer_str}",
                    inline=False
                )
        else:
            embed.add_field(name="No Warnings", value="This member has no warnings.", inline=False)

        embed.set_footer(text=f"User ID: {user.id}")
        await interaction.followup.send(embed=embed)

    # ── /clearwarns ───────────────────────────────────────────────────────────

    @app_commands.command(name="clearwarns", description="Clear one or all warnings for a member.")
    @app_commands.describe(user="The member whose warnings to manage")
    async def clearwarns(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user
        if not is_staff(actor):
            return await interaction.followup.send("❌ Only staff members may clear warnings.", ephemeral=True)

        guild = interaction.guild
        warns = await self.bot.db.get_warns(str(user.id), str(guild.id))

        if not warns:
            return await interaction.followup.send(
                f"❌ {user.mention} has no warnings to clear.", ephemeral=True
            )

        embed = discord.Embed(
            title=f"🗑️ Clear Warnings — {user.display_name}",
            description=f"{user.mention} has **{len(warns)}** warning(s). Select which to remove:",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        view = WarnSelectView(warns, user, self.bot)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    # ── /ban ──────────────────────────────────────────────────────────────────

    @app_commands.command(name="ban", description="Ban a member from the server.")
    @app_commands.describe(
        user="The member to ban", reason="Reason for the ban",
        evidence="Evidence link(s) — separate multiple with commas",
        temporary="Is this a temporary ban?",
        unban_date="If temporary, when they get unbanned (e.g. July 20 2026)",
        delete_days="Number of days of messages to delete (0-7)",
        attachment1="Evidence attachment (optional)",
        attachment2="Second evidence attachment (optional)"
    )
    @app_commands.choices(temporary=[
        app_commands.Choice(name="Yes — Temporary Ban", value="yes"),
        app_commands.Choice(name="No — Permanent Ban",  value="no"),
    ])
    async def ban(self, interaction: discord.Interaction,
                  user: discord.Member, reason: str, temporary: str,
                  evidence: str = "None provided", unban_date: str = None,
                  delete_days: int = 0,
                  attachment1: discord.Attachment = None,
                  attachment2: discord.Attachment = None):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user
        if not is_admin_plus(actor):
            return await interaction.followup.send("❌ Only Administrators or above may use `/ban`.", ephemeral=True)
        if user == actor:
            return await interaction.followup.send("❌ You cannot ban yourself.", ephemeral=True)
        if user.top_role >= interaction.guild.me.top_role:
            return await interaction.followup.send("❌ I cannot ban this user — their role is higher than mine.", ephemeral=True)
        if temporary == "yes" and not unban_date:
            return await interaction.followup.send("❌ Please provide an unban date for a temporary ban.", ephemeral=True)
        if delete_days < 0 or delete_days > 7:
            return await interaction.followup.send("❌ Delete days must be between 0 and 7.", ephemeral=True)

        attachments   = [a for a in [attachment1, attachment2] if a]
        evidence_full = self._format_evidence(evidence, attachments)

        guild        = interaction.guild
        is_temp      = temporary == "yes"
        ban_type_str = f"Temporary — Unban: **{unban_date}**" if is_temp else "Permanent"

        try:
            dm = discord.Embed(title="🔨 You Have Been Banned", color=discord.Color.red(), timestamp=datetime.datetime.utcnow())
            dm.description = (
                f"You have been **{'temporarily' if is_temp else 'permanently'} banned** from **Afternight Legacies**.\n\n"
                f"**Reason:** {reason}\n"
            )
            if is_temp:
                dm.description += f"**Unban Date:** {unban_date}\n\n"
            else:
                dm.description += "\n"
            dm.description += f"If you believe this was a mistake, you may appeal here:\n{APPEAL_SERVER}"
            dm.set_footer(text="Afternight Moderation")
            await user.send(embed=dm)
        except discord.Forbidden:
            pass

        await guild.ban(user, reason=f"{reason} | Banned by {actor}", delete_message_days=delete_days)

        if is_temp:
            await self.bot.db.add_temp_ban(str(user.id), str(guild.id), unban_date, reason, str(actor.id))

        log_embed = discord.Embed(title="🔨 Member Banned", color=discord.Color.red(), timestamp=datetime.datetime.utcnow())
        log_embed.set_thumbnail(url=user.display_avatar.url)
        log_embed.add_field(name="Discord ID",        value=f"{user.mention} (`{user.id}`)", inline=False)
        log_embed.add_field(name="Reason",            value=reason,                          inline=False)
        log_embed.add_field(name="Temporary Or Perm", value=ban_type_str,                    inline=False)
        log_embed.add_field(name="Evidence",          value=evidence_full,                   inline=False)
        log_embed.add_field(name="Banned By",         value=f"{actor.mention} (`{actor.id}`)", inline=True)
        log_embed.add_field(name="Messages Deleted",  value=f"{delete_days} day(s)",         inline=True)
        log_embed.set_footer(text=f"User ID: {user.id}")

        log_channel = guild.get_channel(BAN_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        confirm = discord.Embed(title="✅ Member Banned", color=discord.Color.red(), timestamp=datetime.datetime.utcnow())
        confirm.add_field(name="Member", value=user.mention,  inline=True)
        confirm.add_field(name="Reason", value=reason,        inline=True)
        confirm.add_field(name="Type",   value=ban_type_str,  inline=True)
        await interaction.followup.send(embed=confirm, ephemeral=True)

    # ── /kick ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="kick", description="Kick a member from the server.")
    @app_commands.describe(
        user="The member to kick", reason="Reason for the kick",
        evidence="Evidence link(s) — separate multiple with commas",
        attachment1="Evidence attachment (optional)",
        attachment2="Second evidence attachment (optional)"
    )
    async def kick(self, interaction: discord.Interaction,
                   user: discord.Member, reason: str,
                   evidence: str = "None provided",
                   attachment1: discord.Attachment = None,
                   attachment2: discord.Attachment = None):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user
        if not is_mod_plus(actor):
            return await interaction.followup.send("❌ Only Moderators or above may use `/kick`.", ephemeral=True)
        if user == actor:
            return await interaction.followup.send("❌ You cannot kick yourself.", ephemeral=True)
        if user.top_role >= interaction.guild.me.top_role:
            return await interaction.followup.send("❌ I cannot kick this user — their role is higher than mine.", ephemeral=True)

        attachments   = [a for a in [attachment1, attachment2] if a]
        evidence_full = self._format_evidence(evidence, attachments)
        guild         = interaction.guild

        try:
            dm = discord.Embed(title="👢 You Have Been Kicked", color=discord.Color.orange(), timestamp=datetime.datetime.utcnow())
            dm.description = (
                f"You have been **kicked** from **Afternight Legacies**.\n\n"
                f"**Reason:** {reason}\n\n"
                f"You may rejoin the server, but please ensure you follow the rules.\n\n"
                f"If you believe this was a mistake, you may appeal here:\n{APPEAL_SERVER}"
            )
            dm.set_footer(text="Afternight Moderation")
            await user.send(embed=dm)
        except discord.Forbidden:
            pass

        await guild.kick(user, reason=f"{reason} | Kicked by {actor}")

        log_embed = discord.Embed(title="👢 Member Kicked", color=discord.Color.orange(), timestamp=datetime.datetime.utcnow())
        log_embed.set_thumbnail(url=user.display_avatar.url)
        log_embed.add_field(name="Discord ID", value=f"{user.mention} (`{user.id}`)", inline=False)
        log_embed.add_field(name="Reason",     value=reason,                          inline=False)
        log_embed.add_field(name="Evidence",   value=evidence_full,                   inline=False)
        log_embed.add_field(name="Kicked By",  value=f"{actor.mention} (`{actor.id}`)", inline=False)
        log_embed.set_footer(text=f"User ID: {user.id}")

        log_channel = guild.get_channel(KICK_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        confirm = discord.Embed(title="✅ Member Kicked", color=discord.Color.orange(), timestamp=datetime.datetime.utcnow())
        confirm.add_field(name="Member", value=user.mention, inline=True)
        confirm.add_field(name="Reason", value=reason,       inline=True)
        await interaction.followup.send(embed=confirm, ephemeral=True)

    # ── /mute ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="mute", description="Timeout (mute) a member.")
    @app_commands.describe(
        user="The member to mute", reason="Reason for the mute",
        duration="Duration (e.g. 10m, 1h, 1d — max 28 days)",
        evidence="Evidence link(s) — separate multiple with commas",
        attachment1="Evidence attachment (optional)",
        attachment2="Second evidence attachment (optional)"
    )
    async def mute(self, interaction: discord.Interaction,
                   user: discord.Member, reason: str, duration: str,
                   evidence: str = "None provided",
                   attachment1: discord.Attachment = None,
                   attachment2: discord.Attachment = None):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user
        if not is_staff(actor):
            return await interaction.followup.send("❌ Only staff members may use `/mute`.", ephemeral=True)
        if user == actor:
            return await interaction.followup.send("❌ You cannot mute yourself.", ephemeral=True)
        if user.top_role >= interaction.guild.me.top_role:
            return await interaction.followup.send("❌ I cannot mute this user — their role is higher than mine.", ephemeral=True)

        delta = parse_duration(duration)
        if not delta:
            return await interaction.followup.send("❌ Invalid duration. Use `10m`, `1h`, `1d` etc.", ephemeral=True)
        if delta > datetime.timedelta(days=28):
            return await interaction.followup.send("❌ Maximum mute duration is 28 days.", ephemeral=True)

        attachments   = [a for a in [attachment1, attachment2] if a]
        evidence_full = self._format_evidence(evidence, attachments)

        until     = datetime.datetime.utcnow() + delta
        until_str = until.strftime("%B %d, %Y at %I:%M %p UTC")

        try:
            dm = discord.Embed(title="🔇 You Have Been Muted", color=discord.Color.dark_grey(), timestamp=datetime.datetime.utcnow())
            dm.description = (
                f"You have been **muted** in **Afternight Legacies**.\n\n"
                f"**Reason:** {reason}\n"
                f"**Duration:** {duration}\n"
                f"**Unmuted:** {until_str}\n\n"
                f"If you believe this was a mistake, you may appeal here:\n{APPEAL_SERVER}"
            )
            dm.set_footer(text="Afternight Moderation")
            await user.send(embed=dm)
        except discord.Forbidden:
            pass

        await user.timeout(until, reason=f"{reason} | Muted by {actor}")

        log_embed = discord.Embed(title="🔇 Member Muted", color=discord.Color.dark_grey(), timestamp=datetime.datetime.utcnow())
        log_embed.set_thumbnail(url=user.display_avatar.url)
        log_embed.add_field(name="Discord ID", value=f"{user.mention} (`{user.id}`)", inline=False)
        log_embed.add_field(name="Reason",     value=reason,                          inline=False)
        log_embed.add_field(name="Duration",   value=duration,                        inline=True)
        log_embed.add_field(name="Unmuted",    value=until_str,                       inline=True)
        log_embed.add_field(name="Evidence",   value=evidence_full,                   inline=False)
        log_embed.add_field(name="Muted By",   value=f"{actor.mention} (`{actor.id}`)", inline=False)
        log_embed.set_footer(text=f"User ID: {user.id}")

        log_channel = interaction.guild.get_channel(MUTE_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        confirm = discord.Embed(title="✅ Member Muted", color=discord.Color.dark_grey(), timestamp=datetime.datetime.utcnow())
        confirm.add_field(name="Member",   value=user.mention, inline=True)
        confirm.add_field(name="Duration", value=duration,     inline=True)
        confirm.add_field(name="Reason",   value=reason,       inline=True)
        await interaction.followup.send(embed=confirm, ephemeral=True)

    # ── /unmute ───────────────────────────────────────────────────────────────

    @app_commands.command(name="unmute", description="Remove a timeout from a member.")
    @app_commands.describe(user="The member to unmute", reason="Reason (optional)")
    async def unmute(self, interaction: discord.Interaction,
                     user: discord.Member, reason: str = "Mute lifted by staff"):
        await interaction.response.defer(ephemeral=True)

        if not is_staff(interaction.user):
            return await interaction.followup.send("❌ Only staff members may use `/unmute`.", ephemeral=True)
        if not user.is_timed_out():
            return await interaction.followup.send(f"❌ {user.mention} is not currently muted.", ephemeral=True)

        actor = interaction.user
        await user.timeout(None, reason=f"{reason} | Unmuted by {actor}")

        try:
            dm = discord.Embed(title="🔊 You Have Been Unmuted", color=discord.Color.green(), timestamp=datetime.datetime.utcnow())
            dm.description = (
                f"Your mute in **Afternight Legacies** has been lifted.\n\n"
                f"**Reason:** {reason}\n\nPlease ensure you follow the server rules."
            )
            dm.set_footer(text="Afternight Moderation")
            await user.send(embed=dm)
        except discord.Forbidden:
            pass

        log_embed = discord.Embed(title="🔊 Member Unmuted", color=discord.Color.green(), timestamp=datetime.datetime.utcnow())
        log_embed.set_thumbnail(url=user.display_avatar.url)
        log_embed.add_field(name="Discord ID", value=f"{user.mention} (`{user.id}`)", inline=False)
        log_embed.add_field(name="Reason",     value=reason,                          inline=False)
        log_embed.add_field(name="Unmuted By", value=f"{actor.mention} (`{actor.id}`)", inline=False)
        log_embed.set_footer(text=f"User ID: {user.id}")

        log_channel = interaction.guild.get_channel(MUTE_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        confirm = discord.Embed(title="✅ Member Unmuted", color=discord.Color.green(), timestamp=datetime.datetime.utcnow())
        confirm.add_field(name="Member", value=user.mention, inline=True)
        confirm.add_field(name="Reason", value=reason,       inline=True)
        await interaction.followup.send(embed=confirm, ephemeral=True)

    # ── /unban ────────────────────────────────────────────────────────────────

    @app_commands.command(name="unban", description="Unban a user from the server.")
    @app_commands.describe(user_id="The Discord ID of the user to unban", reason="Reason for the unban")
    async def unban(self, interaction: discord.Interaction,
                    user_id: str, reason: str = "No reason provided"):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user
        if not is_admin_plus(actor):
            return await interaction.followup.send("❌ Only Administrators or above may use `/unban`.", ephemeral=True)

        guild = interaction.guild
        try:
            user = await self.bot.fetch_user(int(user_id))
        except (ValueError, discord.NotFound):
            return await interaction.followup.send("❌ Could not find a user with that ID.", ephemeral=True)

        try:
            await guild.unban(user, reason=f"{reason} | Unbanned by {actor}")
        except discord.NotFound:
            return await interaction.followup.send(f"❌ {user} is not banned from this server.", ephemeral=True)

        try:
            expired = await self.bot.db.get_expired_temp_bans()
            for ban in expired:
                if ban["user_id"] == str(user.id) and ban["guild_id"] == str(guild.id):
                    await self.bot.db.mark_temp_ban_expired(ban["id"])
        except Exception:
            pass

        try:
            dm = discord.Embed(title="✅ You Have Been Unbanned", color=discord.Color.green(), timestamp=datetime.datetime.utcnow())
            dm.description = (
                f"You have been **unbanned** from **Afternight Legacies**.\n\n"
                f"**Reason:** {reason}\n\nYou may rejoin the server. Please follow the rules."
            )
            dm.set_footer(text="Afternight Moderation")
            await user.send(embed=dm)
        except discord.Forbidden:
            pass

        log_embed = discord.Embed(title="✅ Member Unbanned", color=discord.Color.green(), timestamp=datetime.datetime.utcnow())
        log_embed.add_field(name="Discord ID",  value=f"{user.mention} (`{user.id}`)", inline=False)
        log_embed.add_field(name="Reason",      value=reason,                          inline=False)
        log_embed.add_field(name="Unbanned By", value=f"{actor.mention} (`{actor.id}`)", inline=False)
        log_embed.set_footer(text=f"User ID: {user.id}")

        log_channel = guild.get_channel(UNBAN_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        confirm = discord.Embed(title="✅ Member Unbanned", color=discord.Color.green(), timestamp=datetime.datetime.utcnow())
        confirm.add_field(name="User",   value=f"{user} (`{user.id}`)", inline=True)
        confirm.add_field(name="Reason", value=reason,                  inline=True)
        await interaction.followup.send(embed=confirm, ephemeral=True)

    # ── /lockdownserver ───────────────────────────────────────────────────────

    @app_commands.command(name="lockdownserver", description="Lock specific channels so only staff can speak.")
    @app_commands.describe(reason="Reason for the lockdown (optional)")
    async def lockdownserver(self, interaction: discord.Interaction,
                              reason: str = "No reason provided"):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user
        if not has_fire_permission(actor):
            return await interaction.followup.send(
                "❌ Only Overseer of Staff, Community Manager, or Creators may use `/lockdownserver`.",
                ephemeral=True
            )

        guild      = interaction.guild
        staff_role = guild.get_role(ROLE_STAFF_TEAM)
        locked     = 0
        failed     = 0

        await interaction.followup.send("🔒 Locking down server...", ephemeral=True)

        lockdown_embed = discord.Embed(
            title="🔒 Server Lockdown",
            description=(
                f"The server is currently under **lockdown**.\n\n"
                f"**Reason:** {reason}\n\n"
                f"Only staff members may speak during this time. "
                f"Please be patient and wait for further instructions."
            ),
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )
        lockdown_embed.set_footer(text=f"Lockdown initiated by {actor.display_name}")

        # ── Lock text channels ────────────────────────────────────────────────
        sent_messages = []
        for channel_id in LOCKDOWN_TEXT_CHANNELS:
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            try:
                overwrite = channel.overwrites_for(guild.default_role)
                overwrite.send_messages = False
                await channel.set_permissions(guild.default_role, overwrite=overwrite,
                                               reason=f"Server lockdown by {actor}: {reason}")
                if staff_role:
                    staff_ow = channel.overwrites_for(staff_role)
                    staff_ow.send_messages = True
                    await channel.set_permissions(staff_role, overwrite=staff_ow,
                                                   reason="Lockdown — staff override")
                msg = await channel.send(embed=lockdown_embed)
                sent_messages.append(msg)
                locked += 1
            except Exception:
                failed += 1

        # ── Lock voice channels ───────────────────────────────────────────────
        for channel_id in LOCKDOWN_VOICE_CHANNELS:
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            try:
                overwrite = channel.overwrites_for(guild.default_role)
                overwrite.connect = False
                await channel.set_permissions(guild.default_role, overwrite=overwrite,
                                               reason=f"Server lockdown by {actor}: {reason}")
                if staff_role:
                    staff_ow = channel.overwrites_for(staff_role)
                    staff_ow.connect = True
                    await channel.set_permissions(staff_role, overwrite=staff_ow,
                                                   reason="Lockdown — staff override")
                locked += 1
            except Exception:
                failed += 1

        # ── Log ───────────────────────────────────────────────────────────────
        log_embed = discord.Embed(title="🔒 Server Lockdown Initiated", color=discord.Color.red(), timestamp=datetime.datetime.utcnow())
        log_embed.add_field(name="Initiated By",    value=actor.mention,          inline=True)
        log_embed.add_field(name="Reason",          value=reason,                 inline=True)
        log_embed.add_field(name="Channels Locked", value=f"{locked} channel(s)", inline=True)
        if failed:
            log_embed.add_field(name="Failed", value=f"{failed} channel(s)", inline=True)

        log_channel = guild.get_channel(LOCKDOWN_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

    # ── /unlockdownserver ─────────────────────────────────────────────────────

    @app_commands.command(name="unlockdownserver", description="Unlock all channels after a lockdown.")
    @app_commands.describe(reason="Reason for ending the lockdown (optional)")
    async def unlockdownserver(self, interaction: discord.Interaction,
                                reason: str = "Lockdown lifted"):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user
        if not has_fire_permission(actor):
            return await interaction.followup.send(
                "❌ Only Overseer of Staff, Community Manager, or Creators may use `/unlockdownserver`.",
                ephemeral=True
            )

        guild    = interaction.guild
        unlocked = 0
        failed   = 0

        await interaction.followup.send("🔓 Unlocking server...", ephemeral=True)

        unlock_embed = discord.Embed(
            title="🔓 Server Unlocked",
            description=(
                f"The server lockdown has been **lifted**.\n\n"
                f"**Reason:** {reason}\n\n"
                f"You may now speak freely. Please continue to follow the server rules."
            ),
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        unlock_embed.set_footer(text=f"Unlocked by {actor.display_name}")

        # ── Unlock text channels ──────────────────────────────────────────────
        for channel_id in LOCKDOWN_TEXT_CHANNELS:
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            try:
                overwrite = channel.overwrites_for(guild.default_role)
                overwrite.send_messages = None
                await channel.set_permissions(guild.default_role, overwrite=overwrite,
                                               reason=f"Lockdown lifted by {actor}: {reason}")
                msg = await channel.send(embed=unlock_embed)
                # ── Delete after 15 seconds ───────────────────────────────────
                await msg.delete(delay=15)
                unlocked += 1
            except Exception:
                failed += 1

        # ── Unlock voice channels ─────────────────────────────────────────────
        for channel_id in LOCKDOWN_VOICE_CHANNELS:
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            try:
                overwrite = channel.overwrites_for(guild.default_role)
                overwrite.connect = None
                await channel.set_permissions(guild.default_role, overwrite=overwrite,
                                               reason=f"Lockdown lifted by {actor}: {reason}")
                unlocked += 1
            except Exception:
                failed += 1

        # ── Log ───────────────────────────────────────────────────────────────
        log_embed = discord.Embed(title="🔓 Server Lockdown Lifted", color=discord.Color.green(), timestamp=datetime.datetime.utcnow())
        log_embed.add_field(name="Lifted By",         value=actor.mention,            inline=True)
        log_embed.add_field(name="Reason",            value=reason,                   inline=True)
        log_embed.add_field(name="Channels Unlocked", value=f"{unlocked} channel(s)", inline=True)
        if failed:
            log_embed.add_field(name="Failed", value=f"{failed} channel(s)", inline=True)

        log_channel = guild.get_channel(LOCKDOWN_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)


async def setup(bot):
    await bot.add_cog(ModerationCog(bot))
