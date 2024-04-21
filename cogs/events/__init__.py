from core import Robo

from .error import EventError
from .guild import EventGuild
from .ready import EvnetReady
from .greet import Greeting


async def setup(bot: Robo):
    await bot.add_cog(EventError(bot))
    await bot.add_cog(EvnetReady(bot))
    await bot.add_cog(EventGuild(bot))
    await bot.add_cog(Greeting(bot))