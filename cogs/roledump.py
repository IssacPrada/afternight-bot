import discord
from discord import app_commands
from discord.ext import commands
import datetime

class RoleDumpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="dumproles",
        description="Scan all server roles and save their IDs to server_roles.txt."
    )
    async def dumproles(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not interaction.user.guild_permissions.administrator:
            return await interaction.followup.send(
                "❌ Only server administrators can run `/dumproles`.",
                ephemeral=True
            )

        guild = interaction.guild
        # Sort highest to lowest position like Discord's role list
        roles = sorted(guild.roles, key=lambda r: r.position, reverse=True)

        lines = [
            f"Server: {guild.name} ({guild.id})",
            f"Exported: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"Total Roles: {len(roles)}",
            "-" * 60,
        ]
        for r in roles:
            lines.append(f"{r.id}  |  {r.name}")

        output_path = "server_roles.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        await interaction.followup.send(
            f"✅ Exported **{len(roles)}** roles to `{output_path}` in your bot folder! "
            "You can open that file and paste it here (or upload it) so I can map your new roles.",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(RoleDumpCog(bot))
