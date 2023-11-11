from discord.ext import commands
from core import Robo
import discord

class TicketEvent(commands.Cog):
    def __init__(self, bot: Robo):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.TextChannel):
        ...


    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.TextChannel):
        ...
    


async def setup(bot: Robo):
    await bot.add_cog(TicketEvent(bot))