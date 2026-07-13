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
        description="Copy a message and send it to any channel."
    )
    @app_commands.describe(
        message_id="The ID of the message you want to copy",
        source_channel="The channel the message is in",
        destination="The channel to send the copied message to",
        ping="Optional role to ping with the message"
    )
    async def shout(self, interaction: discord.Interaction,
                    message_id: str,
                    source_channel: discord.TextChannel,
                    destination: discord.TextChannel,
                    ping: discord.Role = None):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user

        if not has_fire_permission(actor):
            return await interaction.followup.send(
                "❌ Only Overseer of Staff, Community Manager, or Creators may use `/shout`.",
                ephemeral=True
            )

        # ── Fetch the original message ────────────────────────────────────────
        try:
            original = await source_channel.fetch_message(int(message_id))
        except discord.NotFound:
            return await interaction.followup.send(
                f"❌ Could not find message `{message_id}` in {source_channel.mention}.\n"
                "Make sure you copied the right message ID and selected the correct channel.",
                ephemeral=True
            )
        except ValueError:
            return await interaction.followup.send(
                "❌ Invalid message ID. Right click a message → Copy Message ID.",
                ephemeral=True
            )

        ping_str = ping.mention if ping else None

        # ── Copy embeds if the original has them ──────────────────────────────
        if original.embeds:
            await destination.send(
                content=ping_str,
                embeds=original.embeds
            )

        # ── Copy plain text content ───────────────────────────────────────────
        elif original.content:
            content = f"{ping_str}\n{original.content}" if ping_str else original.content
            await destination.send(content=content)

        # ── Copy attachments if any ───────────────────────────────────────────
        elif original.attachments:
            files = []
            for att in original.attachments:
                files.append(await att.to_file())
            await destination.send(
                content=ping_str,
                files=files
            )

        else:
            return await interaction.followup.send(
                "❌ That message has no content, embeds or attachments to copy.",
                ephemeral=True
            )

        # ── Confirmation ──────────────────────────────────────────────────────
        await interaction.followup.send(
            f"✅ Message copied from {source_channel.mention} and sent to {destination.mention}.",
            ephemeral=True
        )

        # ── Log ───────────────────────────────────────────────────────────────
        log_embed = discord.Embed(
            title="📢 Shout Sent",
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Sent By", value=actor.mention, inline=True)
        log_embed.add_field(name="From", value=source_channel.mention, inline=True)
        log_embed.add_field(name="To", value=destination.mention, inline=True)
        log_embed.add_field(name="Message ID", value=message_id, inline=True)
        log_embed.add_field(name="Ping", value=ping.mention if ping else "None", inline=True)
        await self.bot.log_action(log_embed)


async def setup(bot):
    await bot.add_cog(ShoutCog(bot))
