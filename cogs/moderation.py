"""
cogs/moderation.py — Full moderation suite with slash + prefix commands
"""
import discord
from discord import app_commands
from discord.ext import commands
import datetime
from discord.ext import tasks

# ── Role IDs ──────────────────────────────────────────────────────────────────
ROLE_STAFF    = 1458304077136920668
ROLE_ADMIN    = 1458303682180284681
ROLE_CM       = 1458302857764802683
ROLE_OVERSEER = 1458302854887510210
ROLE_CREATOR  = 1387649282139754587

# ── Log Channels ──────────────────────────────────────────────────────────────
WARN_LOG_CHANNEL         = 1388022887725924372
BAN_LOG_CHANNEL          = 1388022794729558077
KICK_LOG_CHANNEL         = 1526138824173031545
MUTE_LOG_CHANNEL         = 1388022999986212875
LOCKDOWN_LOG_CHANNEL     = 1388022999986212875
UNBAN_LOG_CHANNEL        = 1388022999986212875
STAFF_STRIKE_LOG_CHANNEL = 1527188854765916221

APPEAL_SERVER = "https://discord.gg/dQAbatSEcw"

LOCKDOWN_TEXT_CHANNELS = [
    1533176901273911589,
    1458296382178852886,
    1458296167455785185,
    1458296246719484039,
    1392580593727967386,
]
LOCKDOWN_VOICE_CHANNELS = [
    1388025901736005764,
    1388025936728821780,
]

ALL_STAFF_ROLES = [
    ROLE_STAFF,
    ROLE_ADMIN,
    ROLE_CM,
    ROLE_OVERSEER,
]


# ── Permission helpers ────────────────────────────────────────────────────────

def get_role_ids(member: discord.Member) -> set[int]:
    return {r.id for r in member.roles}


def is_staff(member: discord.Member) -> bool:
    return bool(get_role_ids(member) & {ROLE_STAFF, ROLE_ADMIN, ROLE_CM, ROLE_OVERSEER, ROLE_CREATOR})


def is_admin(member: discord.Member) -> bool:
    return bool(get_role_ids(member) & {ROLE_ADMIN, ROLE_CM, ROLE_OVERSEER, ROLE_CREATOR})


def is_head(member: discord.Member) -> bool:
    return bool(get_role_ids(member) & {ROLE_CM, ROLE_OVERSEER, ROLE_CREATOR})


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


def format_evidence(evidence: str, attachments: list) -> str:
    parts = []
    if evidence and evidence != "None provided":
        parts.append(evidence)
    for att in attachments:
        parts.append(att.url)
    return "\n".join(parts) if parts else "None provided"


# ── Clear Warns Dropdown ──────────────────────────────────────────────────────

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
            for i, w in enumerate(warns[:24])
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
            index   = int(self.values[0])
            warn    = self.warn_list[index]
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
                await interaction.followup.send("❌ Could not remove that warning.", ephemeral=True)

        for item in self.view.children:
            item.disabled = True
        await interaction.message.edit(view=self.view)


class WarnSelectView(discord.ui.View):
    def __init__(self, warns: list, user: discord.Member, bot):
        super().__init__(timeout=60)
        self.add_item(WarnSelect(warns, user, bot))


# ── Cog ───────────────────────────────────────────────────────────────────────

class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_unbans.start()

    def cog_unload(self):
        self.check_unbans.cancel()

    # ── Auto unban ────────────────────────────────────────────────────────────

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
                        dm = discord.Embed(title="✅ You Have Been Unbanned", color=discord.Color.green(), timestamp=discord.utils.utcnow())
                        dm.description = (
                            f"Your temporary ban from **Afternight Legacies** has expired.\n\n"
                            f"You may rejoin the server. Please follow the rules.\n\n"
                            f"If you believe your ban was unfair:\n{APPEAL_SERVER}"
                        )
                        await user.send(embed=dm)
                    except discord.Forbidden:
                        pass
                    log_channel = guild.get_channel(BAN_LOG_CHANNEL)
                    if log_channel:
                        e = discord.Embed(title="✅ Temp Ban Expired", color=discord.Color.green(), timestamp=discord.utils.utcnow())
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

    # ─────────────────────────────────────────────────────────────────────────
    # WARN
    # ─────────────────────────────────────────────────────────────────────────

    async def _warn(self, guild: discord.Guild, actor: discord.Member,
                    user: discord.Member, reason: str, evidence: str):
        await self.bot.db.add_warn(str(user.id), str(guild.id), reason, evidence, str(actor.id))
        warns      = await self.bot.db.get_warns(str(user.id), str(guild.id))
        warn_count = len(warns)

        log_embed = discord.Embed(title="⚠️ Warning Issued", color=discord.Color.yellow(), timestamp=discord.utils.utcnow())
        log_embed.set_thumbnail(url=user.display_avatar.url)
        log_embed.add_field(name="Discord ID",     value=f"{user.mention} (`{user.id}`)", inline=False)
        log_embed.add_field(name="Reason",         value=reason,                          inline=False)
        log_embed.add_field(name="Evidence",       value=evidence,                        inline=False)
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

        try:
            dm = discord.Embed(title="⚠️ You Have Been Warned", color=discord.Color.yellow(), timestamp=discord.utils.utcnow())
            dm.description = (
                f"You have been warned in **Afternight Legacies** for **{reason}**.\n\n"
                f"If this is a mistake open a ticket:\n{APPEAL_SERVER}"
            )
            dm.set_footer(text="Afternight Moderation")
            await user.send(embed=dm)
        except discord.Forbidden:
            pass

        return warn_count

    @app_commands.command(name="warn", description="Warn a community member.")
    @app_commands.describe(user="The member to warn", reason="Reason", evidence="Evidence links (optional)", attachment1="Attachment (optional)", attachment2="Attachment (optional)")
    async def warn_slash(self, interaction: discord.Interaction, user: discord.Member, reason: str, evidence: str = "None provided", attachment1: discord.Attachment = None, attachment2: discord.Attachment = None):
        await interaction.response.defer()
        actor = interaction.user
        if not is_staff(actor):
            return await interaction.followup.send("❌ Only staff may warn members.", ephemeral=True)
        if user.bot or user == actor:
            return await interaction.followup.send("❌ Invalid target.", ephemeral=True)
        attachments   = [a for a in [attachment1, attachment2] if a]
        evidence_full = format_evidence(evidence, attachments)
        count = await self._warn(interaction.guild, actor, user, reason, evidence_full)
        confirm = discord.Embed(title="✅ Warning Issued", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        confirm.add_field(name="Member", value=user.mention, inline=True)
        confirm.add_field(name="Reason", value=reason,       inline=True)
        confirm.add_field(name="Total",  value=f"{count}",   inline=True)
        await interaction.followup.send(embed=confirm)

    @commands.command(name="warn")
    async def warn_prefix(self, ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided"):
        if not is_staff(ctx.author):
            return await ctx.send("❌ Only staff may warn members.")
        if user.bot or user == ctx.author:
            return await ctx.send("❌ Invalid target.")
        evidence = "None provided"
        if ctx.message.attachments:
            evidence = "\n".join(a.url for a in ctx.message.attachments)
        count = await self._warn(ctx.guild, ctx.author, user, reason, evidence)
        await ctx.send(f"✅ **{user.display_name}** has been warned. Total warnings: **{count}**")

    # ─────────────────────────────────────────────────────────────────────────
    # VIEWWARNS
    # ─────────────────────────────────────────────────────────────────────────

    async def _viewwarns(self, guild: discord.Guild, user: discord.Member) -> discord.Embed:
        warns = await self.bot.db.get_warns(str(user.id), str(guild.id))
        count = len(warns)
        embed = discord.Embed(
            title=f"⚠️ Warnings — {user.display_name}",
            color=discord.Color.yellow() if count > 0 else discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Total", value=f"**{count}**", inline=True)
        embed.add_field(name="ID",    value=f"`{user.id}`", inline=True)
        if warns:
            for i, w in enumerate(warns, 1):
                date       = str(w.get("created_at", ""))[:10]
                issuer     = guild.get_member(int(w["warned_by"]))
                issuer_str = issuer.display_name if issuer else f"ID: {w['warned_by']}"
                embed.add_field(
                    name=f"Warning {i} — {date}",
                    value=f"**Reason:** {w['reason']}\n**Evidence:** {w.get('evidence', 'None')}\n**By:** {issuer_str}",
                    inline=False
                )
        else:
            embed.add_field(name="No Warnings", value="This member has no warnings.", inline=False)
        embed.set_footer(text=f"User ID: {user.id}")
        return embed

    @app_commands.command(name="viewwarns", description="View warnings for a member.")
    @app_commands.describe(user="The member to check")
    async def viewwarns_slash(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer()
        if not is_staff(interaction.user):
            return await interaction.followup.send("❌ Only staff may view warnings.", ephemeral=True)
        embed = await self._viewwarns(interaction.guild, user)
        await interaction.followup.send(embed=embed)

    @commands.command(name="viewwarns", aliases=["warns", "warnings"])
    async def viewwarns_prefix(self, ctx: commands.Context, user: discord.Member):
        if not is_staff(ctx.author):
            return await ctx.send("❌ Only staff may view warnings.")
        embed = await self._viewwarns(ctx.guild, user)
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────────────────────────────────
    # CLEARWARNS
    # ─────────────────────────────────────────────────────────────────────────

    @app_commands.command(name="clearwarns", description="Clear one or all warnings for a member.")
    @app_commands.describe(user="The member whose warnings to manage")
    async def clearwarns_slash(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)
        if not is_admin(interaction.user):
            return await interaction.followup.send("❌ Only Admins or above may clear warnings.", ephemeral=True)
        guild = interaction.guild
        warns = await self.bot.db.get_warns(str(user.id), str(guild.id))
        if not warns:
            return await interaction.followup.send(f"❌ {user.mention} has no warnings.", ephemeral=True)
        embed = discord.Embed(
            title=f"🗑️ Clear Warnings — {user.display_name}",
            description=f"{user.mention} has **{len(warns)}** warning(s). Select which to remove:",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        view = WarnSelectView(warns, user, self.bot)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @commands.command(name="clearwarns", aliases=["clearwarn"])
    async def clearwarns_prefix(self, ctx: commands.Context, user: discord.Member):
        if not is_admin(ctx.author):
            return await ctx.send("❌ Only Admins or above may clear warnings.")
        removed = await self.bot.db.clear_warns(str(user.id), str(ctx.guild.id))
        await ctx.send(f"✅ Cleared **{removed}** warning(s) from {user.mention}.")

    # ─────────────────────────────────────────────────────────────────────────
    # BAN
    # ─────────────────────────────────────────────────────────────────────────

    async def _ban(self, guild: discord.Guild, actor: discord.Member,
                   user: discord.Member, reason: str, evidence: str,
                   is_temp: bool, unban_date: str, delete_days: int):
        ban_type_str = f"Temporary — Unban: **{unban_date}**" if is_temp else "Permanent"
        try:
            dm = discord.Embed(title="🔨 You Have Been Banned", color=discord.Color.red(), timestamp=discord.utils.utcnow())
            dm.description = (
                f"You have been **{'temporarily' if is_temp else 'permanently'} banned** from **Afternight Legacies**.\n\n"
                f"**Reason:** {reason}\n"
            )
            if is_temp:
                dm.description += f"**Unban Date:** {unban_date}\n\n"
            else:
                dm.description += "\n"
            dm.description += f"Appeal here:\n{APPEAL_SERVER}"
            dm.set_footer(text="Afternight Moderation")
            await user.send(embed=dm)
        except discord.Forbidden:
            pass

        await guild.ban(user, reason=f"{reason} | Banned by {actor}", delete_message_days=delete_days)

        if is_temp:
            await self.bot.db.add_temp_ban(str(user.id), str(guild.id), unban_date, reason, str(actor.id))

        log_embed = discord.Embed(title="🔨 Member Banned", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        log_embed.set_thumbnail(url=user.display_avatar.url)
        log_embed.add_field(name="Discord ID",        value=f"{user.mention} (`{user.id}`)", inline=False)
        log_embed.add_field(name="Reason",            value=reason,                          inline=False)
        log_embed.add_field(name="Temporary Or Perm", value=ban_type_str,                    inline=False)
        log_embed.add_field(name="Evidence",          value=evidence,                        inline=False)
        log_embed.add_field(name="Banned By",         value=f"{actor.mention} (`{actor.id}`)", inline=True)
        log_embed.add_field(name="Messages Deleted",  value=f"{delete_days} day(s)",         inline=True)
        log_embed.set_footer(text=f"User ID: {user.id}")

        log_channel = guild.get_channel(BAN_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        return ban_type_str

    @app_commands.command(name="ban", description="Ban a member from the server.")
    @app_commands.describe(user="The member to ban", reason="Reason", evidence="Evidence links", temporary="Temp or perm?", unban_date="Unban date if temp", delete_days="Days of messages to delete (0-7)", attachment1="Attachment", attachment2="Attachment")
    @app_commands.choices(temporary=[
        app_commands.Choice(name="Yes — Temporary Ban", value="yes"),
        app_commands.Choice(name="No — Permanent Ban",  value="no"),
    ])
    async def ban_slash(self, interaction: discord.Interaction, user: discord.Member, reason: str, temporary: str, evidence: str = "None provided", unban_date: str = None, delete_days: int = 0, attachment1: discord.Attachment = None, attachment2: discord.Attachment = None):
        await interaction.response.defer()
        actor = interaction.user
        if not is_admin(actor):
            return await interaction.followup.send("❌ Only Admins or above may ban.", ephemeral=True)
        if user == actor:
            return await interaction.followup.send("❌ You cannot ban yourself.", ephemeral=True)
        if user.top_role >= interaction.guild.me.top_role:
            return await interaction.followup.send("❌ I cannot ban this user.", ephemeral=True)
        if temporary == "yes" and not unban_date:
            return await interaction.followup.send("❌ Provide an unban date for a temp ban.", ephemeral=True)
        if not 0 <= delete_days <= 7:
            return await interaction.followup.send("❌ Delete days must be 0-7.", ephemeral=True)
        attachments   = [a for a in [attachment1, attachment2] if a]
        evidence_full = format_evidence(evidence, attachments)
        is_temp       = temporary == "yes"
        ban_type_str  = await self._ban(interaction.guild, actor, user, reason, evidence_full, is_temp, unban_date, delete_days)
        confirm = discord.Embed(title="✅ Member Banned", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        confirm.add_field(name="Member", value=user.mention,  inline=True)
        confirm.add_field(name="Reason", value=reason,        inline=True)
        confirm.add_field(name="Type",   value=ban_type_str,  inline=True)
        await interaction.followup.send(embed=confirm)

    @commands.command(name="ban")
    async def ban_prefix(self, ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided"):
        if not is_admin(ctx.author):
            return await ctx.send("❌ Only Admins or above may ban.")
        if user == ctx.author:
            return await ctx.send("❌ You cannot ban yourself.")
        if user.top_role >= ctx.guild.me.top_role:
            return await ctx.send("❌ I cannot ban this user.")
        evidence = "\n".join(a.url for a in ctx.message.attachments) if ctx.message.attachments else "None provided"
        await self._ban(ctx.guild, ctx.author, user, reason, evidence, False, None, 0)
        await ctx.send(f"✅ **{user.display_name}** has been permanently banned.")

    # ─────────────────────────────────────────────────────────────────────────
    # KICK
    # ─────────────────────────────────────────────────────────────────────────

    async def _kick(self, guild: discord.Guild, actor: discord.Member,
                    user: discord.Member, reason: str, evidence: str):
        try:
            dm = discord.Embed(title="👢 You Have Been Kicked", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
            dm.description = (
                f"You have been **kicked** from **Afternight Legacies**.\n\n"
                f"**Reason:** {reason}\n\nAppeal here:\n{APPEAL_SERVER}"
            )
            dm.set_footer(text="Afternight Moderation")
            await user.send(embed=dm)
        except discord.Forbidden:
            pass

        await guild.kick(user, reason=f"{reason} | Kicked by {actor}")

        log_embed = discord.Embed(title="👢 Member Kicked", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        log_embed.set_thumbnail(url=user.display_avatar.url)
        log_embed.add_field(name="Discord ID", value=f"{user.mention} (`{user.id}`)", inline=False)
        log_embed.add_field(name="Reason",     value=reason,                          inline=False)
        log_embed.add_field(name="Evidence",   value=evidence,                        inline=False)
        log_embed.add_field(name="Kicked By",  value=f"{actor.mention} (`{actor.id}`)", inline=False)
        log_embed.set_footer(text=f"User ID: {user.id}")

        log_channel = guild.get_channel(KICK_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

    @app_commands.command(name="kick", description="Kick a member from the server.")
    @app_commands.describe(user="The member to kick", reason="Reason", evidence="Evidence links", attachment1="Attachment", attachment2="Attachment")
    async def kick_slash(self, interaction: discord.Interaction, user: discord.Member, reason: str, evidence: str = "None provided", attachment1: discord.Attachment = None, attachment2: discord.Attachment = None):
        await interaction.response.defer()
        actor = interaction.user
        if not is_staff(actor):
            return await interaction.followup.send("❌ Only staff may kick.", ephemeral=True)
        if user == actor:
            return await interaction.followup.send("❌ You cannot kick yourself.", ephemeral=True)
        if user.top_role >= interaction.guild.me.top_role:
            return await interaction.followup.send("❌ I cannot kick this user.", ephemeral=True)
        attachments   = [a for a in [attachment1, attachment2] if a]
        evidence_full = format_evidence(evidence, attachments)
        await self._kick(interaction.guild, actor, user, reason, evidence_full)
        confirm = discord.Embed(title="✅ Member Kicked", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        confirm.add_field(name="Member", value=user.mention, inline=True)
        confirm.add_field(name="Reason", value=reason,       inline=True)
        await interaction.followup.send(embed=confirm)

    @commands.command(name="kick")
    async def kick_prefix(self, ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided"):
        if not is_staff(ctx.author):
            return await ctx.send("❌ Only staff may kick.")
        if user == ctx.author:
            return await ctx.send("❌ You cannot kick yourself.")
        if user.top_role >= ctx.guild.me.top_role:
            return await ctx.send("❌ I cannot kick this user.")
        evidence = "\n".join(a.url for a in ctx.message.attachments) if ctx.message.attachments else "None provided"
        await self._kick(ctx.guild, ctx.author, user, reason, evidence)
        await ctx.send(f"✅ **{user.display_name}** has been kicked.")

    # ─────────────────────────────────────────────────────────────────────────
    # MUTE
    # ─────────────────────────────────────────────────────────────────────────

    async def _mute(self, guild: discord.Guild, actor: discord.Member,
                    user: discord.Member, reason: str, duration: str, evidence: str):
        delta = parse_duration(duration)
        if not delta:
            return None, "Invalid duration. Use `10m`, `1h`, `1d` etc."
        if delta > datetime.timedelta(days=28):
            return None, "Maximum mute duration is 28 days."

        until     = discord.utils.utcnow() + delta
        until_str = until.strftime("%B %d, %Y at %I:%M %p UTC")

        try:
            dm = discord.Embed(title="🔇 You Have Been Muted", color=discord.Color.dark_grey(), timestamp=discord.utils.utcnow())
            dm.description = (
                f"You have been **muted** in **Afternight Legacies**.\n\n"
                f"**Reason:** {reason}\n**Duration:** {duration}\n**Unmuted:** {until_str}\n\n"
                f"Appeal here:\n{APPEAL_SERVER}"
            )
            dm.set_footer(text="Afternight Moderation")
            await user.send(embed=dm)
        except discord.Forbidden:
            pass

        await user.timeout(until, reason=f"{reason} | Muted by {actor}")

        log_embed = discord.Embed(title="🔇 Member Muted", color=discord.Color.dark_grey(), timestamp=discord.utils.utcnow())
        log_embed.set_thumbnail(url=user.display_avatar.url)
        log_embed.add_field(name="Discord ID", value=f"{user.mention} (`{user.id}`)", inline=False)
        log_embed.add_field(name="Reason",     value=reason,                          inline=False)
        log_embed.add_field(name="Duration",   value=duration,                        inline=True)
        log_embed.add_field(name="Unmuted",    value=until_str,                       inline=True)
        log_embed.add_field(name="Evidence",   value=evidence,                        inline=False)
        log_embed.add_field(name="Muted By",   value=f"{actor.mention} (`{actor.id}`)", inline=False)
        log_embed.set_footer(text=f"User ID: {user.id}")

        log_channel = guild.get_channel(MUTE_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        return until_str, None

    @app_commands.command(name="mute", description="Timeout (mute) a member.")
    @app_commands.describe(user="The member to mute", reason="Reason", duration="Duration (10m, 1h, 1d)", evidence="Evidence links", attachment1="Attachment", attachment2="Attachment")
    async def mute_slash(self, interaction: discord.Interaction, user: discord.Member, reason: str, duration: str, evidence: str = "None provided", attachment1: discord.Attachment = None, attachment2: discord.Attachment = None):
        await interaction.response.defer()
        actor = interaction.user
        if not is_staff(actor):
            return await interaction.followup.send("❌ Only staff may mute.", ephemeral=True)
        if user == actor:
            return await interaction.followup.send("❌ You cannot mute yourself.", ephemeral=True)
        if user.top_role >= interaction.guild.me.top_role:
            return await interaction.followup.send("❌ I cannot mute this user.", ephemeral=True)
        attachments   = [a for a in [attachment1, attachment2] if a]
        evidence_full = format_evidence(evidence, attachments)
        until_str, error = await self._mute(interaction.guild, actor, user, reason, duration, evidence_full)
        if error:
            return await interaction.followup.send(f"❌ {error}", ephemeral=True)
        confirm = discord.Embed(title="✅ Member Muted", color=discord.Color.dark_grey(), timestamp=discord.utils.utcnow())
        confirm.add_field(name="Member",   value=user.mention, inline=True)
        confirm.add_field(name="Duration", value=duration,     inline=True)
        confirm.add_field(name="Reason",   value=reason,       inline=True)
        await interaction.followup.send(embed=confirm)

    @commands.command(name="mute", aliases=["timeout"])
    async def mute_prefix(self, ctx: commands.Context, user: discord.Member, duration: str, *, reason: str = "No reason provided"):
        if not is_staff(ctx.author):
            return await ctx.send("❌ Only staff may mute.")
        if user == ctx.author:
            return await ctx.send("❌ You cannot mute yourself.")
        if user.top_role >= ctx.guild.me.top_role:
            return await ctx.send("❌ I cannot mute this user.")
        evidence = "\n".join(a.url for a in ctx.message.attachments) if ctx.message.attachments else "None provided"
        until_str, error = await self._mute(ctx.guild, ctx.author, user, reason, duration, evidence)
        if error:
            return await ctx.send(f"❌ {error}")
        await ctx.send(f"✅ **{user.display_name}** has been muted for **{duration}**.")

    # ─────────────────────────────────────────────────────────────────────────
    # UNMUTE
    # ─────────────────────────────────────────────────────────────────────────

    async def _unmute(self, guild: discord.Guild, actor: discord.Member,
                      user: discord.Member, reason: str):
        await user.timeout(None, reason=f"{reason} | Unmuted by {actor}")

        try:
            dm = discord.Embed(title="🔊 You Have Been Unmuted", color=discord.Color.green(), timestamp=discord.utils.utcnow())
            dm.description = f"Your mute in **Afternight Legacies** has been lifted.\n\n**Reason:** {reason}"
            dm.set_footer(text="Afternight Moderation")
            await user.send(embed=dm)
        except discord.Forbidden:
            pass

        log_embed = discord.Embed(title="🔊 Member Unmuted", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        log_embed.set_thumbnail(url=user.display_avatar.url)
        log_embed.add_field(name="Discord ID", value=f"{user.mention} (`{user.id}`)", inline=False)
        log_embed.add_field(name="Reason",     value=reason,                          inline=False)
        log_embed.add_field(name="Unmuted By", value=f"{actor.mention} (`{actor.id}`)", inline=False)
        log_embed.set_footer(text=f"User ID: {user.id}")

        log_channel = guild.get_channel(MUTE_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

    @app_commands.command(name="unmute", description="Remove a timeout from a member.")
    @app_commands.describe(user="The member to unmute", reason="Reason (optional)")
    async def unmute_slash(self, interaction: discord.Interaction, user: discord.Member, reason: str = "Mute lifted by staff"):
        await interaction.response.defer()
        if not is_staff(interaction.user):
            return await interaction.followup.send("❌ Only staff may unmute.", ephemeral=True)
        if not user.is_timed_out():
            return await interaction.followup.send(f"❌ {user.mention} is not muted.", ephemeral=True)
        await self._unmute(interaction.guild, interaction.user, user, reason)
        confirm = discord.Embed(title="✅ Member Unmuted", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        confirm.add_field(name="Member", value=user.mention, inline=True)
        confirm.add_field(name="Reason", value=reason,       inline=True)
        await interaction.followup.send(embed=confirm)

    @commands.command(name="unmute", aliases=["untimeout"])
    async def unmute_prefix(self, ctx: commands.Context, user: discord.Member, *, reason: str = "Mute lifted by staff"):
        if not is_staff(ctx.author):
            return await ctx.send("❌ Only staff may unmute.")
        if not user.is_timed_out():
            return await ctx.send(f"❌ {user.mention} is not muted.")
        await self._unmute(ctx.guild, ctx.author, user, reason)
        await ctx.send(f"✅ **{user.display_name}** has been unmuted.")

    # ─────────────────────────────────────────────────────────────────────────
    # UNBAN
    # ─────────────────────────────────────────────────────────────────────────

    async def _unban(self, guild: discord.Guild, actor: discord.Member,
                     user: discord.User, reason: str):
        await guild.unban(user, reason=f"{reason} | Unbanned by {actor}")

        try:
            expired = await self.bot.db.get_expired_temp_bans()
            for ban in expired:
                if ban["user_id"] == str(user.id) and ban["guild_id"] == str(guild.id):
                    await self.bot.db.mark_temp_ban_expired(ban["id"])
        except Exception:
            pass

        try:
            dm = discord.Embed(title="✅ You Have Been Unbanned", color=discord.Color.green(), timestamp=discord.utils.utcnow())
            dm.description = f"You have been **unbanned** from **Afternight Legacies**.\n\n**Reason:** {reason}"
            dm.set_footer(text="Afternight Moderation")
            await user.send(embed=dm)
        except discord.Forbidden:
            pass

        log_embed = discord.Embed(title="✅ Member Unbanned", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        log_embed.add_field(name="Discord ID",  value=f"{user.mention} (`{user.id}`)", inline=False)
        log_embed.add_field(name="Reason",      value=reason,                          inline=False)
        log_embed.add_field(name="Unbanned By", value=f"{actor.mention} (`{actor.id}`)", inline=False)
        log_embed.set_footer(text=f"User ID: {user.id}")

        log_channel = guild.get_channel(UNBAN_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

    @app_commands.command(name="unban", description="Unban a user from the server.")
    @app_commands.describe(user_id="The Discord ID to unban", reason="Reason")
    async def unban_slash(self, interaction: discord.Interaction, user_id: str, reason: str = "No reason provided"):
        await interaction.response.defer()
        if not is_admin(interaction.user):
            return await interaction.followup.send("❌ Only Admins or above may unban.", ephemeral=True)
        try:
            user = await self.bot.fetch_user(int(user_id))
        except (ValueError, discord.NotFound):
            return await interaction.followup.send("❌ Could not find that user ID.", ephemeral=True)
        try:
            await self._unban(interaction.guild, interaction.user, user, reason)
        except discord.NotFound:
            return await interaction.followup.send(f"❌ {user} is not banned.", ephemeral=True)
        confirm = discord.Embed(title="✅ Member Unbanned", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        confirm.add_field(name="User",   value=f"{user} (`{user.id}`)", inline=True)
        confirm.add_field(name="Reason", value=reason,                  inline=True)
        await interaction.followup.send(embed=confirm)

    @commands.command(name="unban")
    async def unban_prefix(self, ctx: commands.Context, user_id: str, *, reason: str = "No reason provided"):
        if not is_admin(ctx.author):
            return await ctx.send("❌ Only Admins or above may unban.")
        try:
            user = await self.bot.fetch_user(int(user_id))
        except (ValueError, discord.NotFound):
            return await ctx.send("❌ Could not find that user ID.")
        try:
            await self._unban(ctx.guild, ctx.author, user, reason)
        except discord.NotFound:
            return await ctx.send(f"❌ {user} is not banned.")
        await ctx.send(f"✅ **{user}** has been unbanned.")

    # ─────────────────────────────────────────────────────────────────────────
    # LOCKDOWN
    # ─────────────────────────────────────────────────────────────────────────

    async def _lockdown(self, guild: discord.Guild, actor: discord.Member, reason: str):
        staff_role = guild.get_role(ROLE_STAFF)
        admin_role = guild.get_role(ROLE_ADMIN)
        locked     = 0
        failed     = 0

        lockdown_embed = discord.Embed(
            title="🔒 Server Lockdown",
            description=(
                f"The server is currently under **lockdown**.\n\n"
                f"**Reason:** {reason}\n\n"
                f"Only staff members may speak during this time."
            ),
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        lockdown_embed.set_footer(text=f"Lockdown initiated by {actor.display_name}")

        for channel_id in LOCKDOWN_TEXT_CHANNELS:
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            try:
                ow = channel.overwrites_for(guild.default_role)
                ow.send_messages = False
                await channel.set_permissions(guild.default_role, overwrite=ow, reason=f"Lockdown by {actor}: {reason}")
                for role in [staff_role, admin_role]:
                    if role:
                        sow = channel.overwrites_for(role)
                        sow.send_messages = True
                        await channel.set_permissions(role, overwrite=sow, reason="Lockdown — staff override")
                await channel.send(embed=lockdown_embed)
                locked += 1
            except Exception:
                failed += 1

        for channel_id in LOCKDOWN_VOICE_CHANNELS:
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            try:
                ow = channel.overwrites_for(guild.default_role)
                ow.connect = False
                await channel.set_permissions(guild.default_role, overwrite=ow, reason=f"Lockdown by {actor}: {reason}")
                for role in [staff_role, admin_role]:
                    if role:
                        sow = channel.overwrites_for(role)
                        sow.connect = True
                        await channel.set_permissions(role, overwrite=sow, reason="Lockdown — staff override")
                locked += 1
            except Exception:
                failed += 1

        log_embed = discord.Embed(title="🔒 Server Lockdown Initiated", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        log_embed.add_field(name="By",     value=actor.mention,          inline=True)
        log_embed.add_field(name="Reason", value=reason,                 inline=True)
        log_embed.add_field(name="Locked", value=f"{locked} channel(s)", inline=True)
        log_channel = guild.get_channel(LOCKDOWN_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        return locked, failed

    async def _unlockdown(self, guild: discord.Guild, actor: discord.Member, reason: str):
        unlocked = 0
        failed   = 0

        unlock_embed = discord.Embed(
            title="🔓 Server Unlocked",
            description=(
                f"The server lockdown has been **lifted**.\n\n"
                f"**Reason:** {reason}\n\n"
                f"You may now speak freely. Please follow the server rules."
            ),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        unlock_embed.set_footer(text=f"Unlocked by {actor.display_name}")

        for channel_id in LOCKDOWN_TEXT_CHANNELS:
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            try:
                ow = channel.overwrites_for(guild.default_role)
                ow.send_messages = None
                await channel.set_permissions(guild.default_role, overwrite=ow, reason=f"Lockdown lifted by {actor}: {reason}")
                msg = await channel.send(embed=unlock_embed)
                await msg.delete(delay=15)
                unlocked += 1
            except Exception:
                failed += 1

        for channel_id in LOCKDOWN_VOICE_CHANNELS:
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            try:
                ow = channel.overwrites_for(guild.default_role)
                ow.connect = None
                await channel.set_permissions(guild.default_role, overwrite=ow, reason=f"Lockdown lifted by {actor}: {reason}")
                unlocked += 1
            except Exception:
                failed += 1

        log_embed = discord.Embed(title="🔓 Server Lockdown Lifted", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        log_embed.add_field(name="By",       value=actor.mention,            inline=True)
        log_embed.add_field(name="Reason",   value=reason,                   inline=True)
        log_embed.add_field(name="Unlocked", value=f"{unlocked} channel(s)", inline=True)
        log_channel = guild.get_channel(LOCKDOWN_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        return unlocked, failed

    @app_commands.command(name="lockdownserver", description="Lock specific channels.")
    @app_commands.describe(reason="Reason for the lockdown")
    async def lockdown_slash(self, interaction: discord.Interaction, reason: str = "No reason provided"):
        await interaction.response.defer()
        if not is_head(interaction.user):
            return await interaction.followup.send("❌ Only CM/Overseer/Creators may lockdown.", ephemeral=True)
        locked, failed = await self._lockdown(interaction.guild, interaction.user, reason)
        confirm = discord.Embed(title="🔒 Server Locked Down", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        confirm.add_field(name="Reason", value=reason,              inline=True)
        confirm.add_field(name="Locked", value=f"{locked} channels", inline=True)
        await interaction.followup.send(embed=confirm)

    @commands.command(name="lockdown", aliases=["lockdownserver"])
    async def lockdown_prefix(self, ctx: commands.Context, *, reason: str = "No reason provided"):
        if not is_head(ctx.author):
            return await ctx.send("❌ Only CM/Overseer/Creators may lockdown.")
        locked, failed = await self._lockdown(ctx.guild, ctx.author, reason)
        await ctx.send(f"🔒 Server locked down. **{locked}** channel(s) locked.")

    @app_commands.command(name="unlockdownserver", description="Unlock all channels after a lockdown.")
    @app_commands.describe(reason="Reason for ending the lockdown")
    async def unlockdown_slash(self, interaction: discord.Interaction, reason: str = "Lockdown lifted"):
        await interaction.response.defer()
        if not is_head(interaction.user):
            return await interaction.followup.send("❌ Only CM/Overseer/Creators may unlock.", ephemeral=True)
        unlocked, failed = await self._unlockdown(interaction.guild, interaction.user, reason)
        confirm = discord.Embed(title="🔓 Server Unlocked", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        confirm.add_field(name="Reason",   value=reason,                inline=True)
        confirm.add_field(name="Unlocked", value=f"{unlocked} channels", inline=True)
        await interaction.followup.send(embed=confirm)

    @commands.command(name="unlock", aliases=["unlockdownserver"])
    async def unlockdown_prefix(self, ctx: commands.Context, *, reason: str = "Lockdown lifted"):
        if not is_head(ctx.author):
            return await ctx.send("❌ Only CM/Overseer/Creators may unlock.")
        unlocked, failed = await self._unlockdown(ctx.guild, ctx.author, reason)
        await ctx.send(f"🔓 Server unlocked. **{unlocked}** channel(s) unlocked.")

    # ─────────────────────────────────────────────────────────────────────────
    # STAFF STRIKES
    # ─────────────────────────────────────────────────────────────────────────

    async def _staffstrike(self, guild: discord.Guild, actor: discord.Member,
                           user: discord.Member, reason: str, evidence: str):
        await self.bot.db.add_staff_strike(str(user.id), str(guild.id), reason, evidence, str(actor.id))
        strikes      = await self.bot.db.get_staff_strikes(str(user.id), str(guild.id))
        strike_count = len(strikes)

        log_embed = discord.Embed(title="⚡ Staff Strike Issued", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        log_embed.set_thumbnail(url=user.display_avatar.url)
        log_embed.add_field(name="Staff Member",  value=f"{user.mention} (`{user.id}`)", inline=False)
        log_embed.add_field(name="Reason",        value=reason,                          inline=False)
        log_embed.add_field(name="Evidence",      value=evidence,                        inline=False)
        log_embed.add_field(name="Issued By",     value=f"{actor.mention} (`{actor.id}`)", inline=True)
        log_embed.add_field(name="Total Strikes", value=f"**{strike_count}/3**",         inline=True)
        log_embed.set_footer(text=f"User ID: {user.id}")

        if strike_count > 1:
            prev_text = ""
            for i, s in enumerate(strikes[:-1], 1):
                date = str(s.get("created_at", ""))[:10]
                prev_text += f"**{i}.** {s['reason']} *({date})*\n"
            log_embed.add_field(name=f"Previous Strikes ({strike_count - 1})", value=prev_text[:1024], inline=False)

        log_channel = guild.get_channel(STAFF_STRIKE_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(embed=log_embed)

        try:
            dm = discord.Embed(title="⚡ You Have Received a Staff Strike", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
            dm.description = (
                f"You have received a **staff strike** in **Afternight Legacies**.\n\n"
                f"**Reason:** {reason}\n**Strike Count:** {strike_count}/3\n\n"
            )
            if strike_count >= 3:
                dm.description += "⚠️ You have reached **3/3 strikes** and have been **automatically removed from staff**."
            else:
                dm.description += "Reaching **3 strikes** will result in automatic removal from staff."
            dm.set_footer(text="Afternight Staff System")
            await user.send(embed=dm)
        except discord.Forbidden:
            pass

        auto_fired = False
        if strike_count >= 3:
            roles_removed = []
            for role_id in ALL_STAFF_ROLES:
                role = guild.get_role(role_id)
                if role and role in user.roles:
                    roles_removed.append(role)
            if roles_removed:
                await user.remove_roles(*roles_removed, reason="Auto-fired: 3 staff strikes")
            fire_embed = discord.Embed(
                title="🔥 Staff Member Auto-Fired",
                description=(
                    f"{user.mention} has reached **3/3 staff strikes** and has been automatically removed.\n\n"
                    f"**Roles Removed:** {', '.join(r.name for r in roles_removed) or 'None'}"
                ),
                color=discord.Color.dark_red(),
                timestamp=discord.utils.utcnow()
            )
            if log_channel:
                await log_channel.send(embed=fire_embed)
            auto_fired = True

        return strike_count, auto_fired

    @app_commands.command(name="staffstrike", description="Issue a strike to a staff member.")
    @app_commands.describe(user="The staff member", reason="Reason", evidence="Evidence (optional)")
    async def staffstrike_slash(self, interaction: discord.Interaction, user: discord.Member, reason: str, evidence: str = "None provided"):
        await interaction.response.defer()
        actor = interaction.user
        if not is_head(actor):
            return await interaction.followup.send("❌ Only CM/Overseer/Creators may strike staff.", ephemeral=True)
        if not is_staff(user):
            return await interaction.followup.send(f"❌ {user.mention} is not a staff member.", ephemeral=True)
        if user == actor:
            return await interaction.followup.send("❌ You cannot strike yourself.", ephemeral=True)
        count, auto_fired = await self._staffstrike(interaction.guild, actor, user, reason, evidence)
        confirm = discord.Embed(title="✅ Staff Strike Issued", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        confirm.add_field(name="Staff Member", value=user.mention,       inline=True)
        confirm.add_field(name="Strike Count", value=f"{count}/3",       inline=True)
        confirm.add_field(name="Reason",       value=reason,             inline=False)
        if auto_fired:
            confirm.add_field(name="⚠️ Auto Action", value="Staff member has been fired.", inline=False)
        await interaction.followup.send(embed=confirm)

    @commands.command(name="staffstrike")
    async def staffstrike_prefix(self, ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided"):
        if not is_head(ctx.author):
            return await ctx.send("❌ Only CM/Overseer/Creators may strike staff.")
        if not is_staff(user):
            return await ctx.send(f"❌ {user.mention} is not a staff member.")
        if user == ctx.author:
            return await ctx.send("❌ You cannot strike yourself.")
        count, auto_fired = await self._staffstrike(ctx.guild, ctx.author, user, reason, "None provided")
        msg = f"✅ Staff strike issued to **{user.display_name}**. Strike count: **{count}/3**."
        if auto_fired:
            msg += " They have been **auto-fired**."
        await ctx.send(msg)

    @app_commands.command(name="viewstaffstrikes", description="View staff strikes for a staff member.")
    @app_commands.describe(user="The staff member to check")
    async def viewstaffstrikes_slash(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer()
        if not is_head(interaction.user):
            return await interaction.followup.send("❌ Only CM/Overseer/Creators may view staff strikes.", ephemeral=True)
        guild   = interaction.guild
        strikes = await self.bot.db.get_staff_strikes(str(user.id), str(guild.id))
        count   = len(strikes)
        embed   = discord.Embed(
            title=f"⚡ Staff Strikes — {user.display_name}",
            color=discord.Color.orange() if count > 0 else discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Total Strikes", value=f"**{count}/3**", inline=True)
        embed.add_field(name="Discord ID",    value=f"`{user.id}`",   inline=True)
        if strikes:
            for i, s in enumerate(strikes, 1):
                date       = str(s.get("created_at", ""))[:10]
                issuer     = guild.get_member(int(s["issued_by"]))
                issuer_str = issuer.display_name if issuer else f"ID: {s['issued_by']}"
                embed.add_field(
                    name=f"Strike {i} — {date}",
                    value=f"**Reason:** {s['reason']}\n**Evidence:** {s.get('evidence', 'None')}\n**By:** {issuer_str}",
                    inline=False
                )
        else:
            embed.add_field(name="No Strikes", value="This staff member has no strikes.", inline=False)
        embed.set_footer(text=f"User ID: {user.id}")
        await interaction.followup.send(embed=embed)

    @commands.command(name="viewstaffstrikes", aliases=["staffstrikes"])
    async def viewstaffstrikes_prefix(self, ctx: commands.Context, user: discord.Member):
        if not is_head(ctx.author):
            return await ctx.send("❌ Only CM/Overseer/Creators may view staff strikes.")
        strikes = await self.bot.db.get_staff_strikes(str(user.id), str(ctx.guild.id))
        count   = len(strikes)
        await ctx.send(f"⚡ **{user.display_name}** has **{count}/3** staff strike(s).")

    @app_commands.command(name="clearstaffstrikes", description="Clear all staff strikes for a staff member.")
    @app_commands.describe(user="The staff member whose strikes to clear")
    async def clearstaffstrikes_slash(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)
        if not is_head(interaction.user):
            return await interaction.followup.send("❌ Only CM/Overseer/Creators may clear staff strikes.", ephemeral=True)
        removed = await self.bot.db.clear_staff_strikes(str(user.id), str(interaction.guild.id))
        embed = discord.Embed(title="✅ Staff Strikes Cleared", description=f"Cleared **{removed}** strike(s) from {user.mention}.", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        await interaction.followup.send(embed=embed)
        log_channel = interaction.guild.get_channel(STAFF_STRIKE_LOG_CHANNEL)
        if log_channel:
            e = discord.Embed(title="🗑️ Staff Strikes Cleared", color=discord.Color.green(), timestamp=discord.utils.utcnow())
            e.add_field(name="Staff Member", value=f"{user.mention} (`{user.id}`)", inline=True)
            e.add_field(name="Cleared By",   value=interaction.user.mention,        inline=True)
            e.add_field(name="Removed",      value=f"{removed} strike(s)",          inline=True)
            await log_channel.send(embed=e)

    @commands.command(name="clearstaffstrikes")
    async def clearstaffstrikes_prefix(self, ctx: commands.Context, user: discord.Member):
        if not is_head(ctx.author):
            return await ctx.send("❌ Only CM/Overseer/Creators may clear staff strikes.")
        removed = await self.bot.db.clear_staff_strikes(str(user.id), str(ctx.guild.id))
        await ctx.send(f"✅ Cleared **{removed}** staff strike(s) from **{user.display_name}**.")


async def setup(bot):
    await bot.add_cog(ModerationCog(bot))
