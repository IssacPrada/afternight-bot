"""
cogs/help.py — /help command
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
            description="Use `/command` to run any command below.",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(
            name="⚔️ Moderation — Staff",
            value=(
                "`/warn` — Warn a member\n"
                "`/viewwarns` — View warnings for a member\n"
                "`/kick` — Kick a member\n"
                "`/mute` — Timeout a member\n"
                "`/unmute` — Remove a timeout\n"
            ),
            inline=False
        )
        embed.add_field(
            name="🔨 Moderation — Admin+",
            value=(
                "`/ban` — Ban a member\n"
                "`/unban` — Unban a user by ID\n"
                "`/clearwarns` — Clear warnings\n"
                "`/purge` — Delete messages in bulk\n"
                "`/lockdownserver` — Lock specific channels\n"
                "`/unlockdownserver` — Unlock channels\n"
            ),
            inline=False
        )
        embed.add_field(
            name="👑 Moderation — CM/Overseer/Creators",
            value=(
                "`/staffstrike` — Strike a staff member\n"
                "`/viewstaffstrikes` — View staff strikes\n"
                "`/clearstaffstrikes` — Clear staff strikes\n"
            ),
            inline=False
        )
        embed.add_field(
            name="🏰 Staff Management",
            value=(
                "`/promote` — Promote a staff member\n"
                "`/demote` — Demote a staff member\n"
                "`/fire` — Remove all staff roles\n"
                "`/inactivitynotice` — Submit inactivity notice\n"
                "`/resign` — Resign from your role\n"
            ),
            inline=False
        )
        embed.add_field(
            name="⚡ Faction Commands",
            value=(
                "`/strike` — Strike a faction member\n"
                "`/viewstrike` — View faction strikes\n"
                "`/clearstrikes` — Clear faction strikes\n"
                "`/factiondemote` — Remove from faction\n"
                "`/blacklist` — Blacklist a faction member\n"
                "`/unblacklist` — Remove from blacklist\n"
            ),
            inline=False
        )
        embed.add_field(
            name="📊 Activity",
            value=(
                "`/getplayertime` — View player activity\n"
                "`/getfactiontime` — View faction activity\n"
            ),
            inline=False
        )
        embed.add_field(
            name="📢 Announcements",
            value=(
                "`/shout` — Copy and send a message to any channel\n"
                "`/suggest` — Submit a suggestion\n"
                "`/testingsession` — Announce a testing session\n"
            ),
            inline=False
        )
        embed.add_field(
            name="🤖 AutoMod",
            value=(
                "`/addslur` — Add a word to automod\n"
                "`/removeslur` — Remove a word from automod\n"
                "`/viewslurs` — View the automod word list\n"
            ),
            inline=False
        )
        embed.add_field(
            name="🔑 Account",
            value=(
                "`/generatebackupcode` — Generate a role backup code\n"
                "`/transferroles` — Transfer roles to a new account\n"
            ),
            inline=False
        )
        embed.add_field(
            name="📋 Mass Actions",
            value=(
                "`/massrank` — Assign a role to multiple members\n"
                "`/purge` — Bulk delete messages\n"
                "`/setupblacklist` — Post the blacklist embed\n"
            ),
            inline=False
        )
        embed.set_footer(text="The Watcher V2 — Afternight Legacies")
        return embed

    @app_commands.command(name="help", description="View all available commands.")
    async def help_slash(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = self.build_help_embed()
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
