import aiohttp
import discord
from discord.ext import commands, tasks

from core import Robo

class Crypto(commands.Cog):
    def __init__(self, bot: Robo):
        self.bot = bot

    @tasks.loop(minutes=5)
    async def update_crypto_price(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin%2Cethereum%2Cdogecoin%2Clitecoin%2Ctron%2Csolana%2Ccardano%2Cmonero%2Cbinancecoin&vs_currencies=inr") as r:
                inr = await r.json()
            async with session.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin%2Cethereum%2Cdogecoin%2Clitecoin%2Ctron%2Csolana%2Ccardano%2Cmonero%2Cbinancecoin&vs_currencies=usd") as r:
                usd = await r.json()
                
            embed = discord.Embed(
                title="Crypto Price Update",
                color=self.bot.color,
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(
                name="Bitcoin",
                value=f"> ₹ {inr['bitcoin']['inr']}\n> $ {usd['bitcoin']['usd']}",
            )
            embed.add_field(
                name="Ethereum",
                value=f"> ₹ {inr['ethereum']['inr']}\n> $ {usd['ethereum']['usd']}",
            )
            embed.add_field(
                name="Litecoin",
                value=f"> ₹ {inr['litecoin']['inr']}\n> $ {usd['litecoin']['usd']}",
            )
            embed.add_field(
                name="Solana",
                value=f"> ₹ {inr['solana']['inr']}\n> $ {usd['solana']['usd']}",
            )
            embed.add_field(
                name="Dogecoin",
                value=f"> ₹ {inr['dogecoin']['inr']}\n> $ {usd['dogecoin']['usd']}",
            )
            embed.add_field(
                name="Tron",
                value=f"> ₹ {inr['tron']['inr']}\n> $ {usd['tron']['usd']}",
            )
            embed.add_field(
                name="Cardano",
                value=f"> ₹ {inr['cardano']['inr']}\n> $ {usd['cardano']['usd']}",
            )
            embed.add_field(
                name="Monero",
                value=f"> ₹ {inr['monero']['inr']}\n> $ {usd['monero']['usd']}",
            )
            embed.add_field(
                name="Binance",
                value=f"> ₹ {inr['binancecoin']['inr']}\n> $ {usd['binancecoin']['usd']}",
            )

            embed.set_footer(
                text="Last updated"
            )
            guild = await self.bot.fetch_guild(1165304777131966567)
            channel = await guild.fetch_channel(1173179092372299849)
            msg = await channel.fetch_message(1173179512167612477)
            await msg.edit(embed=embed)



    @commands.Cog.listener()
    async def on_ready(self):
        self.update_crypto_price.start()