"""
cogs/inactivity.py — /inactivitynotice slash command
"""
import discord
from discord import app_commands
from discord.ext import commands
from constants import is_staff, FIRE_ALLOWED_ROLES
import datetime

# ── Config ────────────────────────────────────────────────────────────────────
REVIEW_CHANNEL_ID   = 1525942704901587174  # Where notices are reviewed
APPROVED_CHANNEL_ID = 1525942757263278110  # Where approved notices are posted

REVIEWER_ROLES: set[int] = {
    1458302854887510210,  # Overseer of Staff
    1458302857764802683,  # Community Manager
    1387649282139754587,  # [C] Creators
}


def can_review(member: discord.Member) -> bool:
    return bool({r.id for r in member.roles} & REVIEWER_ROLES)


# ── Approval View ─────────────────────────────────────────────────────────────

class InactivityView(discord.ui.View):
    def __init__(self, submitter_id: int, date_start: str, date_end: str, reason: str):
        super().__init__(timeout=None)
        self.submitter_id = submitter_id
        self.date_start   = date_start
        self.date_end     = date_end
        self.reason       = reason

    @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.green, custom_id="inactivity_approve")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not can_review(interaction.user):
            return await interaction.response.send_message(
                "❌ You don't have permission to approve inactivity notices.",
                ephemeral=True
            )

        # ── Disable buttons ───────────────────────────────────────────────────
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

        # ── Update review embed ───────────────────────────────────────────────
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(
            name="✅ Approved By",
            value=f"{interaction.user.mention} — {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
            inline=False
        )
        await interaction.message.edit(embed=embed, view=self)

        # ── Post to approved channel ──────────────────────────────────────────
        approved_channel = interaction.guild.get_channel(APPROVED_CHANNEL_ID)
        submitter = interaction.guild.get_member(self.submitter_id)
        mention   = submitter.mention if submitter else f"<@{self.submitter_id}>"

        approved_embed = discord.Embed(
            title="📋 Inactivity Notice Approved",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        approved_embed.description = (
            f"{mention}\n\n"
            f"📅 **Starting:** {self.date_start}\n"
            f"📅 **Returning:** {self.date_end}\n\n"
            f"**Reason:** {self.reason}"
        )
        approved_embed.set_footer(text=f"Approved by {interaction.user.display_name}")

        if approved_channel:
            await approved_channel.send(embed=approved_embed)

        # ── DM submitter ──────────────────────────────────────────────────────
        if submitter:
            try:
                dm_embed = discord.Embed(
                    title="✅ Inactivity Notice Approved",
                    color=discord.Color.green(),
                    timestamp=datetime.datetime.utcnow()
                )
                dm_embed.description = (
                    f"Your inactivity notice has been **approved**!\n\n"
                    f"📅 **Starting:** {self.date_start}\n"
                    f"📅 **Returning:** {self.date_end}\n\n"
                    f"Enjoy your time off!"
                )
                await submitter.send(embed=dm_embed)
            except discord.Forbidden:
                pass

        await interaction.response.send_message(
            f"✅ Inactivity notice approved and posted to <#{APPROVED_CHANNEL_ID}>.",
            ephemeral=True
        )

    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.red, custom_id="inactivity_deny")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not can_review(interaction.user):
            return await interaction.response.send_message(
                "❌ You don't have permission to deny inactivity notices.",
                ephemeral=True
            )

        # ── Disable buttons ───────────────────────────────────────────────────
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

        # ── Update review embed ───────────────────────────────────────────────
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(
            name="❌ Denied By",
            value=f"{interaction.user.mention} — {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
            inline=False
        )
        await interaction.message.edit(embed=embed, view=self)

        # ── DM submitter ──────────────────────────────────────────────────────
        submitter = interaction.guild.get_member(self.submitter_id)
        if submitter:
            try:
                dm_embed = discord.Embed(
                    title="❌ Inactivity Notice Denied",
                    color=discord.Color.red(),
                    timestamp=datetime.datetime.utcnow()
                )
                dm_embed.description = (
                    f"Your inactivity notice has been **denied**.\n\n"
                    f"📅 **Starting:** {self.date_start}\n"
                    f"📅 **Returning:** {self.date_end}\n\n"
                    f"Please contact the **Overseer of Staff**, **Community Manager**, "
                    f"or **Creators** to ask why it was denied."
                )
                await submitter.send(embed=dm_embed)
            except discord.Forbidden:
                pass

        await interaction.response.send_message(
            "❌ Inactivity notice denied. The submitter has been notified via DM.",
            ephemeral=True
        )


# ── Cog ───────────────────────────────────────────────────────────────────────

class InactivityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="inactivitynotice",
        description="Submit an inactivity notice for staff review."
    )
    @app_commands.describe(
        start_month="Month you go inactive (e.g. July)",
        start_day="Day you go inactive (e.g. 10)",
        start_year="Year you go inactive (e.g. 2026)",
        end_month="Month you return (e.g. July)",
        end_day="Day you return (e.g. 20)",
        end_year="Year you return (e.g. 2026)",
        reason="Reason for inactivity"
    )
    async def inactivitynotice(self, interaction: discord.Interaction,
                                start_month: str, start_day: str, start_year: str,
                                end_month: str, end_day: str, end_year: str,
                                reason: str):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user

        # ── Staff only ────────────────────────────────────────────────────────
        if not is_staff(actor):
            return await interaction.followup.send(
                "❌ Only staff members may submit inactivity notices.",
                ephemeral=True
            )

        date_start = f"{start_month} {start_day}, {start_year}"
        date_end   = f"{end_month} {end_day}, {end_year}"

        # ── Send to review channel ────────────────────────────────────────────
        review_channel = interaction.guild.get_channel(REVIEW_CHANNEL_ID)
        if not review_channel:
            return await interaction.followup.send(
                "❌ Review channel not found. Contact an admin.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="📋 Inactivity Notice — Pending Review",
            color=discord.Color.yellow(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=actor.display_avatar.url)
        embed.add_field(name="Staff Member", value=actor.mention, inline=True)
        embed.add_field(name="Submitted", value=datetime.datetime.utcnow().strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="📅 Starting", value=date_start, inline=True)
        embed.add_field(name="📅 Returning", value=date_end, inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.set_footer(text="Use the buttons below to approve or deny")

        view = InactivityView(
            submitter_id=actor.id,
            date_start=date_start,
            date_end=date_end,
            reason=reason
        )

        await review_channel.send(embed=embed, view=view)

        # ── Confirm to submitter ──────────────────────────────────────────────
        confirm = discord.Embed(
            title="📨 Inactivity Notice Submitted",
            color=discord.Color.yellow(),
            description=(
                f"Your inactivity notice has been submitted for review.\n\n"
                f"📅 **Starting:** {date_start}\n"
                f"📅 **Returning:** {date_end}\n\n"
                f"You will be notified via DM once it has been reviewed."
            )
        )
        await interaction.followup.send(embed=confirm, ephemeral=True)


async def setup(bot):
    await bot.add_cog(InactivityCog(bot))
