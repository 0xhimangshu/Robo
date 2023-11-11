# -*- coding: utf-8 -*-

"""
jishaku.meta
~~~~~~~~~~~~

Meta information about jishaku.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import typing

import pkg_resources

__all__ = (
    '__author__',
    '__copyright__',
    '__docformat__',
    '__license__',
    '__title__',
    '__version__',
    'version_info'
)


class VersionInfo(typing.NamedTuple):
    """Version info named tuple for Jishaku"""
    major: int
    minor: int
    micro: int
    releaselevel: str
    serial: int


version_info = VersionInfo(major=0, minor=1, micro=5, releaselevel='final', serial=0)

__author__ = 'himangshu147-git'
__copyright__ = 'Copyright 2023 himangshu147-git'
__docformat__ = 'restructuredtext en'
__license__ = 'MIT'
__title__ = 'RoboCog'
__version__ = '.'.join(map(str, (version_info.major, version_info.minor, version_info.micro)))

# This ensures that when jishaku is reloaded, pkg_resources requeries it to provide correct version info
pkg_resources.working_set.by_key.pop('robocog', None)  # type: ignore
