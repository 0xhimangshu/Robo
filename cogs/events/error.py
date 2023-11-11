import discord
from discord.ext import commands
from core import Robo
import config
from utils.context import Context
from typing import Union


class EventError(commands.Cog):
    def __init__(self, bot: Robo):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(
        self,
        ctx: Context,
        error: Exception
    ):
        embed = discord.Embed(
            color=config.color_error,
        )
        if isinstance(error, commands.errors.MissingPermissions):
            embed.description = f"You don't have the required permissions to run this command.\nRequired permissions: {', '.join(error.missing_permissions)}"
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.BotMissingPermissions):
            embed.description = f"I don't have the required permissions to run this command.\nRequired permissions: {', '.join(error.missing_permissions)}"
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.CommandOnCooldown):
            embed.description = f"This command is on cooldown. Try again in {round(error.retry_after)} seconds."
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.NoPrivateMessage):
            embed.description = "This command can't be used in DMs."
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            embed.description = f"Missing required argument: `{error.param}`"
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.BadArgument):
            embed.description = f"Bad argument: {error.args[0]}"
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.CommandNotFound):
            embed.description = f"Command not found."
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.CheckFailure):
            embed.description = f"You don't have permission to run this command.\n ```{error}```"
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.UserNotFound):
            embed.description = f"User not found."
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.ChannelNotFound):
            embed.description = f"Channel not found.\n{error.args[0]}"
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.RoleNotFound):
            embed.description = f"Role not found.\n{error.args[0]}"
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.MemberNotFound):
            embed.description = f"Member not found.\n{error.args[0]}"
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.CommandInvokeError):
            embed.description = f"An error occured while running the command.\n{error.original}"
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.HybridCommandError):
            embed.description = f"An error occured while running the command.\n{error.original}"
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.FlagError):
            embed.description = f"An error occured while running the command.\n{error.original}"
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.NSFWChannelRequired):
            embed.description = f"This command can only be used in NSFW channels."
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.DisabledCommand):
            embed.description = f"This command is disabled."
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.ExtensionError):
            embed.description = f"An error occured while loading the extension.\n{error.original}"
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.ExtensionAlreadyLoaded):
            embed.description = f"Extension is already loaded."
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.ExtensionNotLoaded):
            embed.description = f"Extension is not loaded."
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.ExtensionNotFound):
            embed.description = f"Extension not found."
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.ExtensionFailed):
            embed.description = f"An error occured while loading the extension.\n{error.original}"
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.MaxConcurrencyReached):
            embed.description = f"Max concurrency reached."
            await ctx.send(embed=embed)
            return
        elif isinstance(error, commands.errors.NotOwner):
            embed.description = f"You are not the owner of this bot.\nContact {ctx.bot.get_user(ctx.bot.owner_id).mention} for support."
            await ctx.send(embed=embed)
            return
        else:
            embed.description = f"An unknown error occured.\n```py\n{error}```"
            await ctx.send(embed=embed)
            return