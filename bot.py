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

TOKEN          = os.getenv("DISCORD_TOKEN", "YOUR_BOT_TOKEN_HERE")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
GUILD_ID       = 1387648629065650247


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
            help_command=None  # Disable default help so ours works
        )
        self.db             = Database()
        self.log_channel_id = LOG_CHANNEL_ID

    async def setup_hook(self):
        await self.db.init()

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
            "cogs.moderation",
            "cogs.automod",
            "cogs.purge",
            "cogs.help",
        ]:
            await self.load_extension(cog)
            logger.info(f"Loaded cog: {cog}")

        # Clear global commands to remove duplicates
        self.tree.clear_commands(guild=None)
        await self.tree.sync()
        logger.info("Cleared global slash commands")

        # Sync to guild for instant updates
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
        if not self.log_channel_id:
            return
        channel = self.get_channel(self.log_channel_id)
        if channel:
            await channel.send(embed=embed)


bot = AfternightBot()

if __name__ == "__main__":
    asyncio.run(bot.start(TOKEN))

if __name__ == "__main__":
    asyncio.run(bot.start(TOKEN))
