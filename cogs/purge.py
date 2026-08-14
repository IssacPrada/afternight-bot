"""
cogs/purge.py — /purge and !purge commands
"""
import discord
from discord import app_commands
from discord.ext import commands
import datetime

# ── Config ────────────────────────────────────────────────────────────────────
ROLE_ADMIN   = 1458303682180284681
ROLE_CM      = 1458302857764802683
ROLE_OVERSEER = 1458302854887510210
ROLE_CREATOR  = 1387649282139754587

ADMIN_ROLES: set[int] = {
    ROLE_ADMIN, ROLE_CM, ROLE_OVERSEER, ROLE_CREATOR
}


def is_admin_plus(member: discord.Member) -> bool:
    return bool({r.id for r in member.roles} & ADMIN_ROLES)


class PurgeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _do_purge(self, channel: discord.TextChannel,
                        amount: int, target_user: discord.Member = None) -> int:
        if target_user:
            def check(m):
                return m.author == target_user
            deleted = await channel.purge(limit=amount * 5, check=check)
            return len(deleted)
        else:
            deleted = await channel.purge(limit=amount)
            return len(deleted)

    # ── Slash command ─────────────────────────────────────────────────────────

    @app_commands.command(name="purge", description="Purge messages from a channel.")
    @app_commands.describe(
        amount="Number of messages to delete (max 100)",
        channel="Channel to purge (defaults to current channel)",
        user="Only delete messages from this user (optional)"
    )
    async def purge_slash(self, interaction: discord.Interaction,
                          amount: int,
                          channel: discord.TextChannel = None,
                          user: discord.Member = None):
        await interaction.response.defer(ephemeral=True)

        if not is_admin_plus(interaction.user):
            return await interaction.followup.send(
                "❌ Only Admins or above may use `/purge`.", ephemeral=True
            )

        if amount < 1 or amount > 100:
            return await interaction.followup.send(
                "❌ Amount must be between 1 and 100.", ephemeral=True
            )

        target_channel = channel or interaction.channel
        deleted = await self._do_purge(target_channel, amount, user)

        confirm = discord.Embed(
            title="🗑️ Messages Purged",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        confirm.add_field(name="Channel",  value=target_channel.mention,          inline=True)
        confirm.add_field(name="Deleted",  value=f"{deleted} message(s)",         inline=True)
        confirm.add_field(name="Target",   value=user.mention if user else "All", inline=True)
        confirm.add_field(name="By",       value=interaction.user.mention,        inline=True)
        await interaction.followup.send(embed=confirm, ephemeral=True)

    # ── Prefix command ────────────────────────────────────────────────────────

    @commands.command(name="purge", aliases=["clear", "clean"])
    async def purge_prefix(self, ctx: commands.Context,
                           amount: int = 10,
                           user: discord.Member = None):
        if not is_admin_plus(ctx.author):
            return await ctx.send("❌ Only Admins or above may use `!purge`.", delete_after=5)

        if amount < 1 or amount > 100:
            return await ctx.send("❌ Amount must be between 1 and 100.", delete_after=5)

        await ctx.message.delete()
        deleted = await self._do_purge(ctx.channel, amount, user)

        confirm = await ctx.send(
            f"✅ Deleted **{deleted}** message(s){f' from {user.mention}' if user else ''}."
        )
        await confirm.delete(delay=5)


async def setup(bot):
    await bot.add_cog(PurgeCog(bot))
