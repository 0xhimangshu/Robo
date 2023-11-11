from __future__ import annotations
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from utils import Context

# This is because Discord is stupid with Slash Commands and doesn't actually have integer types.
# So to accept snowflake inputs you need a string and then convert it into an integer.
class Snowflake:
    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> int:
        try:
            return int(argument)
        except ValueError:
            param = ctx.current_parameter
            if param:
                raise commands.BadArgument(f'{param.name} argument expected a Discord ID not {argument!r}')
            raise commands.BadArgument(f'expected a Discord ID not {argument!r}')
        
class ColorConverter(commands.Converter):
    async def convert(self, ctx: Context, argument: str) -> discord.Color:
        if argument.startswith("#"):
            argument = argument[1:]
        try:
            return discord.Color(int(argument, base=16))
        except ValueError:
            raise commands.BadArgument("Invalid color.")
        
class RoleConverter(commands.Converter):
    async def convert(self, ctx: Context, argument: str) -> discord.Role:
        try:
            return await commands.RoleConverter().convert(ctx, argument)
        except commands.BadArgument:
            raise commands.BadArgument("Invalid role.")
        
class MemberConverter(commands.Converter):
    async def convert(self, ctx: Context, argument: str) -> discord.Member:
        try:
            return await commands.MemberConverter().convert(ctx, argument)
        except commands.BadArgument:
            raise commands.BadArgument("Invalid member.")

