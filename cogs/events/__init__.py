from core import Robo

from .error import EventError
from .guild import EventGuild
from .message import EventMessage
from .ready import EvnetReady


async def setup(bot: Robo):
    await bot.add_cog(EventError(bot))
    await bot.add_cog(EvnetReady(bot))
    await bot.add_cog(EventMessage(bot))
    await bot.add_cog(EventGuild(bot))
