import discord
from discord.ext import commands
from discord.ext.commands.context import Context
from core import Robo
from utils.context import Context

class NSFW(commands.Cog):
    def __init__(self, bot: Robo):
        self.bot = bot

    async def get_image(
            self,
            endpoint: str,
    ):
        async with self.bot.session.get(
                f"https://purrbot.site/api/{endpoint}"
        ) as resp:
            print(f"https://purrbot.site/api/{endpoint}")
            data = await resp.json()
            return data["link"]
        
        
    @commands.hybrid_group()
    async def nsfw(self, ctx: Context):
        """NSFW Commands"""
        pass
        
    @nsfw.command(aliases=["pussylick", "psl"])
    @commands.is_nsfw()
    async def pussy(self, ctx: Context):
        """Get a random pussy image"""
        await ctx.send(
            embed=discord.Embed(
                color=self.bot.color,
                timestamp=ctx.message.created_at,
            ).set_image(url=await self.get_image("img/nsfw/pussyLick/gif"))
        )

    @nsfw.command(aliases=["a", "an"])
    @commands.is_nsfw()
    async def anal(self, ctx: Context):
        """Get a random anal image"""
        await ctx.send(
            embed=discord.Embed(
                color=self.bot.color,
                timestamp=ctx.message.created_at,
            ).set_image(url=await self.get_image("img/nsfw/anal/gif"))
        )
    
    @nsfw.command(aliaess=["cum"])
    @commands.is_nsfw()
    async def blowjob(self, ctx: Context):
        """Get some random blowjob images"""
        await ctx.send(
            embed = discord.Embed(
                color=self.bot.color,
                timestamp=ctx.message.created_at,
            ).set_image(url=await self.get_image("img/nsfw/blowjob/gif"))
        )
    
    @nsfw.command()
    @commands.is_nsfw()
    async def fuck(self, ctx: Context):
        """
        Get some random fuck images
        """
        await ctx.send(
            embed = discord.Embed(
                color=self.bot.color,
                timestamp=ctx.message.created_at,
            ).set_image(url=await self.get_image("img/nsfw/fuck/gif"))
        )

    @nsfw.group()
    @commands.is_nsfw()
    async def threesome(self, ctx: Context):
        """
        Get some thresome images
        """
        await ctx.send(ctx.command)

    @threesome.command()
    @commands.is_nsfw()
    async def fff(self, ctx: Context):
        await ctx.send(
            embed = discord.Embed(
                color=self.bot.color,
                timestamp=ctx.message.created_at,
            ).set_image(url=await self.get_image("/img/nsfw/threesome_fff/gif"))
        )
    
    @threesome.command()
    @commands.is_nsfw()
    async def ffm(self, ctx: Context):
        await ctx.send(
            embed = discord.Embed(
                color=self.bot.color,
                timestamp=ctx.message.created_at,
            ).set_image(url=await self.get_image("/img/nsfw/threesome_ffm/gif"))
        )

    @threesome.command()
    @commands.is_nsfw()
    async def mmf(self, ctx: Context):
        await ctx.send(
            embed = discord.Embed(
                color=self.bot.color,
                timestamp=ctx.message.created_at,
            ).set_image(url=await self.get_image("/img/nsfw/threesome_mmf/gif"))
        )
    
    @nsfw.command()
    @commands.is_nsfw()
    async def yaoi(self, ctx: Context):
        await ctx.send(
            embed = discord.Embed(
                color=self.bot.color,
                timestamp=ctx.message.created_at,
            ).set_image(url=await self.get_image("/img/nsfw/yaoi/gif"))
        )

    @nsfw.command()
    @commands.is_nsfw()
    async def yuri(self, ctx: Context):
        await ctx.send(
            embed = discord.Embed(
                color=self.bot.color,
                timestamp=ctx.message.created_at,
            ).set_image(url=await self.get_image("/img/nsfw/yuri/gif"))
        )
        
# GET /img/nsfw/anal/gif
# GET /img/nsfw/blowjob/gif
# GET /img/nsfw/cum/gif
# GET /img/nsfw/fuck/gif
# GET /img/nsfw/neko/{type}
# GET /img/nsfw/pussylick/gif
# GET /img/nsfw/solo/gif
# GET /img/nsfw/solo_male/gif
# GET /img/nsfw/threesome_fff/gif
# GET /img/nsfw/threesome_ffm/gif
# GET /img/nsfw/threesome_mmf/gif
# GET /img/nsfw/yaoi/gif
# GET /img/nsfw/yuri/gif