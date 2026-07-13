"""
cogs/backup.py — /generatebackupcode and /transferroles slash commands
"""
import discord
from discord import app_commands
from discord.ext import commands
from constants import (
    STAFF_HIERARCHY, STAFF_HIERARCHY_NAMES,
    ROLE_STAFF_TEAM, ROLE_ADMIN_TEAM,
    FIRE_ALLOWED_ROLES, is_staff
)
import datetime
import secrets
import string

# ── Config ────────────────────────────────────────────────────────────────────
TRANSFER_LOG_CHANNEL = 1526028790650634260

NOTIFY_ROLES: set[int] = {
    1458302854887510210,  # Overseer of Staff
    1458302857764802683,  # Community Manager
    1387649282139754587,  # [C] Creators
}


def generate_code() -> str:
    """Generate a random 16-character alphanumeric code."""
    chars = string.ascii_uppercase + string.digits
    return "-".join(
        "".join(secrets.choice(chars) for _ in range(4))
        for _ in range(4)
    )


class BackupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # In-memory store: code -> {user_id, guild_id, roles, created_at}
        self.backup_codes: dict[str, dict] = {}

    # ── /generatebackupcode ───────────────────────────────────────────────────

    @app_commands.command(
        name="generatebackupcode",
        description="Generate a backup code to transfer your roles if your account is compromised."
    )
    async def generatebackupcode(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        member = interaction.user

        if not is_staff(member):
            return await interaction.followup.send(
                "❌ Only staff members may generate a backup code.",
                ephemeral=True
            )

        # ── Check if they already have a code ─────────────────────────────────
        existing = next(
            (code for code, data in self.backup_codes.items()
             if data["user_id"] == member.id and data["guild_id"] == interaction.guild.id),
            None
        )

        if existing:
            # Show their existing code
            data = self.backup_codes[existing]
            embed = discord.Embed(
                title="🔑 Your Existing Backup Code",
                color=discord.Color.yellow(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.description = (
                f"You already have a backup code. Keep it safe!\n\n"
                f"```{existing}```\n\n"
                f"⚠️ **Never share this code with anyone.**\n"
                f"If you believe it has been compromised, use `/generatebackupcode` "
                f"again to generate a new one."
            )
            embed.add_field(
                name="Roles Stored",
                value=", ".join(data["role_names"]) or "None",
                inline=False
            )
            embed.set_footer(text="Store this somewhere safe — it never expires.")
            return await interaction.followup.send(embed=embed, ephemeral=True)

        # ── Store their current staff roles ───────────────────────────────────
        staff_role_ids = []
        staff_role_names = []
        member_role_ids = {r.id for r in member.roles}

        for role_id in STAFF_HIERARCHY:
            if role_id in member_role_ids:
                staff_role_ids.append(role_id)
                staff_role_names.append(STAFF_HIERARCHY_NAMES.get(role_id, "Unknown"))

        for rid in [ROLE_STAFF_TEAM, ROLE_ADMIN_TEAM]:
            if rid in member_role_ids:
                staff_role_ids.append(rid)

        # Also store privileged roles
        for rid in FIRE_ALLOWED_ROLES:
            if rid in member_role_ids:
                staff_role_ids.append(rid)

        if not staff_role_ids:
            return await interaction.followup.send(
                "❌ You don't have any staff roles to back up.",
                ephemeral=True
            )

        # ── Generate code ─────────────────────────────────────────────────────
        code = generate_code()
        while code in self.backup_codes:
            code = generate_code()

        self.backup_codes[code] = {
            "user_id":    member.id,
            "guild_id":   interaction.guild.id,
            "role_ids":   staff_role_ids,
            "role_names": staff_role_names,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "used":       False
        }

        # ── Send code via DM ──────────────────────────────────────────────────
        try:
            dm_embed = discord.Embed(
                title="🔑 Your Backup Code",
                color=discord.Color.blurple(),
                timestamp=datetime.datetime.utcnow()
            )
            dm_embed.description = (
                f"Here is your backup code. **Store it somewhere safe.**\n\n"
                f"```{code}```\n\n"
                f"⚠️ **Never share this with anyone.**\n\n"
                f"If your account is ever compromised, join the server on your new "
                f"account and use `/transferroles` with this code to transfer your roles."
            )
            dm_embed.add_field(
                name="Roles Stored",
                value=", ".join(staff_role_names) or "None",
                inline=False
            )
            dm_embed.set_footer(text="This code never expires — keep it safe.")
            await member.send(embed=dm_embed)

            await interaction.followup.send(
                "✅ Your backup code has been sent to your DMs! Keep it safe.",
                ephemeral=True
            )
        except discord.Forbidden:
            # DMs closed — show in ephemeral
            embed = discord.Embed(
                title="🔑 Your Backup Code",
                color=discord.Color.blurple(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.description = (
                f"⚠️ Could not DM you. Here is your code — **copy it now, "
                f"this message will disappear.**\n\n"
                f"```{code}```\n\n"
                f"**Never share this with anyone.**"
            )
            embed.add_field(
                name="Roles Stored",
                value=", ".join(staff_role_names) or "None",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /transferroles ────────────────────────────────────────────────────────

    @app_commands.command(
        name="transferroles",
        description="Transfer your staff roles to this account using your backup code."
    )
    @app_commands.describe(
        code="Your backup code (format: XXXX-XXXX-XXXX-XXXX)",
        old_account="Your old Discord account (mention or ID)"
    )
    async def transferroles(self, interaction: discord.Interaction,
                             code: str, old_account: discord.Member):
        await interaction.response.defer(ephemeral=True)

        new_member = interaction.user
        guild      = interaction.guild
        code       = code.strip().upper()

        # ── Validate code ─────────────────────────────────────────────────────
        if code not in self.backup_codes:
            return await interaction.followup.send(
                "❌ Invalid backup code. Double check and try again.",
                ephemeral=True
            )

        data = self.backup_codes[code]

        # ── Check guild matches ───────────────────────────────────────────────
        if data["guild_id"] != guild.id:
            return await interaction.followup.send(
                "❌ This code was not generated in this server.",
                ephemeral=True
            )

        # ── Check old account matches ─────────────────────────────────────────
        if data["user_id"] != old_account.id:
            return await interaction.followup.send(
                "❌ That code does not belong to the old account you specified.",
                ephemeral=True
            )

        # ── Check code not already used ───────────────────────────────────────
        if data["used"]:
            return await interaction.followup.send(
                "❌ This backup code has already been used.",
                ephemeral=True
            )

        # ── Check new account doesn't already have staff roles ────────────────
        if is_staff(new_member):
            return await interaction.followup.send(
                "❌ Your new account already has staff roles.",
                ephemeral=True
            )

        # ── Transfer roles ────────────────────────────────────────────────────
        roles_added   = []
        roles_removed = []

        # Add roles to new account
        for role_id in data["role_ids"]:
            role = guild.get_role(role_id)
            if role:
                try:
                    await new_member.add_roles(role, reason=f"Role transfer from {old_account}")
                    roles_added.append(role)
                except discord.Forbidden:
                    pass

        # Remove roles from old account
        for role_id in data["role_ids"]:
            role = guild.get_role(role_id)
            if role and role in old_account.roles:
                try:
                    await old_account.remove_roles(role, reason=f"Role transfer to {new_member}")
                    roles_removed.append(role)
                except discord.Forbidden:
                    pass

        # Mark code as used
        self.backup_codes[code]["used"] = True

        # ── Notify log channel ────────────────────────────────────────────────
        log_channel = guild.get_channel(TRANSFER_LOG_CHANNEL)

        # Ping all notify roles
        pings = []
        for role_id in NOTIFY_ROLES:
            role = guild.get_role(role_id)
            if role:
                pings.append(role.mention)
        ping_str = " ".join(pings)

        log_embed = discord.Embed(
            title="🔄 Staff Role Transfer",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(
            name="Old Account",
            value=f"{old_account.mention} (`{old_account.id}`)",
            inline=True
        )
        log_embed.add_field(
            name="New Account",
            value=f"{new_member.mention} (`{new_member.id}`)",
            inline=True
        )
        log_embed.add_field(
            name="Roles Transferred",
            value=", ".join(r.name for r in roles_added) or "None",
            inline=False
        )
        log_embed.add_field(
            name="Roles Removed from Old Account",
            value=", ".join(r.name for r in roles_removed) or "None",
            inline=False
        )
        log_embed.set_footer(text="Please verify this transfer is legitimate.")

        if log_channel:
            await log_channel.send(content=ping_str, embed=log_embed)

        # ── Also log to main log channel ──────────────────────────────────────
        await self.bot.log_action(log_embed)

        # ── DM old account ────────────────────────────────────────────────────
        try:
            old_dm = discord.Embed(
                title="🔄 Roles Transferred Away",
                color=discord.Color.red(),
                timestamp=datetime.datetime.utcnow()
            )
            old_dm.description = (
                f"Your staff roles have been transferred to a new account.\n\n"
                f"**Roles Removed:** {', '.join(r.name for r in roles_removed) or 'None'}\n\n"
                f"If you did not authorize this transfer contact an Overseer of Staff "
                f"or Community Manager immediately."
            )
            await old_account.send(embed=old_dm)
        except discord.Forbidden:
            pass

        # ── Confirm to new account ────────────────────────────────────────────
        confirm_embed = discord.Embed(
            title="✅ Roles Successfully Transferred",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        confirm_embed.description = (
            f"Your staff roles have been transferred to this account.\n\n"
            f"**Roles Added:** {', '.join(r.name for r in roles_added) or 'None'}\n\n"
            f"Leadership has been notified of this transfer."
        )
        await interaction.followup.send(embed=confirm_embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(BackupCog(bot))
