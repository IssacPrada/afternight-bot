"""
cogs/serverids.py — /listids exports every channel and role ID in the server
"""
import io
import discord
from discord import app_commands
from discord.ext import commands


class ServerIDsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="listids",
        description="Export all channel and role IDs in this server."
    )
    @app_commands.default_permissions(administrator=True)
    async def listids(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not interaction.user.guild_permissions.administrator:
            return await interaction.followup.send(
                "❌ Only server administrators may use this.", ephemeral=True
            )

        guild = interaction.guild
        lines = [f"SERVER: {guild.name} — {guild.id}", ""]

        lines.append("=== TEXT CHANNELS ===")
        for ch in guild.text_channels:
            cat = ch.category.name if ch.category else "No category"
            lines.append(f"[{cat}] #{ch.name} — {ch.id}")

        lines += ["", "=== VOICE CHANNELS ==="]
        for ch in guild.voice_channels:
            cat = ch.category.name if ch.category else "No category"
            lines.append(f"[{cat}] {ch.name} — {ch.id}")

        lines += ["", "=== ROLES ==="]
        for role in reversed(guild.roles):
            if role.is_default():
                continue
            lines.append(f"{role.name} — {role.id}")

        data = "\n".join(lines).encode("utf-8")
        await interaction.followup.send(
            "✅ Here are all the IDs in this server.",
            file=discord.File(io.BytesIO(data), filename="server_ids.txt"),
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(ServerIDsCog(bot))
