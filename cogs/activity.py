"""
cogs/activity.py — /getplayertime, /getfactiontime slash commands
"""
import discord
from discord import app_commands
from discord.ext import commands
from constants import (
    FACTION_COLORS, STRIKE_STATUS,
    get_leader_faction
)
from utils.roblox import fetch_roblox_user
import datetime

INACTIVE_DAYS = 5


def fmt(seconds: int) -> str:
    if not seconds:
        return "0m"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m {s}s"


def days_since(date_str: str) -> int:
    """Return how many days since a datetime string."""
    try:
        last = datetime.datetime.fromisoformat(date_str)
        return (datetime.datetime.utcnow() - last).days
    except Exception:
        return 999


class ActivityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── /getplayertime ────────────────────────────────────────────────────────

    @app_commands.command(
        name="getplayertime",
        description="View a faction member's Roblox activity."
    )
    @app_commands.describe(
        roblox_username="Their exact Roblox username",
        discord_user="Their Discord account (for strike info)"
    )
    async def getplayertime(self, interaction: discord.Interaction,
                             roblox_username: str,
                             discord_user: discord.Member = None):
        await interaction.response.defer()

        actor = interaction.user
        actor_faction = get_leader_faction(actor)

        if not actor_faction:
            return await interaction.followup.send(
                "❌ Only faction leaders may use this command.", ephemeral=True
            )

        faction_color = FACTION_COLORS.get(actor_faction, 0x5865F2)

        # ── Fetch Roblox profile ──────────────────────────────────────────────
        roblox_data = await fetch_roblox_user(roblox_username)

        # ── Fetch sessions (last 7 days) ──────────────────────────────────────
        sessions = await self.bot.db.get_player_sessions(roblox_username, days=7)
        total_seconds = sum(s.get("duration_s") or 0 for s in sessions)
        last_session = sessions[0] if sessions else None

        # ── Work out inactivity ───────────────────────────────────────────────
        if last_session:
            inactive_for = days_since(last_session.get("joined_at", ""))
            is_inactive = inactive_for >= INACTIVE_DAYS
        else:
            inactive_for = INACTIVE_DAYS
            is_inactive = True

        # ── Build embed ───────────────────────────────────────────────────────
        embed = discord.Embed(
            title=f"🕒 Activity — {roblox_username}",
            color=discord.Color.red() if is_inactive else faction_color,
            timestamp=datetime.datetime.utcnow()
        )

        if roblox_data:
            embed.url = f"https://www.roblox.com/users/{roblox_data['id']}/profile"
            if roblox_data.get("avatar_url"):
                embed.set_thumbnail(url=roblox_data["avatar_url"])
            embed.add_field(
                name="🔗 Roblox Profile",
                value=f"[{roblox_data.get('displayName', roblox_username)}]"
                      f"(https://www.roblox.com/users/{roblox_data['id']}/profile)",
                inline=False
            )

        embed.add_field(name="🏰 Faction", value=actor_faction, inline=True)
        embed.add_field(name="⏱ Total Time This Week", value=fmt(total_seconds), inline=True)
        embed.add_field(name="🎮 Sessions This Week", value=str(len(sessions)), inline=True)

        # ── Last seen ─────────────────────────────────────────────────────────
        if last_session:
            joined = last_session.get("joined_at", "N/A")[:16].replace("T", " ")
            left = last_session.get("left_at")
            left_str = left[:16].replace("T", " ") if left else "Still in session"
            duration = fmt(last_session.get("duration_s") or 0)
            embed.add_field(
                name="📌 Last Session",
                value=(
                    f"**Joined:** {joined}\n"
                    f"**Left:** {left_str}\n"
                    f"**Duration:** {duration}"
                ),
                inline=False
            )
        else:
            embed.add_field(
                name="📌 Last Session",
                value="No sessions recorded this week.",
                inline=False
            )

        # ── Inactivity flag ───────────────────────────────────────────────────
        if is_inactive:
            embed.add_field(
                name="⚠️ INACTIVE",
                value=f"No activity for **{inactive_for} day(s)** — threshold is {INACTIVE_DAYS} days.",
                inline=False
            )

        # ── Strikes ───────────────────────────────────────────────────────────
        if discord_user:
            strikes = await self.bot.db.get_strikes(
                str(discord_user.id), str(interaction.guild.id)
            )
            count = len(strikes)
            status_text, _ = STRIKE_STATUS.get(min(count, 3), STRIKE_STATUS[3])
            embed.add_field(
                name="⚡ Strikes",
                value=f"{count}/3 — {status_text}",
                inline=True
            )

        embed.set_footer(text=f"Afternight Activity Tracker · {actor_faction}")
        await interaction.followup.send(embed=embed)

    # ── /getfactiontime ───────────────────────────────────────────────────────

    @app_commands.command(
        name="getfactiontime",
        description="View full activity overview for your faction."
    )
    @app_commands.describe(days="How many days back to look (default 7)")
    async def getfactiontime(self, interaction: discord.Interaction, days: int = 7):
        await interaction.response.defer()

        actor = interaction.user
        actor_faction = get_leader_faction(actor)

        if not actor_faction:
            return await interaction.followup.send(
                "❌ Only faction leaders may use this command.", ephemeral=True
            )

        faction_color = FACTION_COLORS.get(actor_faction, 0x5865F2)
        sessions = await self.bot.db.get_faction_sessions(actor_faction, days)

        embed = discord.Embed(
            title=f"📊 Faction Activity — {actor_faction}",
            description=f"Activity overview for the past **{days} days**.",
            color=faction_color,
            timestamp=datetime.datetime.utcnow()
        )

        if not sessions:
            embed.add_field(
                name="No Data",
                value="No sessions recorded for this period.",
                inline=False
            )
            await interaction.followup.send(embed=embed)
            return

        # ── Summary stats ─────────────────────────────────────────────────────
        total_faction_seconds = sum(s.get("total_s") or 0 for s in sessions)
        inactive_members = [
            s for s in sessions
            if days_since(s.get("last_seen") or "") >= INACTIVE_DAYS
        ]

        embed.add_field(name="👥 Active Members", value=str(len(sessions)), inline=True)
        embed.add_field(name="⏱ Total Faction Time", value=fmt(total_faction_seconds), inline=True)
        embed.add_field(
            name="⚠️ Inactive Members",
            value=str(len(inactive_members)),
            inline=True
        )

        # ── Most active ranked ────────────────────────────────────────────────
        ranked = sorted(sessions, key=lambda s: s.get("total_s") or 0, reverse=True)
        leaderboard = ""
        for i, member in enumerate(ranked, 1):
            name = member["roblox_user"]
            total = fmt(member.get("total_s") or 0)
            count = member.get("session_count", 0)
            last = (member.get("last_seen") or "N/A")[:10]
            inactive = days_since(member.get("last_seen") or "") >= INACTIVE_DAYS

            # Fetch strikes for this member if we can match discord user
            flag = " ⚠️" if inactive else ""
            leaderboard += (
                f"`{i:>2}.` **{name}**{flag}\n"
                f"      ⏱ {total} · 🎮 {count} sessions · 📅 Last: {last}\n"
            )

        # Chunk if too long
        if len(leaderboard) <= 1024:
            embed.add_field(
                name="🏆 Most Active (Ranked)",
                value=leaderboard,
                inline=False
            )
        else:
            chunks = [leaderboard[i:i+1000] for i in range(0, len(leaderboard), 1000)]
            for idx, chunk in enumerate(chunks):
                embed.add_field(
                    name=f"🏆 Most Active (Ranked) {idx + 1}",
                    value=chunk,
                    inline=False
                )

        # ── Inactive members list ─────────────────────────────────────────────
        if inactive_members:
            inactive_text = ""
            for member in inactive_members:
                name = member["roblox_user"]
                last = (member.get("last_seen") or "Never")[:10]
                days_ago = days_since(member.get("last_seen") or "")
                inactive_text += f"• **{name}** — last seen {last} ({days_ago}d ago)\n"

            if len(inactive_text) <= 1024:
                embed.add_field(
                    name=f"⚠️ Inactive ({INACTIVE_DAYS}+ days)",
                    value=inactive_text,
                    inline=False
                )
            else:
                chunks = [inactive_text[i:i+1000] for i in range(0, len(inactive_text), 1000)]
                for idx, chunk in enumerate(chunks):
                    embed.add_field(
                        name=f"⚠️ Inactive ({INACTIVE_DAYS}+ days) {idx + 1}",
                        value=chunk,
                        inline=False
                    )

        embed.set_footer(text=f"Afternight Activity Tracker · {actor_faction}")
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ActivityCog(bot))
