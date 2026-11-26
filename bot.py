import os
import io
import asyncio
import datetime
import logging
from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext import commands
from discord import app_commands
from database import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AfternightBot")

TOKEN          = os.getenv("DISCORD_TOKEN")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
GUILD_ID       = int(os.getenv("GUILD_ID", "0"))  # Optional: set in .env or leave 0 to sync all joined guilds

COGS = [
    "cogs.strikes",
    "cogs.activity",
    "cogs.faction",
    "cogs.blacklist",
    "cogs.shout",
    "cogs.suggestions",
    "cogs.testing",
    "cogs.inactivity",
    "cogs.resign",
    "cogs.backup",
    "cogs.massrank",
    "cogs.moderation",
    "cogs.automod",
    "cogs.purge",
    "cogs.help",
]

intents = discord.Intents.default()
intents.members         = True
intents.guilds          = True
intents.message_content = True
intents.messages        = True


class AfternightBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
        self.db             = Database()
        self.log_channel_id = LOG_CHANNEL_ID
        self._synced        = False

    async def setup_hook(self):
        if not TOKEN:
            raise RuntimeError("DISCORD_TOKEN is not set in environment variables.")

        await self.db.init()

        for cog in COGS:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.exception(f"Failed to load cog {cog}: {e}")

        # Sync to explicit GUILD_ID if configured and accessible
        if GUILD_ID:
            try:
                guild_obj = discord.Object(id=GUILD_ID)
                self.tree.copy_global_to(guild=guild_obj)
                await self.tree.sync(guild=guild_obj)
                self._synced = True
                logger.info(f"Synced slash commands to guild {GUILD_ID}")
            except discord.Forbidden:
                logger.warning(
                    f"Missing access to GUILD_ID={GUILD_ID}. "
                    "Will sync to connected guilds in on_ready instead."
                )

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")

        # If GUILD_ID wasn't set or failed, sync to every guild the bot is currently in
        if not self._synced:
            for guild in self.guilds:
                try:
                    self.tree.copy_global_to(guild=guild)
                    await self.tree.sync(guild=guild)
                    logger.info(f"Synced slash commands to {guild.name} ({guild.id})")
                except discord.Forbidden:
                    logger.warning(
                        f"Missing applications.commands scope in {guild.name} ({guild.id}). "
                        "Re-invite the bot with both 'bot' and 'applications.commands' scopes."
                    )
            self._synced = True

        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Afternight Factions"
            )
        )

    async def log_action(self, embed: discord.Embed):
        if not self.log_channel_id:
            return
        channel = self.get_channel(self.log_channel_id)
        if channel:
            await channel.send(embed=embed)

    async def close(self):
        if getattr(self.db, "pool", None):
            await self.db.pool.close()
            logger.info("Closed database pool")
        await super().close()


bot = AfternightBot()


@bot.tree.command(
    name="dumproles",
    description="Export all server role IDs and names as a downloadable text file."
)
async def dumproles(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message(
            "❌ Only server administrators can use `/dumproles`.",
            ephemeral=True
        )

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    roles = sorted(guild.roles, key=lambda r: r.position, reverse=True)

    lines = [
        f"Server: {guild.name} ({guild.id})",
        f"Exported: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"Total Roles: {len(roles)}",
        "-" * 60,
    ]
    for r in roles:
        lines.append(f"{r.id}  |  {r.name}")

    buf = io.BytesIO("\n".join(lines).encode("utf-8"))
    file = discord.File(buf, filename="server_roles.txt")

    await interaction.followup.send(
        f"✅ Exported **{len(roles)}** roles from **{guild.name}**:",
        file=file,
        ephemeral=True
    )


if __name__ == "__main__":
    asyncio.run(bot.start(TOKEN))
