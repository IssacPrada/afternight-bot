"""
cogs/activity.py — /getplayertime and /getfactiontime slash commands
"""
import discord
from discord import app_commands
from discord.ext import commands
from constants import can_view_activity
from utils.roblox import fetch_roblox_user


def format_playtime(seconds: int) -> str:
    seconds = int(seconds or 0)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def _norm_faction(name: str) -> str:
    """Lowercase, no spaces, and tolerate the 'Sepharine' misspelling."""
    return name.lower().replace(" ", "").replace("sepharine", "seraphine")


async def get_player_playtime(db, roblox_name: str, roblox_id: int) -> int | None:
    """Total seconds from the sessions table. Matches the stored name or ID, case-insensitive."""
    try:
        async with db.pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT COALESCE(SUM(duration_s), 0) FROM sessions "
                "WHERE LOWER(roblox_user) = ANY($1::text[])",
                [roblox_name.lower(), str(roblox_id)],
            )
        return int(total or 0)
    except Exception:
        return None


async def get_faction_playtime(db, faction: str) -> int | None:
    """Total seconds across every session tagged with this faction."""
    try:
        async with db.pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT COALESCE(SUM(duration_s), 0) FROM sessions "
                "WHERE LOWER(REPLACE(faction, ' ', '')) = ANY($1::text[])",
                [_norm_faction(faction), _norm_faction(faction).replace("seraphine", "sepharine")],
            )
        return int(total or 0)
    except Exception:
        return None


class ActivityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── /getplayertime ────────────────────────────────────────────────────────

    @app_commands.command(
        name="getplayertime",
        description="Get total playtime in Afternight for a Roblox user."
    )
    @app_commands.describe(username="Roblox username")
    async def getplayertime(self, interaction: discord.Interaction, username: str):
        await interaction.response.defer(ephemeral=True)

        if not can_view_activity(interaction.user):
            return await interaction.followup.send(
                "❌ Only Owner, Co-Owner, Community Manager, Faction Leaders, or Faction Overseers may use this command.",
                ephemeral=True
            )

        roblox_data = await fetch_roblox_user(username)
        if not roblox_data:
            return await interaction.followup.send(
                f"❌ Could not find Roblox user `{username}`.",
                ephemeral=True
            )

        playtime = await get_player_playtime(self.bot.db, roblox_data["name"], roblox_data["id"])
        if playtime is None:
            return await interaction.followup.send(
                f"⚠️ Could not fetch playtime for `{roblox_data['name']}`.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="⏱️ Player Playtime",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=roblox_data.get("avatar_url") or "")
        embed.add_field(name="Roblox User", value=f"`{roblox_data['name']}`", inline=True)
        embed.add_field(name="Total Playtime", value=f"**{format_playtime(playtime)}**", inline=True)
        embed.set_footer(text="Afternight Activity")

        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /getfactiontime ───────────────────────────────────────────────────────

    @app_commands.command(
        name="getfactiontime",
        description="Get total playtime for a faction."
    )
    @app_commands.describe(faction="Name of the faction")
    @app_commands.choices(faction=[
        app_commands.Choice(name="Sanguis Order", value="Sanguis Order"),
        app_commands.Choice(name="Eldritch Thorn", value="Eldritch Thorn"),
        app_commands.Choice(name="Silver Venom", value="Silver Venom"),
        app_commands.Choice(name="Seraphine Coven", value="Seraphine Coven"),
    ])
    async def getfactiontime(self, interaction: discord.Interaction, faction: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)

        if not can_view_activity(interaction.user):
            return await interaction.followup.send(
                "❌ Only Owner, Co-Owner, Community Manager, Faction Leaders, or Faction Overseers may use this command.",
                ephemeral=True
            )

        playtime = await get_faction_playtime(self.bot.db, faction.value)
        if playtime is None:
            return await interaction.followup.send(
                f"⚠️ Could not fetch playtime for **{faction.name}**.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="🏰 Faction Playtime",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Faction", value=f"**{faction.name}**", inline=True)
        embed.add_field(name="Total Playtime", value=f"**{format_playtime(playtime)}**", inline=True)
        embed.set_footer(text="Afternight Faction Activity")

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ActivityCog(bot))
