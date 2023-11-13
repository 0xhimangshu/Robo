from .mod import Mod
from core import Robo

async def setup(bot: Robo):
    await bot.add_cog(Mod(bot))