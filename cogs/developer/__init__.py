from .developer import Developer
from core import Robo

async def setup(bot: Robo):
    await bot.add_cog(Developer(bot))