"""
cogs/automod.py — Auto moderation for slurs
"""
import discord
from discord import app_commands
from discord.ext import commands
import datetime
import json
import os

# ── Config ────────────────────────────────────────────────────────────────────
AUTOMOD_LOG_CHANNEL = 1537657791748247673
SLURS_FILE          = "data/slurs.json"

IMMUNE_ROLES: set[int] = {
    1387649282139754587,  # [C] Creators
}

ALLOWED_TO_MANAGE: set[int] = {
    1458302857764802683,  # Community Manager
    1458302854887510210,  # Overseer of Staff
    1387649282139754587,  # [C] Creators
}

APPEAL_SERVER = "https://discord.gg/dQAbatSEcw"


def load_slurs() -> list[str]:
    try:
        if not os.path.exists(SLURS_FILE):
            return []
        with open(SLURS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_slurs(slurs: list[str]):
    try:
        os.makedirs(os.path.dirname(SLURS_FILE), exist_ok=True)
        with open(SLURS_FILE, "w") as f:
            json.dump(slurs, f)
    except Exception:
        pass


def contains_slur(content: str, slurs: list[str]) -> bool:
    content_lower = content.lower()
    for slur in slurs:
        if slur.lower() in content_lower:
            return True
    return False


class AutoModCog(commands.Cog):
    def __init__(self, bot):
        self.bot   = bot
        self.slurs = load_slurs()

    # ── Message listener ──────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return

        member_role_ids = {r.id for r in message.author.roles}
        if member_role_ids & IMMUNE_ROLES:
            return

        if not self.slurs:
            return

        if not contains_slur(message.content, self.slurs):
            return

        # ── Delete message ────────────────────────────────────────────────────
        try:
            await message.delete()
        except discord.Forbidden:
            pass

        # ── Auto warn ─────────────────────────────────────────────────────────
        guild = message.guild
        try:
            await self.bot.db.add_warn(
                str(message.author.id),
                str(guild.id),
                "Slur usage",
                f"Auto-detected slur in #{message.channel.name}",
                str(self.bot.user.id)
            )
            warns      = await self.bot.db.get_warns(str(message.author.id), str(guild.id))
            warn_count = len(warns)
        except Exception:
            warn_count = 1

        # ── Warn message in channel ───────────────────────────────────────────
        try:
            await message.channel.send(
                f"{message.author.mention} you have been warned for slur usage.",
                delete_after=10
            )
        except discord.Forbidden:
            pass

        # ── DM the user ───────────────────────────────────────────────────────
        try:
            dm = discord.Embed(
                title="⚠️ You Have Been Warned",
                color=discord.Color.yellow(),
                timestamp=discord.utils.utcnow()
            )
            dm.description = (
                f"You have been warned in **Afternight Legacies** for **slur usage**.\n\n"
                f"**Warning Count:** {warn_count}\n\n"
                f"If you believe this was a mistake, open a ticket:\n{APPEAL_SERVER}"
            )
            dm.set_footer(text="Afternight Auto Moderation")
            await message.author.send(embed=dm)
        except discord.Forbidden:
            pass

        # ── Log ───────────────────────────────────────────────────────────────
        log_channel = guild.get_channel(AUTOMOD_LOG_CHANNEL)
        if log_channel:
            log_embed = discord.Embed(
                title="🤖 AutoMod — Slur Detected",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            log_embed.set_thumbnail(url=message.author.display_avatar.url)
            log_embed.add_field(
                name="User",
                value=f"{message.author.mention} (`{message.author.id}`)",
                inline=True
            )
            log_embed.add_field(name="Channel",       value=message.channel.mention, inline=True)
            log_embed.add_field(name="Warning Count", value=f"{warn_count}",         inline=True)
            log_embed.add_field(name="Action",        value="Message deleted + Auto warned", inline=False)
            log_embed.set_footer(text=f"User ID: {message.author.id}")
            await log_channel.send(embed=log_embed)

    # ── /addslur ──────────────────────────────────────────────────────────────

    @app_commands.command(name="addslur", description="Add a word to the automod slur list.")
    @app_commands.describe(word="The word to add")
    async def addslur(self, interaction: discord.Interaction, word: str):
        await interaction.response.defer(ephemeral=True)

        if not {r.id for r in interaction.user.roles} & ALLOWED_TO_MANAGE:
            return await interaction.followup.send(
                "❌ Only Community Manager, Overseer of Staff, or Creators may manage the slur list.",
                ephemeral=True
            )

        word = word.lower().strip()
        if word in self.slurs:
            return await interaction.followup.send(
                f"❌ `{word}` is already in the slur list.", ephemeral=True
            )

        self.slurs.append(word)
        save_slurs(self.slurs)

        await interaction.followup.send(
            f"✅ Added `{word}` to the automod slur list. Total: **{len(self.slurs)}** word(s).",
            ephemeral=True
        )

    # ── /removeslur ───────────────────────────────────────────────────────────

    @app_commands.command(name="removeslur", description="Remove a word from the automod slur list.")
    @app_commands.describe(word="The word to remove")
    async def removeslur(self, interaction: discord.Interaction, word: str):
        await interaction.response.defer(ephemeral=True)

        if not {r.id for r in interaction.user.roles} & ALLOWED_TO_MANAGE:
            return await interaction.followup.send(
                "❌ Only Community Manager, Overseer of Staff, or Creators may manage the slur list.",
                ephemeral=True
            )

        word = word.lower().strip()
        if word not in self.slurs:
            return await interaction.followup.send(
                f"❌ `{word}` is not in the slur list.", ephemeral=True
            )

        self.slurs.remove(word)
        save_slurs(self.slurs)

        await interaction.followup.send(
            f"✅ Removed `{word}` from the automod slur list. Total: **{len(self.slurs)}** word(s).",
            ephemeral=True
        )

    # ── /viewslurs ────────────────────────────────────────────────────────────

    @app_commands.command(name="viewslurs", description="View all words in the automod slur list.")
    async def viewslurs(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not {r.id for r in interaction.user.roles} & ALLOWED_TO_MANAGE:
            return await interaction.followup.send(
                "❌ Only Community Manager, Overseer of Staff, or Creators may view the slur list.",
                ephemeral=True
            )

        # ── Reload from file in case another instance updated it ──────────────
        self.slurs = load_slurs()

        if not self.slurs:
            return await interaction.followup.send(
                "The slur list is currently empty.", ephemeral=True
            )

        embed = discord.Embed(
            title="🤖 AutoMod Slur List",
            description="\n".join(f"`{s}`" for s in self.slurs),
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"Total: {len(self.slurs)} word(s)")
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AutoModCog(bot))
