"""
cogs/tiktok.py — /tiktok slash command to download a TikTok video and post it
as a playable .mp4 attachment without exposing the source URL in the message.
"""
import asyncio
import datetime
import os
import re
import shutil
import tempfile
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp

TIKTOK_URL_RE = re.compile(
    r"^https?://(?:www\.|vm\.|vt\.|m\.)?tiktok\.com/\S+$",
    re.IGNORECASE,
)


def _extract_tiktok_url(raw_input: str) -> Optional[str]:
    text = (raw_input or "").strip()
    if TIKTOK_URL_RE.match(text):
        return text
    match = re.search(r"https?://(?:www\.|vm\.|vt\.|m\.)?tiktok\.com/\S+", text, re.IGNORECASE)
    return match.group(0) if match else None


def _download_sync(url: str, output_dir: str) -> str:
    """Run yt-dlp synchronously inside a temporary directory and return the downloaded file path."""
    out_template = os.path.join(output_dir, "video.%(ext)s")
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": out_template,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "max_filesize": 100 * 1024 * 1024,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        prepared = ydl.prepare_filename(info)

    if os.path.exists(prepared):
        return prepared

    mp4_candidate = os.path.splitext(prepared)[0] + ".mp4"
    if os.path.exists(mp4_candidate):
        return mp4_candidate

    for fname in os.listdir(output_dir):
        full = os.path.join(output_dir, fname)
        if os.path.isfile(full):
            return full

    raise RuntimeError("Downloaded video file could not be found.")


async def _ensure_playable_mp4(src_path: str, work_dir: str) -> str:
    """If ffmpeg is available, remux/transcode to H.264 + AAC MP4 so Discord plays it reliably."""
    if not shutil.which("ffmpeg"):
        return src_path

    dst_path = os.path.join(work_dir, "playable.mp4")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        src_path,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        dst_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.communicate()
    if proc.returncode == 0 and os.path.exists(dst_path) and os.path.getsize(dst_path) > 0:
        return dst_path
    return src_path


class TikTokCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="tiktok",
        description="Download a TikTok video and post it directly as a playable video."
    )
    @app_commands.describe(
        url="TikTok video link (hidden from the posted message)",
        reencode="Force H.264/MP4 conversion for maximum player compatibility (requires ffmpeg)"
    )
    async def tiktok(
        self,
        interaction: discord.Interaction,
        url: str,
        reencode: bool = False,
    ):
        await interaction.response.defer()

        clean_url = _extract_tiktok_url(url)
        if not clean_url:
            return await interaction.followup.send(
                "❌ Please provide a valid TikTok video URL.",
                ephemeral=True,
            )

        max_bytes = getattr(interaction.guild, "filesize_limit", 20 * 1024 * 1024)

        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                downloaded_path = await asyncio.to_thread(_download_sync, clean_url, tmp_dir)
                final_path = (
                    await _ensure_playable_mp4(downloaded_path, tmp_dir)
                    if reencode
                    else downloaded_path
                )
            except Exception as exc:
                return await interaction.followup.send(
                    f"❌ Could not download that TikTok video: `{exc}`",
                    ephemeral=True,
                )

            file_size = os.path.getsize(final_path)
            if file_size > max_bytes:
                size_mb = file_size / (1024 * 1024)
                limit_mb = max_bytes / (1024 * 1024)
                return await interaction.followup.send(
                    f"❌ The downloaded video is **{size_mb:.1f} MB**, which exceeds this server's "
                    f"**{limit_mb:.0f} MB** upload limit.",
                    ephemeral=True,
                )

            discord_file = discord.File(final_path, filename="tiktok_video.mp4")
            await interaction.followup.send(
                content=f"🎬 Downloaded for {interaction.user.mention}",
                file=discord_file,
            )

        log_embed = discord.Embed(
            title="📥 TikTok Video Downloaded",
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        log_embed.add_field(
            name="By",
            value=f"{interaction.user.mention} (`{interaction.user.id}`)",
            inline=True,
        )
        log_embed.add_field(name="Source URL", value="Hidden (redacted)", inline=True)
        await self.bot.log_action(log_embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(TikTokCog(bot))
