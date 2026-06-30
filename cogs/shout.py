"""
cogs/shout.py — /shout slash command
"""
import discord
from discord import app_commands
from discord.ext import commands
from constants import has_fire_permission
import datetime


class ShoutCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="shout",
        description="Send an announcement to any channel."
    )
    @app_commands.describe(
        channel="The channel to send the shout to",
        message="The message content",
        ping="Optional role to ping",
        use_embed="Send as a fancy embed instead of a plain message",
        embed_color="Embed color as hex code e.g. ff0000 for red (only used with embed)",
        image_url="Image URL to attach to the embed (only used with embed)"
    )
    async def shout(self, interaction: discord.Interaction,
                    channel: discord.TextChannel,
                    message: str,
                    ping: discord.Role = None,
                    use_embed: bool = False,
                    embed_color: str = None,
                    image_url: str = None):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user

        if not has_fire_permission(actor):
            return await interaction.followup.send(
                "❌ Only Overseer of Staff, Community Manager, or Creators may use `/shout`.",
                ephemeral=True
            )

        ping_str = ping.mention if ping else ""

        if use_embed:
            # ── Parse color ───────────────────────────────────────────────────
            color = discord.Color.blurple()
            if embed_color:
                try:
                    color = discord.Color(int(embed_color.strip("#"), 16))
                except ValueError:
                    return await interaction.followup.send(
                        "❌ Invalid color. Use a hex code like `ff0000` or `#ff0000`.",
                        ephemeral=True
                    )

            embed = discord.Embed(
                description=message,
                color=color,
                timestamp=datetime.datetime.utcnow()
            )
            embed.set_footer(text=f"Afternight — {actor.display_name}")

            if image_url:
                embed.set_image(url=image_url)

            await channel.send(content=ping_str if ping_str else None, embed=embed)

        else:
            # ── Plain message ─────────────────────────────────────────────────
            content = f"{ping_str}\n{message}" if ping_str else message
            await channel.send(content=content)

        # ── Confirmation ──────────────────────────────────────────────────────
        await interaction.followup.send(
            f"✅ Shout sent to {channel.mention}.", ephemeral=True
        )

        # ── Log ───────────────────────────────────────────────────────────────
        log_embed = discord.Embed(
            title="📢 Shout Sent",
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Sent By", value=actor.mention, inline=True)
        log_embed.add_field(name="Channel", value=channel.mention, inline=True)
        log_embed.add_field(name="Ping", value=ping.mention if ping else "None", inline=True)
        log_embed.add_field(name="Type", value="Embed" if use_embed else "Plain", inline=True)
        log_embed.add_field(name="Message", value=message[:500], inline=False)
        await self.bot.log_action(log_embed)


async def setup(bot):
    await bot.add_cog(ShoutCog(bot))