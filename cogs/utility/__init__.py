from .utility import Utility
from core import Robo

async def setup(bot: Robo):
    await bot.add_cog(Utility(bot))