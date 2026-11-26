"""
cogs/purge.py — /purge and !purge commands
"""
import datetime
import discord
from discord import app_commands
from discord.ext import commands
from constants import MOD_LOG_CHANNEL_ID

# ── Config ────────────────────────────────────────────────────────────────────
ADMIN_ROLES: set[int] = {
    1575225137542733954,  # [O] Owner.
    1575225368577704116,  # [Co-O] Co-Owner.
    1575225624837099631,  # [CM] Community Manager.
    1575225697406947418,  # [SOH] Staff OverHead.
    1575225917368705104,  # [SA] Senior Administrator.
    1575226137003687976,  # [A] Administrator.
    1575233276556214343,  # Admin
}


def is_admin_plus(member: discord.abc.User | discord.Member) -> bool:
    if not isinstance(member, discord.Member):
        return False
    return bool({r.id for r in member.roles} & ADMIN_ROLES)


class PurgeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _post_log(self, guild: discord.Guild | None, embed: discord.Embed):
        if guild:
            channel = guild.get_channel(MOD_LOG_CHANNEL_ID)
            if isinstance(channel, discord.TextChannel):
                await channel.send(embed=embed)
                return
        await self.bot.log_action(embed)

    async def _do_purge(
        self,
        channel: discord.abc.GuildChannel,
        amount: int,
        target_user: discord.Member = None
    ) -> int:
        if not isinstance(channel, discord.TextChannel):
            return 0
        if target_user:
            def check(m: discord.Message):
                return m.author.id == target_user.id
            deleted = await channel.purge(limit=amount * 5, check=check)
            return len(deleted)
        deleted = await channel.purge(limit=amount)
        return len(deleted)

    # ── Slash command ─────────────────────────────────────────────────────────

    @app_commands.command(name="purge", description="Purge messages from a channel.")
    @app_commands.describe(
        amount="Number of messages to delete (max 100)",
        channel="Channel to purge (defaults to current channel)",
        user="Only delete messages from this user (optional)"
    )
    async def purge_slash(
        self,
        interaction: discord.Interaction,
        amount: int,
        channel: discord.TextChannel = None,
        user: discord.Member = None
    ):
        await interaction.response.defer(ephemeral=True)

        if not is_admin_plus(interaction.user):
            return await interaction.followup.send(
                "❌ Only Admins or above may use `/purge`.",
                ephemeral=True
            )

        if amount < 1 or amount > 100:
            return await interaction.followup.send(
                "❌ Amount must be between 1 and 100.",
                ephemeral=True
            )

        target_channel = channel or interaction.channel
        if not isinstance(target_channel, discord.TextChannel):
            return await interaction.followup.send(
                "❌ Please select a valid text channel.",
                ephemeral=True
            )

        deleted = await self._do_purge(target_channel, amount, user)

        confirm = discord.Embed(
            title="🗑️ Messages Purged",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        confirm.add_field(name="Channel", value=target_channel.mention, inline=True)
        confirm.add_field(name="Deleted", value=f"{deleted} message(s)", inline=True)
        confirm.add_field(name="Target", value=user.mention if user else "All", inline=True)
        confirm.add_field(name="By", value=interaction.user.mention, inline=True)
        await interaction.followup.send(embed=confirm, ephemeral=True)

        log_embed = discord.Embed(
            title="🗑️ Channel Purged",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Actor", value=interaction.user.mention, inline=True)
        log_embed.add_field(name="Channel", value=target_channel.mention, inline=True)
        log_embed.add_field(name="Deleted", value=f"{deleted} message(s)", inline=True)
        log_embed.add_field(name="Target User", value=user.mention if user else "All", inline=True)
        await self._post_log(interaction.guild, log_embed)

    # ── Prefix command ────────────────────────────────────────────────────────

    @commands.command(name="purge", aliases=["clear", "clean"])
    async def purge_prefix(
        self,
        ctx: commands.Context,
        amount: int = 10,
        user: discord.Member = None
    ):
        if not is_admin_plus(ctx.author):
            return await ctx.send("❌ Only Admins or above may use `!purge`.", delete_after=5)

        if amount < 1 or amount > 100:
            return await ctx.send("❌ Amount must be between 1 and 100.", delete_after=5)

        if not isinstance(ctx.channel, discord.TextChannel):
            return await ctx.send("❌ This command can only be used in a text channel.", delete_after=5)

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        deleted = await self._do_purge(ctx.channel, amount, user)

        confirm = await ctx.send(
            f"✅ Deleted **{deleted}** message(s){f' from {user.mention}' if user else ''}."
        )
        await confirm.delete(delay=5)

        log_embed = discord.Embed(
            title="🗑️ Channel Purged (!purge)",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Actor", value=ctx.author.mention, inline=True)
        log_embed.add_field(name="Channel", value=ctx.channel.mention, inline=True)
        log_embed.add_field(name="Deleted", value=f"{deleted} message(s)", inline=True)
        log_embed.add_field(name="Target User", value=user.mention if user else "All", inline=True)
        await self._post_log(ctx.guild, log_embed)


async def setup(bot):
    await bot.add_cog(PurgeCog(bot))
