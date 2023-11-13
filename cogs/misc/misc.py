from __future__ import annotations

import asyncio
import datetime
import io
import json
import logging
import os
import random
import re
import string
import zlib
import aiohttp
from typing import (TYPE_CHECKING, Annotated, Any, Generator, List, NamedTuple,
                    Optional, Union)
from collections import Counter

import discord
import yarl
from discord import app_commands
from discord.ext import commands, menus, tasks
from lxml import html
from typing_extensions import Self

from core import Robo
from utils import Pages, fuzzy
from utils.context import Context
from utils.friendlytime import format_datetime_human_readable, time_formatter
from utils.paginator import SimplePages
from utils.formats import truncate_string, plural
from utils.friendlytime import format_relative
import config

from .utils import translate, TagEdit, TagEditButton

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from core import Robo
    from utils import Pages
    from utils.context import Context, GuildContext

def to_emoji(c: int) -> str:
    base = 0x1F1E6
    return chr(base + c)

def can_use_spoiler():
    def predicate(ctx: GuildContext) -> bool:
        if ctx.guild is None:
            raise commands.BadArgument('Cannot be used in private messages.')

        my_permissions = ctx.channel.permissions_for(ctx.guild.me)
        if not (my_permissions.read_message_history and my_permissions.manage_messages and my_permissions.add_reactions):
            raise commands.BadArgument(
                'Need Read Message History, Add Reactions and Manage Messages '
                'to permission to use this. Sorry if I spoiled you.'
            )
        return True

    return commands.check(predicate)


SPOILER_EMOJI_ID = 430469957042831371
DICTIONARY_EMBED_COLOUR = discord.Colour(0x5F9EB3)


def html_to_markdown(node: Any, *, include_spans: bool = False, base_url: Optional[yarl.URL] = None) -> str:
    text = []
    italics_marker = '_'

    for child in node:
        if child.tag == 'i':
            text.append(f'{italics_marker}{child.text.strip()}{italics_marker}')
            italics_marker = '_' if italics_marker == '*' else '*'
        elif child.tag == 'b':
            if text and text[-1].endswith('*'):
                text.append('\u200b')

            text.append(f'**{child.text.strip()}**')
        elif child.tag == 'a':
            # No markup for links
            if base_url is None:
                text.append(child.text)
            else:
                url = base_url.join(yarl.URL(child.attrib['href']))
                text.append(f'[{child.text}]({url})')
        elif include_spans and child.tag == 'span':
            text.append(child.text)

        if child.tail:
            text.append(child.tail)

    return ''.join(text).strip()

def inner_trim(s: str, *, _regex=re.compile(r'\s+')) -> str:
    return _regex.sub(' ', s.strip())


class FreeDictionaryDefinition(NamedTuple):
    definition: str
    example: Optional[str]
    children: list[FreeDictionaryDefinition]

    @classmethod
    def from_node(cls, node: Any) -> Self:
        # Note that in here we're inside either a ds-list or a ds-single node
        # The first child is basically always a superfluous bolded number
        number = node.find('b')
        definition: str = node.text or ''
        if number is not None:
            tail = number.tail
            node.remove(number)
            if tail:
                definition = tail

        definition += html_to_markdown(node, include_spans=False)
        definition = inner_trim(definition)

        example: Optional[str] = None
        example_nodes = node.xpath("./span[@class='illustration']")
        if example_nodes:
            example = example_nodes[0].text_content()

        children: list[FreeDictionaryDefinition] = [cls.from_node(child) for child in node.xpath("./div[@class='sds-list']")]
        return cls(definition, example, children)

    def to_json(self) -> dict[str, Any]:
        return {
            'definition': self.definition,
            'example': self.example,
            'children': [child.to_json() for child in self.children],
        }

    def to_markdown(self, *, indent: int = 2) -> str:
        content = self.definition
        if self.example:
            content = f'{content} [*{self.example}*]'
        if not content:
            content = '\u200b'
        if self.children:
            inner = '\n'.join(f'{" " * indent }- {child.to_markdown(indent=indent + 2)}' for child in self.children)
            return f'{content}\n{inner}'
        return content


class FreeDictionaryMeaning:
    part_of_speech: str
    definitions: list[FreeDictionaryDefinition]

    __slots__ = ('part_of_speech', 'definitions')

    def __init__(self, definitions: Any, part_of_speech: str) -> None:
        self.part_of_speech = part_of_speech
        self.definitions = [FreeDictionaryDefinition.from_node(definition) for definition in definitions]

    def to_json(self) -> dict[str, Any]:
        return {'part_of_speech': self.part_of_speech, 'definitions': [defn.to_json() for defn in self.definitions]}

    @property
    def markdown(self) -> str:
        inner = '\n'.join(f'{i}. {defn.to_markdown()}' for i, defn in enumerate(self.definitions, start=1))
        return f'{self.part_of_speech}\n{inner}'


class FreeDictionaryPhrasalVerb(NamedTuple):
    word: str
    meaning: FreeDictionaryMeaning

    def to_embed(self) -> discord.Embed:
        return discord.Embed(title=self.word, colour=DICTIONARY_EMBED_COLOUR, description=self.meaning.markdown)


class FreeDictionaryWord:
    raw_word: str
    word: str
    pronunciation_url: Optional[str]
    pronunciation: Optional[str]
    meanings: list[FreeDictionaryMeaning]
    phrasal_verbs: list[FreeDictionaryPhrasalVerb]
    etymology: Optional[str]

    def __init__(self, raw_word: str, word: str, node: Any, base_url: yarl.URL) -> None:
        self.raw_word = raw_word
        self.word = word
        self.meanings = []
        self.phrasal_verbs = []
        self.get_pronunciation(node)
        self.get_meanings(node)
        self.get_etymology(node, base_url)

    def get_pronunciation(self, node) -> None:
        self.pronunciation_url = None
        self.pronunciation = None
        snd = node.xpath("span[@class='snd' and @data-snd]")
        if not snd:
            return None

        snd = snd[0]
        pron = node.xpath("span[@class='pron']")
        if pron:
            self.pronunciation = pron[0].text_content() + (pron[0].tail or '')
            self.pronunciation = self.pronunciation.strip()

        data_src = node.attrib.get('data-src')
        if data_src is not None:
            mp3 = snd.attrib.get('data-snd')
            self.pronunciation_url = f'https://img.tfd.com/{data_src}/{mp3}.mp3'

    def get_meanings(self, node) -> None:
        conjugations: Optional[str] = None

        data_src = node.attrib.get('data-src')

        child_nodes = []
        if data_src == 'hm':
            child_nodes = node.xpath("./div[@class='pseg']")
        elif data_src == 'hc_dict':
            child_nodes = node.xpath('./div[not(@class)]')
        elif data_src == 'rHouse':
            child_nodes = node

        for div in child_nodes:
            definitions = div.xpath("div[@class='ds-list' or @class='ds-single']")
            if not definitions:
                # Probably a conjugation
                # If it isn't a conjugation then it probably just has a single definition
                bolded = div.find('b')
                if bolded is not None:
                    children = iter(div)
                    next(children)  # skip the italic `v.` bit
                    conjugations = html_to_markdown(children, include_spans=True)
                    continue

            pos_node = div.find('i')
            if pos_node is None:
                continue

            pos = html_to_markdown(div)
            if conjugations is not None:
                if conjugations.startswith(','):
                    pos = f'{pos}{conjugations}'
                else:
                    pos = f'{pos} {conjugations}'

            meaning = FreeDictionaryMeaning(definitions, pos)
            self.meanings.append(meaning)

        for div in node.find_class('pvseg'):
            # phrasal verbs are simple
            # <b><i>{word}</i></b>
            # ... definitions
            word = div.find('b/i')
            if word is None:
                continue

            word = word.text_content().strip()
            meaning = FreeDictionaryMeaning(div, 'phrasal verb')
            self.phrasal_verbs.append(FreeDictionaryPhrasalVerb(word, meaning))

    def get_etymology(self, node: Any, base_url: yarl.URL) -> None:
        etyseg = node.xpath("./div[@class='etyseg']")
        if not etyseg:
            self.etymology = None
            return

        etyseg = etyseg[0]
        self.etymology = etyseg.text + html_to_markdown(etyseg, include_spans=True, base_url=base_url)

        if self.etymology.startswith('[') and self.etymology.endswith(']'):
            self.etymology = self.etymology[1:-1]

    def to_json(self) -> dict[str, Any]:
        return {
            'raw_word': self.raw_word,
            'word': self.word,
            'pronunciation_url': self.pronunciation_url,
            'pronunciation': self.pronunciation,
            'meanings': [meaning.to_json() for meaning in self.meanings],
            'phrasal_verbs': [
                {
                    'word': verb.word,
                    'meaning': verb.meaning.to_json(),
                }
                for verb in self.phrasal_verbs
            ],
            'etymology': self.etymology,
        }


async def parse_free_dictionary_for_word(session: ClientSession, *, word: str) -> Optional[FreeDictionaryWord]:
    url = yarl.URL('https://www.thefreedictionary.com') / word

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
        'TE': 'trailers',
    }

    async with session.get(url, headers=headers) as resp:
        if resp.status != 200:
            return None

        text = await resp.text()
        document = html.document_fromstring(text)

        try:
            definitions = document.get_element_by_id('Definition')
        except KeyError:
            return None

        h1 = document.find('h1')
        raw_word = h1.text if h1 is not None else word

        section = definitions.xpath("section[@data-src='hm' or @data-src='hc_dict' or @data-src='rHouse']")
        if not section:
            return None

        node = section[0]
        h2: Optional[Any] = node.find('h2')
        if h2 is None:
            return None

        try:
            return FreeDictionaryWord(raw_word, h2.text, node, resp.url)
        except RuntimeError:
            log.exception('Error happened while parsing free dictionary')
            return None


async def free_dictionary_autocomplete_query(session: ClientSession, *, query: str) -> list[str]:
    url = yarl.URL('https://www.thefreedictionary.com/_/search/suggest.ashx')

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
        'TE': 'trailers',
    }

    async with session.get(url, params={'query': query}, headers=headers) as resp:
        if resp.status != 200:
            return []

        js = await resp.json()
        if len(js) == 2:
            return js[1]
        return []


class FreeDictionaryWordMeaningPageSource(menus.ListPageSource):
    entries: list[FreeDictionaryMeaning]

    def __init__(self, word: FreeDictionaryWord):
        super().__init__(entries=word.meanings, per_page=1)
        self.word: FreeDictionaryWord = word

    async def format_page(self, menu: Pages, entry: FreeDictionaryMeaning) -> discord.Embed:
        maximum = self.get_max_pages()
        heading = f'{self.word.raw_word}: {menu.current_page + 1} out of {maximum}' if maximum >= 2 else self.word.raw_word
        if self.word.pronunciation:
            title = f'{self.word.word} {self.word.pronunciation}'
        else:
            title = self.word.word

        embed = discord.Embed(title=title, colour=DICTIONARY_EMBED_COLOUR)
        embed.set_author(name=heading)
        embed.description = entry.markdown

        if self.word.etymology:
            embed.add_field(name='Etymology', value=self.word.etymology, inline=False)

        return embed


class UrbanDictionaryPageSource(menus.ListPageSource):
    BRACKETED = re.compile(r'(\[(.+?)\])')

    def __init__(self, data: list[dict[str, Any]]):
        super().__init__(entries=data, per_page=1)

    def cleanup_definition(self, definition: str, *, regex=BRACKETED) -> str:
        def repl(m):
            word = m.group(2)
            return f'[{word}](http://{word.replace(" ", "-")}.urbanup.com)'

        ret = regex.sub(repl, definition)
        if len(ret) >= 2048:
            return ret[0:2000] + ' [...]'
        return ret

    async def format_page(self, menu: Pages, entry: dict[str, Any]):
        maximum = self.get_max_pages()
        title = f'{entry["word"]}: {menu.current_page + 1} out of {maximum}' if maximum else entry['word']
        embed = discord.Embed(title=title, url=entry['permalink'])
        embed.color = config.color
        # embed.set_footer(text=f'by {entry["author"]}')
        embed.set_footer(text="Uploaded at")
        embed.description = self.cleanup_definition(entry['definition'])

        # try:
        #     up, down = entry['thumbs_up'], entry['thumbs_down']
        # except KeyError:
        #     pass
        # else:
        #     embed.add_field(name='Votes', value=f'\N{THUMBS UP SIGN} {up} \N{THUMBS DOWN SIGN} {down}', inline=False)

        try:
            date = discord.utils.parse_time(entry['written_on'][0:-1])
        except (ValueError, KeyError):
            pass
        else:
            embed.timestamp = date

        return embed


RTFM_PAGE_TYPES = {
    'stable': 'https://discordpy.readthedocs.io/en/stable',
    'latest': 'https://discordpy.readthedocs.io/en/latest',
    'python': 'https://docs.python.org/3',
}

class SphinxObjectFileReader:
    # Inspired by Sphinx's InventoryFileReader
    BUFSIZE = 16 * 1024

    def __init__(self, buffer: bytes):
        self.stream = io.BytesIO(buffer)

    def readline(self) -> str:
        return self.stream.readline().decode('utf-8')

    def skipline(self) -> None:
        self.stream.readline()

    def read_compressed_chunks(self) -> Generator[bytes, None, None]:
        decompressor = zlib.decompressobj()
        while True:
            chunk = self.stream.read(self.BUFSIZE)
            if len(chunk) == 0:
                break
            yield decompressor.decompress(chunk)
        yield decompressor.flush()

    def read_compressed_lines(self) -> Generator[str, None, None]:
        buf = b''
        for chunk in self.read_compressed_chunks():
            buf += chunk
            pos = buf.find(b'\n')
            while pos != -1:
                yield buf[:pos].decode('utf-8')
                buf = buf[pos + 1 :]
                pos = buf.find(b'\n')

class Misc(commands.Cog):
    """Misclenous commands for your server."""
    _rtfm_cache: dict[str, dict[str, str]] 
    def __init__(self, bot: Robo):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name='translate_',
            callback=self.translate_ctx,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(
            id=1120667756300353638,
            name="Commands"
        )
    
    def parse_object_inv(self, stream: SphinxObjectFileReader, url: str) -> dict[str, str]:
        # key: URL
        # n.b.: key doesn't have `discord` or `discord.ext.commands` namespaces
        result: dict[str, str] = {}

        # first line is version info
        inv_version = stream.readline().rstrip()

        if inv_version != '# Sphinx inventory version 2':
            raise RuntimeError('Invalid objects.inv file version.')

        # next line is "# Project: <name>"
        # then after that is "# Version: <version>"
        projname = stream.readline().rstrip()[11:]
        version = stream.readline().rstrip()[11:]

        # next line says if it's a zlib header
        line = stream.readline()
        if 'zlib' not in line:
            raise RuntimeError('Invalid objects.inv file, not z-lib compatible.')

        # This code mostly comes from the Sphinx repository.
        entry_regex = re.compile(r'(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)')
        for line in stream.read_compressed_lines():
            match = entry_regex.match(line.rstrip())
            if not match:
                continue

            name, directive, prio, location, dispname = match.groups()
            domain, _, subdirective = directive.partition(':')
            if directive == 'py:module' and name in result:
                # From the Sphinx Repository:
                # due to a bug in 1.1 and below,
                # two inventory entries are created
                # for Python modules, and the first
                # one is correct
                continue

            # Most documentation pages have a label
            if directive == 'std:doc':
                subdirective = 'label'

            if location.endswith('$'):
                location = location[:-1] + name

            key = name if dispname == '-' else dispname
            prefix = f'{subdirective}:' if domain == 'std' else ''

            if projname == 'discord.py':
                key = key.replace('discord.ext.commands.', '').replace('discord.', '')

            result[f'{prefix}{key}'] = os.path.join(url, location)

        return result

    async def build_rtfm_lookup_table(self):
        cache: dict[str, dict[str, str]] = {}
        for key, page in RTFM_PAGE_TYPES.items():
            cache[key] = {}
            async with self.bot.session.get(page + '/objects.inv') as resp:
                if resp.status != 200:
                    raise RuntimeError('Cannot build rtfm lookup table, try again later.')

                stream = SphinxObjectFileReader(await resp.read())
                cache[key] = self.parse_object_inv(stream, page)

        self._rtfm_cache = cache

    async def do_rtfm(self, ctx: Context, key: str, obj: Optional[str]):
        if obj is None:
            await ctx.send(RTFM_PAGE_TYPES[key])
            return

        if not hasattr(self, '_rtfm_cache'):
            await ctx.typing()
            await self.build_rtfm_lookup_table()

        obj = re.sub(r'^(?:discord\.(?:ext\.)?)?(?:commands\.)?(.+)', r'\1', obj)

        if key.startswith('latest'):
            # point the abc.Messageable types properly:
            q = obj.lower()
            for name in dir(discord.abc.Messageable):
                if name[0] == '_':
                    continue
                if q == name:
                    obj = f'abc.Messageable.{name}'
                    break

        cache = list(self._rtfm_cache[key].items())
        matches = fuzzy.finder(obj, cache, key=lambda t: t[0])[:8]

        e = discord.Embed(colour=self.bot.config.color)
        if len(matches) == 0:
            return await ctx.send('Could not find anything. Sorry.')

        e.description = '\n'.join(f'[`{key}`]({url})' for key, url in matches)
        await ctx.send(embed=e, reference=ctx.replied_reference)

    async def rtfm_slash_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:

        # Degenerate case: not having built caching yet
        if not hasattr(self, '_rtfm_cache'):
            await interaction.response.autocomplete([])
            await self.build_rtfm_lookup_table()
            return []

        if not current:
            return []

        if len(current) < 3:
            return [app_commands.Choice(name=current, value=current)]

        assert interaction.command is not None
        key = interaction.command.name
        if key == 'latest':
            key = 'latest'
        elif key == 'stable':
            key = 'stable'
        elif key == 'python':
            key = 'python'
        matches = fuzzy.finder(current, self._rtfm_cache[key])[:10]
        return [app_commands.Choice(name=m, value=m) for m in matches]
    

    @commands.hybrid_group(aliases=['rtfd'], fallback="stable")
    @app_commands.describe(entity='The object to search for')
    @app_commands.autocomplete(entity=rtfm_slash_autocomplete)
    async def rtfm(self, ctx: Context, *, entity: Optional[str] = None):
        """Gives you a documentation link for a discord.py or python entity.

        Events, objects, and functions are all supported through
        a cruddy fuzzy algorithm.
        """
        await self.do_rtfm(ctx, 'stable', entity)
        
    @rtfm.command(name='latest')
    @app_commands.describe(entity='The object to search for')
    @app_commands.autocomplete(entity=rtfm_slash_autocomplete)
    async def rtfm_master(self, ctx: Context, *, entity: Optional[str] = None):
        """Gives you a documentation link for a discord.py entity (master branch)"""
        await self.do_rtfm(ctx, 'latest', entity)
        

    @rtfm.command(name='python', aliases=['py'])
    @app_commands.describe(entity='The object to search for')
    @app_commands.autocomplete(entity=rtfm_slash_autocomplete)
    async def rtfm_python(self, ctx: Context, *, entity: Optional[str] = None):
        """Gives you a documentation link for a Python entity."""
        await self.do_rtfm(ctx, 'python', entity)

    
        
    @commands.hybrid_command(aliases=["si", "server"])
    @commands.guild_only()
    async def serverinfo(self, ctx: GuildContext, *, guild_id: int = None):
        """Shows info about the current server."""

        if guild_id is not None and await self.bot.is_owner(ctx.author):
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                return await ctx.send(f'Invalid Guild ID given.')
        else:
            guild = ctx.guild

        roles = [role.name.replace('@', '@\u200b') for role in guild.roles]

        if not guild.chunked:
            async with ctx.typing():
                await guild.chunk(cache=True)
        # source Robo Danny
        # figure out what channels are 'secret'
        everyone = guild.default_role
        everyone_perms = everyone.permissions.value
        secret = Counter()
        totals = Counter()
        for channel in guild.channels:
            allow, deny = channel.overwrites_for(everyone).pair()
            perms = discord.Permissions((everyone_perms & ~deny.value) | allow.value)
            channel_type = type(channel)
            totals[channel_type] += 1
            if not perms.read_messages:
                secret[channel_type] += 1
            elif isinstance(channel, discord.VoiceChannel) and (not perms.connect or not perms.speak):
                secret[channel_type] += 1

        e = discord.Embed()
        e.title = guild.name
        e.description = f'**ID**: {guild.id}\n**Owner**: {guild.owner}'
        if guild.icon:
            e.set_thumbnail(url=guild.icon.url)

        channel_info = []
        key_to_emoji = {
            discord.TextChannel: '<:textch:1173194877090152468>',
            discord.VoiceChannel: '<:voicech:1173195392280703026>',
        }
        for key, total in totals.items():
            secrets = secret[key]
            try:
                emoji = key_to_emoji[key]
            except KeyError:
                continue

            if secrets:
                channel_info.append(f'{emoji} {total} ({secrets} locked)')
            else:
                channel_info.append(f'{emoji} {total}')

        info = []
        features = set(guild.features)
        all_features = {
            'PARTNERED': 'Partnered',
            'VERIFIED': 'Verified',
            'DISCOVERABLE': 'Server Discovery',
            'COMMUNITY': 'Community Server',
            'FEATURABLE': 'Featured',
            'WELCOME_SCREEN_ENABLED': 'Welcome Screen',
            'INVITE_SPLASH': 'Invite Splash',
            'VIP_REGIONS': 'VIP Voice Servers',
            'VANITY_URL': 'Vanity Invite',
            'COMMERCE': 'Commerce',
            'LURKABLE': 'Lurkable',
            'NEWS': 'News Channels',
            'ANIMATED_ICON': 'Animated Icon',
            'BANNER': 'Banner',
        }

        for feature, label in all_features.items():
            if feature in features:
                info.append(f'{ctx.tick(True)}: {label}')

        if info:
            e.add_field(name='Features', value='\n'.join(info))

        e.add_field(name='Channels', value='\n'.join(channel_info))

        if guild.premium_tier != 0:
            boosts = f'Level {guild.premium_tier}\n{guild.premium_subscription_count} boosts'
            last_boost = max(guild.members, key=lambda m: m.premium_since or guild.created_at)
            if last_boost.premium_since is not None:
                boosts = f'{boosts}\nLast Boost: {last_boost} ({format_relative(last_boost.premium_since)})'
            e.add_field(name='Boosts', value=boosts, inline=False)

        bots = sum(m.bot for m in guild.members)
        fmt = f'Total: {guild.member_count} ({plural(bots):bot})'

        e.add_field(name='Members', value=fmt, inline=False)
        e.add_field(name='Roles', value=', '.join(roles) if len(roles) < 10 else f'{len(roles)} roles')

        emoji_stats = Counter()
        for emoji in guild.emojis:
            if emoji.animated:
                emoji_stats['animated'] += 1
                emoji_stats['animated_disabled'] += not emoji.available
            else:
                emoji_stats['regular'] += 1
                emoji_stats['disabled'] += not emoji.available

        fmt = (
            f'Regular: {emoji_stats["regular"]}/{guild.emoji_limit}\n'
            f'Animated: {emoji_stats["animated"]}/{guild.emoji_limit}\n'
        )
        if emoji_stats['disabled'] or emoji_stats['animated_disabled']:
            fmt = f'{fmt}Disabled: {emoji_stats["disabled"]} regular, {emoji_stats["animated_disabled"]} animated\n'

        fmt = f'{fmt}Total Emoji: {len(guild.emojis)}/{guild.emoji_limit*2}'
        e.add_field(name='Emoji', value=fmt, inline=False)
        e.set_footer(text='Created').timestamp = guild.created_at
        await ctx.send(embed=e)


    @commands.hybrid_command(aliases=["ui", "user"])
    @commands.guild_only()
    async def userinfo(self, ctx: GuildContext, *, user: Optional[Union[discord.User, discord.Member]] = None):
        """Shows info about a user."""

        if user is None:
            user = ctx.author

        if not isinstance(user, discord.Member):
            try:
                user = await ctx.guild.fetch_member(user.id)
            except discord.NotFound:
                return await ctx.send('User not found.')
            
        if user is None:
            return await ctx.send('User not found.')
        
        if isinstance(user, discord.Member):
            if not user.guild.chunked:
                async with ctx.typing():
                    await user.guild.chunk(cache=True)

        e = discord.Embed(colour=self.bot.color)
        e.set_author(name=str(user), icon_url=user.avatar.url)
        e.set_thumbnail(url=user.avatar.url)
        e.add_field(name='ID', value=user.id)
        e.add_field(name='Bot', value=ctx.tick(user.bot))
        e.add_field(name='Created', value=format_datetime_human_readable(user.created_at))
        if isinstance(user, discord.Member):
            e.add_field(name='Joined', value=format_datetime_human_readable(user.joined_at))
            e.add_field(name='Boosting', value=ctx.tick(bool(user.premium_since)))
            e.add_field(name='Status', value=str(user.status).title())
            if user.activity is not None:
                e.add_field(name='Activity', value=str(user.activity.name))
                if user.activity.type == discord.ActivityType.listening and user.activity.album is not None:
                    e.add_field(name='Listening to', value=f'[{user.activity.title}]({user.activity.track_url}) by {user.activity.artist}')
            if user.voice is not None:
                e.add_field(name='Voice', value=user.voice.channel.mention)
            if user.nick is not None:
                e.add_field(name='Nickname', value=user.nick)
        
            if user.activity == discord.Game:
                e.add_field(name='Playing', value=f'{user.activity.name}')
            if user.activity == discord.Streaming:
                e.add_field(name='Streaming', value=f'{user.activity.name}')
        if len(user.roles) > 1:
            e.add_field(name="Roles", value=', '.join(role.mention for role in user.roles[1:]), inline=False)

        if isinstance(user, discord.User):
            e = discord.Embed(colour=self.bot.color)
            e.set_author(name=str(user), icon_url=user.avatar.url)
            e.set_thumbnail(url=user.avatar.url)
            e.add_field(name='ID', value=user.id)
            e.add_field(name='Bot', value=ctx.tick(user.bot))
            e.add_field(name='Created', value=format_datetime_human_readable(user.created_at))
            if user.activity is not None:
                e.add_field(name='Activity', value=str(user.activity))
            if user.status is not None:
                e.add_field(name='Status', value=str(user.status).title())
        await ctx.send(embed=e)

    @commands.hybrid_command(aliases=["av", "pfp"])
    @commands.guild_only()
    async def avatar(self, ctx: GuildContext, *, user: Optional[Union[discord.User, discord.Member]] = None):
        """Shows a user's avatar."""

        if user is None:
            user = ctx.author

        if not isinstance(user, discord.Member):
            try:
                user = await ctx.guild.fetch_member(user.id)
            except discord.NotFound:
                return await ctx.send('User not found.')
            
        if user is None:
            return await ctx.send('User not found.')
        
        if isinstance(user, discord.Member):
            if not user.guild.chunked:
                async with ctx.typing():
                    await user.guild.chunk(cache=True)

        e = discord.Embed(colour=self.bot.color)
        e.set_author(name=str(user), icon_url=user.avatar.url)
        e.set_image(url=user.avatar.url)
        await ctx.send(embed=e)

    def extract_track_id(self, url):
        pattern = r'/track/(\w+)'
        match = re.search(pattern, url)
        if match:
            track_id = match.group(1)
            return track_id
        else:
            return None

    async def generate_thumbnail(self, url: str):
        identifier = self.extract_track_id(url)
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://embed.spotify.com/oembed/?url=spotify:track:{identifier}") as r:
                data = await r.json()
                return data['thumbnail_url']

    @commands.hybrid_command(aliases=["ac", "actv"])
    @commands.guild_only()
    async def activity(self, ctx: GuildContext, *, user: Optional[Union[discord.User, discord.Member]] = None):
        """Shows a user's activity."""
        async with ctx.typing():
            if user is None:
                user = ctx.author

            if not isinstance(user, discord.Member):
                try:
                    user = await ctx.guild.fetch_member(user.id)
                except discord.NotFound:
                    return await ctx.send('User not found.')
                
            if user is None:
                return await ctx.send('User not found.')

            if len(user.activities) == 0:
                return await ctx.send('User has no activities.')
            
            if isinstance(user, discord.Member):
                if not user.guild.chunked:
                    async with ctx.typing():
                        await user.guild.chunk(cache=True)
            

            e = discord.Embed(colour=self.bot.color)
            e.set_author(name=str(user), icon_url=user.avatar.url)
        
            if user.activities is not None:
                for activity in user.activities:
                    if activity is not None:
                        if activity.type == discord.ActivityType.listening and activity.album is not None: 
                            if activity.name == "Spotify":
                                e.set_thumbnail(url=await self.generate_thumbnail(activity.track_url))
                                e.add_field(name='Listening to', value=f'[{activity.title}]({activity.track_url}) by {activity.artist}', inline=False)  

                        if activity.type == discord.ActivityType.playing:
                            e.add_field(name='Playing', value=f'{activity.name}', inline=False)

                        if activity.type == discord.ActivityType.streaming:
                            e.add_field(name='Streaming', value=f'{activity.name}', inline=False)

                        if activity.type == discord.ActivityType.watching:
                            e.add_field(name='Watching', value=f'{activity.name}', inline=False)

                        if activity.type == discord.ActivityType.custom:
                            e.add_field(name='Custom', value=f'{activity.name}', inline=False)

                        if activity.type == discord.ActivityType.unknown:
                            e.add_field(name='Unknown', value=f'{activity.name}', inline=False)
            await ctx.send(embed=e)

    @commands.hybrid_group(name='define')
    async def _define(self, ctx: Context, *, word: Optional[str] = None):
        """Looks up an English word in the dictionary."""

        result = await parse_free_dictionary_for_word(self.bot.session, word=word)
        if result is None:
            return await ctx.send('Could not find that word.', ephemeral=True)

        phrase = discord.utils.find(lambda v: v.word.lower() == word.lower(), result.phrasal_verbs)
        if phrase is not None:
            embed = phrase.to_embed()
            embed.color = self.bot.color
            return await ctx.send(embed=embed)

        if not result.meanings:
            return await ctx.send('Could not find any definitions for that word.', ephemeral=True)

        pages = Pages(FreeDictionaryWordMeaningPageSource(result), ctx=ctx, compact=True)
        await pages.start()

    @commands.command(name="urban")
    async def urban(self, ctx: Context, *, word: Optional[str] = None):
        """Searches urban dictionary."""

        url = 'http://api.urbandictionary.com/v0/define'
        async with self.bot.session.get(url, params={'term': word}) as resp:
            if resp.status != 200:
                return await ctx.send(f'An error occurred: {resp.status} {resp.reason}')

            js = await resp.json()
            data = js.get('list', [])
            if not data:
                return await ctx.send('No results found, sorry.')

        pages = Pages(UrbanDictionaryPageSource(data), ctx=ctx)
        await pages.start()


    @_define.command(name='word')
    @app_commands.describe(word='The word to look up')
    async def _define_word(self, ctx: Context, *, word: str):
        """Looks up an English word in the dictionary."""

        result = await parse_free_dictionary_for_word(self.bot.session, word=word)
        if result is None:
            return await ctx.send('Could not find that word.', ephemeral=True)

        phrase = discord.utils.find(lambda v: v.word.lower() == word.lower(), result.phrasal_verbs)
        if phrase is not None:
            embed = phrase.to_embed()
            embed.color = self.bot.color
            return await ctx.send(embed=embed)

        if not result.meanings:
            return await ctx.send('Could not find any definitions for that word.', ephemeral=True)

        pages = Pages(FreeDictionaryWordMeaningPageSource(result), ctx=ctx, compact=True)
        await pages.start()

    @_define.command(name='urban')
    async def _define_urban(self, ctx: Context, *, word: str):
        """Searches urban dictionary."""

        url = 'http://api.urbandictionary.com/v0/define'
        async with self.bot.session.get(url, params={'term': word}) as resp:
            if resp.status != 200:
                return await ctx.send(f'An error occurred: {resp.status} {resp.reason}')

            js = await resp.json()
            data = js.get('list', [])
            if not data:
                return await ctx.send('No results found, sorry.')

        pages = Pages(UrbanDictionaryPageSource(data), ctx=ctx)
        await pages.start()

    @_define.autocomplete('word')
    async def _define_word_autocomplete(
        self, interaction: discord.Interaction, query: str
    ) -> list[app_commands.Choice[str]]:
        if not query:
            return []

        result = await free_dictionary_autocomplete_query(self.bot.session, query=query)
        return [app_commands.Choice(name=word, value=word) for word in result][:25]
    
    @commands.hybrid_command()
    @app_commands.describe(message="The message to translate (please use original language script not english/latin script)")
    async def translate(self, ctx: Context, *, message: Annotated[Optional[str], commands.clean_content] = None):
        """Translates a message to English using Google translate.
        """
        loop = self.bot.loop
        async with ctx.typing():
            if message is None:
                reply = ctx.replied_message
                if reply is not None:
                    message = reply.content
                else:
                    return await ctx.send('Missing a message to translate')

            try:
                result = await translate(message, session=self.bot.session)
            except Exception as e:
                return await ctx.send(f'An error occurred: {e.__class__.__name__}: {e}')

            embed = discord.Embed(colour=self.bot.color)
            embed.add_field(name=f'{result.source_language} ->', value=result.original)
            embed.add_field(name=f'{result.target_language}', value=result.translated)
            await ctx.send(embed=embed)

    async def translate_ctx(self, interaction: discord.Interaction, message: discord.Message):
        """Translates a message to English using Google translate.
        """
        try:
            result = await translate(message.content, session=self.bot.session)
            
            embed = discord.Embed(colour=self.bot.color)
            embed.add_field(name=f'{result.source_language} ->', value=result.original)
            embed.add_field(name=f'{result.target_language}', value=result.translated)
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            return await interaction.response.send_message(f'An error occurred: {e.__class__.__name__}: {e}')
        
    async def gtranslate_autocomplete(self, interaction: discord.Interaction, current: str):
        if not current:
            return []
        print(current)

        choices  = [
            app_commands.Choice(name=v, value=k)
            for k, v in config.LANGUAGES if current.lower() in v or current.lower() in k
        ]
        return choices[:5]
            
    def generate_id(self):
        letters_and_digits = string.ascii_letters + string.digits
        result_str = ''.join(random.choice(letters_and_digits) for i in range(6))
        return result_str

    @commands.hybrid_group()
    @app_commands.describe(tag="The tag to search for")
    async def tag(self, ctx: Context, tag: Optional[str] = None):
        """
        Tag creation and management. do `r.tag help` for more information.

        `tag` is the name or id of the tag

        example:
        `r.tag hello`
        `r.tag XjhUsd`
        `r.tag create hello Hello world!`
        `r.tag delete hello`
        """
        search = tag
        if search is None:
            return await ctx.reply("You need to provide a tag name or id!")
        
        if ctx.interaction:
            await ctx.interaction.response.defer()

        async with self.bot.db.cursor() as cur:
            await cur.execute(
                "SELECT * FROM tags WHERE tag_name = ? OR tag_id = ?",
                (search, search)
            )
            data = await cur.fetchone()
            if not data:
                return await ctx.reply("That tag doesn't exist!")
            
            await ctx.channel.send(data[2])
            if ctx.interaction:
                await ctx.send(data[2])

        async with self.bot.db.cursor() as cur:
            await cur.execute(
                "UPDATE tags SET tag_uses = tag_uses + 1 WHERE tag_name = ? OR tag_id = ?",
                (search, search)
            )
            await self.bot.db.commit()
       

    @tag.command(name="create")
    @app_commands.describe(name="The name of the tag")
    @app_commands.describe(content="The content of the tag")
    async def tag_create(self, ctx: Context, name: str, *, content: str):
        """
        Create a tag.

        `name` is the name of the tag
        `content` is the content of the tag

        example:
        `r.tag create hello Hello world!`
        """
        if ctx.interaction:
            await ctx.interaction.response.defer()

        if len(content) > 1990:
            return await ctx.reply("That tag content is too long! Max length is 1990 characters.")
        
        random_id = self.generate_id()

        async with self.bot.db.cursor() as cur:
            await cur.execute(
                """
                SELECT * FROM tags WHERE tag_name = ? AND tag_guild_id = ?
                """,
                (name, ctx.guild.id)
            )
            if await cur.fetchone():
                return await ctx.reply("That tag already exists!")
            
            data = await cur.fetchall()
            
            for row in data:
                if row[0] == name:
                    return await ctx.reply("That tag already exists!")
                
                if row[1] == random_id:
                    random_id = self.generate_id()
                
            await cur.execute(
                """
                INSERT INTO tags (tag_id, tag_name, tag_content, tag_owner_id, tag_guild_id, tag_uses, tag_created_at) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    random_id,
                    name,
                    content,
                    ctx.author.id,
                    ctx.guild.id,
                    0,
                    ctx.message.created_at
                )
            )
            await self.bot.db.commit()
            embed=discord.Embed()
            embed.description = f"<:plus:1172608535050338434> | **Name:** `{name}` **ID:** `{random_id}`"
            embed.color = self.bot.color
            await ctx.channel.send(embed=embed)
            if ctx.interaction:
                await ctx.interaction.followup.send(embed=embed)

    @tag.command(name="show")
    @app_commands.describe(search="The argument to search for")
    async def tag_show(self, ctx: Context, search: Optional[str]):
        """
        Show a tag.

        `name` is the name of the tag
        `id` is the id of the tag
        *don't use both

        example:
        `r.tag show hello`
        """
        if search is None:
            return await ctx.reply("You need to provide a tag name or id!")
        
        if ctx.interaction:
            await ctx.interaction.response.defer()

        async with self.bot.db.cursor() as cur:
            await cur.execute(
                "SELECT * FROM tags WHERE tag_name = ? OR tag_id = ?",
                (search, search)
            )
            data = await cur.fetchone()
            if not data:
                return await ctx.reply("That tag doesn't exist!")
            
            await ctx.channel.send(data[2])
            if ctx.interaction:
                await ctx.send(data[2])

        async with self.bot.db.cursor() as cur:
            await cur.execute(
                "UPDATE tags SET tag_uses = tag_uses + 1 WHERE tag_name = ? OR tag_id = ?",
                (search, search)
            )
            await self.bot.db.commit()


    @tag.command(name="edit")
    @app_commands.describe(search="The tag to search for")
    async def tag_edit(self, ctx: Context, search: str):
        """
        Edit a tag.

        `search` is the name or id of the tag

        example:
        `r.tag edit hello`
        """
        if search is None:
                return await ctx.reply("You need to provide a tag name or id!", delete_after=5)

        async with self.bot.db.cursor() as cur:
            await cur.execute(
                "SELECT * FROM tags WHERE tag_name = ? OR tag_id = ?",
                (search, search)
            )
            data = await cur.fetchone()
            if not data:
                return await ctx.reply("That tag doesn't exist!")
            
            owner = self.bot.get_user(data[3])
            if ctx.author.id != owner.id:
                return await ctx.reply("You don't own that tag!", ephemeral=True)

            if ctx.interaction:
                await ctx.interaction.response.send_modal(TagEdit(tag_name=search, bot=self.bot))
            else:
                await ctx.reply(view=TagEditButton(tag_name=search, user=ctx.author, bot=self.bot))

    @tag.command(name="list")
    async def tag_list(
        self,
        ctx: Context,
        *,
        member: Optional[discord.Member] = None
    ):
        """
        List all tags.

        `member` is the member to list tags for (optional)

        example:
        `r.tag list`
        """
        if ctx.interaction:
            await ctx.interaction.response.defer()

        async with self.bot.db.cursor() as cur: 
            if member is not None:
                await cur.execute(
                    "SELECT * FROM tags WHERE tag_owner_id = ? AND tag_guild_id = ?",
                    (member.id, ctx.guild.id)
                )
            else:
                await cur.execute(
                    "SELECT * FROM tags WHERE tag_guild_id = ?",
                    (ctx.guild.id,)
                )
            data = await cur.fetchall()

        if member is not None:
            if not data:
                return await ctx.reply("That member doesn't have any tags!")
            
            tags = []
            for row in data:
                tags.append(f"id: `{row[0]}` name: `{row[1]}`")
            page = SimplePages(entries=tags, ctx=ctx, per_page=5)
            page.embed.title = f"Tags for {member.name}"
            page.embed.color=self.bot.color
            await page.start()

        else:
            if not data:
                return await ctx.reply("This server doesn't have any tags!")
            
            tags = []
            for row in data:
                tags.append(f"id: `{row[0]}` name: `{row[1]}`")
            
            page = SimplePages(entries=tags, ctx=ctx, per_page=5)
            page.embed.title = f"Tags for {ctx.guild.name}"
            page.embed.color=self.bot.color
            await page.start()

    @tag.command(name="info")
    @app_commands.describe(search="The tag to search for")
    async def tag_info(self, ctx: Context, search: Optional[str]):
        """
        Get info about a tag.

        `search` is the name or id of the tag

        example:
        `r.tag info hello`
        """
        if search is None:
            return await ctx.reply("You need to provide a tag name or id!")
        
        if ctx.interaction:
            await ctx.interaction.response.defer()

        async with self.bot.db.cursor() as cur:
            await cur.execute(
                "SELECT * FROM tags WHERE tag_name = ? OR tag_id = ?",
                (search, search)
            )
            data = await cur.fetchone()
            if not data:
                return await ctx.reply("That tag doesn't exist!")
            if len(data[2]) > 100:
                x = f" `+{len(data[2]) - 100} characters`\n"
            else:
                x = "\n"

            embed=discord.Embed()
            embed.description = (
                f"**Name**: `{data[1]}`\n"
                f"**ID**: `{data[0]}`\n"
                f"**Content**: {truncate_string(value=data[2], max_length=100)}{x}"
                f"**Uses**: `{data[5]}`\n"
                f"**Owner**: `{self.bot.get_user(data[3]).name}`\n"
                f"**Created At**: `{format_datetime_human_readable(dt=datetime.datetime.fromisoformat(data[6]).astimezone(datetime.timezone.utc))}`\n"
            )
            await ctx.send(embed=embed)
            
            
    @tag.command(name="delete")
    @app_commands.describe(search="The tag to search for")
    async def tag_delete(
        self,
        ctx: Context,
        search: Optional[str],
    ):
        """
        Delete a tag.
        
        `search` is the name or id of the tag
        
        example:
        `r.tag delete hello`
        `r.tag delete kxUhsI`
        """
        if ctx.interaction:
            await ctx.interaction.response.defer()

        if search is None:
            return await ctx.reply("You need to provide a tag name or id!")
        async with self.bot.db.cursor() as cur:
            await cur.execute(
                "SELECT * FROM tags WHERE tag_name = ? OR tag_id = ?",
                (search, search)
            )
            data = await cur.fetchone()
            if not data:
                return await ctx.reply("That tag doesn't exist!")
            
            if data[3] != ctx.author.id:
                return await ctx.reply("You don't own that tag!", ephemeral=True)
            
            await cur.execute(
                "DELETE FROM tags WHERE tag_name = ? OR tag_id = ?",
                (search, search)
            )
            await self.bot.db.commit()
            await ctx.reply(embed=discord.Embed(description=f"<:trash:1172606399595937913> | **Name:** `{data[1]}` **ID:** `{data[0]}`", color=self.bot.color))

    @tag.command()
    @commands.guild_only()
    @app_commands.describe(query='The tag name to search for')
    async def search(self, ctx: GuildContext, *, query: Annotated[str, commands.clean_content]):
        """Searches for a tag.

        The query must be at least 3 characters.
        """

        if len(query) < 3:
            return await ctx.send('The query length must be at least three characters.')

        async with self.bot.db.cursor() as cur:
            await cur.execute(
                """
                SELECT tag_name, tag_uses
                FROM tags
                WHERE tag_name LIKE ?
                AND tag_guild_id = ?
                ORDER BY tag_uses DESC
                LIMIT 20
                """,
                (f'%{query}%', ctx.guild.id)
            )
            results = await cur.fetchall()

        x = []
        for result in results:
            x.append(result[0])

        if results:
            p = SimplePages(entries=x, per_page=10, ctx=ctx)
            p.embed.title = f'Results for "{query}"'
            p.embed.color = self.bot.color
            await p.start()
        else:
            await ctx.send('No tags found.')


    @commands.hybrid_command()
    @commands.guild_only()
    async def poll(self, ctx: GuildContext, *, question: str):
        """
        Interactively creates a poll with the given question.

        To vote, use reactions!
        """

        # a list of messages to delete when we're all done
        messages: list[discord.Message] = [ctx.message]
        answers = []

        def check(m: discord.Message):
            return m.author == ctx.author and m.channel == ctx.channel and len(m.content) <= 100

        for i in range(20):
            messages.append(await ctx.send(f'Say poll `option (yes, no, whatever, bla)` or `publish` to publish poll.'))

            try:
                entry = await self.bot.wait_for('message', check=check, timeout=60.0)
            except asyncio.TimeoutError:
                break
        

            messages.append(entry)

            if entry.clean_content.startswith(f'publish'):
                break

            answers.append((to_emoji(i), entry.clean_content))

        try:
            await ctx.channel.delete_messages(messages)
        except:
            pass  # oh well

        answer = '\n'.join(f'{keycap}: {content}' for keycap, content in answers)
        actual_poll = await ctx.send(f'{ctx.author} asks: {question}\n\n{answer}')
        for emoji, _ in answers:
            await actual_poll.add_reaction(emoji)

    @poll.error
    async def poll_error(self, ctx: GuildContext, error: commands.CommandError):
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send('Missing the question.')
        
    # @commands.hybrid_group()
    # async def sticky(self, ctx: Context):
    #     """
    #     Sticky messages. do `r.help sticky` for more information.
    #     """
    #     await ctx.send_help(ctx.command)

    # @sticky.command(name="set")
    # @app_commands.describe(channel="The channel for sending sticky message" ,message="The message")
    # async def sticky_set(self, ctx: Context, channel:Optional[discord.TextChannel], *, message: str):
    #     """
    #     Set a sticky message.

    #     `channel` is the channel for sending sticky message
    #     `message` is the message

    #     example:
    #     `r.sticky set #general Hello world!`
    #     """
    #     if channel is None:
    #         channel = ctx.channel

    #     async with self.bot.db.cursor() as cur:
    #         await cur.execute(
    #             """
    #             SELECT * FROM sticky WHERE sticky_channel_id = ?
    #             """,
    #             (channel.id,)
    #         )
    #         if await cur.fetchone():
    #             return await ctx.reply("That channel already has a sticky message!")
            
    #         await cur.execute(
    #             """
    #             INSERT INTO sticky (sticky_channel_id, sticky_message) VALUES (?, ?)
    #             """,
    #             (
    #                 channel.id,
    #                 message
    #             )
    #         )
    #         await self.bot.db.commit()
    #         await ctx.reply(embed=discord.Embed(description=f"<:plus:1172608535050338434> | **Channel:** {channel.mention} **Message:** {message}", color=self.bot.color))

    # @sticky.command(name="delete", aliases=["del"])
    # @app_commands.describe(channel="The channel for deleting sticky message")
    # async def sticky_delete(self, ctx: Context, channel: discord.TextChannel):
    #     """
    #     Delete a sticky message.

    #     `channel` is the channel for deleting sticky message

    #     example:
    #     `r.sticky delete #general`
    #     """
    #     if ctx.interaction:
    #         await ctx.interaction.response.defer()

    #     async with self.bot.db.cursor() as cur:
    #         await cur.execute(
    #             """
    #             SELECT * FROM sticky WHERE sticky_channel_id = ?
    #             """,
    #             (channel.id,)
    #         )
    #         if not await cur.fetchone():
    #             return await ctx.reply("That channel doesn't have a sticky message!")
            
    #         await cur.execute(
    #             """
    #             DELETE FROM sticky WHERE sticky_channel_id = ?
    #             """,
    #             (channel.id,)
    #         )
    #         await self.bot.db.commit()
    #         await ctx.reply(embed=discord.Embed(description=f"<:trash:1172606399595937913> | **Channel:** {channel.mention}", color=self.bot.color))

    # @commands.Cog.listener("on_message")
    # async def sticky_message(self, message: discord.Message):
    #     async with self.bot.db.cursor() as cur:
    #         await cur.execute(
    #             """
    #             SELECT * FROM sticky WHERE sticky_channel_id = ?
    #             """,
    #             (message.channel.id,)
    #         )
    #         if message.author.bot:
    #             return
    #         data = await cur.fetchone()

    #         if not data:
    #             return
            
    #         if message.channel.id == data[0]:
    #             await message.channel.send(data[1])
    #         else:
    #             return