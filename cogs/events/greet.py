import aiohttp
import discord
from discord.ext import commands, tasks

from core import Robo

class Greeting(commands.Cog):
    def __init__(self, bot: Robo):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        chans =  [1201558985942237225]
        for chan in chans:
            ch = await self.bot.fetch_channel(chan)
            if ch.guild == member.guild:
                rules = discord.utils.find(
                    lambda channel: channel.name == "rules-and-info" or "rules",
                    member.guild.text_channels
                )
                updates = discord.utils.find(
                    lambda channel: channel.name == "updates",
                    member.guild.text_channels
                ) 
                embed = discord.Embed(
                    title=f"Welcome to {member.guild.name}",
                    color=member.accent_color)
                embed.description = ""
                if rules is not None:
                    embed.description += f"Read rules {rules.mentions}\n"
                if updates is not None:
                    embed.description += f"Get updates {updates.mentions}\n"

                embed.set_footer(icon_url=self.bot.user.display_avatar.url, text=f"You are #{member.guild.member_count}")
                embed.set_thumbnail(url=member.display_avatar.url)
                await ch.send(embed=embed)

                
