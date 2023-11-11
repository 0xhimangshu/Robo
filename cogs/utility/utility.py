from __future__ import annotations

import asyncio
import datetime
import io
import json
import os
import re
from typing import List, Optional, Sequence, Union

import discord
import pytz
from discord import app_commands
from discord.ext import commands
from typing_extensions import Annotated

from core import Robo
from utils.context import Context
from utils.converter import (ColorConverter, MemberConverter, RoleConverter,
                             Snowflake)
from utils.formats import format_dt
from utils.views import PermissionView, PingRoleSelect

from .utils import EmojiURL, TicketClose, TicketCreate, emoji_name


class AfkFlag(commands.FlagConverter):
    globally: Optional[bool] = commands.flag(description="Whether to set your AFK globally or not (default: True)", default=True)
    
class Utility(commands.Cog):
    """
    Commands for guild customization."""
    def __init__(self, bot: Robo):
        self.bot = bot

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(
            id=1169531187975421962,
            name="magicwand"
        )
    
    async def cog_load(self) -> None:
        try:
            self.bot.add_view(TicketCreate(bot=self.bot))
            self.bot.logger.info("Loaded view TicketCreate")

        except Exception as e:
            self.bot.logger.info(f"Failed to load TicketCreate: {e}")
        try:
            await self.bot.load_extension("cogs.utility.utils.ticketevent")
            self.bot.logger.info("Loaded ticketevent")
        except commands.errors.ExtensionAlreadyLoaded as e:
            ...

    @commands.hybrid_command(
        name="emoji",
        description="Creates a new emoji in the server using imoji url or file",
    )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.describe(
        name="The emoji name",
        file="The image file to use for uploading",
        url="The URL to use for uploading",
    )
    async def emoji(
        self,
        ctx: commands.Context[Robo],
        name: Annotated[str, emoji_name],
        file: Optional[discord.Attachment],
        *,
        url: Optional[str],
    ):
        """
        Creates a new emoji in the server using imoji url or file

        `name:` - The emoji name
        `file:` - The image file to use for uploading
        `url:` - The URL to use for uploading
         *Note: You can only use one of the arguments, not both url and name*

        example:
        `r.emoji emoji_name https://cdn.discordapp.com/emojis/1111533250951782421.webp?size=96&quality=lossless`
        `r.emoji emoji_name https://cdn3.emoji.gg/emojis/kono_baka.png`
        `r.emoji emoji_name attachment`
        *Note: attachment must be png, or gif
        """
        if not ctx.me.guild_permissions.manage_emojis:
            return await ctx.send("Bot does not have permission to add emoji.")
        
        reason = f"Action done by {ctx.author} (ID: {ctx.author.id})"

        if file is None and url is None:
            return await ctx.send("Missing emoji file or url to upload with")
        
        if file is not None and url is not None:
            return await ctx.send("Cannot mix both file and url arguments, choose only")
        
        is_animated = False

        request_url = ""

        if url is not None:
            upgraded = await EmojiURL.convert(ctx, url)
            is_animated = upgraded.animated
            request_url = upgraded.url

        elif file is not None:
            if not file.filename.endswith((".png", ".jpg", ".jpeg", ".gif")):
                return await ctx.send(
                    "Unsupported file type given, expected png, jpg, or gif"
                )

            is_animated = file.filename.endswith(".gif")
            request_url = file.url

        emoji_count = sum(e.animated == is_animated for e in ctx.guild.emojis)
        if emoji_count >= ctx.guild.emoji_limit:
            return await ctx.send("There are no more emoji slots in this server.")
        
        if request_url.startswith("https://cdn.discordapp.com/emojis/"):
            # https://cdn.discordapp.com/emojis/596577462335307777.webp?size=96&quality=lossless
            url = request_url.split("?")[0]
            request_url = url.replace(".webp", ".png")

        async with self.bot.session.get(request_url) as resp:
            if resp.status >= 400:
                return await ctx.send("Could not fetch the image.")
            if int(resp.headers["Content-Length"]) >= (256 * 1024):
                return await ctx.send("Image is too big.")

            data = await resp.read()

            coro = ctx.guild.create_custom_emoji(name=name, image=data, reason=reason)

            async with ctx.typing():
                try:
                    created = await asyncio.wait_for(coro, timeout=10.0)
                except asyncio.TimeoutError:
                    return await ctx.send(
                        "Sorry, the bot is rate limited or it took too long."
                    )
                except discord.HTTPException as e:
                    return await ctx.send(f"Failed to create emoji somehow: {e}")
                else:
                    return await ctx.send(
                        embed = discord.Embed(
                            title="Emoji Created",
                            description=(
                                f"**Emoji:** {created} `<:{created.name}:{created.id}>`\n"
                                f"**Emoji ID:**`{created.id}`"
                                ),
                            color=self.bot.color
                        )
                    )
                         

    @commands.hybrid_command()
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @app_commands.guild_only()
    @app_commands.describe(
        channel="The channel to edit",
        backup="Whether to backup the channel or not (default: False)",
    )
    async def nuke(self, ctx: Context, channel:Optional[Union[discord.TextChannel, discord.Thread]], backup:bool=False):
        """
        Nukes a channel in the server

        `channel:` - The channel to nuke
        `backup:` - Whether to backup the channel or not (default: False)
        """
        if isinstance(channel, discord.Thread):
            channel = channel.parent
        
        if channel is None:
            channel = ctx.channel

        if not ctx.me.guild_permissions.manage_channels:
            return await ctx.send("Bot does not have permission to manage channels.")
        
        reason = f"Action done by {ctx.author} (ID: {ctx.author.id})"
        confirm = await ctx.confirm(f"Are you sure you want to nuke {channel.mention}?", timeout=30, author_id=ctx.author.id)

        if not confirm:
            return await ctx.send('Aborting.')
        
        if ctx.interaction:
            await ctx.interaction.response.defer(thinking=True)

        async for message in channel.history(limit=None):            
            with open("backup.txt", "a") as f:
                for attachment in message.attachments:
                    f.write(f"{message.author} - {message.created_at}: {attachment.filename}\n")
                else:
                    f.write(f"{message.author} - {message.created_at}: {message.content}\n")

            c = await channel.clone(reason=reason)
            await channel.delete(reason=reason)
            await c.send(
                content=f"Hey {message.author.mention} I have nuked #{channel.name} for you!",
                embed = discord.Embed(
                    title="Channel Nuked",
                    description=(
                        f"**Channel:** {channel.mention} \n"
                        f"**Channel ID:** `{channel.id}`"
                        ),
                    color=self.bot.color
                ),
            )
            await c.send(file=discord.File("backup.txt"))
            await asyncio.sleep(10)
            os.remove("backup.txt")
               

    @commands.hybrid_command(usage="r.afk [flags...] [reason]")
    @commands.guild_only()
    @app_commands.describe(
        reason="The reason why you are AFK",
    )
    async def afk(
        self,
        ctx: Context,
        *,
        reason: Optional[str] = None,
        flags: AfkFlag = None,
    ):
        """
        Sets your AFK message

        `reason:` - The reason why you are AFK
        `flags:` - The flags to use for the command

        example:
        `r.afk I'm AFK`
        `r.afk I'm AFK globally:yes`
        """
        if ctx.interaction:
            await ctx.interaction.response.defer(thinking=True)

        async with self.bot.db.cursor() as cur:
            await cur.execute(
                "SELECT * FROM afk WHERE afk_user_id = ?", (ctx.author.id,)
            )
            afk = await cur.fetchone()

        

        if flags is None:
            globally = True
        else:
            globally = flags.globally

        
        if reason is None:
            reason = "I dont know why he/she is AFK"

        if afk is None:
            async with self.bot.db.cursor() as cur:
                await cur.execute(
                    "INSERT INTO afk (afk_user_id, afk_reason, afk_global, afk_from, afk_mentions, afk_guild) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        ctx.author.id,
                        reason,
                        globally,
                        str(ctx.message.created_at),
                        0,
                        ctx.guild.id if not globally else None,
                    ),
                    )
                await self.bot.db.commit()
            await ctx.send(
                (
                    f"> I've set your AFK {' for this guild' if not globally else ''}\n"
                    f"> **Reason:** {reason}\n"
                )
            )
        else:
            return
        
    def timecalc(self, message: discord.Message, time: str):
        afk_from_time = datetime.datetime.fromisoformat(str(time)).replace(tzinfo=pytz.utc)
        message_time = message.created_at.replace(tzinfo=pytz.utc)

        time_difference = message_time - afk_from_time
        time_difference_seconds = time_difference.total_seconds()

        days, remainder = divmod(time_difference_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        if days > 0:
            time = f"{round(days)} days, {round(hours)} hours, {round(minutes)} minutes, and {round(seconds)} seconds"
        elif hours > 0:
            time = f"{round(hours)} hours, {round(minutes)} minutes, and {round(seconds)} seconds"
        elif minutes > 0:
            time = f"{round(minutes)} minutes and {round(seconds)} seconds"
        else:
            time = f"{round(seconds)} seconds"

        return time
                
    @commands.Cog.listener("on_message")
    async def on_afk_message(self, message: discord.Message):
        """
        Handles AFK messages

        This is a listener, so it will only work if the bot is online when the message is sent
        """
        async with self.bot.db.cursor() as cur:
            await cur.execute("SELECT * FROM afk")
            afk_list = await cur.fetchall()

        for afk in afk_list:
            if bool(afk[2]):
                user = self.bot.get_user(afk[0])
                time = self.timecalc(message, afk[3])
                mentions = afk[4] 

                # Check for mentions before checking if the author is AFK
                for mention in message.mentions:
                    if mention.id == afk[0]:
                        await message.channel.send(
                            f"> {user.name} is AFK\n> Reason: {afk[1]}"
                        )
                        async with self.bot.db.cursor() as cur:
                            await cur.execute(
                                "UPDATE afk SET afk_mentions = ? WHERE afk_user_id = ?",
                                (mentions, afk[0]),
                            )
                            await self.bot.db.commit()
                        return

                if message.author.id == afk[0]:
                    async with self.bot.db.cursor() as cur:
                        await cur.execute(
                            "DELETE FROM afk WHERE afk_user_id = ?", (message.author.id,)
                        )
                        await self.bot.db.commit()
                    await message.channel.send(
                        f"> Welcome back {user.name}! I've removed your AFK.\n> You were afk for {time}\n{f'> You were mentioned {mentions} times' if mentions > 0 else ''} "
                    )
                    return
            else:
                if message.guild is not None:
                    if message.guild.id == afk[5]:
                        user = self.bot.get_user(afk[0])
                        time = self.timecalc(message, afk[3])
                        mentions = afk[4] + 1

                        # Check for mentions before checking if the author is AFK
                        for mention in message.mentions:
                            if mention.id == afk[0]:
                                await message.channel.send(
                                    f"> {user.name} is AFK\n> Reason: {afk[1]}"
                                )
                                async with self.bot.db.cursor() as cur:
                                    await cur.execute(
                                        "UPDATE afk SET afk_mentions = ? WHERE afk_user_id = ?",
                                        (mentions, afk[0]),
                                    )
                                    await self.bot.db.commit()
                                return

                        if message.author.id == afk[0]:
                            async with self.bot.db.cursor() as cur:
                                await cur.execute(
                                    "DELETE FROM afk WHERE afk_user_id = ?", (message.author.id,)
                                )
                                await self.bot.db.commit()
                            await message.channel.send(
                                f"> Welcome back {user.name}! I've removed your AFK.\n> You were afk for {time}\n{f'> You were mentioned {mentions} times' if mentions > 0 else ''} "
                            )
                            return

      
    @commands.hybrid_group()
    async def ticket(self, ctx: Context):
        """
        Commands for ticket management

        Do `r.help ticket setup` for more information
        """
        await ctx.send_help(ctx.command.parent)

    @ticket.group(name="setup")
    async def ticket_setup(self, ctx: Context):
        """
        Commands for ticket setup

        Do `r.help ticket setup` for more information
        """
        await ctx.send_help(ctx.command.parent)

    @ticket_setup.command(name="add")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @app_commands.guild_only()
    @app_commands.describe(
        category="The category to create the ticket channel in",
        role="The role to ping when a ticket is created",
    )
    async def ticket_setup_add(
        self,
        ctx: Context,
        *,
        category: Optional[discord.CategoryChannel]=None,
        role: Optional[discord.Role]=None,
    ):
        """
        Sets up ticket system in the server
        
        `category:` - The category to create the ticket channel in (optional)
        `role:` - The role to ping when a ticket is created (optional)
        """
        if ctx.interaction:
            await ctx.defer()
        async with self.bot.db.cursor() as cur:
            await cur.execute(
                "SELECT * FROM tickets WHERE ticket_guild_id = ?", (ctx.guild.id,)
            )
            data = await cur.fetchone()

        if data is not None:
            return await ctx.send("Ticket system is already setup in this server", delete_after=10)
        
        embed = discord.Embed(
            title="Ticket Setup",
            description=(
                "This will setup the ticket system in the server\n"
                "This will create a category, role, and channel\n"
                "You can customize the category and role if you want\n"
            ),
            color=self.bot.color
        )
        msge = await ctx.send(embed=embed)
        await ctx.send("Please wait...", delete_after=3)
        await asyncio.sleep(4)
        embed = discord.Embed(
            title="Ticket Setup",
            color=self.bot.color,
            description="Setting up ticket system..."
        )
        await msge.edit(embed=embed)
        
        await asyncio.sleep(1)
        if category is None:
            cat = await ctx.guild.create_category(
            name="Tickets",
            reason=f"Action done by {ctx.author} (ID: {ctx.author.id})",
        )
            embed.description = f"Category created {cat.mention}\n"
            await msge.edit(embed=embed)
        await asyncio.sleep(1)

        if role is None:
            role = await ctx.guild.create_role(
                name="Ticket Support",
                reason=f"Action done by {ctx.author} (ID: {ctx.author.id})",
            )
            embed.description += f"Role created {role.mention}\n"
            await msge.edit(embed=embed)
        
        await asyncio.sleep(1)
        chan = await ctx.guild.create_text_channel(
            name="create-ticket",
            category=cat,
            reason=f"Action done by {ctx.author} (ID: {ctx.author.id})",
        )
        embed.description += f"Channel created {chan.mention}\n"
        await msge.edit(embed=embed)

        await asyncio.sleep(1)
        embed.description += "Updating permissions...\n"
        await msge.edit(embed=embed)

        await role.edit(mentionable=True, reason=f"Action done by {ctx.author} (ID: {ctx.author.id})")
        await chan.set_permissions(
            ctx.guild.default_role,
            send_messages=False,
            reason=f"Action done by {ctx.author} (ID: {ctx.author.id})",
        )
        
        await chan.send(
            embed=discord.Embed(
                title="Ticket System",
                description=(
                    "Press the button  message to create a ticket\n"
                    "Dont create ticket for fun\n"
                    "If you create ticket for fun, you will get banned\n"
                ),
                color=self.bot.color
            ),
            view=TicketCreate(bot=self.bot)
        )
        embed.description += "Permissions updated\n"
        await msge.edit(embed=embed)

        await asyncio.sleep(1)
        
        async with self.bot.db.cursor() as cur:
            await cur.execute(
                "INSERT INTO tickets (ticket_guild_id, ticket_category_id, ticket_channel_id, ticket_ping_role_id) VALUES (?, ?, ?, ?)",
                (
                    ctx.guild.id,
                    cat.id,
                    chan.id,
                    role.id,
                ),
            )
            await self.bot.db.commit()

        embed.description += "Setup complete\n"
        await msge.edit(embed=embed)
        await asyncio.sleep(1)
        embed.description = (
            f"Category: {cat.mention}\n"
            f"Channel: {chan.mention}\n"
            f"Role: {role.mention}\n"
        )
        await msge.edit(embed=embed)

    @ticket_setup.command(name="delete", aliases=["del"])
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @app_commands.guild_only()
    async def ticket_setup_delete(self, ctx: Context):
        """
        Deletes ticket system in the server
        """

        async with self.bot.db.cursor() as cur:
            await cur.execute(
                "SELECT * FROM tickets WHERE ticket_guild_id = ?", (ctx.guild.id,)
            )
            data = await cur.fetchone()

        if data is None:
            return await ctx.send("Ticket system is not setup in this server")
        
        confirm = await ctx.confirm("Are you sure you want to delete ticket system.", author_id=ctx.author.id)
        if not confirm:
            return await ctx.send("Aborting.")
        
        x = await ctx.send("Please wait")

        async with self.bot.db.cursor() as cur:
            await cur.execute(
                "SELECT * FROM tickets WHERE ticket_guild_id = ?", (ctx.guild.id,)
            )
            data = await cur.fetchone()

        cat = ctx.guild.get_channel(data[1])
        chan = ctx.guild.get_channel(data[2])
        role = ctx.guild.get_role(data[3])

        await x.edit(content="Deleting ticket system...")

        await chan.delete(reason=f"Action done by {ctx.author} (ID: {ctx.author.id})")
        await x.edit(content=f"`{chan.name}` deleted")
        await asyncio.sleep(1
                            )
        await cat.delete(reason=f"Action done by {ctx.author} (ID: {ctx.author.id})")
        await x.edit(content=f"`{cat.name}` deleted")
        await asyncio.sleep(1)

        await role.delete(reason=f"Action done by {ctx.author} (ID: {ctx.author.id})")
        await x.edit(content=f"`{role.name}` deleted")
        await asyncio.sleep(1)

        await x.edit(content="Ticket system deleted")
        
        async with self.bot.db.cursor() as cur:
            await cur.execute(
                "DELETE FROM tickets WHERE ticket_guild_id = ?", (ctx.guild.id,)
            )
            await self.bot.db.commit()

    @ticket.group(name="pingrole")
    async def ticket_pingrole(self, ctx: Context):
        """
        Commands for ticket pingrole

        Do `r.help ticket pingrole` for more information
        """
        await ctx.send_help(ctx.command.parent)

    @ticket_pingrole.command(name="add")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @app_commands.guild_only()
    async def add_pingrole(self, ctx: Context):
        async with self.bot.db.cursor() as cur:
            await cur.execute(
                "SELECT * FROM tickets WHERE ticket_guild_id = ?", (ctx.guild.id,)
            )
            data = await cur.fetchone()

        if data is None:
            return await ctx.send("Ticket system is not setup in this server")
        
        embed = discord.Embed(
            title="Ticket Pingrole Setup",
            color=self.bot.color
            )
        view=PingRoleSelect(bot=self.bot)
        view.message = await ctx.send(embed=embed, view=view)