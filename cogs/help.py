"""
cogs/help.py — /help and !help commands
"""
import discord
from discord import app_commands
from discord.ext import commands
import datetime


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def build_help_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="📖 The Watcher V2 — Command List",
            description="All commands are available as both `/slash` and `!prefix` commands.",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="⚔️ Moderation — Staff",
            value=(
                "`/warn` `!warn` — Warn a member\n"
                "`/viewwarns` `!viewwarns` — View warnings for a member\n"
                "`/kick` `!kick` — Kick a member\n"
                "`/mute` `!mute` — Timeout a member\n"
                "`/unmute` `!unmute` — Remove a timeout\n"
            ),
            inline=False
        )

        embed.add_field(
            name="🔨 Moderation — Admin+",
            value=(
                "`/ban` `!ban` — Ban a member\n"
                "`/unban` `!unban` — Unban a user by ID\n"
                "`/clearwarns` `!clearwarns` — Clear warnings\n"
                "`/purge` `!purge` — Delete messages in bulk\n"
                "`/lockdownserver` `!lockdown` — Lock specific channels\n"
                "`/unlockdownserver` `!unlock` — Unlock channels\n"
            ),
            inline=False
        )

        embed.add_field(
            name="👑 Moderation — CM/Overseer/Creators",
            value=(
                "`/staffstrike` `!staffstrike` — Strike a staff member\n"
                "`/viewstaffstrikes` `!viewstaffstrikes` — View staff strikes\n"
                "`/clearstaffstrikes` `!clearstaffstrikes` — Clear staff strikes\n"
            ),
            inline=False
        )

        embed.add_field(
            name="🏰 Staff Management",
            value=(
                "`/promote` `!promote` — Promote a staff member\n"
                "`/demote` `!demote` — Demote a staff member\n"
                "`/fire` `!fire` — Remove all staff roles\n"
                "`/inactivitynotice` `!inactivitynotice` — Submit inactivity notice\n"
                "`/resign` `!resign` — Resign from your role\n"
            ),
            inline=False
        )

        embed.add_field(
            name="⚡ Faction Commands",
            value=(
                "`/strike` `!strike` — Strike a faction member\n"
                "`/viewstrike` `!viewstrike` — View faction strikes\n"
                "`/clearstrikes` `!clearstrikes` — Clear faction strikes\n"
                "`/factiondemote` `!factiondemote` — Remove from faction\n"
                "`/blacklist` `!blacklist` — Blacklist a faction member\n"
                "`/unblacklist` `!unblacklist` — Remove from blacklist\n"
            ),
            inline=False
        )

        embed.add_field(
            name="📊 Activity",
            value=(
                "`/getplayertime` `!getplayertime` — View player activity\n"
                "`/getfactiontime` `!getfactiontime` — View faction activity\n"
            ),
            inline=False
        )

        embed.add_field(
            name="📢 Announcements",
            value=(
                "`/shout` `!shout` — Copy and send a message to any channel\n"
                "`/suggest` `!suggest` — Submit a suggestion\n"
                "`/testingsession` `!testingsession` — Announce a testing session\n"
            ),
            inline=False
        )

        embed.add_field(
            name="🤖 AutoMod",
            value=(
                "`/addslur` `!addslur` — Add a word to automod\n"
                "`/removeslur` `!removeslur` — Remove a word from automod\n"
                "`/viewslurs` `!viewslurs` — View the automod word list\n"
            ),
            inline=False
        )

        embed.add_field(
            name="🔑 Account",
            value=(
                "`/generatebackupcode` `!generatebackupcode` — Generate a role backup code\n"
                "`/transferroles` `!transferroles` — Transfer roles to a new account\n"
            ),
            inline=False
        )

        embed.add_field(
            name="📋 Mass Actions",
            value=(
                "`/massrank` `!massrank` — Assign a role to multiple members\n"
                "`/setupblacklist` — Post the blacklist embed\n"
            ),
            inline=False
        )

        embed.set_footer(text="The Watcher V2 — Afternight Legacies")
        return embed

    # ── Slash command ─────────────────────────────────────────────────────────

    @app_commands.command(name="help", description="View all available commands.")
    async def help_slash(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = self.build_help_embed()
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── Prefix command ────────────────────────────────────────────────────────

    @commands.command(name="help", aliases=["commands", "cmds"])
    async def help_prefix(self, ctx: commands.Context):
        embed = self.build_help_embed()
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
