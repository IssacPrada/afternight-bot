"""
cogs/automod.py — Automated moderation (invite/link filter, spam/rate detection, and auto-timeout/log)
"""
import collections
import datetime
import re
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from constants import (
    AUTOMOD_LOG_CHANNEL_ID,
    is_staff,
)

INVITE_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?(?:discord\.gg|discordapp\.com/invite|discord\.com/invite)/[A-Za-z0-9-]+",
    re.IGNORECASE
)
URL_REGEX = re.compile(r"https?://\S+", re.IGNORECASE)


class AutoModCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.enabled = True
        self.block_invites = True
        self.block_links = False
        self.spam_threshold = 6        # messages within window
        self.spam_window_seconds = 5
        self._recent_messages: dict[tuple[int, int], collections.deque[float]] = collections.defaultdict(
            lambda: collections.deque(maxlen=25)
        )

    async def _post_automod_log(self, guild: discord.Guild, embed: discord.Embed):
        channel = guild.get_channel(AUTOMOD_LOG_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)
        else:
            await self.bot.log_action(embed)

    def _is_exempt(self, member: discord.abc.User | discord.Member) -> bool:
        if member.bot:
            return True
        if isinstance(member, discord.Member):
            if member.guild_permissions.administrator or member.guild_permissions.manage_messages:
                return True
            if is_staff(member):
                return True
        return False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self.enabled or not message.guild or self._is_exempt(message.author):
            return

        member = message.author
        content = message.content or ""
        trigger_reason: Optional[str] = None
        should_timeout = False

        # 1. Discord invite check
        if self.block_invites and INVITE_REGEX.search(content):
            trigger_reason = "Unauthorized Discord invite link"

        # 2. General link check (if enabled)
        if not trigger_reason and self.block_links and URL_REGEX.search(content):
            trigger_reason = "Unauthorized external link"

        # 3. Burst spam check
        if not trigger_reason and self.spam_threshold > 0:
            now_ts = datetime.datetime.utcnow().timestamp()
            bucket = self._recent_messages[(message.guild.id, member.id)]
            bucket.append(now_ts)
            recent_count = sum(1 for ts in bucket if (now_ts - ts) <= self.spam_window_seconds)
            if recent_count >= self.spam_threshold:
                bucket.clear()
                trigger_reason = f"Message spam ({recent_count} messages in {self.spam_window_seconds}s)"
                should_timeout = True

        if not trigger_reason:
            return

        try:
            await message.delete()
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            pass

        timeout_status = "No timeout"
        if should_timeout and isinstance(member, discord.Member):
            try:
                until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)
                await member.timeout(until, reason=f"AutoMod: {trigger_reason}")
                timeout_status = "Timed out for 10 minutes"
            except discord.Forbidden:
                timeout_status = "Missing timeout permissions"
            except discord.HTTPException:
                timeout_status = "Failed to apply timeout"

        try:
            await member.send(
                f"🛡️ Your message in **{message.guild.name}** was removed by AutoMod.\n"
                f"**Reason:** {trigger_reason}\n"
                f"**Action:** {timeout_status}"
            )
        except discord.Forbidden:
            pass

        log_embed = discord.Embed(
            title="🛡️ AutoMod Action Triggered",
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=True)
        log_embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        log_embed.add_field(name="Action", value=f"Deleted message · {timeout_status}", inline=True)
        log_embed.add_field(name="Reason", value=trigger_reason, inline=False)
        if content:
            log_embed.add_field(name="Content", value=content[:1024], inline=False)
        await self._post_automod_log(message.guild, log_embed)

    automod_group = app_commands.Group(
        name="automod",
        description="Configure automated moderation settings."
    )

    @automod_group.command(name="status", description="View current AutoMod configuration.")
    async def status(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member) or not (
            interaction.user.guild_permissions.manage_guild or is_staff(interaction.user)
        ):
            return await interaction.response.send_message(
                "❌ You don't have permission to view AutoMod settings.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="🛡️ AutoMod Status",
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Enabled", value="✅ Yes" if self.enabled else "❌ No", inline=True)
        embed.add_field(name="Block Invites", value="✅ Yes" if self.block_invites else "❌ No", inline=True)
        embed.add_field(name="Block Links", value="✅ Yes" if self.block_links else "❌ No", inline=True)
        embed.add_field(
            name="Spam Limit",
            value=f"{self.spam_threshold} msgs / {self.spam_window_seconds}s",
            inline=True
        )
        embed.add_field(name="Log Channel", value=f"<#{AUTOMOD_LOG_CHANNEL_ID}>", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @automod_group.command(name="toggle", description="Enable or disable AutoMod or specific filters.")
    @app_commands.describe(
        feature="Which feature to toggle (all, invites, links)",
        enabled="Whether to enable or disable it"
    )
    @app_commands.choices(feature=[
        app_commands.Choice(name="All AutoMod", value="all"),
        app_commands.Choice(name="Discord Invites", value="invites"),
        app_commands.Choice(name="External Links", value="links"),
    ])
    async def toggle(self, interaction: discord.Interaction, feature: str, enabled: bool):
        if not isinstance(interaction.user, discord.Member) or not (
            interaction.user.guild_permissions.manage_guild or is_staff(interaction.user)
        ):
            return await interaction.response.send_message(
                "❌ You don't have permission to change AutoMod settings.",
                ephemeral=True
            )

        if feature == "all":
            self.enabled = enabled
            label = "AutoMod"
        elif feature == "invites":
            self.block_invites = enabled
            label = "Invite Filter"
        else:
            self.block_links = enabled
            label = "Link Filter"

        log_embed = discord.Embed(
            title="🛡️ AutoMod Setting Updated",
            color=discord.Color.gold(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Setting", value=label, inline=True)
        log_embed.add_field(name="State", value="Enabled" if enabled else "Disabled", inline=True)
        log_embed.add_field(name="Updated By", value=f"{interaction.user.mention}", inline=True)
        await self._post_automod_log(interaction.guild, log_embed)

        await interaction.response.send_message(
            f"✅ **{label}** is now **{'enabled' if enabled else 'disabled'}**.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(AutoModCog(bot))
