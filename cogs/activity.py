"""
cogs/activity.py — /getplayertime, /getfactiontime slash commands
"""
import discord
from discord import app_commands
from discord.ext import commands
from constants import (
    FACTION_COLORS, STRIKE_STATUS,
    can_use_faction_commands
)
from utils.roblox import (
    fetch_roblox_user, fetch_faction_members,
    fetch_player_rank_in_group, RANK_TO_FACTION
)
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


def to_str(dt) -> str:
    """Convert datetime object or string to string."""
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def days_since(dt) -> int:
    """Return how many days since a datetime object or string."""
    try:
        if isinstance(dt, str):
            dt = datetime.datetime.fromisoformat(dt)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return (datetime.datetime.utcnow() - dt).days
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
        discord_user="Their Discord account (for strike info, optional)"
    )
    async def getplayertime(self, interaction: discord.Interaction,
                             roblox_username: str,
                             discord_user: discord.Member = None):
        await interaction.response.defer()

        actor = interaction.user
        allowed, faction_restriction = can_use_faction_commands(actor)

        if not allowed:
            return await interaction.followup.send(
                "❌ Only faction leaders or faction council may use this command.",
                ephemeral=True
            )

        # ── Fetch Roblox profile ──────────────────────────────────────────────
        roblox_data = await fetch_roblox_user(roblox_username)
        if not roblox_data:
            return await interaction.followup.send(
                f"❌ Could not find Roblox user: `{roblox_username}`",
                ephemeral=True
            )

        # ── Check faction restriction ─────────────────────────────────────────
        rank = await fetch_player_rank_in_group(roblox_data["id"])
        player_faction = RANK_TO_FACTION.get(rank, "Unknown")

        if faction_restriction and player_faction != faction_restriction:
            return await interaction.followup.send(
                f"❌ `{roblox_username}` is not in **{faction_restriction}**.",
                ephemeral=True
            )

        faction_color = FACTION_COLORS.get(player_faction, 0x5865F2)

        # ── Fetch sessions ────────────────────────────────────────────────────
        sessions = await self.bot.db.get_player_sessions(roblox_username, days=7)
        total_seconds = sum(s.get("duration_s") or 0 for s in sessions)
        last_session = sessions[0] if sessions else None

        # ── Work out inactivity ───────────────────────────────────────────────
        if last_session:
            inactive_for = days_since(last_session.get("joined_at"))
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

        if roblox_data.get("avatar_url"):
            embed.set_thumbnail(url=roblox_data["avatar_url"])

        embed.add_field(
            name="🔗 Roblox Profile",
            value=f"[{roblox_data.get('displayName', roblox_username)}]"
                  f"(https://www.roblox.com/users/{roblox_data['id']}/profile)",
            inline=False
        )
        embed.add_field(name="🏰 Faction", value=player_faction, inline=True)
        embed.add_field(name="⏱ Total Time This Week", value=fmt(total_seconds), inline=True)
        embed.add_field(name="🎮 Sessions This Week", value=str(len(sessions)), inline=True)

        # ── Last session ──────────────────────────────────────────────────────
        if last_session:
            joined_dt = last_session.get("joined_at")
            left_dt   = last_session.get("left_at")
            joined    = to_str(joined_dt)[:16].replace("T", " ") if joined_dt else "N/A"
            left_str  = to_str(left_dt)[:16].replace("T", " ") if left_dt else "Still in session"
            duration  = fmt(last_session.get("duration_s") or 0)
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
                value=f"No activity for **{inactive_for} day(s)** "
                      f"— threshold is {INACTIVE_DAYS} days.",
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

        embed.set_footer(text="Afternight Activity Tracker")
        await interaction.followup.send(embed=embed)

    # ── /getfactiontime ───────────────────────────────────────────────────────

    @app_commands.command(
        name="getfactiontime",
        description="View full activity overview for a faction."
    )
    @app_commands.describe(
        faction="Faction to view (council can pick any, leaders see their own)",
        days="How many days back to look (default 7)"
    )
    @app_commands.choices(faction=[
        app_commands.Choice(name="Sanguis Order",   value="Sanguis Order"),
        app_commands.Choice(name="Eldritch Thorn",  value="Eldritch Thorn"),
        app_commands.Choice(name="Silver Venom",    value="Silver Venom"),
        app_commands.Choice(name="Sepharine Coven", value="Sepharine Coven"),
    ])
    async def getfactiontime(self, interaction: discord.Interaction,
                              faction: str = None, days: int = 7):
        await interaction.response.defer()

        actor = interaction.user
        allowed, faction_restriction = can_use_faction_commands(actor)

        if not allowed:
            return await interaction.followup.send(
                "❌ Only faction leaders or faction council may use this command.",
                ephemeral=True
            )

        # ── Enforce faction restriction ───────────────────────────────────────
        if faction_restriction:
            faction = faction_restriction
        elif not faction:
            return await interaction.followup.send(
                "❌ Please select a faction.", ephemeral=True
            )

        faction_color = FACTION_COLORS.get(faction, 0x5865F2)

        # ── Loading message ───────────────────────────────────────────────────
        loading = discord.Embed(
            title=f"⏳ Loading {faction} activity...",
            description="Fetching live member list from Roblox group...",
            color=faction_color
        )
        msg = await interaction.followup.send(embed=loading)

        # ── Pull live member list from Roblox group ───────────────────────────
        group_members = await fetch_faction_members(faction)

        if not group_members:
            err = discord.Embed(
                title="❌ No Members Found",
                description=f"Could not fetch members for **{faction}** from the Roblox group.",
                color=discord.Color.red()
            )
            await msg.edit(embed=err)
            return

        # ── Pull playtime data for each member ────────────────────────────────
        member_data = []
        for member in group_members:
            username = member["username"]
            sessions = await self.bot.db.get_player_sessions(username, days=days)
            total_s  = sum(s.get("duration_s") or 0 for s in sessions)
            last_seen = sessions[0].get("joined_at") if sessions else None
            inactive_days_count = days_since(last_seen) if last_seen else 999
            is_inactive = inactive_days_count >= INACTIVE_DAYS

            member_data.append({
                "username":          username,
                "displayName":       member["displayName"],
                "total_s":           total_s,
                "sessions":          len(sessions),
                "last_seen":         last_seen,
                "inactive_days":     inactive_days_count,
                "is_inactive":       is_inactive,
            })

        # ── Sort by most active ───────────────────────────────────────────────
        member_data.sort(key=lambda x: x["total_s"], reverse=True)

        total_faction_seconds = sum(m["total_s"] for m in member_data)
        inactive_members      = [m for m in member_data if m["is_inactive"]]
        active_members        = [m for m in member_data if not m["is_inactive"]]

        # ── Build embed ───────────────────────────────────────────────────────
        embed = discord.Embed(
            title=f"📊 Faction Activity — {faction}",
            description=f"Live data from Roblox group · Past **{days} days**",
            color=faction_color,
            timestamp=datetime.datetime.utcnow()
        )

        embed.add_field(name="👥 Total Members",     value=str(len(group_members)), inline=True)
        embed.add_field(name="⏱ Total Faction Time", value=fmt(total_faction_seconds), inline=True)
        embed.add_field(name="⚠️ Inactive",          value=f"{len(inactive_members)} member(s)", inline=True)

        # ── Most active ranked ────────────────────────────────────────────────
        if active_members:
            leaderboard = ""
            for i, m in enumerate(active_members, 1):
                last = to_str(m["last_seen"])[:10] if m["last_seen"] else "Never"
                leaderboard += (
                    f"`{i:>2}.` **{m['username']}** "
                    f"— ⏱ {fmt(m['total_s'])} "
                    f"· 🎮 {m['sessions']} sessions "
                    f"· 📅 {last}\n"
                )
            if len(leaderboard) <= 1024:
                embed.add_field(name="🏆 Most Active", value=leaderboard, inline=False)
            else:
                chunks = [leaderboard[i:i+1000] for i in range(0, len(leaderboard), 1000)]
                for idx, chunk in enumerate(chunks):
                    embed.add_field(name=f"🏆 Most Active ({idx + 1})", value=chunk, inline=False)
        else:
            embed.add_field(name="🏆 Most Active", value="No active members this period.", inline=False)

        # ── Inactive members ──────────────────────────────────────────────────
        if inactive_members:
            inactive_text = ""
            for m in inactive_members:
                last     = to_str(m["last_seen"])[:10] if m["last_seen"] else "Never played"
                days_ago = m["inactive_days"]
                days_str = f"{days_ago}d ago" if days_ago != 999 else "Never"
                inactive_text += f"• **{m['username']}** — last seen {last} ({days_str})\n"

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
                        name=f"⚠️ Inactive ({INACTIVE_DAYS}+ days) ({idx + 1})",
                        value=chunk,
                        inline=False
                    )

        embed.set_footer(text=f"Afternight Activity Tracker · {len(group_members)} members fetched live")
        await msg.edit(embed=embed)


async def setup(bot):
    await bot.add_cog(ActivityCog(bot))
