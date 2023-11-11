import discord
import aiohttp
from discord.ext import commands
import config
from typing import Optional
import aiohttp

async def send_webhook2(
        msg: str,
        ):
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(
            url=config.webhook1,
            session=session,
        )
        await webhook.send(msg)
       
async def send_webhook1(
        bot: commands.Bot,
        title: str,
        description: str,
        username: str,
        author: Optional[str]=None,
        url: Optional[str]=None,
):
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(
            url=config.webhook2,
            session=session,
        )
        embed=discord.Embed(
                description=description,
                color=config.color,
            )
        if title:
            embed.title = title
        if author and url:
            embed.set_author(name=author, url=url)
        embed.set_footer(text=f"Robo 147 logs")
        embed.timestamp = discord.utils.utcnow()
        await webhook.send(
            embed=embed,
            username=username,
            avatar_url=bot.user.display_avatar.url
        )