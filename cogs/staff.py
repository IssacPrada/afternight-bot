"""
cogs/staff.py — /promote, /demote, /fire slash commands
"""
import discord
from discord import app_commands
from discord.ext import commands
from constants import (
    STAFF_HIERARCHY, STAFF_HIERARCHY_NAMES,
    ROLE_STAFF_TEAM, ROLE_ADMIN_TEAM,
    FIRE_ALLOWED_ROLES,
    get_member_rank_index, has_fire_permission, is_staff
)
import datetime


ADMIN_TIER_START = 4  # index of Administrator in STAFF_HIERARCHY


class StaffCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _make_log_embed(self, action: str, actor: discord.Member,
                        target: discord.Member, color: discord.Color,
                        extra: str = "") -> discord.Embed:
        embed = discord.Embed(
            title=f"📋 Staff Action — {action}",
            color=color,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Actor", value=actor.mention, inline=True)
        embed.add_field(name="Target", value=target.mention, inline=True)
        if extra:
            embed.add_field(name="Details", value=extra, inline=False)
        embed.set_footer(text=f"Target ID: {target.id}")
        return embed

    async def _update_admin_team_role(self, member: discord.Member, new_rank_index: int):
        """Add or remove the Administrative Team role based on new rank."""
        guild = member.guild
        admin_team_role = guild.get_role(ROLE_ADMIN_TEAM)
        if not admin_team_role:
            return
        if new_rank_index >= ADMIN_TIER_START:
            if admin_team_role not in member.roles:
                await member.add_roles(admin_team_role, reason="Reached Administrator tier")
        else:
            if admin_team_role in member.roles:
                await member.remove_roles(admin_team_role, reason="Below Administrator tier")

    # ── /promote ──────────────────────────────────────────────────────────────

    @app_commands.command(name="promote", description="Promote a staff member one rank up.")
    @app_commands.describe(user="The staff member to promote")
    async def promote(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user

        if not has_fire_permission(actor):
            return await interaction.followup.send(
                "❌ You do not have permission to use this command.\n"
                "Required: Overseer of Staff, Community Manager, or Creators.",
                ephemeral=True
            )

        target_rank = get_member_rank_index(user)

        if target_rank == -1:
            return await interaction.followup.send(
                f"❌ {user.mention} does not hold a staff rank.", ephemeral=True
            )
        if target_rank >= len(STAFF_HIERARCHY) - 1:
            return await interaction.followup.send(
                f"❌ {user.mention} is already at the highest rank (Lead Administrator).",
                ephemeral=True
            )

        guild = interaction.guild
        old_role = guild.get_role(STAFF_HIERARCHY[target_rank])
        new_role = guild.get_role(STAFF_HIERARCHY[target_rank + 1])

        if not new_role:
            return await interaction.followup.send("❌ Target role not found in this server.", ephemeral=True)

        await user.remove_roles(old_role, reason=f"Promoted by {actor}")
        await user.add_roles(new_role, reason=f"Promoted by {actor}")
        await self._update_admin_team_role(user, target_rank + 1)

        old_name = STAFF_HIERARCHY_NAMES.get(STAFF_HIERARCHY[target_rank], "Unknown")
        new_name = STAFF_HIERARCHY_NAMES.get(STAFF_HIERARCHY[target_rank + 1], "Unknown")

        await self.bot.db.log_staff_action(
            "PROMOTE", str(user.id), str(actor.id), str(guild.id),
            f"{old_name} → {new_name}"
        )

        embed = self._make_log_embed(
            "Promotion", actor, user, discord.Color.green(),
            f"{old_name} → **{new_name}**"
        )
        await self.bot.log_action(embed)

        success_embed = discord.Embed(
            title="✅ Promotion Successful",
            description=f"{user.mention} promoted from **{old_name}** to **{new_name}**.",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=success_embed)

        try:
            dm_embed = discord.Embed(
                title="🎉 You've Been Promoted!",
                description=f"Congratulations! You have been promoted to **{new_name}** in Afternight.",
                color=discord.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass

    # ── /demote ───────────────────────────────────────────────────────────────

    @app_commands.command(name="demote", description="Demote a staff member one rank down.")
    @app_commands.describe(user="The staff member to demote")
    async def demote(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user

        if not has_fire_permission(actor):
            return await interaction.followup.send(
                "❌ You do not have permission to use this command.\n"
                "Required: Overseer of Staff, Community Manager, or Creators.",
                ephemeral=True
            )

        target_rank = get_member_rank_index(user)

        if target_rank == -1:
            return await interaction.followup.send(
                f"❌ {user.mention} does not hold a staff rank.", ephemeral=True
            )
        if target_rank == 0:
            return await interaction.followup.send(
                f"❌ {user.mention} is already at the lowest rank (Trial Moderator).",
                ephemeral=True
            )

        guild = interaction.guild
        old_role = guild.get_role(STAFF_HIERARCHY[target_rank])
        new_role = guild.get_role(STAFF_HIERARCHY[target_rank - 1])

        if not new_role:
            return await interaction.followup.send("❌ Target role not found in this server.", ephemeral=True)

        await user.remove_roles(old_role, reason=f"Demoted by {actor}")
        await user.add_roles(new_role, reason=f"Demoted by {actor}")
        await self._update_admin_team_role(user, target_rank - 1)

        old_name = STAFF_HIERARCHY_NAMES.get(STAFF_HIERARCHY[target_rank], "Unknown")
        new_name = STAFF_HIERARCHY_NAMES.get(STAFF_HIERARCHY[target_rank - 1], "Unknown")

        await self.bot.db.log_staff_action(
            "DEMOTE", str(user.id), str(actor.id), str(guild.id),
            f"{old_name} → {new_name}"
        )

        embed = self._make_log_embed(
            "Demotion", actor, user, discord.Color.orange(),
            f"{old_name} → **{new_name}**"
        )
        await self.bot.log_action(embed)

        success_embed = discord.Embed(
            title="⬇️ Demotion Applied",
            description=f"{user.mention} demoted from **{old_name}** to **{new_name}**.",
            color=discord.Color.orange()
        )
        await interaction.followup.send(embed=success_embed)

        try:
            dm_embed = discord.Embed(
                title="📉 Staff Demotion Notice",
                description=f"You have been demoted to **{new_name}** in Afternight.",
                color=discord.Color.orange(),
                timestamp=datetime.datetime.utcnow()
            )
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass

    # ── /fire ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="fire", description="Remove all staff roles from a user.")
    @app_commands.describe(user="The staff member to fire", reason="Reason for firing")
    async def fire(self, interaction: discord.Interaction,
                   user: discord.Member, reason: str = "No reason provided."):
        await interaction.response.defer(ephemeral=True)

        actor = interaction.user
        if not has_fire_permission(actor):
            return await interaction.followup.send(
                "❌ You do not have permission to use `/fire`.\n"
                "Required: Overseer of Staff, Community Manager, or Creators.",
                ephemeral=True
            )

        guild = interaction.guild
        roles_to_remove = []

        for role_id in STAFF_HIERARCHY:
            role = guild.get_role(role_id)
            if role and role in user.roles:
                roles_to_remove.append(role)

        for rid in [ROLE_STAFF_TEAM, ROLE_ADMIN_TEAM]:
            role = guild.get_role(rid)
            if role and role in user.roles:
                roles_to_remove.append(role)

        if not roles_to_remove:
            return await interaction.followup.send(
                f"❌ {user.mention} does not have any staff roles.", ephemeral=True
            )

        await user.remove_roles(*roles_to_remove, reason=f"Fired by {actor}: {reason}")

        await self.bot.db.log_staff_action(
            "FIRE", str(user.id), str(actor.id), str(guild.id), reason
        )

        embed = self._make_log_embed(
            "Fired", actor, user, discord.Color.red(), f"Reason: {reason}"
        )
        await self.bot.log_action(embed)

        success_embed = discord.Embed(
            title="🔥 Staff Member Fired",
            description=f"{user.mention} has been removed from the staff team.\n**Reason:** {reason}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=success_embed)

        try:
            dm_embed = discord.Embed(
                title="📢 You Have Been Removed from Staff",
                description=(
                    f"You have been removed from the Afternight staff team.\n\n"
                    f"**Reason:** {reason}\n\n"
                    "If you believe this was in error, please contact a Community Manager."
                ),
                color=discord.Color.red(),
                timestamp=datetime.datetime.utcnow()
            )
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass


async def setup(bot):
    await bot.add_cog(StaffCog(bot))