# from utils.webhook import log
from discord.ext import commands
from core import Robo
import discord
import json

class EventGuild(commands.Cog):
    def __init__(self, bot: Robo):
        self.bot = bot

    @commands.Cog.listener("on_guild_join")
    async def on_robo_guild_join(self, guild: discord.Guild):
        try:
            url = await guild.text_channels[0].create_invite()
        except discord.errors.Forbidden:
            url = None

        self.bot.logger.info(f"joined a guild {guild.name} ({guild.id}) with {guild.member_count} members. Invite: {url if url else 'None'}")

        # async with self.bot.db.cursor() as cur:
        #     await cur.execute(
        #         """"""
        #     )

    @commands.Cog.listener("on_guild_remove")
    async def on_robo_guild_remove(self, guild: discord.Guild):
        try:
            url = await guild.text_channels[0].create_invite()
        except discord.errors.Forbidden:
            url = None

        self.bot.logger.info(f"left a guild {guild.name} ({guild.id}) with {guild.member_count} members. Invite: {url if url else 'None'}")

        with open("data/guild.json", "r") as f:
            data = json.load(f)

        guild_id = str(guild.id)
        if guild_id in data["guilds"]:
            del data["guilds"][guild_id]

        with open("data/guild.json", "w") as f:
            json.dump(data, f, indent=4)

        async with self.bot.db.cursor() as cur:
            await cur.execute(
                """DELETE FROM guilds WHERE id = ?""",
                (guild.id,)
            )