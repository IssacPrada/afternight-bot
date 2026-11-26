"""
cogs/suggestions.py — /suggest slash command
"""
import datetime
import discord
from discord import app_commands
from discord.ext import commands
from constants import SUGGESTION_CHANNEL_ID


class SuggestionModal(discord.ui.Modal, title="Submit a Suggestion"):
    title_input = discord.ui.TextInput(
        label="Suggestion Title",
        style=discord.TextStyle.short,
        placeholder="Short summary of your suggestion...",
        min_length=3,
        max_length=120
    )

    details_input = discord.ui.TextInput(
        label="Details",
        style=discord.TextStyle.long,
        placeholder="Explain your idea and why it would help...",
        min_length=10,
        max_length=1500
    )

    def __init__(
        self,
        bot,
        image_1: discord.Attachment | None = None,
        image_2: discord.Attachment | None = None
    ):
        super().__init__()
        self.bot = bot
        self.image_1 = image_1
        self.image_2 = image_2

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        channel = interaction.guild.get_channel(SUGGESTION_CHANNEL_ID)
        if not channel:
            return await interaction.followup.send(
                "❌ Suggestion channel not found. Check `SUGGESTION_CHANNEL_ID` in `constants.py`.",
                ephemeral=True
            )

        user = interaction.user
        embed = discord.Embed(
            title=f"💡 {self.title_input.value}",
            description=self.details_input.value,
            color=discord.Color.gold(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_author(
            name=f"{user.display_name} ({user.id})",
            icon_url=user.display_avatar.url
        )
        embed.set_footer(text="Vote with 👍 or 👎 below")

        attachments_to_send: list[discord.Attachment] = []
        for att in (self.image_1, self.image_2):
            if att is not None:
                attachments_to_send.append(att)

        if attachments_to_send:
            embed.set_image(url=attachments_to_send[0].url)
            if len(attachments_to_send) > 1:
                embed.add_field(
                    name="📎 Extra Attachment",
                    value=f"[View Attachment 2]({attachments_to_send[1].url})",
                    inline=False
                )

        files = [await att.to_file() for att in attachments_to_send]
        msg = await channel.send(embed=embed, files=files if files else None)

        try:
            await msg.add_reaction("👍")
            await msg.add_reaction("👎")
        except discord.HTTPException:
            pass

        log_embed = discord.Embed(
            title="💡 New Suggestion Submitted",
            color=discord.Color.gold(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Submitted By", value=f"{user.mention} (`{user.id}`)", inline=True)
        log_embed.add_field(name="Title", value=self.title_input.value, inline=True)
        log_embed.add_field(name="Channel", value=f"<#{SUGGESTION_CHANNEL_ID}>", inline=True)
        log_embed.add_field(name="Details", value=self.details_input.value[:1024], inline=False)
        if msg.jump_url:
            log_embed.add_field(name="Message Link", value=f"[Jump to Suggestion]({msg.jump_url})", inline=False)
        await self.bot.log_action(log_embed)

        await interaction.followup.send(
            f"✅ Your suggestion has been posted in <#{SUGGESTION_CHANNEL_ID}>!",
            ephemeral=True
        )


class SuggestionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="suggest",
        description="Submit a suggestion with optional image/video attachments."
    )
    @app_commands.describe(
        image_1="Optional first image or video attachment",
        image_2="Optional second image or video attachment"
    )
    async def suggest(
        self,
        interaction: discord.Interaction,
        image_1: discord.Attachment | None = None,
        image_2: discord.Attachment | None = None
    ):
        await interaction.response.send_modal(
            SuggestionModal(bot=self.bot, image_1=image_1, image_2=image_2)
        )


async def setup(bot):
    await bot.add_cog(SuggestionsCog(bot))
