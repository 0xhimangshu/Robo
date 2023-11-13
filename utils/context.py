import asyncio
import io
from contextlib import suppress
from typing import (Any, Callable, Generic, List, Optional,
                    TypeVar, Union)

import discord
from discord.ext import commands

import config

from .buttons import ConfirmationView, DisambiguatorView

T = TypeVar("T")


class Context(commands.Context[commands.Bot], Generic[T]):
    bot: commands.Bot
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
  
    @discord.utils.cached_property
    def replied_reference(self) -> Optional[discord.MessageReference]:
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved.to_reference()
        return None

    @discord.utils.cached_property
    def replied_message(self) -> Optional[discord.Message]:
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved
        return None
        
    async def send(
        self,
        content: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[discord.Message]:
        perms: discord.Permissions = self.channel.permissions_for(self.me)
        if not (perms.send_messages and perms.embed_links):
            with suppress(discord.Forbidden):
                await self.author.send(
                    (
                        "Bot don't have either Embed Links or Send Messages permission in that channel. "
                        "Please give sufficient permissions to the bot."
                    )
                )
                return None

        embeds: Union[discord.Embed, List[discord.Embed]] = kwargs.get(
            "embed"
        ) or kwargs.get("embeds")

        def __set_embed_defaults(embed: discord.Embed, /):
            if not embed.color:
                embed.color = config.color
            
        if isinstance(embeds, (list, tuple)):
            for embed in embeds:
                if isinstance(embed, discord.Embed):
                    __set_embed_defaults(embed)
        else:
            if isinstance(embeds, discord.Embed):
                __set_embed_defaults(embeds)

        return await super().send(str(content)[:1990] if content else None, **kwargs)
    
    async def error(self, message: str, delete_after: bool = None, **kwargs: Any) -> Optional[discord.Message]:
        with suppress(discord.HTTPException):
            msg: Optional[discord.Message] = await self.reply(
                embed=discord.Embed(description=message, color=discord.Color.red()),
                delete_after=delete_after,
                **kwargs,
            )
            try:
                await self.bot.wait_for("message_delete", check=lambda m: m.id == self.message.id, timeout=30)
            except asyncio.TimeoutError:
                pass
            else:
                if msg is not None:
                    await msg.delete(delay=0)
            finally:
                return msg

        return None

    async def wait_and_purge(
        self,
        channel: Union[discord.TextChannel, discord.Thread],
        *,
        limit: int = 100,
        wait_for: Union[int, float] = 10,
        check: Callable = lambda m: True,
    ):
        await asyncio.sleep(wait_for)

        with suppress(discord.HTTPException):
            await channel.purge(limit=limit, check=check)
            
    async def confirm(
        self,
        message: str,
        *,
        timeout: float = 60.0,
        delete_after: bool = True,
        author_id: Optional[int] = None,
    ) -> Optional[bool]:
        author_id = author_id or self.author.id
        view = ConfirmationView(
            timeout=timeout,
            delete_after=delete_after,
            author_id=author_id,
        )
        view.message = await self.send(message, view=view, ephemeral=delete_after)
        await view.wait()
        return view.value
    
    def tick(self, opt: Optional[bool], label: Optional[str] = None) -> str:
        lookup = {
            True: '<:greentick:1172524936292741131>',
            False: '<:xsign:1172524698081427477>',
            None: '<:greytick:1173195940442669157>',
        }
        emoji = lookup.get(opt, '<:xsign:1172524698081427477>')
        if label is not None:
            return f'{emoji}: {label}'
        return emoji
    
    async def disambiguate(self, matches: list[T], entry: Callable[[T], Any], *, ephemeral: bool = False) -> T:
        if len(matches) == 0:
            raise ValueError('No results found.')

        if len(matches) == 1:
            return matches[0]

        if len(matches) > 25:
            raise ValueError('Too many results... sorry.')

        view = DisambiguatorView(self, matches, entry)
        view.message = await self.send(
            'There are too many matches... Which one did you mean?', view=view, ephemeral=ephemeral
        )
        await view.wait()
        return view.selected


    async def show_help(self, command: Any = None) -> None:
        """Shows the help command for the specified command if given.

        If no command is given, then it'll show help for the current
        command.
        """
        cmd = self.bot.get_command('help')
        command = command or self.command.qualified_name
        await self.invoke(cmd, command=command)  # type: ignore

    async def safe_send(self, content: str, *, escape_mentions: bool = True, **kwargs) -> discord.Message:
        """Same as send except with some safe guards.

        1) If the message is too long then it sends a file with the results instead.
        2) If ``escape_mentions`` is ``True`` then it escapes mentions.
        """
        if escape_mentions:
            content = discord.utils.escape_mentions(content)

        if len(content) > 2000:
            fp = io.BytesIO(content.encode())
            kwargs.pop('file', None)
            return await self.send(file=discord.File(fp, filename='message_too_long.txt'), **kwargs)
        else:
            return await self.send(content)
        
    async def on_command_error(self, error: Exception) -> None:
        await self.error(f"```py\n{error}\n```")

class GuildContext(Context):
    author: discord.Member
    guild: discord.Guild
    channel: Union[discord.VoiceChannel, discord.TextChannel, discord.Thread]
    me: discord.Member
    prefix: str