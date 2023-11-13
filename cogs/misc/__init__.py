from .misc import Misc
from core import Robo   

async def setup(bot: Robo):
    await bot.add_cog(Misc(bot))
    