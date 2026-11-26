"""
cogs/blacklist.py — /blacklist, /unblacklist, and /blacklistlist commands
"""
import datetime
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from constants import (
    BLACKLIST_CHANNEL_ID,
    FACTION_COLORS,
    can_use_blacklist,
)


class BlacklistCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="blacklist",
        description="Blacklist a user from a faction."
    )
    @app_commands.describe(
        user="Discord user to blacklist",
        faction="Faction name (e.g. Sanguis Order, Eldritch Thorn, SilverVenom, Seraphine Coven)",
        reason="Reason for the blacklist",
        roblox_username="Optional Roblox username of the blacklisted user"
    )
    async def blacklist(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        faction: str,
        reason: str,
        roblox_username: Optional[str] = None
    ):
        allowed, scoped_faction = can_use_blacklist(interaction.user)
        if not allowed:
            return await interaction.response.send_message(
                "❌ You don't have permission to use blacklist commands.",
                ephemeral=True
            )

        target_faction = scoped_faction or faction.strip()
        if scoped_faction and faction.strip().lower() != scoped_faction.lower():
            return await interaction.response.send_message(
                f"❌ You can only manage blacklists for **{scoped_faction}**.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        existing = await self.bot.db.is_blacklisted(str(user.id), str(interaction.guild.id))
        if existing:
            return await interaction.followup.send(
                f"⚠️ {user.mention} is already blacklisted from **{existing['faction']}** "
                f"(ID `#{existing['id']}`): {existing['reason']}",
                ephemeral=True
            )

        clean_roblox = roblox_username.strip() if roblox_username else None
        blacklist_id = await self.bot.db.add_blacklist(
            user_id=str(user.id),
            guild_id=str(interaction.guild.id),
            faction=target_faction,
            reason=reason,
            blacklisted_by=str(interaction.user.id),
            roblox_username=clean_roblox
        )

        color = FACTION_COLORS.get(target_faction, discord.Color.dark_red().value)
        embed = discord.Embed(
            title="⛔ Faction Blacklist Issued",
            color=color,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="User", value=f"{user.mention} (`{user.id}`)", inline=True)
        embed.add_field(name="Faction", value=target_faction, inline=True)
        embed.add_field(name="Issued By", value=f"{interaction.user.mention}", inline=True)
        if clean_roblox:
            embed.add_field(name="Roblox Username", value=f"`{clean_roblox}`", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Blacklist ID: #{blacklist_id}")

        channel = interaction.guild.get_channel(BLACKLIST_CHANNEL_ID)
        msg_id: Optional[str] = None
        if channel:
            sent = await channel.send(embed=embed)
            msg_id = str(sent.id)
            await self.bot.db.set_blacklist_embed_msg(blacklist_id, msg_id)

        await self.bot.db.log_staff_action(
            action="BLACKLIST_ADD",
            target_id=str(user.id),
            actor_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            note=f"Faction: {target_faction} | Reason: {reason}"
        )

        log_embed = discord.Embed(
            title="⛔ Blacklist Added",
            color=discord.Color.dark_red(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Target", value=f"{user.mention} (`{user.id}`)", inline=True)
        log_embed.add_field(name="Faction", value=target_faction, inline=True)
        log_embed.add_field(name="By", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=True)
        if clean_roblox:
            log_embed.add_field(name="Roblox", value=f"`{clean_roblox}`", inline=True)
        log_embed.add_field(name="Reason", value=reason, inline=False)
        await self.bot.log_action(log_embed)

        dest_text = f"<#{BLACKLIST_CHANNEL_ID}>" if channel else "database (channel not found)"
        await interaction.followup.send(
            f"✅ Blacklisted {user.mention} from **{target_faction}** (ID `#{blacklist_id}`) and posted to {dest_text}.",
            ephemeral=True
        )

    @app_commands.command(
        name="unblacklist",
        description="Remove a user's faction blacklist."
    )
    @app_commands.describe(
        user="Discord user to unblacklist"
    )
    async def unblacklist(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        allowed, scoped_faction = can_use_blacklist(interaction.user)
        if not allowed:
            return await interaction.response.send_message(
                "❌ You don't have permission to remove blacklists.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        existing = await self.bot.db.is_blacklisted(str(user.id), str(interaction.guild.id))
        if not existing:
            return await interaction.followup.send(
                f"❌ {user.mention} does not have an active blacklist in this server.",
                ephemeral=True
            )

        if scoped_faction and existing["faction"].lower() != scoped_faction.lower():
            return await interaction.followup.send(
                f"❌ You can only remove blacklists for **{scoped_faction}** (this one is for **{existing['faction']}**).",
                ephemeral=True
            )

        removed = await self.bot.db.remove_blacklist(str(user.id), str(interaction.guild.id))
        if not removed:
            return await interaction.followup.send(
                "❌ Failed to remove blacklist entry.",
                ephemeral=True
            )

        if existing.get("blacklist_embed_msg_id"):
            channel = interaction.guild.get_channel(BLACKLIST_CHANNEL_ID)
            if channel:
                try:
                    msg = await channel.fetch_message(int(existing["blacklist_embed_msg_id"]))
                    if msg.embeds:
                        updated = msg.embeds[0].copy()
                        updated.color = discord.Color.green()
                        updated.title = "✅ Faction Blacklist Removed"
                        updated.add_field(
                            name="Removed By",
                            value=f"{interaction.user.mention}",
                            inline=True
                        )
                        await msg.edit(embed=updated)
                except discord.NotFound:
                    pass
                except discord.HTTPException:
                    pass

        await self.bot.db.log_staff_action(
            action="BLACKLIST_REMOVE",
            target_id=str(user.id),
            actor_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            note=f"Removed from {existing['faction']}"
        )

        log_embed = discord.Embed(
            title="✅ Blacklist Removed",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Target", value=f"{user.mention} (`{user.id}`)", inline=True)
        log_embed.add_field(name="Faction", value=existing["faction"], inline=True)
        log_embed.add_field(name="By", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=True)
        await self.bot.log_action(log_embed)

        await interaction.followup.send(
            f"✅ Removed {user.mention}'s blacklist from **{existing['faction']}**.",
            ephemeral=True
        )

    @app_commands.command(
        name="blacklistlist",
        description="View active faction blacklists in the server."
    )
    @app_commands.describe(
        faction="Optional faction filter"
    )
    async def blacklistlist(
        self,
        interaction: discord.Interaction,
        faction: Optional[str] = None
    ):
        allowed, scoped_faction = can_use_blacklist(interaction.user)
        if not allowed:
            return await interaction.response.send_message(
                "❌ You don't have permission to view blacklist records.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        entries = await self.bot.db.get_all_blacklisted(str(interaction.guild.id))
        active_filter = scoped_faction or (faction.strip() if faction else None)
        if active_filter:
            entries = [e for e in entries if e["faction"].lower() == active_filter.lower()]

        if not entries:
            scope_msg = f" for **{active_filter}**" if active_filter else ""
            return await interaction.followup.send(
                f"📭 No active blacklists found{scope_msg}.",
                ephemeral=True
            )

        embed = discord.Embed(
            title=f"⛔ Active Blacklists{f' — {active_filter}' if active_filter else ''}",
            color=discord.Color.dark_red(),
            timestamp=datetime.datetime.utcnow()
        )

        for entry in entries[:25]:
            roblox_part = f" · Roblox: `{entry['roblox_username']}`" if entry.get("roblox_username") else ""
            embed.add_field(
                name=f"#{entry['id']} — <@{entry['user_id']}> ({entry['faction']})",
                value=f"**Reason:** {entry['reason']}\nBy <@{entry['blacklisted_by']}>{roblox_part}",
                inline=False
            )

        if len(entries) > 25:
            embed.set_footer(text=f"Showing 25 of {len(entries)} total entries")

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(BlacklistCog(bot))
