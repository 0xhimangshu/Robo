

import contextlib
import pathlib
import re
import shutil
import sys
import tempfile
import typing
import os

from discord.ext import commands

from ..codeblocks import Codeblock, codeblock_converter
from ..exception_handling import ReplResponseReactor
from ..features.baseclass import Feature
from ..flags import Flags
from ..paginators import PaginatorInterface, WrappedPaginator
from ..shell import ShellReader
from ..types import ContextA

SCAFFOLD_FOLDER = pathlib.Path(__file__).parent / 'scaffolds'


@contextlib.contextmanager
def scaffold(name: str, **kwargs: typing.Any):
    """
    A context manager that sets up a temporary directory with a scaffold formatted to kwargs.

    This allows it to create temporary projects for different shell tools according to the template.
    """

    source = SCAFFOLD_FOLDER / name

    if not (source.exists() and source.is_dir()):
        raise ValueError(f"{name} is not a valid shell scaffold")

    with tempfile.TemporaryDirectory() as temp:
        temp = pathlib.Path(temp)

        for item in source.glob("**/*"):
            if '__pycache__' in str(item):
                continue

            if item.is_file():
                with open(item, 'r', encoding='utf-8') as fp:
                    content = fp.read()

                target = temp / item.relative_to(source)
                target.parent.mkdir(parents=True, exist_ok=True)

                with open(target, 'w', encoding='utf-8') as fp:
                    fp.write(content.format(**kwargs))

        yield temp


class ShellFeature(Feature):
    """
    Feature containing the shell-related commands
    """

    @Feature.Command(parent="robo", name="shell", aliases=["bash", "sh", "powershell", "ps1", "ps", "cmd", "terminal"])
    async def robo_shell(self, ctx: ContextA, *, argument: codeblock_converter):  # type: ignore
        """
        Executes statements in the system shell.

        This uses the system shell as defined in $SHELL, or `/bin/bash` otherwise.
        Execution can be cancelled by closing the paginator.
        """

        if typing.TYPE_CHECKING:
            argument: Codeblock = argument  # type: ignore

        async with ReplResponseReactor(ctx.message):
            with self.submit(ctx):
                with ShellReader(argument.content, escape_ansi=not Flags.use_ansi(ctx)) as reader:
                    prefix = "```" + reader.highlight

                    paginator = WrappedPaginator(prefix=prefix, max_size=1975)
                    paginator.add_line(f"{reader.ps1} {argument.content}\n")

                    interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
                    self.bot.loop.create_task(interface.send_to(ctx))

                    async for line in reader:
                        if interface.closed:
                            return
                        await interface.add_line(line)

                await interface.add_line(f"\n[status] Return code {reader.close_code}")

    @Feature.Command(parent="robo", name="git")
    async def robo_git(self, ctx: ContextA, *, argument: codeblock_converter):  # type: ignore
        """
        Shortcut for 'robo sh git'. Invokes the system shell.
        """

        if typing.TYPE_CHECKING:
            argument: Codeblock = argument  # type: ignore

        return await ctx.invoke(self.robo_shell, argument=Codeblock(argument.language, "git " + argument.content))  # type: ignore

    @Feature.Command(parent="robo", name="pip")
    async def robo_pip(self, ctx: commands.Context, *, argument: codeblock_converter):  # type: ignore
        """
        Shortcut for 'robo sh pip'. Invokes the system shell.
        """

        if typing.TYPE_CHECKING:
            argument: Codeblock = argument  # type: ignore

        executable: str = "pip"
        location = pathlib.Path(sys.prefix)

        for test in (
            location / 'bin' / 'pip',
            location / 'bin' / 'pip3',
            location / 'Scripts' / 'pip.exe',
            location / 'Scripts' / 'pip3.exe',
        ):
            if test.exists() and test.is_file():
                executable = str(test)
                break

        return await ctx.invoke(self.robo_shell, argument=Codeblock(argument.language, f"{executable} {argument.content}"))  # type: ignore

    if shutil.which('node') and shutil.which('npm'):
        @Feature.Command(parent="robo", name="node")
        async def robo_node(self, ctx: commands.Context, *, argument: codeblock_converter):  # type: ignore
            """
            Shortcut for scaffolding and executing 'npm run'. Only exists if the executables are detected.
            """

            if typing.TYPE_CHECKING:
                argument: Codeblock = argument  # type: ignore

            requirements = ''.join(f"npm install {match} ; " for match in re.findall('// robo require: (.+)', argument.content))

            with scaffold('npm', content=argument.content) as directory:
                return await ctx.invoke(self.robo_shell, argument=Codeblock("js", f"cd {directory} {'&' if os.name != 'posix' else ';'} {requirements}npm run main"))  # type: ignore

    if shutil.which('pyright'):
        @Feature.Command(parent="robo", name="pyright")
        async def robo_pyright(self, ctx: commands.Context, *, argument: codeblock_converter):  # type: ignore
            """
            Shortcut for scaffolding and executing 'pyright main.py'. Only exists if the executables are detected.
            """

            if typing.TYPE_CHECKING:
                argument: Codeblock = argument  # type: ignore

            with scaffold('pyright', content=argument.content) as directory:
                return await ctx.invoke(self.robo_shell, argument=Codeblock("js", f"cd {directory} {'&' if os.name != 'posix' else ';'} pyright main.py"))  # type: ignore

    if shutil.which('rustc') and shutil.which('cargo'):
        @Feature.Command(parent="robo", name="rustc")
        async def robo_rustc(self, ctx: commands.Context, *, argument: codeblock_converter):  # type: ignore
            """
            Shortcut for scaffolding and executing 'cargo run'. Only exists if the executables are detected.
            """

            if typing.TYPE_CHECKING:
                argument: Codeblock = argument  # type: ignore

            requirements = '\n'.join(re.findall('// robo require: (.+)', argument.content))

            with scaffold('cargo', content=argument.content, requirements=requirements) as directory:
                return await ctx.invoke(self.robo_shell, argument=Codeblock("rust", f"cd {directory} {'&' if os.name != 'posix' else ';'} cargo run"))  # type: ignore
