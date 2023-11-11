# -*- coding: utf-8 -*-

"""
.repl
~~~~~~~~~~~~

Repl-related operations and tools for Jishaku.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

# pylint: disable=wildcard-import
from ..repl.compilation import *  # noqa: F401
from ..repl.disassembly import create_tree, disassemble  # type: ignore  # noqa: F401
from ..repl.inspections import all_inspections  # type: ignore  # noqa: F401
from ..repl.repl_builtins import get_var_dict_from_ctx  # type: ignore  # noqa: F401
from ..repl.scope import *  # noqa: F401
