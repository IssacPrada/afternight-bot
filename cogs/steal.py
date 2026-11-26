"""
cogs/steal.py — Copy emojis and stickers from other servers into this one.

Commands
  /stealemoji    paste custom emojis (any server) or upload an image/GIF
  /stealsticker  give a message link, a sticker ID, or upload an image
  Right-click a message -> Apps -> "Steal Emojis & Stickers"
                 grabs every custom emoji and sticker on that message

The bot needs the "Manage Expressions" permission (called "Manage Emojis and
Stickers" in older Discord versions) in your server.
"""
import datetime
import io
import re
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from constants import MOD_LOG_CHANNEL_ID, has_fire_permission

EMOJI_RE = re.compile(r"<(a?):(\w{2,32}):(\d{15,25})>")
MESSAGE_LINK_RE = re.compile(r"discord(?:app)?\.com/channels/(\d+)/(\d+)/(\d+)")

MAX_EMOJI_BYTES = 256 * 1024      # Discord limit for emoji uploads
MAX_STICKER_BYTES = 512 * 1024    # Discord limit for sticker uploads
MAX_PER_RUN = 10                  # safety cap per command


class StealError(Exception):
    """A readable, user-facing reason something could not be copied."""


def _clean_name(raw: Optional[str], fallback: str, max_len: int) -> str:
    name = re.sub(r"[^A-Za-z0-9_]", "_", raw or "").strip("_")
    if len(name) < 2:
        name = fallback
    return name[:max_len]


def _sticker_ext(fmt: discord.StickerFormatType) -> Optional[str]:
    """File extension to upload as, or None if bots can't upload that format."""
    if fmt in (discord.StickerFormatType.png, discord.StickerFormatType.apng):
        return "png"
    if fmt is discord.StickerFormatType.gif:
        return "gif"
    return None  # Lottie stickers can't be created by bots


class StealCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name="Steal Emojis & Stickers",
            callback=self.steal_from_message,
        )

    async def cog_load(self):
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _allowed(member: discord.abc.User | discord.Member) -> bool:
        return isinstance(member, discord.Member) and (
            member.guild_permissions.manage_expressions or has_fire_permission(member)
        )

    @staticmethod
    def _bot_can_manage(guild: discord.Guild) -> bool:
        return guild.me is not None and guild.me.guild_permissions.manage_expressions

    async def _download(self, url: str, limit: int) -> bytes:
        timeout = aiohttp.ClientTimeout(total=20)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        raise StealError(f"couldn't download it (HTTP {resp.status})")
                    if resp.content_length and resp.content_length > limit:
                        raise StealError(
                            f"file is {resp.content_length // 1024} KB, the limit is {limit // 1024} KB"
                        )
                    data = await resp.read()
        except aiohttp.ClientError as e:
            raise StealError(f"download error: {e}")
        if len(data) > limit:
            raise StealError(f"file is {len(data) // 1024} KB, the limit is {limit // 1024} KB")
        return data

    async def _post_log(self, guild: discord.Guild, embed: discord.Embed):
        channel = guild.get_channel(MOD_LOG_CHANNEL_ID)
        if isinstance(channel, discord.TextChannel):
            await channel.send(embed=embed)
        else:
            await self.bot.log_action(embed)

    # ── Emoji ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _emoji_jobs_from_text(text: str) -> list[dict]:
        jobs, seen = [], set()
        for animated, name, eid in EMOJI_RE.findall(text or ""):
            if eid in seen:
                continue
            seen.add(eid)
            ext = "gif" if animated else "png"
            jobs.append({
                "name": name,
                "animated": bool(animated),
                "url": f"https://cdn.discordapp.com/emojis/{eid}.{ext}",
            })
        return jobs[:MAX_PER_RUN]

    async def _create_emoji(
        self, guild: discord.Guild, name: str, animated: bool, data: bytes, actor
    ) -> discord.Emoji:
        used = sum(1 for e in guild.emojis if e.animated == animated)
        if used >= guild.emoji_limit:
            kind = "animated" if animated else "static"
            raise StealError(f"no free {kind} emoji slots ({used}/{guild.emoji_limit})")

        taken = {e.name.lower() for e in guild.emojis}
        final, n = name, 1
        while final.lower() in taken:
            n += 1
            final = f"{name[:29]}_{n}"

        try:
            return await guild.create_custom_emoji(
                name=final, image=data, reason=f"Emoji stolen by {actor}"
            )
        except discord.Forbidden:
            raise StealError("I'm missing the **Manage Expressions** permission")
        except discord.HTTPException as e:
            raise StealError(f"Discord rejected it: {e.text or e}")

    async def _steal_emojis(self, guild, actor, jobs) -> tuple[list[discord.Emoji], list[str]]:
        added, failed = [], []
        for job in jobs:
            try:
                data = await self._download(job["url"], MAX_EMOJI_BYTES)
                added.append(await self._create_emoji(guild, job["name"], job["animated"], data, actor))
            except StealError as e:
                failed.append(f"`:{job['name']}:` — {e}")
        return added, failed

    # ── Stickers ──────────────────────────────────────────────────────────────

    async def _sticker_jobs_from_message(self, message: discord.Message) -> tuple[list[dict], list[str]]:
        jobs, problems = [], []
        for item in message.stickers[:MAX_PER_RUN]:
            ext = _sticker_ext(item.format)
            if ext is None:
                problems.append(f"`{item.name}` — Lottie stickers can't be copied by bots")
                continue
            full = None
            try:
                full = await item.fetch()
            except discord.HTTPException:
                pass
            if isinstance(full, discord.StandardSticker):
                problems.append(f"`{item.name}` — Discord's built-in stickers can't be copied")
                continue
            jobs.append({
                "name": item.name,
                "url": item.url,
                "ext": ext,
                "description": getattr(full, "description", None),
                "related": getattr(full, "emoji", None),
            })
        return jobs, problems

    async def _create_sticker(self, guild: discord.Guild, job: dict, data: bytes, actor) -> discord.GuildSticker:
        if len(guild.stickers) >= guild.sticker_limit:
            raise StealError(f"no free sticker slots ({len(guild.stickers)}/{guild.sticker_limit})")

        name = _clean_name(job["name"], "sticker", 30)
        description = (job.get("description") or name)[:100]
        if len(description) < 2:
            description = name
        file = discord.File(io.BytesIO(data), filename=f"sticker.{job['ext']}")
        try:
            return await guild.create_sticker(
                name=name,
                description=description,
                emoji=job.get("related") or "slight_smile",
                file=file,
                reason=f"Sticker stolen by {actor}",
            )
        except discord.Forbidden:
            raise StealError("I'm missing the **Manage Expressions** permission")
        except discord.HTTPException as e:
            raise StealError(f"Discord rejected it (must be PNG/APNG/GIF, 320x320 recommended): {e.text or e}")

    async def _steal_stickers(self, guild, actor, jobs) -> tuple[list[discord.GuildSticker], list[str]]:
        added, failed = [], []
        for job in jobs:
            try:
                data = await self._download(job["url"], MAX_STICKER_BYTES)
                added.append(await self._create_sticker(guild, job, data, actor))
            except StealError as e:
                failed.append(f"`{job['name']}` — {e}")
        return added, failed

    async def _message_from_link(self, link: str) -> discord.Message:
        m = MESSAGE_LINK_RE.search(link or "")
        if not m:
            raise StealError("that doesn't look like a Discord message link")
        _, channel_id, message_id = (int(x) for x in m.groups())
        try:
            channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
            return await channel.fetch_message(message_id)
        except (discord.NotFound, discord.Forbidden):
            raise StealError(
                "I can't see that message — I have to be a member of that server. "
                "Use the **image** option or the right-click menu instead"
            )

    # ── Reporting ─────────────────────────────────────────────────────────────

    async def _report(
        self,
        interaction: discord.Interaction,
        kind: str,
        added: list,
        failed: list[str],
    ):
        color = discord.Color.green() if added and not failed else (
            discord.Color.orange() if added else discord.Color.red()
        )
        embed = discord.Embed(
            title=f"{'✅' if added else '❌'} {kind} Steal",
            color=color,
            timestamp=datetime.datetime.utcnow(),
        )
        if added:
            embed.add_field(
                name=f"Added ({len(added)})",
                value=" ".join(str(x) if isinstance(x, discord.Emoji) else f"`{x.name}`" for x in added)[:1024],
                inline=False,
            )
        if failed:
            embed.add_field(name=f"Failed ({len(failed)})", value="\n".join(failed)[:1024], inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

        if added:
            log = discord.Embed(
                title=f"🪙 {kind} Stolen",
                color=discord.Color.gold(),
                timestamp=datetime.datetime.utcnow(),
            )
            log.add_field(name="By", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=True)
            log.add_field(name="Added", value=", ".join(f"`{x.name}`" for x in added)[:1024], inline=False)
            await self._post_log(interaction.guild, log)

    async def _precheck(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild or not self._allowed(interaction.user):
            await interaction.response.send_message(
                "❌ You need the **Manage Expressions** permission (or a leadership role) to use this.",
                ephemeral=True,
            )
            return False
        if not self._bot_can_manage(interaction.guild):
            await interaction.response.send_message(
                "❌ I'm missing the **Manage Expressions** permission in this server. "
                "Give my role that permission and try again.",
                ephemeral=True,
            )
            return False
        return True

    # ── /stealemoji ───────────────────────────────────────────────────────────

    @app_commands.command(
        name="stealemoji",
        description="Copy custom emojis from other servers into this server."
    )
    @app_commands.describe(
        emojis="Paste one or more custom emojis (from any server)",
        image="Or upload an image / GIF to turn into an emoji",
        name="Name for the new emoji (only for a single emoji or an uploaded image)"
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_expressions=True)
    async def stealemoji(
        self,
        interaction: discord.Interaction,
        emojis: Optional[str] = None,
        image: Optional[discord.Attachment] = None,
        name: Optional[str] = None,
    ):
        if not await self._precheck(interaction):
            return
        await interaction.response.defer(ephemeral=True)

        jobs = self._emoji_jobs_from_text(emojis or "")
        if image:
            if not (image.content_type or "").startswith("image/"):
                return await interaction.followup.send("❌ That attachment isn't an image.", ephemeral=True)
            jobs.append({
                "name": _clean_name(name or image.filename.rsplit(".", 1)[0], "emoji", 32),
                "animated": image.content_type == "image/gif",
                "url": image.url,
            })
        if not jobs:
            return await interaction.followup.send(
                "❌ Give me at least one custom emoji (e.g. `<:name:123...>`) or upload an image.\n"
                "💡 Don't have Nitro? Use the right-click **Steal Emojis & Stickers** option on a message "
                "that contains the emoji, or upload the image.",
                ephemeral=True,
            )
        if name and len(jobs) == 1:
            jobs[0]["name"] = _clean_name(name, jobs[0]["name"], 32)

        added, failed = await self._steal_emojis(interaction.guild, interaction.user, jobs)
        await self._report(interaction, "Emoji", added, failed)

    # ── /stealsticker ─────────────────────────────────────────────────────────

    @app_commands.command(
        name="stealsticker",
        description="Copy a sticker from another server into this server."
    )
    @app_commands.describe(
        message_link="Link to a message containing the sticker (I must be in that server)",
        sticker_id="The sticker's ID",
        image="Or upload a PNG / APNG / GIF (under 512 KB) to use as the sticker",
        name="Name for the new sticker"
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_expressions=True)
    async def stealsticker(
        self,
        interaction: discord.Interaction,
        message_link: Optional[str] = None,
        sticker_id: Optional[str] = None,
        image: Optional[discord.Attachment] = None,
        name: Optional[str] = None,
    ):
        if not await self._precheck(interaction):
            return
        await interaction.response.defer(ephemeral=True)

        jobs: list[dict] = []
        problems: list[str] = []
        try:
            if image:
                ctype = (image.content_type or "").lower()
                if ctype not in ("image/png", "image/apng", "image/gif"):
                    raise StealError("stickers must be PNG, APNG or GIF")
                jobs.append({
                    "name": _clean_name(name or image.filename.rsplit(".", 1)[0], "sticker", 30),
                    "url": image.url,
                    "ext": "gif" if ctype == "image/gif" else "png",
                    "description": None,
                    "related": None,
                })
            elif sticker_id:
                if not sticker_id.strip().isdigit():
                    raise StealError("the sticker ID must be a number")
                try:
                    sticker = await self.bot.fetch_sticker(int(sticker_id.strip()))
                except discord.NotFound:
                    raise StealError("no sticker with that ID exists")
                if isinstance(sticker, discord.StandardSticker):
                    raise StealError("Discord's built-in stickers can't be copied")
                ext = _sticker_ext(sticker.format)
                if ext is None:
                    raise StealError("Lottie stickers can't be copied by bots")
                jobs.append({
                    "name": sticker.name, "url": sticker.url, "ext": ext,
                    "description": sticker.description, "related": sticker.emoji,
                })
            elif message_link:
                message = await self._message_from_link(message_link)
                if not message.stickers:
                    raise StealError("that message has no stickers")
                jobs, problems = await self._sticker_jobs_from_message(message)
            else:
                raise StealError(
                    "give me a **message_link**, a **sticker_id**, or upload an **image**.\n"
                    "💡 Easiest: right-click a message that has the sticker → Apps → **Steal Emojis & Stickers**"
                )
        except StealError as e:
            return await interaction.followup.send(f"❌ {e}", ephemeral=True)

        if name and len(jobs) == 1:
            jobs[0]["name"] = _clean_name(name, jobs[0]["name"], 30)

        added, failed = await self._steal_stickers(interaction.guild, interaction.user, jobs)
        await self._report(interaction, "Sticker", added, problems + failed)

    # ── Right-click: Steal Emojis & Stickers ──────────────────────────────────

    @app_commands.guild_only()
    @app_commands.default_permissions(manage_expressions=True)
    async def steal_from_message(self, interaction: discord.Interaction, message: discord.Message):
        if not await self._precheck(interaction):
            return
        await interaction.response.defer(ephemeral=True)

        emoji_jobs = self._emoji_jobs_from_text(message.content)
        sticker_jobs, problems = await self._sticker_jobs_from_message(message)

        if not emoji_jobs and not sticker_jobs and not problems:
            return await interaction.followup.send(
                "❌ That message has no custom emojis or stickers.", ephemeral=True
            )

        if emoji_jobs:
            added, failed = await self._steal_emojis(interaction.guild, interaction.user, emoji_jobs)
            await self._report(interaction, "Emoji", added, failed)
        if sticker_jobs or problems:
            added, failed = await self._steal_stickers(interaction.guild, interaction.user, sticker_jobs)
            await self._report(interaction, "Sticker", added, problems + failed)


async def setup(bot):
    await bot.add_cog(StealCog(bot))
