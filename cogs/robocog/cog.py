# -*- coding: utf-8 -*-

"""
RoboCog.cog
~~~~~~~~~~~~

The RoboCog debugging and diagnostics cog implementation.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import inspect
import typing

from discord.ext import commands

from .features.baseclass import Feature
from .features.filesystem import FilesystemFeature
from .features.guild import GuildFeature
from .features.invocation import InvocationFeature
from .features.management import ManagementFeature
from .features.python import PythonFeature
from .features.root_command import RootCommand
from .features.shell import ShellFeature
from .features.voice import VoiceFeature

__all__ = (
    "RoboCog",
    "STANDARD_FEATURES",
    "OPTIONAL_FEATURES",
    "setup",
)

STANDARD_FEATURES = (VoiceFeature, GuildFeature, FilesystemFeature, InvocationFeature, ShellFeature, PythonFeature, ManagementFeature, RootCommand)

OPTIONAL_FEATURES: typing.List[typing.Type[Feature]] = []

try:
    from features.youtube import YouTubeFeature
except ImportError:
    pass
else:
    OPTIONAL_FEATURES.insert(0, YouTubeFeature)


class RoboCog(*OPTIONAL_FEATURES, *STANDARD_FEATURES):  # type: ignore  # pylint: disable=too-few-public-methods
    """
    The frontend subclass that mixes in to form the final RoboCog cog.
    """

async def async_setup(bot: commands.Bot):
    await bot.add_cog(RoboCog(bot=bot))


def setup(bot: commands.Bot):  # pylint: disable=inconsistent-return-statements
   
    if inspect.iscoroutinefunction(bot.add_cog):
        return async_setup(bot)

    bot.add_cog(RoboCog(bot=bot))  # type: ignore[reportUnusedCoroutine]
