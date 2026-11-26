"""
cogs/backup.py — /generatebackupcode and /transferroles slash commands
"""
import datetime
import secrets
import string
import discord
from discord import app_commands
from discord.ext import commands
from constants import (
    FIRE_ALLOWED_ROLES,
    MOD_LOG_CHANNEL_ID,
    ROLE_ADMIN_TEAM,
    ROLE_STAFF_TEAM,
    STAFF_HIERARCHY,
    STAFF_HIERARCHY_NAMES,
    is_staff,
)

# ── Config ────────────────────────────────────────────────────────────────────
NOTIFY_ROLES: set[int] = {
    1575225137542733954,  # [O] Owner.
    1575225368577704116,  # [Co-O] Co-Owner.
    1575225624837099631,  # [CM] Community Manager.
    1575225697406947418,  # [SOH] Staff OverHead.
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
        # In-memory store: code -> {user_id, guild_id, role_ids, role_names, created_at, used}
        self.backup_codes: dict[str, dict] = {}

    async def _post_transfer_log(self, guild: discord.Guild | None, content: str | None, embed: discord.Embed):
        if guild:
            channel = guild.get_channel(MOD_LOG_CHANNEL_ID)
            if isinstance(channel, discord.TextChannel):
                await channel.send(content=content, embed=embed)
                return
        await self.bot.log_action(embed)

    # ── /generatebackupcode ───────────────────────────────────────────────────

    @app_commands.command(
        name="generatebackupcode",
        description="Generate a backup code to transfer your roles if your account is compromised."
    )
    async def generatebackupcode(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        guild = interaction.guild

        if not isinstance(member, discord.Member) or not guild or not is_staff(member):
            return await interaction.followup.send(
                "❌ Only staff members may generate a backup code.",
                ephemeral=True
            )

        # ── Check if they already have a code ─────────────────────────────────
        existing = next(
            (code for code, data in self.backup_codes.items()
             if data["user_id"] == member.id and data["guild_id"] == guild.id),
            None
        )

        if existing:
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
        staff_role_ids: list[int] = []
        staff_role_names: list[str] = []
        member_role_ids = {r.id for r in member.roles}

        for role_id in STAFF_HIERARCHY:
            if role_id in member_role_ids:
                staff_role_ids.append(role_id)
                staff_role_names.append(STAFF_HIERARCHY_NAMES.get(role_id, "Unknown"))

        for rid in [ROLE_STAFF_TEAM, ROLE_ADMIN_TEAM]:
            if rid in member_role_ids and rid not in staff_role_ids:
                staff_role_ids.append(rid)

        for rid in FIRE_ALLOWED_ROLES:
            if rid in member_role_ids and rid not in staff_role_ids:
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
            "user_id": member.id,
            "guild_id": guild.id,
            "role_ids": staff_role_ids,
            "role_names": staff_role_names,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "used": False,
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
                f"⚠️ **Never share this code with anyone.**\n\n"
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
    async def transferroles(
        self,
        interaction: discord.Interaction,
        code: str,
        old_account: discord.Member
    ):
        await interaction.response.defer(ephemeral=True)

        new_member = interaction.user
        guild = interaction.guild
        code = code.strip().upper()

        if not isinstance(new_member, discord.Member) or not guild:
            return await interaction.followup.send(
                "❌ This command can only be used inside a server.",
                ephemeral=True
            )

        if code not in self.backup_codes:
            return await interaction.followup.send(
                "❌ Invalid backup code. Double check and try again.",
                ephemeral=True
            )

        data = self.backup_codes[code]

        if data["guild_id"] != guild.id:
            return await interaction.followup.send(
                "❌ This code was not generated in this server.",
                ephemeral=True
            )

        if data["user_id"] != old_account.id:
            return await interaction.followup.send(
                "❌ That code does not belong to the old account you specified.",
                ephemeral=True
            )

        if data["used"]:
            return await interaction.followup.send(
                "❌ This backup code has already been used.",
                ephemeral=True
            )

        if is_staff(new_member):
            return await interaction.followup.send(
                "❌ Your new account already has staff roles.",
                ephemeral=True
            )

        roles_added: list[discord.Role] = []
        roles_removed: list[discord.Role] = []

        for role_id in data["role_ids"]:
            role = guild.get_role(role_id)
            if role:
                try:
                    await new_member.add_roles(role, reason=f"Role transfer from {old_account}")
                    roles_added.append(role)
                except discord.Forbidden:
                    pass

        for role_id in data["role_ids"]:
            role = guild.get_role(role_id)
            if role and role in old_account.roles:
                try:
                    await old_account.remove_roles(role, reason=f"Role transfer to {new_member}")
                    roles_removed.append(role)
                except discord.Forbidden:
                    pass

        self.backup_codes[code]["used"] = True

        pings = []
        for role_id in NOTIFY_ROLES:
            role = guild.get_role(role_id)
            if role:
                pings.append(role.mention)
        ping_str = " ".join(pings) or None

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

        await self._post_transfer_log(guild, ping_str, log_embed)

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
