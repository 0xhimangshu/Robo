import json
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Callable, Coroutine, List, Union, Optional

import aiohttp
import aiosqlite
import datetime
import discord
from discord.ext import commands
import sys
import config
from utils.context import Context

from cogs.robocog import flags

flags.Flags.NO_DM_TRACEBACK = True
flags.Flags.HIDE = True
flags.Flags.NO_UNDERSCORE = True


from utils.formats import format_dt

on_startup: List[Callable[["Robo"], Coroutine]] = []

class Robo(commands.Bot):
    def __init__(
            self, 
            intents=discord.Intents.all(),
            owner_ids=config.owner_ids,
            case_insensitive=True,
            *args,
            **kwargs
        ):
        super().__init__(
            intents=intents,
            owner_ids=owner_ids,
            case_insensitive=case_insensitive,
            command_prefix=self.get_prefix,
            *args,
            **kwargs
        )
        self.owner_id = config.owner_id
        self.owner_ids = config.owner_ids
        self.uptime = None
        self.session: aiohttp.ClientSession = None
        self.color = config.color2
        self.support_invite = config.support_invite
        self.ram_usage = None
        self.setup_logging()
        self.config = config
        self.MAINTENANCE = False
        self.db = None

    async def setup_hook(self) -> None:
        self.uptime = datetime.datetime.now()
        self.session = aiohttp.ClientSession()
        self.db = await aiosqlite.connect("data/robo.db")
        for coro_func in on_startup:
            self.loop.create_task(coro_func(self))

    async def get_prefix(self, message: discord.Message):
        async with self.db.cursor() as cursor:
            await cursor.execute("SELECT * FROM no_prefix")
            np = await cursor.fetchall()
            await cursor.execute("SELECT * FROM guilds WHERE id = ?", (message.guild.id,))
            p = await cursor.fetchone()

        np_ids = [row[0] for row in np]

        if p is None:
            if message.author.id in np_ids:
                extra = [p for p in config.prefixes]
                extra.append("")
                return commands.when_mentioned_or(*extra)(self, message)
            else:
                return commands.when_mentioned_or(*config.prefixes)(self, message)
        else:
            if message.author.id in np_ids:
                extra = [p for p in config.prefixes]
                extra.append(p[1])
                extra.append("")
                return commands.when_mentioned_or(*extra)(self, message)
            else:
                return commands.when_mentioned_or(*config.prefixes, p[1])(self, message)


    @on_startup.append
    async def load_extensions(self):
        # await self.load_extension("cogs.robo")
        # self.logger.info("Loaded cogs.Robo ")
        
        for cog in os.listdir("cogs"): 
            # await self.load_extension(f"cogs.{cog}")
            try:
                await self.load_extension(f"cogs.{cog}")
            except Exception as e:
                self.logger.error(f"Error while loading {cog}: {e.args[0]} {e.with_traceback(e.__traceback__)}")
            else:   
                self.logger.info(f"Loaded {cog}")
        
        synced = await self.tree.sync()
        self.logger.info(f"Synced {len(synced)} global commands")

    async def get_context(self, origin: Union[discord.Interaction, discord.Message], /, *, cls=Context) -> Context:
        return await super().get_context(origin, cls=cls)

    async def process_commands(self, message: discord.Message):
        if message.content and message.guild is not None:
            ctx = await self.get_context(message)
            if ctx.command is None:
                if ctx.message.content.startswith(tuple("")):
                    return
                elif ctx.message.content.startswith(tuple(config.prefixes)):
                    return await ctx.error(f"`{ctx.clean_prefix}{ctx.invoked_with}` is not a valid command.")
            else:
                if self.MAINTENANCE and message.author.id != self.owner_id:
                    return await message.channel.send("Bot is in maintenance mode. Please try again later.")
                await self.invoke(ctx)
            try:
                with open("data/stats.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
            
                with open("data/stats.json", "w", encoding="utf-8") as f:
                    data["commands_ran"] += 1
                
                    json.dump(data, f, indent=4)
            except json.JSONDecodeError:
                pass

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        try:
            with open("data/stats.json", "r", encoding="utf-8") as f:
                data = json.load(f)

            with open("data/stats.json", "w", encoding="utf-8") as f:
                data["messages_seen"] += 1
            
                json.dump(data, f, indent=4)
        except json.JSONDecodeError:
            pass

        if message.content == self.user.mention:
            embed = discord.Embed(
                title=f"Hey {message.author}, I'm {self.user.name}!",
                description=(
                    f"> My prefixes are `{'`, `'.join(config.prefixes)}` Type `{config.prefixes[0]}help` for more information\n"
                    f"> I've been running since {format_dt(self.user.created_at, 'F')}\n"
                    f"> I don't have a lot of commands, but I'm still being worked on!\n"
                    f"> If you have any suggestions, join the [support server]({config.support_invite}) and post them there!"
                ),
                color=self.color
            )
            embed.set_footer(text=f"Made with discord.py 🐍 and v{discord.__version__} by {self.get_user(self.owner_id).name}")
            await message.channel.send(embed=embed)
            return
        await self.process_commands(message)

    # @on_startup.append
    # async def emojigg(self):
    #     async with self.session.get("https://emoji.gg/api/") as resp:
    #         data = await resp.json()
    #         with open("data/emoji.json", "w", encoding="utf-8") as f:
    #             json.dump(data, f, indent=4)

    def setup_logging(self):
        self.logger = logging.getLogger("Robo")
        self.logger.setLevel(logging.INFO)  

        dt_fmt = '%Y-%m-%d %H:%M:%S'
        formatter = logging.Formatter('{asctime} {levelname:<8} {name} {message}', dt_fmt, style='{')

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(stream_handler)

        file_handler = RotatingFileHandler(filename='robo.log', mode="a", maxBytes=1024 * 1024 * 5, backupCount=5)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def boot(self):
        self.logger.info("Booting up...")
        super().run(config.token)

        try:
            with open("data/stats.json", "r", encoding="utf-8") as f:
                data = json.load(f)

            with open("data/stats.json", "w", encoding="utf-8") as f:
                data["booted"] += 1
                json.dump(data, f, indent=4)
        except json.JSONDecodeError:
            pass

        if KeyboardInterrupt:
            os._exit(0)
            

    def clearshell(self):
        os.system("cls" if os.name == "nt" else "clear")

    def reboot(self):
        with open("data/stats.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        data["boot_m"]["sent"] = False
        
        with open("data/stats.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        loop = self.loop
        loop.create_task(self.close())
        loop.stop()
        
        self.clearshell()
        os.execv(sys.executable, ["python"] + sys.argv)

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
