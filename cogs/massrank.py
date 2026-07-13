"""
cogs/massrank.py — /massrank slash command
"""
import discord
from discord import app_commands
from discord.ext import commands
import datetime

# ── Config ────────────────────────────────────────────────────────────────────
ALLOWED_ROLES: set[int] = {
    1458302857764802683,  # Community Manager
    1387649282139754587,  # [C] Creators
}


def can_mass_rank(member: discord.Member) -> bool:
    return bool({r.id for r in member.roles} & ALLOWED_ROLES)


class MassRankCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="massrank",
        description="Assign a role to multiple members at once."
    )
    @app_commands.describe(
        role="The role to assign",
        members="Mention all the members to rank (e.g. @user1 @user2 @user3)"
    )
    async def massrank(self, interaction: discord.Interaction,
                       role: discord.Role,
                       members: str):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user

        if not can_mass_rank(actor):
            return await interaction.followup.send(
                "❌ Only Community Managers or Creators may use `/massrank`.",
                ephemeral=True
            )

        # ── Parse mentioned members from the string ───────────────────────────
        guild = interaction.guild
        parsed_members = []
        failed_parse   = []

        for mention in members.split():
            # Handle <@123456> and <@!123456> formats
            user_id = mention.strip("<@!>")
            if user_id.isdigit():
                member = guild.get_member(int(user_id))
                if member:
                    parsed_members.append(member)
                else:
                    failed_parse.append(mention)
            else:
                failed_parse.append(mention)

        if not parsed_members:
            return await interaction.followup.send(
                "❌ No valid members found. Make sure you mention them with @.",
                ephemeral=True
            )

        # ── Assign role to each member ────────────────────────────────────────
        success = []
        failed  = []

        for member in parsed_members:
            try:
                if role not in member.roles:
                    await member.add_roles(
                        role,
                        reason=f"Mass rank by {actor.display_name}"
                    )
                success.append(member)
            except discord.Forbidden:
                failed.append(member)
            except Exception:
                failed.append(member)

        # ── Build result embed ────────────────────────────────────────────────
        embed = discord.Embed(
            title="✅ Mass Rank Complete",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(
            name="Role Assigned",
            value=role.mention,
            inline=True
        )
        embed.add_field(
            name="Total Ranked",
            value=f"{len(success)} member(s)",
            inline=True
        )
        embed.add_field(
            name="\u200b",
            value="\u200b",
            inline=True
        )

        if success:
            success_text = " ".join(m.mention for m in success)
            if len(success_text) <= 1024:
                embed.add_field(
                    name="✅ Successfully Ranked",
                    value=success_text,
                    inline=False
                )
            else:
                embed.add_field(
                    name="✅ Successfully Ranked",
                    value=f"{len(success)} members ranked successfully.",
                    inline=False
                )

        if failed:
            embed.add_field(
                name="❌ Failed",
                value=" ".join(m.mention for m in failed),
                inline=False
            )
            embed.color = discord.Color.orange()

        if failed_parse:
            embed.add_field(
                name="⚠️ Could Not Parse",
                value=" ".join(failed_parse),
                inline=False
            )

        embed.set_footer(text=f"Mass rank by {actor.display_name}")
        await interaction.followup.send(embed=embed, ephemeral=False)

        # ── Log ───────────────────────────────────────────────────────────────
        log_embed = discord.Embed(
            title="📋 Mass Rank",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="By", value=actor.mention, inline=True)
        log_embed.add_field(name="Role", value=role.mention, inline=True)
        log_embed.add_field(name="Ranked", value=f"{len(success)} members", inline=True)
        await self.bot.log_action(log_embed)


async def setup(bot):
    await bot.add_cog(MassRankCog(bot))
