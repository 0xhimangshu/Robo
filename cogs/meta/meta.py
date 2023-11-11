import ast
import json
import os
import platform
import sys
import unicodedata
from datetime import datetime, timezone
from typing import Union

import discord
import psutil
from discord.ext import commands
import time
from core import Robo
from utils.context import Context
from utils.page import SimplePages


class Meta(commands.Cog):
    """
    Commands that shows information about the bot."""
    def __init__(self, bot: Robo) -> None:
        self.bot = bot

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(
            id=1122432155256094770,
            name="Bot3"
        )

    def count_classes_in_file(self, file_path):
        with open(file_path, 'r', errors='ignore') as file:
            tree = ast.parse(file.read())
            classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            return len(classes)

    def count_classes_in_directory(self):
        total_classes = 0

        for dirpath, _, filenames in os.walk("./"):
            for filename in filenames:
                if filename.endswith('.py'):  # Process Python files only
                    file_path = os.path.join(dirpath, filename)
                    total_classes += self.count_classes_in_file(file_path)

        return total_classes

    def count_lines_in_file(self, file_path):
        with open(file_path, 'r', errors='ignore') as file:
            lines = len(file.readlines())
            return lines

    def count_lines_in_directory(self):
        total_lines = 0

        for dirpath, _, filenames in os.walk("./"):
            for filename in filenames:
                if filename.endswith('.py'):  # Process Python files only
                    file_path = os.path.join(dirpath, filename)
                    total_lines += self.count_lines_in_file(file_path)

        return total_lines
    
    def count_functions_in_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            try:
                tree = ast.parse(content)
            except UnicodeDecodeError:
                content = content.encode('utf-8', 'ignore').decode('utf-8')
                tree = ast.parse(content)
            
            non_async_functions = len([node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)])
            async_functions = len([node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)])

            return non_async_functions, async_functions

    def count_functions_in_directory(self):
        total_non_async_functions = 0
        total_async_functions = 0

        for dirpath, _, filenames in os.walk("./"):
            for filename in filenames:
                if filename.endswith('.py'):  # Process Python files only
                    file_path = os.path.join(dirpath, filename)
                    non_async, async_func = self.count_functions_in_file(file_path)
                    total_non_async_functions += non_async
                    total_async_functions += async_func
                    total_func  = total_non_async_functions + total_async_functions

        return total_non_async_functions, total_async_functions, total_func

    @commands.hybrid_command(name="ping")
    async def ping(self, ctx: Context):
        """Reply with the bot's latency."""
        goodping = "https://cdn.discordapp.com/emojis/880113406915538995.webp?size=40&quality=lossless"
        idleping = "https://cdn.discordapp.com/emojis/880113405720145990.webp?size=40&quality=lossless"
        badping = "https://cdn.discordapp.com/emojis/880113405007114271.webp?size=40&quality=lossless"

        if self.bot.latency * 1000 < 100:
            icon = goodping
        elif self.bot.latency * 1000 < 250:
            icon = idleping
        else:
            icon = badping

        embed = discord.Embed(
            color=self.bot.color
        ).set_author(icon_url=icon, name=f"{round(self.bot.latency * 1000)}ms")
        await ctx.reply(embed=embed)

    async def get_latest_change(self):
        async with self.bot.session as session:
            async with session.get(f"https://api.github.com/repos/himangshu147-git/Robo/commits?per_page=1") as r:
                data = await r.json()
                sha = data[0]['sha']
                url = data[0]['html_url']
                author = data[0]['commit']['author']['name']
                message = data[0]['commit']['message']
                time = data[0]['commit']['author']['date']
                dt = datetime.fromisoformat(time[:-1])
                timestamp = dt.replace(tzinfo=timezone.utc).timestamp()
                return sha, url, message, author, timestamp
            
    async def dblatency(self):
        async with self.bot.db.cursor() as cur:
            t1 = time.perf_counter()
            await cur.execute("SELECT * FROM tickets")
            t2 = time.perf_counter()
            return round((t2-t1)*1000)
        

    @commands.hybrid_command()
    async def stats(self, ctx: Context):
        """Get the bot's stats."""
        with open("data/stats.json", "r") as f:
            data = json.load(f)

        mem = round(psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2)
        tmem = round(psutil.virtual_memory().total / 1024 / 1024)
        dblatency = await self.dblatency()

        osname = platform.system()
        osrelease = platform.release()
        osversion = platform.version()

        pyversion = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        dpyversion = discord.__version__

        uptime = discord.utils.format_dt(self.bot.uptime, "R")
        booted = data["booted"]
        commands_ran = data["commands_ran"]
        messages_seen = data["messages_seen"]

        guilds = len(self.bot.guilds)
        users = len(self.bot.users)
        cachedmsg = len(self.bot.cached_messages)

        commands = len(self.bot.commands)
        cogs = len(self.bot.cogs)

        shards = self.bot.shard_count
        shard_id = ctx.guild.shard_id
        latency = round(self.bot.latency * 1000)

        lines = self.count_lines_in_directory()
        classes = self.count_classes_in_directory()
        functions = self.count_functions_in_directory()[2]

        changes = await self.get_latest_change()
        embed = discord.Embed(title=f"{self.bot.user.name}", color=self.bot.config.color)
        embed.description = (
            f"**Latest Changes**\n"
            f"[{(changes[0][:8])}]({changes[1]}) - `{changes[2]}` - [{changes[3]}](https://github.com/{changes[3]}) - <t:{int(changes[4])}:R>\n"
            "\n"
            f"**Bot Stats**\n"
            f"**Uptime:** {uptime}\n"
            # f"**Boot Time:** {booted}\n"
            f"**Commands Ran:** {commands_ran}\n"
            f"**Messages Seen:** {messages_seen}, {cachedmsg} cached\n"
            f"**Guilds:** {guilds}\n"
            f"**Users:** {users}\n"
            f"**Shards:** {shards}\n"
            f"**Shard ID:** {shard_id}\n"
            f"**Latency:** {latency}ms\n"
            f"**DB Latency:** {dblatency}ms\n"
            f"**Memory:** {mem}MB/{tmem}MB\n"
            f"**Lines of Code:** {lines}\n"
            f"**Classes:** {classes}\n"
            f"**Functions:** {functions}\n"
            f"**Commands:** {commands}\n"
            f"**Cogs:** {cogs}\n"
            f"**Python Version:** {pyversion}\n"
            f"**Discord.py Version:** {dpyversion}\n"
            f"**OS:** {osname}\n"
            f"**OS Release:** {osrelease}\n"
            f"**OS Version:** {osversion}\n"
        )



        


    @commands.command(hidden=True)
    async def perms_list(self, ctx: Context):
        """Get a list of permissions."""
        permissions_dict = {
            "CREATE_INSTANT_INVITE": 1,
            "KICK_MEMBERS": 2,
            "BAN_MEMBERS": 4,
            "ADMINISTRATOR": 8,
            "MANAGE_CHANNELS": 16,
            "MANAGE_GUILD": 32,
            "ADD_REACTIONS": 64,
            "VIEW_AUDIT_LOG": 128,
            "PRIORITY_SPEAKER": 256,
            "STREAM": 512,
            "VIEW_CHANNEL": 1024,
            "SEND_MESSAGES": 2048,
            "SEND_TTS_MESSAGES": 4096,
            "MANAGE_MESSAGES": 8192,
            "EMBED_LINKS": 16384,
            "ATTACH_FILES": 32768,
            "READ_MESSAGE_HISTORY": 65536,
            "MENTION_EVERYONE": 131072,
            "USE_EXTERNAL_EMOJIS": 262144,
            "VIEW_GUILD_INSIGHTS": 524288,
            "CONNECT": 1048576,
            "SPEAK": 2097152,
            "MUTE_MEMBERS": 4194304,
            "DEAFEN_MEMBERS": 8388608,
            "MOVE_MEMBERS": 16777216,
            "USE_VAD": 33554432,
            "CHANGE_NICKNAME": 67108864,
            "MANAGE_NICKNAMES": 134217728,
            "MANAGE_ROLES": 268435456,
            "MANAGE_WEBHOOKs": 536870912,
            "MANAGE_GUILD_EXPRESSIONS": 1073741824,
            "USE_APPLICATION_COMMANDS": 2147483648,
            "REQUEST_TO_SPEAK": 4294967296,
            "MANAGE_EVENTS": 8589934592,
            "MANAGE_THREADS": 17179869184,
            "CREATE_PUBLIC_THREADS": 34359738368,
            "CREATE_PRIVATE_THREADS": 68719476736,
            "USE_EXTERNAL_STICKERS": 137438953472,
            "SEND_MESSAGES_IN_THREADS": 274877906944,
            "USE_EMBEDDED_ACTIVITIES": 549755813888,
            "MODERATE_MEMBERS": 1099511627776,
            "VIEW_CREATOR_MONETIZATION_ANALYTICS": 2199023255552,
            "USE_SOUNDBOARD": 4398046511104,
            "USE_EXTERNAL_SOUNDS": 8796093022208,
            "SEND_VOICE_MESSAGES": 17592186044416
        }
        entries = []
        for key, value in permissions_dict.items():
            entries.append(f"`{key}` **:** `{value}`")
        pages = SimplePages(entries=entries, ctx=ctx, per_page=5)
        pages.embed.title = "Permissions and their values"
        pages.embed.color = self.bot.color
        await pages.start()

    async def say_permissions(
        self, ctx: Context, member: discord.Member, channel: Union[discord.abc.GuildChannel, discord.Thread]
    ):
        permissions = channel.permissions_for(member)
        e = discord.Embed(colour=self.bot.color)
        avatar = member.display_avatar.with_static_format('png')
        e.set_author(name=f"Permissions for {str(member)}", url=avatar)
        perms = []
        for name, value in permissions:
            name = name.replace('_', ' ').replace('guild', 'server').title()
            if value:
                perms.append(f"<:greentick:1172524936292741131> {name}")
            else:
                perms.append(f"<:xsign:1172524698081427477> {name}")
        e.description = '\n'.join(perms)
        e.set_footer(text=f"Permissions in #{channel.name}")
        await ctx.send(embed=e)

    @commands.command()
    @commands.guild_only()
    async def permissions(
        self,
        ctx: Context,
        member: discord.Member = None,
        channel: Union[discord.abc.GuildChannel, discord.Thread] = None,
    ):
        """Shows a member's permissions in a specific channel.

        If no channel is given then it uses the current one.

        You cannot use this in private messages. If no member is given then
        the info returned will be yours.
        """
        channel = channel or ctx.channel
        if member is None:
            member = ctx.author

        await self.say_permissions(ctx, member, channel)
        
    @commands.command(aliases=["chi"])
    async def charinfo(self, ctx: Context, *, characters: str):
        """Shows you information about a number of characters.

        Only up to 25 characters at a time.
        """

        def to_string(c):
            digit = f'{ord(c):x}'
            name = unicodedata.name(c, 'Name not found.')
            return f'{c} - `\\U{digit:>08}` - [**{name}**](<http://www.fileformat.info/info/unicode/char/{digit}>)'

        msg = '\n'.join(map(to_string, characters))
        if len(msg) > 2000:
            return await ctx.send('Output too long to display.')
        
        embed = discord.Embed(
            color=self.bot.color,
            description="".join(msg)
        )

        await ctx.send(embed=embed)
