# credit : RoboDanny

from __future__ import annotations

import datetime
import inspect
import itertools
from typing import TYPE_CHECKING, Any, Optional, Union

import discord
from discord.ext import commands, menus

import config
from utils.context import Context
from utils.formats import format_dt
from utils.page import Pages

if TYPE_CHECKING:
    from core import Robo as Bot
    from utils.context import GuildContext

display_cogs = [
    "MISC",
    "MOD",
    "UTILITY",
    "META",
    "EMOJIGG",
    "MUSIC",
    "NSFW"
]

class Prefix(commands.Converter):
    async def convert(self, ctx: GuildContext, argument: str) -> str:
        user_id = ctx.bot.user.id
        if argument.startswith((f'<@{user_id}>', f'<@!{user_id}>')):
            raise commands.BadArgument('That is a reserved prefix already in use.')
        if len(argument) > 150:
            raise commands.BadArgument('That prefix is too long.')
        return argument


class GroupHelpPageSource(menus.ListPageSource):
    def __init__(self, group: Union[commands.Group, commands.Cog], entries: list[commands.Command], *, prefix: str):
        super().__init__(entries=entries, per_page=5)
        self.group: Union[commands.Group, commands.Cog] = group
        self.prefix: str = prefix
        self.description: str = f'{getattr(self.group, "display_emoji", None)} **{self.group.qualified_name} Commands**\n{self.group.description}'

    async def format_page(self, menu: Pages, commands: list[commands.Command]):
        embed = discord.Embed(description=self.description, colour=menu.ctx.bot.color)

        for command in commands:
            signature = f'{command.qualified_name} {command.signature}'
            embed.add_field(name=f"{config.prefixes[0]}{signature}", value=command.short_doc or 'No help given...', inline=False)

        maximum = self.get_max_pages()
        if maximum > 1:
            embed.set_author(name=f'Page {menu.current_page + 1}/{maximum} ({len(self.entries)} commands)')

        embed.set_footer(text=f'Use "{self.prefix}help command" for more info on a command.')
        return embed

class HelpSelectMenu(discord.ui.Select['HelpMenu']):
    def __init__(self, entries: dict[commands.Cog, list[commands.Command]], bot: Bot):
        super().__init__(
            placeholder='Select a category...',
            min_values=1,
            max_values=1,
            row=0,
        )
        self.commands: dict[commands.Cog, list[commands.Command]] = entries
        self.bot: Bot = bot
        self.__fill_options()

    def __fill_options(self) -> None:
        self.add_option(
            label='Index',
            emoji='<:requester:1121352087352115251>',
            value='__index',
            description='The help page showing how to use the bot.',
        )
        for cog, command in self.commands.items():
            if (
                cog.qualified_name.upper() in display_cogs
                and command
                and len(cog.get_commands()) != 0
            ):
                description = cog.description.split('\n', 1)[0] or None
                emoji = getattr(cog, 'display_emoji', None)
                if emoji is None:
                    emoji = '\N{BLACK QUESTION MARK ORNAMENT}'
                self.add_option(label=cog.qualified_name, value=cog.qualified_name, description=description, emoji=emoji)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        value = self.values[0]
        if value == '__index':
            await self.view.rebind(FrontPageSource(), interaction)
        else:
            cog = self.bot.get_cog(value)
            if cog is None:
                await interaction.response.send_message('Somehow this category does not exist?', ephemeral=True)
                return

            commands = self.commands[cog]
            if not commands:
                await interaction.response.send_message('This category has no commands for you', ephemeral=True)
                return

            source = GroupHelpPageSource(cog, commands, prefix=self.view.ctx.clean_prefix)
            await self.view.rebind(source, interaction)


class FrontPageSource(menus.PageSource):
    def is_paginating(self) -> bool:
        # This forces the buttons to appear even in the front page
        return True

    def get_max_pages(self) -> Optional[int]:
        # There's only one actual page in the front page
        # However we need at least 2 to show all the buttons
        return 2

    async def get_page(self, page_number: int) -> Any:
        # The front page is a dummy
        self.index = page_number
        return self

    def format_page(self, menu: HelpMenu, page: Any):
        embed = discord.Embed(title='Bot Help', colour=menu.ctx.bot.color)
        embed.description = inspect.cleandoc(
            f"""
            Hello {menu.ctx.author.mention}, Welcome to the help page.

            Use "`{menu.ctx.clean_prefix}help <command>`" for more info on a command.
            Use the dropdown menu below to select a category.
        """
        )

        created_at = format_dt(menu.ctx.bot.user.created_at, 'F')
        if self.index == 0:
            embed.add_field(
                name='Who am I?',
                value=(
                    f"I'm {menu.ctx.bot.user.name}. I've been running since {created_at}.\n"
                    "I don't have a lot of features, but still I am good enough to manage\na small discord server.\n"
                    f"You can use dropdown menu below to get more information\n\n"
                    f"Join my [support server]({config.support_invite}) for more help.\n"
                    f"You can also submit bugs, feature requests, suggestions [here]({config.support_invite}).\n"
                ),
                inline=False,
            )
        elif self.index == 1:
            # entries = (
            #     ('`<argument>`', 'This means the argument is **required**.'),
            #     ('`[argument]`', 'This means the argument is **optional**.'),
            #     ('`[A|B]`', 'This means that it can be **either A or B**.'),
            #     (
            #         '[argument...]',
            #         'This means you can have multiple arguments.\n'
            #         'Now that you know the basics, it should be noted that...\n'
            #         '**You do not type in the brackets!**',
            #     ),
            # )

            # embed.add_field(name='How do I use this bot?', value='Reading the bot signature is pretty simple.')

            # for name, value in entries:
            #     embed.add_field(name=name, value=value, inline=False)

            embed.description = (
                            """
                            **How do I use this bot?**
                            __Reading the bot signature is pretty simple.__
```ansi\n
[2;36m[2;31m<argument>[0m[2;36m[0m [2;37mmeans the argument is [1;37mrequired[0m[2;37m[0m[2;37m[0m. 
[2;33m[argument][0m [2;37mmeans the argument is [1;37moptional[0m[2;37m[0m.
[2;34m[A|B][0m [2;37mmeans that it can be [1;37meither A or B[0m[2;37m[0m.
[2;36m[argument...][0m [2;37mmeans you can have [2;37mmultiple[0m[2;37m arguments.[0m
```
            """
            )

        return embed


class HelpMenu(Pages):
    def __init__(self, source: menus.PageSource, ctx: Context):
        super().__init__(source, ctx=ctx, compact=True)

    def add_categories(self, commands: dict[commands.Cog, list[commands.Command]]) -> None:
        self.clear_items()
        self.add_item(HelpSelectMenu(commands, self.ctx.bot))
        self.fill_items()

    async def rebind(self, source: menus.PageSource, interaction: discord.Interaction) -> None:
        self.source = source
        self.current_page = 0

        await self.source._prepare_once()
        page = await self.source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        self._update_labels(0)
        await interaction.response.edit_message(**kwargs, view=self)


class PaginatedHelpCommand(commands.HelpCommand):
    context: Context
    def __init__(self):
        super().__init__(
            command_attrs={
                'cooldown': commands.CooldownMapping.from_cooldown(1, 3.0, commands.BucketType.member),
                'help': 'Shows help about the bot, a command, or a category',
                'aliases': ['he', 'commands', 'h', 'cmd', 'cmds'],
            }
        )

    async def on_help_command_error(self, ctx: Context, error: commands.CommandError):
        if isinstance(error, commands.CommandInvokeError):
            # Ignore missing permission errors
            if isinstance(error.original, discord.HTTPException) and error.original.code == 50013:
                return

            await ctx.send(str(error.original))

    def get_command_signature(self, command: commands.Command) -> str:
        parent = command.full_parent_name
        if len(command.aliases) > 0:
            aliases = '|'.join(command.aliases)
            fmt = f'[{command.name}|{aliases}]'
            if parent:
                fmt = f'{parent} {fmt}'
            alias = fmt
        else:
            alias = command.name if not parent else f'{parent} {command.name}'
        return f'{alias} {command.signature}'

    async def send_bot_help(self, mapping):
        bot = self.context.bot

        def key(command) -> str:
            cog = command.cog
            return cog.qualified_name if cog else '\U0010ffff'

        entries: list[commands.Command] = await self.filter_commands(bot.commands, sort=True, key=key)

        all_commands: dict[commands.Cog, list[commands.Command]] = {}
        for name, children in itertools.groupby(entries, key=key):
            if name == '\U0010ffff':
                continue

            cog = bot.get_cog(name)
            assert cog is not None
            all_commands[cog] = sorted(children, key=lambda c: c.qualified_name)

        menu = HelpMenu(FrontPageSource(), ctx=self.context)
        menu.add_categories(all_commands)
        await menu.start()

    async def send_cog_help(self, cog):
        entries = await self.filter_commands(cog.get_commands(), sort=True)
        menu = HelpMenu(GroupHelpPageSource(cog, entries, prefix=self.context.clean_prefix), ctx=self.context)
        await menu.start()

    def common_command_formatting(self, embed_like, command):
        somedescription = (
            """
```ansi\n
[2;36m[2;31m<argument>[0m[2;36m[0m [2;37mmeans the argument is [1;37mrequired[0m[2;37m[0m[2;37m[0m. 
[2;33m[argument][0m [2;37mmeans the argument is [1;37moptional[0m[2;37m[0m.
[2;34m[A|B][0m [2;37mmeans that it can be [1;37meither A or B (are alisas)[0m[2;37m[0m.
[2;36m[argument...][0m [2;37mmeans you can have [2;37mmultiple[0m[2;37m arguments.[0m

```
            """
        )
        embed_like.title = self.get_command_signature(command)
        if command.description:
            embed_like.description = (
                f'{command.description or command.help}\n{somedescription}'
                )
        else:
            embed_like.description = f"{command.help}\n{somedescription}" or 'No help found...'

    async def send_command_help(self, command):
        # No pagination necessary for a single command.
        embed = discord.Embed(colour=__import__('config').color)
        self.common_command_formatting(embed, command)
        await self.context.send(embed=embed)

    async def send_group_help(self, group):
        subcommands = group.commands
        if len(subcommands) == 0:
            return await self.send_command_help(group)

        entries = await self.filter_commands(subcommands, sort=True)
        if len(entries) == 0:
            return await self.send_command_help(group)

        source = GroupHelpPageSource(group, entries, prefix=self.context.clean_prefix)
        self.common_command_formatting(source, group)
        menu = HelpMenu(source, ctx=self.context)
        await menu.start()