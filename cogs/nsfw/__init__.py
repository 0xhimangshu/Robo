from .nsfw import NSFW
from core import Robo

async def setup(bot: Robo):
    await bot.add_cog(NSFW(bot))