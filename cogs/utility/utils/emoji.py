from __future__ import annotations

import re

import discord
import yarl
from discord.ext import commands

from utils.context import Context

BLOB_GUILD_ID = 1064154848477589584
EMOJI_REGEX = re.compile(r"<a?:.+?:([0-9]{15,21})>")
EMOJI_NAME_REGEX = re.compile(r"^[0-9a-zA-Z\_]{2,32}$")


class BlobEmoji(commands.Converter):
    async def convert(
        self, ctx: Context, argument: str
    ) -> discord.Emoji:
        guild = ctx.bot.get_guild(BLOB_GUILD_ID)
        assert guild is not None

        emojis = {e.id: e for e in guild.emojis}

        m = EMOJI_REGEX.match(argument)
        if m is not None:
            emoji = emojis.get(int(m.group(1)))
        elif argument.isdigit():
            emoji = emojis.get(int(argument))
        else:
            emoji = discord.utils.find(lambda e: e.name == argument, emojis.values())

        if emoji is None:
            raise commands.BadArgument("Not a valid blob emoji.")
        return emoji


def partial_emoji(argument: str, *, regex=EMOJI_REGEX) -> int:
    if argument.isdigit():
        # assume it's an emoji ID
        return int(argument)

    m = regex.match(argument)
    if m is None:
        raise commands.BadArgument("That's not a custom emoji...")
    return int(m.group(1))


def emoji_name(argument: str, *, regex=EMOJI_NAME_REGEX) -> str:
    m = regex.match(argument)
    if m is None:
        raise commands.BadArgument("Invalid emoji name.")
    return argument


class EmojiURL:
    def __init__(self, *, animated: bool, url: str):
        self.url: str = url
        self.animated: bool = animated

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> EmojiURL:
        try:
            partial = await commands.PartialEmojiConverter().convert(ctx, argument)
        except commands.BadArgument as e:
            try:
                url = yarl.URL(argument)
                if url.scheme not in ("http", "https"):
                    raise RuntimeError from e
                path = url.path.lower()
                if not path.endswith((".png", ".jpeg", ".jpg", ".gif", ".webp")):
                    raise RuntimeError from e
                return cls(animated=url.path.endswith(".gif"), url=argument)
            except Exception:
                raise commands.BadArgument(
                    "Not a valid or supported emoji URL."
                ) from None
        else:
            return cls(animated=partial.animated, url=str(partial.url))