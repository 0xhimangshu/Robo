from utils.webhook import send_webhook1
from discord.ext import commands
from core import Robo
import discord

class EventGuild(commands.Cog):
    def __init__(self, bot: Robo):
        self.bot = bot

    @commands.Cog.listener("on_guild_join")
    async def on_robo_guild_join(self, guild: discord.Guild):
        try:
            url = await guild.text_channels[0].create_invite()
        except discord.errors.Forbidden:
            url = None

        await send_webhook1(
            bot=self.bot,
            author=guild.name,
            url=url,
            description=(
                f"**Name:** {guild.name}\n"
                f"**ID:** {guild.id}\n"
                f"**Owner:** {guild.owner}\n"
                f"**Members:** {guild.member_count}\n"
                f"**Created at:** {guild.created_at}"
            ),
            username="Robo 147",
        )

    @commands.Cog.listener("on_guild_remove")
    async def on_robo_guild_remove(self, guild: discord.Guild):
        try:
            url = await guild.text_channels[0].create_invite()
        except discord.errors.Forbidden:
            url = None
        await send_webhook1(
            bot=self.bot,
            author=guild.name,
            url=url,
            description=(
                f"**Name:** {guild.name}\n"
                f"**ID:** {guild.id}\n"
                f"**Owner:** {guild.owner}\n"
                f"**Members:** {guild.member_count}\n"
                f"**Created at:** {guild.created_at}"
            ),
            username="Robo 147",
        )