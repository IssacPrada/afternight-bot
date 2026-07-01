"""
cogs/testing.py — Auto-rank to Tester + /testingsession command
"""
import discord
from discord import app_commands
from discord.ext import commands
from utils.roblox import fetch_roblox_user
from utils.roblox_group import get_roblox_user_id, get_xcsrf_token, HEADERS
import aiohttp
import datetime
import os

# ── Config ────────────────────────────────────────────────────────────────────
TESTING_CHANNEL_ID    = 1458533750806937764
FEEDBACK_CHANNEL_ID   = 1458533639095849010
GAME_TESTER_ROLE_ID   = 1458302213368840458
LEGACIES_GROUP_ID     = 1024076883
TESTER_RANK           = 40

ALLOWED_ROLES: set[int] = {
    1458303507659624683,  # Programmer
    1387649282139754587,  # Creators
}

GAME_LINK = "https://www.roblox.com/games/92315559992414/Afternight-Legacies-TESTING"
COOKIE    = os.getenv("ROBLOX_SECURITY_COOKIE")

HEADERS_LEGACIES = {
    "Cookie": f".ROBLOSECURITY={COOKIE}",
    "Content-Type": "application/json",
}


# ── Roblox helpers ────────────────────────────────────────────────────────────

async def get_legacies_role_id(rank: int) -> int | None:
    """Get the roleId for a given rank in the Legacies group."""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://groups.roblox.com/v1/groups/{LEGACIES_GROUP_ID}/roles",
            headers=HEADERS_LEGACIES
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            for role in data.get("roles", []):
                if role["rank"] == rank:
                    return role["id"]
    return None


async def rank_to_tester(roblox_username: str) -> tuple[bool, str]:
    """Rank a user to Tester in the Legacies group."""
    if not COOKIE:
        return False, "ROBLOX_SECURITY_COOKIE is not set."

    # Get user ID
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://users.roblox.com/v1/usernames/users",
            json={"usernames": [roblox_username], "excludeBannedUsers": False},
            headers=HEADERS_LEGACIES
        ) as resp:
            if resp.status != 200:
                return False, f"Could not find Roblox user: `{roblox_username}`"
            data = await resp.json()
            users = data.get("data", [])
            if not users:
                return False, f"Roblox user `{roblox_username}` does not exist."
            user_id = users[0]["id"]

    # Get role ID for tester rank
    role_id = await get_legacies_role_id(TESTER_RANK)
    if not role_id:
        return False, "Could not find the Tester role in the Legacies group."

    # Get XCSRF token
    try:
        token = await get_xcsrf_token()
        headers = {**HEADERS_LEGACIES, "x-csrf-token": token}

        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f"https://groups.roblox.com/v1/groups/{LEGACIES_GROUP_ID}/users/{user_id}",
                headers=headers,
                json={"roleId": role_id}
            ) as resp:
                if resp.status == 200:
                    return True, f"✅ `{roblox_username}` has been ranked to **Tester** in Afternight Legacies."
                else:
                    error = await resp.json()
                    msg = error.get("errors", [{}])[0].get("message", "Unknown error")
                    return False, f"❌ Roblox API error: {msg}"

    except Exception as e:
        return False, f"❌ Exception: {str(e)}"


class TestingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── Auto-rank listener ────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id != TESTING_CHANNEL_ID:
            return
        if message.channel.id != TESTING_CHANNEL_ID:
            return

        # DEBUG - remove after testing
        print(f"[DEBUG] {message.author} roles: {[r.id for r in message.author.roles]}")
        print(f"[DEBUG] Looking for role: {GAME_TESTER_ROLE_ID}")
        print(f"[DEBUG] Tester role found: {message.guild.get_role(GAME_TESTER_ROLE_ID)}")

        # ── Prevent duplicate ranking ─────────────────────────────────────────────
        async for msg in message.channel.history(limit=100):
            if msg.author == self.bot.user and msg.reference:
                ref = msg.reference.resolved
                if ref and ref.author == message.author and "Tester Rank Granted" in (
                msg.embeds[0].title if msg.embeds else ""):
                    await message.reply(
                        "⚠️ You have already been ranked to Tester!",
                        delete_after=10
                    )
                    return

        # ── Only Game Testers can use this channel ────────────────────────────
        tester_role = message.guild.get_role(GAME_TESTER_ROLE_ID)
        if tester_role not in message.author.roles:
            await message.reply(
                "❌ Only Game Testers may submit their username here.",
                delete_after=10
            )
            return

        roblox_username = message.content.strip()

        # Basic validation — no spaces, reasonable length
        if " " in roblox_username or len(roblox_username) > 20 or len(roblox_username) < 1:
            await message.reply(
                "❌ Please send just your Roblox username with no spaces.",
                delete_after=10
            )
            return

        # Show typing indicator while we process
        async with message.channel.typing():
            roblox_data = await fetch_roblox_user(roblox_username)
            if not roblox_data:
                await message.reply(
                    f"❌ Could not find Roblox user `{roblox_username}`. "
                    "Please double check your username and try again.",
                    delete_after=15
                )
                return

            success, result_msg = await rank_to_tester(roblox_username)

        if success:
            embed = discord.Embed(
                title="🎮 Tester Rank Granted!",
                color=discord.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.set_thumbnail(url=roblox_data.get("avatar_url") or message.author.display_avatar.url)
            embed.add_field(name="Discord", value=message.author.mention, inline=True)
            embed.add_field(name="Roblox", value=f"`{roblox_username}`", inline=True)
            embed.add_field(
                name="Game Link",
                value=f"[Click to join]({GAME_LINK})",
                inline=False
            )
            embed.set_footer(text="Afternight Legacies Testing")
            await message.reply(embed=embed)
        else:
            await message.reply(f"❌ Failed to rank: {result_msg}", delete_after=15)

            # Rank them to tester
            success, result_msg = await rank_to_tester(roblox_username)

        if success:
            embed = discord.Embed(
                title="🎮 Tester Rank Granted!",
                color=discord.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.set_thumbnail(url=roblox_data.get("avatar_url") or message.author.display_avatar.url)
            embed.add_field(name="Discord", value=message.author.mention, inline=True)
            embed.add_field(name="Roblox", value=f"`{roblox_username}`", inline=True)
            embed.add_field(
                name="Game Link",
                value=f"[Click to join]({GAME_LINK})",
                inline=False
            )
            embed.set_footer(text="Afternight Legacies Testing")
            await message.reply(embed=embed)
        else:
            await message.reply(f"❌ Failed to rank: {result_msg}", delete_after=15)

    # ── /testingsession ───────────────────────────────────────────────────────

    @app_commands.command(
        name="testingsession",
        description="Announce a testing session and ping all game testers."
    )
    @app_commands.describe(
        channel="Channel to send the announcement to",
        date="Date of the session e.g. July 1st 2026",
        time="Time of the session e.g. 5:00 PM EST",
        testing="What will be tested e.g. combat system, map layout"
    )
    async def testingsession(self, interaction: discord.Interaction,
                              channel: discord.TextChannel,
                              date: str,
                              time: str,
                              testing: str):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user
        actor_role_ids = {r.id for r in actor.roles}

        if not actor_role_ids & ALLOWED_ROLES:
            return await interaction.followup.send(
                "❌ Only Programmers or Creators may use `/testingsession`.",
                ephemeral=True
            )

        guild       = interaction.guild
        tester_role = guild.get_role(GAME_TESTER_ROLE_ID)
        ping_str    = tester_role.mention if tester_role else "@GameTester"

        embed = discord.Embed(
            title="🎮 Testing Session Announcement",
            color=discord.Color.from_rgb(88, 101, 242),
            timestamp=datetime.datetime.utcnow()
        )
        embed.description = (
            f"*We will be conducting a testing session to evaluate **{testing}**. "
            f"This session will help us identify issues, gather feedback, and make "
            f"improvements for the game.*"
        )
        embed.add_field(
            name="Details",
            value=(
                f"📅 **Date:** {date}\n"
                f"⏰ **Time:** {time}\n"
                f"📍 **Link:** [Click to join]({GAME_LINK})"
            ),
            inline=False
        )
        embed.add_field(
            name="Feedback Channel",
            value=f"Please share any feedback, observations, or issues you encounter in <#{FEEDBACK_CHANNEL_ID}>.",
            inline=False
        )
        embed.set_footer(text="Thank you for your participation and support! — Afternight Team")

        await channel.send(content=ping_str, embed=embed)

        await interaction.followup.send(
            f"✅ Testing session announcement sent to {channel.mention}.",
            ephemeral=True
        )

        # ── Log ───────────────────────────────────────────────────────────────
        log_embed = discord.Embed(
            title="📋 Testing Session Announced",
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Announced By", value=actor.mention, inline=True)
        log_embed.add_field(name="Channel", value=channel.mention, inline=True)
        log_embed.add_field(name="Date", value=date, inline=True)
        log_embed.add_field(name="Time", value=time, inline=True)
        log_embed.add_field(name="Testing", value=testing, inline=False)
        await self.bot.log_action(log_embed)


async def setup(bot):
    await bot.add_cog(TestingCog(bot))
