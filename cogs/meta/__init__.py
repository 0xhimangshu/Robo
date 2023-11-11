from .meta import Meta
from core import Robo

async def setup(bot: Robo):
    await bot.add_cog(Meta(bot))