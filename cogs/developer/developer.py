import asyncio
import json
import os
from typing import Optional

import discord
from discord.ext import commands

import config
from core import Robo
from utils.context import Context
from utils.converter import MemberConverter


class Developer(commands.Cog):
    def __init__(self, bot: Robo):
        self.bot = bot

    # @commands.command(hidden=True)
    # @commands.is_owner()
    # async def reload(self, ctx: Context, *, cog: str):
    #     """Reloads a cog"""
    #     if cog == "~":
    #         for cog in config.extensions:
    #             try:
    #                 await self.bot.reload_extension("cogs."+cog)
    #             except Exception as e:
    #                 if isinstance(e, discord.ext.commands.errors.ExtensionNotLoaded):
    #                     try:
    #                         await self.bot.load_extension("cogs."+cog)
    #                     except Exception as e:
    #                         return await ctx.error(f'Failed to load cog `{cog}`: `{e}`')
    #                     else:
    #                         await ctx.send(f'Loaded cog `{cog}`')
    #                         continue
    #             else:
    #                 await ctx.send(f'Reloaded cog `{cog}`')
    #     else:
    #         try:
    #             await self.bot.unload_extension("cogs."+cog)
    #             await self.bot.load_extension("cogs."+cog)
    #         except Exception as e:
    #             return await ctx.error(f'Failed to reload cog `{cog}`: `{e}`')
    #         else:
    #             await ctx.send(f'Reloaded cog `{cog}`')


    # @commands.command(hidden=True)
    # @commands.is_owner()
    # async def load(self, ctx: Context, *, cog: str):
    #     """Loads a cog"""
    #     if cog == "all":
    #         for cog in config.extensions:
    #             try:
    #                 await self.bot.load_extension("cogs."+cog)
    #             except Exception as e:
    #                 return await ctx.error(f'Failed to reload cog `{cog}`: `{e}`')
    #             else:
    #                 await ctx.send(f'Reloaded cog `{cog}`')
    #     else:
    #         try:
    #             await self.bot.load_extension("cogs."+cog)
    #         except Exception as e:
    #             return await ctx.error(f'Failed to load cog `{cog}`: `{e}`')
    #         else:
    #             await ctx.send(f'Loaded cog `{cog}`')

    # @commands.command(hidden=True)
    # @commands.is_owner()
    # async def sync(self, ctx: Context, scope:Optional[str]) -> None:
    #     if scope == "global":
    #         await ctx.send("Synchronizing. It may take more then 30 sec", delete_after=15)
    #         synced=await ctx.bot.tree.sync()
    #         await asyncio.sleep(5)
    #         await ctx.send(f"{len(synced)} Slash commands have been globally synchronized.")
    #         return
    #     elif scope == "guild":
    #         await ctx.send("Synchronizing. It may take more then 30 sec", delete_after=15)
    #         ctx.bot.tree.copy_global_to(guild=ctx.guild)
    #         synced = await ctx.bot.tree.sync(guild=ctx.guild)
    #         await asyncio.sleep(5)
    #         await ctx.send(f"{len(synced)} Slash commands have been synchronized in this guild.", delete_after=5)
    #         return
    #     await ctx.send("The scope must be `global` or `guild`.", delete_after=5)

    # @commands.command(hidden=True)
    # @commands.is_owner()
    # async def unsync(self, ctx: Context, scope:Optional[str]) -> None:
    #     if scope == "global":
    #         await ctx.send("Unsynchronizing...", delete_after=5)
    #         ctx.bot.tree.clear_commands(guild=None)
    #         return
    #     elif scope == "guild":
    #         await ctx.send("Unsynchronizing...", delete_after=5)
    #         ctx.bot.tree.clear_commands(guild=ctx.guild)
    #         return
    #     await ctx.send("The scope must be `global` or `guild`.", delete_after=5)


    @commands.group(hidden=True, name="np")
    @commands.is_owner()
    async def no_prefix(self, ctx: Context):
        """No prefix commands"""
        ...

    @no_prefix.command(name="add", hidden=True)
    async def no_prefix_add(self, ctx: Context, *, user: MemberConverter):
        """Removes the prefix for a guild"""
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("SELECT * FROM no_prefix WHERE user_id=?", (user.id,))
            if await cursor.fetchone() is not None:
                return await ctx.error("Already in noprefix mode.")
            
            await cursor.execute("INSERT INTO no_prefix VALUES (?)", (user.id,))
            await self.bot.db.commit()

        await ctx.send(f"Added {user.mention} to noprefix mode.")

    @no_prefix.command(name="remove", hidden=True, aliases=["del", "rem"])
    async def no_prefix_remove(self, ctx: Context, *, user: MemberConverter):
        """Removes the prefix for a guild"""
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("SELECT * FROM no_prefix WHERE user_id=?", (user.id,))
            if await cursor.fetchone() is None:
                return await ctx.error("Not in noprefix mode.")
            
            await cursor.execute("DELETE FROM no_prefix WHERE user_id=?", (user.id,))
            await self.bot.db.commit()

        await ctx.send(f"Removed {user.mention} from noprefix mode.")

    @no_prefix.command(name="list", hidden=True)
    async def no_prefix_list(self, ctx: Context):
        """Removes the prefix for a guild"""
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("SELECT * FROM no_prefix")
            data = await cursor.fetchall()

        if not data:
            return await ctx.error("No one is in noprefix mode.")
        
        ids = []
        for row in data:
            ids.append(row[0])

        users = []
        for id in ids:
            users.append(self.bot.get_user(id))

        await ctx.send(f"Users in noprefix mode: {', '.join([user.name for user in users])}")
        

    @commands.command(hidden=True)
    @commands.is_owner()
    async def reboot(self, ctx: Context):
        """Reboots the bot"""
        with open("data/stats.json", "r") as f:
            data = json.load(f)

        data["boot_m"]["sent"] = "false"
        data["boot_m"]["id"] = ctx.channel.id

        with open("data/stats.json", "w") as f:
            json.dump(data, f, indent=4)

        await ctx.send("Rebooting...")
        if os.name == "nt":
            await self.bot.reboot()
        if os.name == "posix":
            os.system("pm2 restart robo")
        else:
            await ctx.send("Reboot failed.")

