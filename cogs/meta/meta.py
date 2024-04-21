import ast
import json
import os
import platform
import sys
import unicodedata
from datetime import datetime, timezone
from typing import Union
import aiohttp
import discord
import psutil
from discord.ext import commands
import time
from core import Robo
from utils.context import Context
from utils.paginator import SimplePages
from utils.formats import truncate_string
from discord import app_commands
import config

class Meta(commands.Cog):
    """
    Commands that shows information about the bot."""
    def __init__(self, bot: Robo) -> None:
        self.bot = bot
        self.github_headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {config.git_token}"
    }

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(
            id=1122432155256094770,
            name="Bot3"
        )
    
    async def dblatency(self):
        async with self.bot.db.cursor() as cur:
            t1 = time.perf_counter()
            await cur.execute("SELECT * FROM tickets")
            t2 = time.perf_counter()
            return round((t2-t1)*1000+2)
        

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
        )
        embed.description = (
            f"**API Latency:** {round(self.bot.latency * 1000)}ms\n"
            f"**DB Latency:** {await self.dblatency()}ms"
            )
        await ctx.reply(embed=embed)

    async def get_latest_change(self):
        async with aiohttp.ClientSession(headers=self.bot.config.github_headers) as session:
            async with session.get(f"https://api.github.com/repos/0xhimangshu/Robo/commits?per_page=3") as r:
                data = await r.json()
                c = []
                for i in range(3):
                    c.append((data[i]['sha'], data[i]['commit']['message'], data[i]['commit']['author']['name'], data[i]['commit']['author']['date'], data[i]['html_url']))
                return c
            
    async def _commits(self):
        commits = await self.get_latest_change()
        xx = ""
        for commit in commits:
            try:
                commit_date = datetime.fromisoformat(commit[3])
            except ValueError as e:
                print(f"Error parsing date {commit[3]}: {e}")
                continue

            try:
                # Convert to IST timezone
                commit_date_ist = commit_date.astimezone(self.bot.config.ist)
            except Exception as e:
                print(f"Error converting timezone: {e}")
                continue

            try:
                # Convert datetime to timestamp and round it
                timestamp = round(commit_date_ist.timestamp())
            except Exception as e:
                print(f"Error converting datetime to timestamp: {e}")
                continue

            xx += (
                f"[{truncate_string(commit[0], max_length=6, suffix='')}]({commit[4]}) "
                f"- `{commit[1]}` by [{commit[2]}](https://github.com/{commit[2]}) "
                f"<t:{timestamp}:R>\n"
            )

        return xx

    @commands.hybrid_command()
    async def stats(self, ctx: Context):
        """Get the bot's stats."""
        with open("data/stats.json", "r") as f:
            data = json.load(f)

        mem = round(psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2)
        tmem = round(psutil.virtual_memory().total / 1024 / 1024)
        dblatency = await self.dblatency()

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

        embed = discord.Embed(title=f"{self.bot.user.name}", color=self.bot.color)
        embed.description = (
            f"**Latest Changes**\n"
            f"{await self._commits()}"
            "\n"
            f"**__Bot Stats__**\n"
            f"**Uptime:** {uptime}\n"
            f"**Commands Ran:** {commands_ran}\n"
            f"**Messages Seen:** {messages_seen}, {cachedmsg} cached\n"
            f"**Guilds:** {guilds}\n"
            f"**Users:** {users}\n"
            f"**Shards:** {shards}\n"
            f"**Shard ID:** {shard_id}\n"
            f"**Latency:** {latency}ms\n"
            f"**DB Latency:** {dblatency}ms\n"
            f"**Memory:** {mem}MB/{tmem}MB\n"
            f"**Commands:** {commands}\n"
            f"**Cogs:** {cogs}\n"
            f"**Python Version:** {pyversion}\n"
            f"**Discord.py Version:** {dpyversion}\n"
        )
        x = await self.bot.fetch_user(self.bot.owner_ids[0])
        embed.set_footer(text=f"Made by {x.name}", icon_url=x.display_avatar.url)
        await ctx.send(embed=embed)

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

    @commands.hybrid_group(name="github")
    async def github(self, ctx: Context):
        """Commands related to the bot's GitHub repository."""
        await ctx.send_help(ctx.command)

    async def get_user_repos(self, user: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.github.com/users/{user}/repos") as r:
                data = await r.json()
                return data
            
    async def get_repo(self, user: str, repo: str):
        async with aiohttp.ClientSession(headers=self.github_headers) as session:
            async with session.get(f"https://api.github.com/repos/{user}/{repo}") as r:
                data = await r.json()
                return data
            
    async def get_user(self, user: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.github.com/users/{user}") as r:
                data = await r.json()
                return data
            

    @github.command(name="repo")
    async def github_repo(self, ctx: Context, user: str, repo: str):
        try:
            data = await self.get_repo(user, repo)
            if data is None:
                return await ctx.send("Repository not found.")
            embed = discord.Embed(
                color=self.bot.color,
                title=data['full_name'],
                url=data['html_url'],
                description=data['description']
            )
            embed.set_thumbnail(url=data['owner']['avatar_url'])
            embed.add_field(name="Language", value=data['language'])
            embed.add_field(name="Stars", value=data['stargazers_count'])
            embed.add_field(name="Forks", value=data['forks_count'])
            embed.add_field(name="Is Fork", value=data['fork'])
            embed.add_field(name="Watchers", value=data['watchers_count'])
            embed.add_field(name="Open Issues", value=data['open_issues_count'])
            embed.add_field(name="License", value=data['license']['name'] if data['license'] else "None")
            embed.add_field(name="Created", value=f"<t:{int(datetime.fromisoformat(data['created_at'][:-1]).replace(tzinfo=timezone.utc).timestamp())}:R>")
            embed.add_field(name="Last Updated", value=f"<t:{int(datetime.fromisoformat(data['updated_at'][:-1]).replace(tzinfo=timezone.utc).timestamp())}:R>")

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"```{e}```")

    @github.command(name="user")
    async def github_user(self, ctx: Context, user: str):
        """Get information about a GitHub user."""
        try:
            data = await self.get_user(user)
            if data is None:
                return await ctx.send("User not found.")
            embed = discord.Embed(
                color=self.bot.color,
                title=data['login'],
                url=data['html_url'],
                description=data['bio']
            )
            embed.set_thumbnail(url=data['avatar_url'])
            embed.add_field(name="Name", value=data['name'])
            embed.add_field(name="Company", value=data['company'])
            embed.add_field(name="Location", value=data['location'])
            embed.add_field(name="Twitter", value=data['twitter_username'])
            embed.add_field(name="Website", value=data['blog'])
            embed.add_field(name="Followers", value=data['followers'])
            embed.add_field(name="Following", value=data['following'])
            embed.add_field(name="Public Repos", value=data['public_repos'])
            embed.add_field(name="Public Gists", value=data['public_gists'])
            embed.add_field(name="Created", value=f"<t:{int(datetime.fromisoformat(data['created_at'][:-1]).replace(tzinfo=timezone.utc).timestamp())}:R>")
            embed.add_field(name="Last Updated", value=f"<t:{int(datetime.fromisoformat(data['updated_at'][:-1]).replace(tzinfo=timezone.utc).timestamp())}:R>")

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"```{e}```")

    @github.command(name="repos")
    async def github_repos(self, ctx: Context, user: str):
        """Get a list of GitHub repositories for a user."""
        try:
            data = await self.get_user_repos(user)
            if data is None:
                return await ctx.send("User not found.")
            embed = discord.Embed(
                color=self.bot.color,
                title=f"Repositories for {user}",
                description="\n".join([f"[{repo['name']}]({repo['html_url']})" for repo in data])
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"```{e}```")

    @commands.hybrid_group(name="prefix")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def prefix(self, ctx: Context):
        """Get the bot's prefix."""
        async with self.bot.db.cursor() as cur:
            await cur.execute("SELECT prefix FROM guilds WHERE id = ?", (ctx.guild.id,))
            prefix = await cur.fetchone()
            prefix = prefix[0]
        await ctx.send(f"My prefix is `{prefix}`")

    @prefix.command(name="set")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def prefix_set(self, ctx: Context, prefix: str):
        """Set the bot's prefix."""
        async with self.bot.db.cursor() as cur:
            await cur.execute("SELECT prefix FROM guilds WHERE id = ?", (ctx.guild.id,))
            data = await cur.fetchone()
            if data is None:
                await cur.execute("INSERT INTO guilds VALUES (?, ?)", (ctx.guild.id, prefix))
            await cur.execute("UPDATE guilds SET prefix = ? WHERE id = ?", (prefix, ctx.guild.id))
        await self.bot.db.commit()
        await ctx.send(f"Prefix set to `{prefix}`")

    @prefix.command(name="reset")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def prefix_reset(self, ctx: Context):
        """Reset the bot's prefix."""
        async with self.bot.db.cursor() as cur:
            await cur.execute("DELETE FROM guilds WHERE id = ?", (ctx.guild.id,))
        await self.bot.db.commit()
        await ctx.send(f"Prefix reset to `{config.prefixes[0]}`")