"""
cogs/suggestions.py — /suggest slash command
"""
import discord
from discord import app_commands
from discord.ext import commands
import datetime

SUGGESTION_CHANNEL_ID = 1489800735658086581


class SuggestionModal(discord.ui.Modal, title="Submit a Suggestion"):
    suggestion = discord.ui.TextInput(
        label="Your Suggestion",
        style=discord.TextStyle.long,
        placeholder="Describe your suggestion in detail...",
        min_length=10,
        max_length=1000
    )

    def __init__(self, attachments: list[discord.Attachment]):
        super().__init__()
        self.attachments = attachments

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        channel = interaction.guild.get_channel(SUGGESTION_CHANNEL_ID)
        if not channel:
            return await interaction.followup.send(
                "❌ Suggestion channel not found. Contact an admin.", ephemeral=True
            )

        author = interaction.user

        # ── Sort attachments ──────────────────────────────────────────────────
        image_attachments = []
        video_attachments = []
        for att in self.attachments:
            if att.content_type and att.content_type.startswith("image/"):
                image_attachments.append(att)
            elif att.content_type and att.content_type.startswith("video/"):
                video_attachments.append(att)

        # ── Main suggestion embed ─────────────────────────────────────────────
        embed = discord.Embed(
            description=f"## 💡 New Suggestion\n\n{self.suggestion.value}",
            color=discord.Color.from_rgb(88, 101, 242),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_author(
            name=author.display_name,
            icon_url=author.display_avatar.url
        )
        embed.set_footer(text=f"User ID: {author.id}")

        # First image goes into the main embed
        if image_attachments:
            embed.set_image(url=image_attachments[0].url)

        # ── Send main embed ───────────────────────────────────────────────────
        suggestion_msg = await channel.send(embed=embed)

        # ── Send second image as follow up embed ──────────────────────────────
        for att in image_attachments[1:]:
            extra = discord.Embed(color=discord.Color.from_rgb(88, 101, 242))
            extra.set_image(url=att.url)
            await channel.send(embed=extra)

        # ── Send videos as plain links ────────────────────────────────────────
        for att in video_attachments:
            await channel.send(content=f"🎥 **Video Reference:** {att.url}")

        # ── Add vote reactions ────────────────────────────────────────────────
        await suggestion_msg.add_reaction("👍")
        await suggestion_msg.add_reaction("👎")

        # ── Confirm to user ───────────────────────────────────────────────────
        confirm = discord.Embed(
            title="✅ Suggestion Submitted!",
            description=(
                f"Your suggestion has been sent to {channel.mention}.\n\n"
                f"Thank you for helping improve Afternight!"
            ),
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=confirm, ephemeral=True)


class SuggestionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="suggest",
        description="Submit a suggestion for Afternight."
    )
    @app_commands.describe(
        reference1="First image or video reference (optional)",
        reference2="Second image or video reference (optional)"
    )
    async def suggest(self, interaction: discord.Interaction,
                      reference1: discord.Attachment = None,
                      reference2: discord.Attachment = None):

        # ── Collect attachments ───────────────────────────────────────────────
        attachments = [a for a in [reference1, reference2] if a is not None]

        # ── Validate file types ───────────────────────────────────────────────
        for att in attachments:
            if att.content_type and not (
                att.content_type.startswith("image/") or
                att.content_type.startswith("video/")
            ):
                return await interaction.response.send_message(
                    f"❌ `{att.filename}` is not a valid image or video file.",
                    ephemeral=True
                )

            if att.size > 50 * 1024 * 1024:
                return await interaction.response.send_message(
                    f"❌ `{att.filename}` is too large. Max file size is 50MB.",
                    ephemeral=True
                )

        # ── Open the modal ────────────────────────────────────────────────────
        await interaction.response.send_modal(SuggestionModal(attachments=attachments))


async def setup(bot):
    await bot.add_cog(SuggestionCog(bot))