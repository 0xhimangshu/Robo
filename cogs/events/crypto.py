import aiohttp
import discord
from discord.ext import commands, tasks

from core import Robo

class Crypto(commands.Cog):
    def __init__(self, bot: Robo):
        self.bot = bot
        self.ltc_price = 0
        self.btc_price = 0
        self.eth_price = 0
        self.sol_price = 0
        self.doge_price = 0
        self.tron_price = 0
        self.cardano_price = 0
        self.monero_price = 0
        self.binancecoin_price = 0

        self.emoji_up = "⬆️"
        self.emoji_down = "⬇️"
        

    @tasks.loop(seconds=10)
    async def update_crypto_price(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin%2Cethereum%2Cdogecoin%2Clitecoin%2Ctron%2Csolana%2Ccardano%2Cmonero%2Cbinancecoin&vs_currencies=inr") as r:
                inr = await r.json()
            async with session.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin%2Cethereum%2Cdogecoin%2Clitecoin%2Ctron%2Csolana%2Ccardano%2Cmonero%2Cbinancecoin&vs_currencies=usd") as r:
                usd = await r.json()
            try:
                self.sol_price = inr['solana']['inr']
                self.btc_price = inr['bitcoin']['inr']
                self.eth_price = inr['ethereum']['inr']
                self.ltc_price = inr['litecoin']['inr']
                self.doge_price = inr['dogecoin']['inr']
                self.tron_price = inr['tron']['inr']
                self.cardano_price = inr['cardano']['inr']
                self.monero_price = inr['monero']['inr']
                self.binancecoin_price = inr['binancecoin']['inr']

                btc_price_emoji = self.emoji_up if self.btc_price > inr['bitcoin']['inr'] else self.emoji_down
                eth_price_emoji = self.emoji_up if self.eth_price > inr['ethereum']['inr'] else self.emoji_down
                ltc_price_emoji = self.emoji_up if self.ltc_price > inr['litecoin']['inr'] else self.emoji_down
                sol_price_emoji = self.emoji_up if self.sol_price > inr['solana']['inr'] else self.emoji_down
                doge_price_emoji = self.emoji_up if self.doge_price > inr['dogecoin']['inr'] else self.emoji_down
                tron_price_emoji = self.emoji_up if self.tron_price > inr['tron']['inr'] else self.emoji_down
                cardano_price_emoji = self.emoji_up if self.cardano_price > inr['cardano']['inr'] else self.emoji_down
                monero_price_emoji = self.emoji_up if self.monero_price > inr['monero']['inr'] else self.emoji_down
                binancecoin_price_emoji = self.emoji_up if self.binancecoin_price > inr['binancecoin']['inr'] else self.emoji_down
            except KeyError:
                pass
                
            embed = discord.Embed(
                title="Crypto Price Update",
                color=self.bot.color,
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(
                name="Bitcoin",
                value=f"> ₹ {inr['bitcoin']['inr']}\n> $ {usd['bitcoin']['usd']} {btc_price_emoji}",
            )
            embed.add_field(
                name="Ethereum",
                value=f"> ₹ {inr['ethereum']['inr']}\n> $ {usd['ethereum']['usd']} {eth_price_emoji}",
            )
            embed.add_field(
                name="Litecoin",
                value=f"> ₹ {inr['litecoin']['inr']}\n> $ {usd['litecoin']['usd']} {ltc_price_emoji}",
            )
            embed.add_field(
                name="Solana",
                value=f"> ₹ {inr['solana']['inr']}\n> $ {usd['solana']['usd']} {sol_price_emoji}",
            )
            embed.add_field(
                name="Dogecoin",
                value=f"> ₹ {inr['dogecoin']['inr']}\n> $ {usd['dogecoin']['usd']} {doge_price_emoji}",
            )
            embed.add_field(
                name="Tron",
                value=f"> ₹ {inr['tron']['inr']}\n> $ {usd['tron']['usd']} {tron_price_emoji}",
            )
            embed.add_field(
                name="Cardano",
                value=f"> ₹ {inr['cardano']['inr']}\n> $ {usd['cardano']['usd']} {cardano_price_emoji}",
            )
            embed.add_field(
                name="Monero",
                value=f"> ₹ {inr['monero']['inr']}\n> $ {usd['monero']['usd']} {monero_price_emoji}",
            )
            embed.add_field(
                name="Binance",
                value=f"> ₹ {inr['binancecoin']['inr']}\n> $ {usd['binancecoin']['usd']} {binancecoin_price_emoji}",
            )

            embed.set_footer(
                text="Last updated"
            )
            async with self.bot.db.cursor() as cur:
                await cur.execute("SELECT * FROM crypto")
                data = await cur.fetchone()
                
                if data is None:
                    return
                
                try:
                    guild = await self.bot.fetch_guild(data[0])
                    channel = await guild.fetch_channel(data[1])
                    msg = await channel.fetch_message(data[2])
                    await msg.edit(embed=embed, content=None)
                except discord.DiscordException:
                    pass

    @commands.Cog.listener()
    async def on_ready(self):
        self.update_crypto_price.start()