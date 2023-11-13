# -*- coding: utf-8 -*-

"""
RoboCog
~~~~~~~

A discord.py extension including useful tools for bot development and debugging.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

# pylint: disable=wildcard-import
from .cog import *  # noqa: F401
from .features.baseclass import Feature  # noqa: F401
from .flags import Flags  # noqa: F401
from .meta import *  # noqa: F401

__all__ = (
    'RoboCog',
    'Feature',
    'Flags',
    'setup'
)