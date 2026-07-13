import os
import asyncio
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

# ─── Config ───────────────────────────────────────────────────────────────────
TOKEN          = os.getenv("DISCORD_TOKEN", "YOUR_BOT_TOKEN_HERE")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
GUILD_ID       = 1387648629065650247

# ─── Bot Setup ────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members         = True
intents.guilds          = True
intents.message_content = True
intents.messages        = True


class AfternightBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.db            = Database()
        self.log_channel_id = LOG_CHANNEL_ID

    async def setup_hook(self):
        await self.db.init()

        # Load all cogs
        for cog in [
            "cogs.staff",
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
        ]:
            await self.load_extension(cog)
            logger.info(f"Loaded cog: {cog}")

        # Sync globally
        synced = await self.tree.sync()
        logger.info(f"Synced {len(synced)} global slash command(s)")

        # Sync to your guild instantly
        guild_obj = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild_obj)
        await self.tree.sync(guild=guild_obj)
        logger.info(f"Synced slash commands to guild {GUILD_ID}")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Afternight Factions"
            )
        )

    async def log_action(self, embed: discord.Embed):
        """Send an embed to the log channel."""
        if not self.log_channel_id:
            return
        channel = self.get_channel(self.log_channel_id)
        if channel:
            await channel.send(embed=embed)


bot = AfternightBot()

if __name__ == "__main__":
    asyncio.run(bot.start(TOKEN))
