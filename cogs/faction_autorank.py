"""
cogs/faction_autorank.py — Auto-rank faction leaders, members, and overseers
(as basic members) in Roblox group 127271910, accept join requests, delete
side conversations, and keep a sticky prompt at the bottom.
"""
import os
import re
import datetime
import aiohttp
import discord
from discord.ext import commands
from constants import (
    FACTION_AUTORANK_CHANNEL_ID,
    FACTION_AUTORANK_ROLE_MAP,
    FACTION_COLORS,
    FACTION_LEADER_MAIN_ROLE,
    FACTION_LEADERS,
    FACTIONS_GROUP_ID,
)
from utils.roblox import fetch_roblox_user
from utils.roblox_group import get_xcsrf_token

COOKIE = os.getenv("ROBLOX_SECURITY_COOKIE")
HEADERS = {
    "Cookie": f".ROBLOSECURITY={COOKIE}",
    "Content-Type": "application/json",
}
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
STICKY_TITLE = "📌 Faction Group Auto-Rank"


def get_target_faction_and_rank(member: discord.Member) -> tuple[str, int, str] | None:
    """
    Determine target faction name, rank number, and rank label for a Discord member.
    Leaders get Leader rank; Overseers always get Basic Member rank (never Leader).
    """
    role_ids = {r.id for r in member.roles}

    # Check specific faction leader roles first
    for role_id in FACTION_LEADERS:
        if role_id in role_ids and role_id in FACTION_AUTORANK_ROLE_MAP:
            return FACTION_AUTORANK_ROLE_MAP[role_id]

    # Check member and overseer roles (overseers map to Basic Member)
    for role_id, info in FACTION_AUTORANK_ROLE_MAP.items():
        if role_id in role_ids:
            return info

    # Fallback if user holds [FL] Faction Leader without a faction-specific leader role
    if FACTION_LEADER_MAIN_ROLE in role_ids:
        for role_id, info in FACTION_AUTORANK_ROLE_MAP.items():
            if info[2] == "Leader" and role_id in role_ids:
                return info

    return None


async def get_group_role_id_by_rank(group_id: int, rank_number: int) -> int | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://groups.roblox.com/v1/groups/{group_id}/roles",
            headers=HEADERS,
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            for role in data.get("roles", []):
                if role.get("rank") == rank_number:
                    return role.get("id")
    return None


async def accept_join_request_if_pending(group_id: int, user_id: int, xcsrf: str) -> tuple[bool, str]:
    """
    Accept a pending join request for user_id in group_id.
    Returns (True, status_msg) if accepted or already in group, or (False, reason) if no request exists.
    """
    req_headers = {**HEADERS, "x-csrf-token": xcsrf}
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://groups.roblox.com/v1/groups/{group_id}/users/{user_id}/role",
            headers=req_headers,
        ) as role_resp:
            if role_resp.status == 200:
                role_json = await role_resp.json()
                if role_json.get("role", {}).get("rank", 0) > 0:
                    return True, "Already in group"

        async with session.post(
            f"https://groups.roblox.com/v1/groups/{group_id}/join-requests/users/{user_id}",
            headers=req_headers,
        ) as resp:
            if resp.status in (200, 204):
                return True, "Join request accepted"
            try:
                err_data = await resp.json()
                msg = err_data.get("errors", [{}])[0].get("message", "Unknown Roblox API error")
            except Exception:
                msg = f"HTTP {resp.status}"
            return False, (
                f"You must **request to join** the Factions group "
                f"(https://www.roblox.com/communities/{group_id}) before being accepted and ranked. "
                f"({msg})"
            )


async def rank_faction_member_in_group(
    roblox_username: str, target_rank: int, rank_label: str
) -> tuple[bool, str]:
    if not COOKIE:
        return False, "ROBLOX_SECURITY_COOKIE is not configured."

    roblox_user = await fetch_roblox_user(roblox_username)
    if not roblox_user or not roblox_user.get("id"):
        return False, f"Could not find Roblox user `{roblox_username}`."

    user_id = int(roblox_user["id"])
    role_id = await get_group_role_id_by_rank(FACTIONS_GROUP_ID, target_rank)
    if not role_id:
        return False, f"Could not find group role for rank `{target_rank}` in community `{FACTIONS_GROUP_ID}`."

    try:
        xcsrf = await get_xcsrf_token()
        accepted, join_msg = await accept_join_request_if_pending(FACTIONS_GROUP_ID, user_id, xcsrf)
        if not accepted:
            return False, join_msg

        patch_headers = {**HEADERS, "x-csrf-token": xcsrf}
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f"https://groups.roblox.com/v1/groups/{FACTIONS_GROUP_ID}/users/{user_id}",
                headers=patch_headers,
                json={"roleId": role_id},
            ) as resp:
                if resp.status == 200:
                    return True, f"{join_msg} & ranked to {rank_label} (rank `{target_rank}`)."
                try:
                    err_data = await resp.json()
                    msg = err_data.get("errors", [{}])[0].get("message", "Unknown error")
                except Exception:
                    msg = f"HTTP {resp.status}"
                return False, f"Failed to assign rank: {msg}"
    except Exception as exc:
        return False, f"Error communicating with Roblox: {exc}"


class FactionAutoRankCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def refresh_sticky_note(self, channel: discord.TextChannel):
        """Delete previous sticky note in channel and post a fresh one at the bottom."""
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
                "• You **must request to join** the Factions group "
                f"([Afternight Factions](https://www.roblox.com/communities/{FACTIONS_GROUP_ID})) "
                "first so your request can be accepted.\n"
                "• Leaders receive their **Leader** rank; Overseers are ranked as **basic faction members**.\n"
                "• Any side conversations or non-username messages will be deleted."
            ),
            color=discord.Color.blurple(),
        )
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        if not FACTION_AUTORANK_CHANNEL_ID:
            return
        channel = self.bot.get_channel(FACTION_AUTORANK_CHANNEL_ID)
        if isinstance(channel, discord.TextChannel):
            await self.refresh_sticky_note(channel)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if not FACTION_AUTORANK_CHANNEL_ID or message.channel.id != FACTION_AUTORANK_CHANNEL_ID:
            return

        content = message.content.strip()
        is_valid_username = bool(USERNAME_RE.match(content)) and not message.attachments and not message.stickers

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

        target_info = get_target_faction_and_rank(message.author)
        if not target_info:
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            await message.channel.send(
                f"{message.author.mention} You do not have an eligible Faction role.",
                delete_after=10,
            )
            await self.refresh_sticky_note(message.channel)
            return

        faction_name, target_rank, rank_label = target_info
        faction_color = FACTION_COLORS.get(faction_name, 0x5865F2)

        async with message.channel.typing():
            roblox_data = await fetch_roblox_user(content)
            if not roblox_data:
                await message.reply(
                    f"❌ Could not find Roblox user `{content}`.",
                    delete_after=12,
                )
                await self.refresh_sticky_note(message.channel)
                return

            success, detail_msg = await rank_faction_member_in_group(
                content, target_rank, rank_label
            )

        if success:
            embed = discord.Embed(
                title="⚔️ Faction Rank Granted",
                color=faction_color,
                timestamp=datetime.datetime.utcnow(),
            )
            if roblox_data.get("avatar_url"):
                embed.set_thumbnail(url=roblox_data["avatar_url"])
            embed.add_field(name="Discord", value=message.author.mention, inline=True)
            embed.add_field(name="Roblox", value=f"`{content}`", inline=True)
            embed.add_field(name="Faction", value=f"{faction_name} ({rank_label})", inline=False)
            embed.add_field(name="Status", value=detail_msg, inline=False)
            await message.reply(embed=embed)
        else:
            await message.reply(f"❌ {detail_msg}", delete_after=15)

        await self.refresh_sticky_note(message.channel)


async def setup(bot: commands.Bot):
    await bot.add_cog(FactionAutoRankCog(bot))
