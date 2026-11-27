"""
cogs/testing.py — Auto-rank to Tester + /testingsession command
"""
import os
import re
import datetime
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from utils.roblox import fetch_roblox_user
from utils.roblox_group import get_xcsrf_token

# ── Config ────────────────────────────────────────────────────────────────────
TESTING_CHANNEL_ID  = 1575319215643033690
FEEDBACK_CHANNEL_ID = 1575319889755906159
GAME_TESTER_ROLE_ID = 1575227735914061924  # [T] Tester.
LEGACIES_GROUP_ID   = 1024076883
TESTER_RANK         = 40
STICKY_TITLE        = "📌 Tester Group Auto-Rank"
USERNAME_RE         = re.compile(r"^[A-Za-z0-9_]{3,20}$")

ALLOWED_ROLES: set[int] = {
    1575225137542733954,  # [O] Owner.
    1575225368577704116,  # [Co-O] Co-Owner.
    1575233518265700353,  # [D] Developer.
}

GAME_LINK = "https://www.roblox.com/games/92315559992414/Afternight-Legacies-TESTING"
COOKIE    = os.getenv("ROBLOX_SECURITY_COOKIE")

HEADERS_LEGACIES = {
    "Cookie": f".ROBLOSECURITY={COOKIE}",
    "Content-Type": "application/json",
}


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

    role_id = await get_legacies_role_id(TESTER_RANK)
    if not role_id:
        return False, "Could not find the Tester role in the Legacies group."

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
                    return True, f"`{roblox_username}` has been ranked to **Tester** in Afternight Legacies."
                else:
                    error = await resp.json()
                    msg = error.get("errors", [{}])[0].get("message", "Unknown error")
                    return False, f"Roblox API error: {msg}"

    except Exception as e:
        return False, f"Exception: {str(e)}"


class TestingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def refresh_sticky_note(self, channel: discord.TextChannel):
        """Remove previous sticky note and post a fresh one at the bottom."""
        async for msg in channel.history(limit=30):
            if msg.author == self.bot.user and msg.embeds:
                if (msg.embeds[0].title or "") == STICKY_TITLE:
                    try:
                        await msg.delete()
                    except discord.Forbidden:
                        pass

        embed = discord.Embed(
            title=STICKY_TITLE,
            description=(
                "**Enter your Roblox username to be ranked.**\n\n"
                "• Only `[T] Tester.` members may submit usernames here.\n"
                "• Any side conversations or non-username messages will be deleted."
            ),
            color=discord.Color.green(),
        )
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        channel = self.bot.get_channel(TESTING_CHANNEL_ID)
        if isinstance(channel, discord.TextChannel):
            await self.refresh_sticky_note(channel)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.channel.id != TESTING_CHANNEL_ID:
            return

        roblox_username = message.content.strip()
        is_valid_username = (
            bool(USERNAME_RE.match(roblox_username))
            and not message.attachments
            and not message.stickers
        )

        # Delete side conversations / non-username messages
        if not is_valid_username:
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            await message.channel.send(
                f"{message.author.mention} Only Roblox usernames are allowed here. Side conversations are removed.",
                delete_after=8,
            )
            return

        async for msg in message.channel.history(limit=100):
            if msg.author == self.bot.user and msg.reference:
                ref = msg.reference.resolved
                if ref and ref.author == message.author and "Tester Rank Granted" in (
                    msg.embeds[0].title if msg.embeds else ""
                ):
                    await message.reply(
                        "⚠️ You have already been ranked to Tester!",
                        delete_after=10
                    )
                    await self.refresh_sticky_note(message.channel)
                    return

        tester_role = message.guild.get_role(GAME_TESTER_ROLE_ID)
        if tester_role not in message.author.roles:
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            await message.channel.send(
                f"{message.author.mention} Only Game Testers may submit their username here.",
                delete_after=10
            )
            await self.refresh_sticky_note(message.channel)
            return

        async with message.channel.typing():
            roblox_data = await fetch_roblox_user(roblox_username)
            if not roblox_data:
                await message.reply(
                    f"❌ Could not find Roblox user `{roblox_username}`. "
                    "Please double check your username and try again.",
                    delete_after=15
                )
                await self.refresh_sticky_note(message.channel)
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

        await self.refresh_sticky_note(message.channel)

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
                "❌ Only Developers, Co-Owners, or Owners may use `/testingsession`.",
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
