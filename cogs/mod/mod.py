import datetime
import io
import re
from collections import Counter
from typing import Annotated, Any, Callable, Literal, Optional, Union

import discord
from discord import app_commands
from discord.ext import commands

from core import Robo
from utils import checks
from utils.context import Context, GuildContext
from utils.converter import MemberConverter, Snowflake
from utils.formats import plural


class PurgeFlags(commands.FlagConverter):
    user: Optional[discord.User] = commands.flag(description="Remove messages from this user", default=None)
    contains: Optional[str] = commands.flag(
        description='Remove messages that contains this string (case sensitive)', default=None
    )
    prefix: Optional[str] = commands.flag(
        description='Remove messages that start with this string (case sensitive)', default=None
    )
    suffix: Optional[str] = commands.flag(
        description='Remove messages that end with this string (case sensitive)', default=None
    )
    after: Annotated[Optional[int], Snowflake] = commands.flag(
        description='Search for messages that come after this message ID', default=None
    )
    before: Annotated[Optional[int], Snowflake] = commands.flag(
        description='Search for messages that come before this message ID', default=None
    )
    bot: bool = commands.flag(description='Remove messages from bots (not webhooks!)', default=False)
    webhooks: bool = commands.flag(description='Remove messages from webhooks', default=False)
    embeds: bool = commands.flag(description='Remove messages that have embeds', default=False)
    files: bool = commands.flag(description='Remove messages that have attachments', default=False)
    emoji: bool = commands.flag(description='Remove messages that have custom emoji', default=False)
    reactions: bool = commands.flag(description='Remove messages that have reactions', default=False)
    require: Literal['any', 'all'] = commands.flag(
        description='Whether any or all of the flags should be met before deleting messages. Defaults to "all"',
        default='all',
    )

class MassbanFlags(commands.FlagConverter):
    channel: Optional[Union[discord.TextChannel, discord.Thread, discord.VoiceChannel]] = commands.flag(
        description='The channel to search for message history', default=None
    )
    reason: Optional[str] = commands.flag(description='The reason to ban the members for', default=None)
    username: Optional[str] = commands.flag(description='The regex that usernames must match', default=None)
    bot: bool = commands.flag(description='ban bots (not webhooks!)', default=False)
    created: Optional[int] = commands.flag(
        description='Matches users whose accounts were created less than specified minutes ago.', default=None
    )
    joined: Optional[int] = commands.flag(
        description='Matches users that joined less than specified minutes ago.', default=None
    )
    joined_before: Optional[discord.Member] = commands.flag(
        description='Matches users who joined before this member', default=None, name='joined-before'
    )
    joined_after: Optional[discord.Member] = commands.flag(
        description='Matches users who joined after this member', default=None, name='joined-after'
    )
    avatar: Optional[bool] = commands.flag(
        description='Matches users depending on whether they have avatars or not', default=None
    )
    role: Optional[discord.Role] = commands.flag(
        description='Matches users depending on whether they have the role or not', default=None
    )
    roles: Optional[bool] = commands.flag(
        description='Matches users depending on whether they have roles or not', default=None
    )
    show: bool = commands.flag(description='Show members instead of banning them', default=False)
    
    # Message history related flags
    contains: Optional[str] = commands.flag(description='The substring to search for in the message.', default=None)
    starts: Optional[str] = commands.flag(description='The substring to search if the message starts with.', default=None)
    ends: Optional[str] = commands.flag(description='The substring to search if the message ends with.', default=None)
    match: Optional[str] = commands.flag(description='The regex to match the message content to.', default=None)
    search: commands.Range[int, 1, 2000] = commands.flag(description='How many messages to search for', default=100)
    after: Annotated[Optional[int], Snowflake] = commands.flag(
        description='Messages must come after this message ID.', default=None
    )
    before: Annotated[Optional[int], Snowflake] = commands.flag(
        description='Messages must come before this message ID.', default=None
    )
    files: Optional[bool] = commands.flag(description='Whether the message should have attachments.', default=None)
    embeds: Optional[bool] = commands.flag(description='Whether the message should have embeds.', default=None)

class ActionReason(commands.Converter):
    async def convert(self, ctx: GuildContext, argument: str):
        ret = f'{ctx.author} (ID: {ctx.author.id}): {argument}'

        if len(ret) > 512:
            reason_max = 512 - len(ret) + len(argument)
            raise commands.BadArgument(f'Reason is too long ({len(argument)}/{reason_max})')
        return ret


def can_execute_action(ctx: GuildContext, user: discord.Member, target: discord.Member) -> bool:
    return user.id == ctx.bot.owner_id or user == ctx.guild.owner or user.top_role > target.top_role
    
class Mod(commands.Cog):
    """Commands for guild moderation."""
    def __init__(self, bot : Robo):
        self.bot = bot

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(
            id=1169530523434090557,
            name="Hammer"
        )

    @commands.hybrid_command(aliases=["remove", "clear", "clean"], usage='[search] [flags...]')
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(search='How many messages to search for')
    async def purge(self, ctx: GuildContext, search: Optional[commands.Range[int, 1, 2000]] = None, *, flags: PurgeFlags):
        """Removes messages that meet a criteria.

        This command uses a syntax similar to Discord's search bar.
        The messages are only deleted if all options are met unless
        the `require:` flag is passed to override the behaviour.

        The following flags are valid.

        `user:` Remove messages from the given user.
        `contains:` Remove messages that contain a substring.
        `prefix:` Remove messages that start with a string.
        `suffix:` Remove messages that end with a string.
        `after:` Search for messages that come after this message ID.
        `before:` Search for messages that come before this message ID.
        `bot: yes` Remove messages from Robos (not webhooks!)
        `webhooks: yes` Remove messages from webhooks
        `embeds: yes` Remove messages that have embeds
        `files: yes` Remove messages that have attachments
        `emoji: yes` Remove messages that have custom emoji
        `reactions: yes` Remove messages that have reactions
        `require: any or all` Whether any or all flags should be met before deleting messages.

        example:
        `purge user:@Robo 147#7445 contains:hello` - Removes messages from Robo Razi#7445  that contain hello.
        `purge search:100 contain:shit` Removes 100 message that contains shit
        `purge bot:yes` - Remove all bot message
        """
        if not ctx.interaction:
            await ctx.message.delete()
        predicates: list[Callable[[discord.Message], Any]] = []
        if flags.bot:
            if flags.webhooks:
                predicates.append(lambda m: m.author.bot)
            else:
                predicates.append(lambda m: (m.webhook_id is None or m.interaction is not None) and m.author.bot)
        elif flags.webhooks:
            predicates.append(lambda m: m.webhook_id is not None)

        if flags.embeds:
            predicates.append(lambda m: len(m.embeds))

        if flags.files:
            predicates.append(lambda m: len(m.attachments))

        if flags.reactions:
            predicates.append(lambda m: len(m.reactions))

        if flags.emoji:
            custom_emoji = re.compile(r'<:(\w+):(\d+)>')
            predicates.append(lambda m: custom_emoji.search(m.content))

        if flags.user:
            predicates.append(lambda m: m.author == flags.user)

        if flags.contains:
            predicates.append(lambda m: flags.contains in m.content)  # type: ignore

        if flags.prefix:
            predicates.append(lambda m: m.content.startswith(flags.prefix))  # type: ignore

        if flags.suffix:
            predicates.append(lambda m: m.content.endswith(flags.suffix))  # type: ignore

        require_prompt = False
        if not predicates:
            require_prompt = True
            predicates.append(lambda m: True)

        op = all if flags.require == 'all' else any

        def predicate(m: discord.Message) -> bool:
            r = op(p(m) for p in predicates)
            return r

        if flags.after:
            if search is None:
                search = 2000

        if search is None:
            search = 100

        if require_prompt:
            confirm = await ctx.confirm(f'Are you sure you want to delete {plural(search):message}?', timeout=30, author_id=ctx.author.id)
            if not confirm:
                return await ctx.send('Aborting.')
            

        before = discord.Object(id=flags.before) if flags.before else None
        after = discord.Object(id=flags.after) if flags.after else None
        if ctx.interaction is None:
            await ctx.defer()
        
        if before is None and ctx.interaction is not None:
            before = await ctx.interaction.original_response()

        if before is not None:
            before = discord.Object(id=before.id) # type: ignore

        try:
            deleted = await ctx.channel.purge(limit=search, before=before, after=after, check=predicate)
        except discord.Forbidden as e:
            return await ctx.send('I do not have permissions to delete messages.')
        except discord.HTTPException as e:
            return await ctx.send(f'Error: {e} (try a smaller search?)')

        spammers = Counter(m.author.display_name for m in deleted)
        deleted = len(deleted)
        messages = [f'{deleted} message{" was" if deleted == 1 else "s were"} removed.']
        if deleted:
            messages.append('')
            spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
            messages.extend(f'**{name}**: {count}' for name, count in spammers)

        to_send = '\n'.join(messages)

        if len(to_send) > 2000:
            await ctx.send(f'Successfully removed {deleted} messages.', delete_after=10)
        else:
            await ctx.send(to_send, delete_after=10)

    @commands.hybrid_command(usage='[flags...]')
    @commands.guild_only()
    @checks.hybrid_permissions_check(ban_members=True)
    async def massban(self, ctx: Context, *, args: MassbanFlags):
        """Mass bans multiple members from the server.

        This command uses a syntax similar to Discord's search bar. To use this command
        you and the bot must both have Ban Members permission. **Every option is optional.**

        Users are only banned **if and only if** all conditions are met.

        The following options are valid.

        `channel:` Channel to search for message history.
        `reason:` The reason for the ban.
        `regex:` Regex that usernames must match.
        `created:` Matches users whose accounts were created less than specified minutes ago.
        `joined:` Matches users that joined less than specified minutes ago.
        `joined-before:` Matches users who joined before the member ID given.
        `joined-after:` Matches users who joined after the member ID given.
        `avatar:` Matches users who have no avatar.
        `roles:` Matches users that have no role.
        `show:` Show members instead of banning them.

        Message history filters (Requires `channel:`):

        `contains:` A substring to search for in the message.
        `starts:` A substring to search if the message starts with.
        `ends:` A substring to search if the message ends with.
        `match:` A regex to match the message content to.
        `search:` How many messages to search. Default 100. Max 2000.
        `after:` Messages must come after this message ID.
        `before:` Messages must come before this message ID.
        `files:` Checks if the message has attachments.
        `embeds:` Checks if the message has embeds.
        """

        await ctx.defer()
        author = ctx.author
        members = []
        reason = args.reason
        if reason is None:
            reason = f"banned by {ctx.author} (ID: {ctx.author.id})"

        if args.channel:
            before = discord.Object(id=args.before) if args.before else None
            after = discord.Object(id=args.after) if args.after else None
            predicates = []
            if args.contains:
                predicates.append(lambda m: args.contains in m.content)
            if args.starts:
                predicates.append(lambda m: m.content.startswith(args.starts))
            if args.ends:
                predicates.append(lambda m: m.content.endswith(args.ends))
            if args.match:
                try:
                    _match = re.compile(args.match)
                except re.error as e:
                    return await ctx.send(f'Invalid regex passed to `match:` flag: {e}')
                else:
                    predicates.append(lambda m, x=_match: x.match(m.content))
            if args.embeds:
                predicates.append(args.embeds)
            if args.files:
                predicates.append(args.files)

            async for message in args.channel.history(limit=args.search, before=before, after=after):
                if all(p(message) for p in predicates):
                    members.append(message.author)
        else:
            if ctx.guild.chunked:
                members = ctx.guild.members
            else:
                async with ctx.typing():
                    await ctx.guild.chunk(cache=True)
                members = ctx.guild.members

        # member filters
        predicates = [
            lambda m: isinstance(m, discord.Member) and can_execute_action(ctx, author, m),  # Only if applicable
            lambda m: m.discriminator != '0000',  # No deleted users
        ]

        if args.bot:
            predicates.append(lambda m: m.bot)

        if args.username:
            try:
                _regex = re.compile(args.username)
            except re.error as e:
                return await ctx.send(f'Invalid regex passed to `username:` flag: {e}')
            else:
                predicates.append(lambda m, x=_regex: x.match(m.name))

        if args.avatar is False:
            predicates.append(lambda m: m.avatar is None)
        if args.roles is False:
            predicates.append(lambda m: len(getattr(m, 'roles', [])) <= 1)

        now = discord.utils.utcnow()
        if args.created:

            def created(member, *, offset=now - datetime.timedelta(minutes=args.created)):
                return member.created_at > offset

            predicates.append(created)
        if args.joined:

            def joined(member, *, offset=now - datetime.timedelta(minutes=args.joined)):
                if isinstance(member, discord.User):
                    # If the member is a user then they left already
                    return True
                return member.joined_at and member.joined_at > offset

            predicates.append(joined)
        if args.joined_after:

            def joined_after(member, *, _other=args.joined_after):
                return member.joined_at and _other.joined_at and member.joined_at > _other.joined_at

            predicates.append(joined_after)
        if args.joined_before:

            def joined_before(member, *, _other=args.joined_before):
                return member.joined_at and _other.joined_at and member.joined_at < _other.joined_at

            predicates.append(joined_before)

        # if len(predicates) == 3:
        #     return await ctx.send('Missing at least one filter to use')

        members = {m for m in members if all(p(m) for p in predicates)}
        if len(members) == 0:
            return await ctx.send('No members found matching criteria.')

        if args.show:
            members = sorted(members, key=lambda m: m.joined_at or now)
            fmt = "\n".join(f'{m.id}\tJoined: {m.joined_at}\tCreated: {m.created_at}\t{m}' for m in members)
            content = f'Current Time: {discord.utils.utcnow()}\nTotal members: {len(members)}\n{fmt}'
            file = discord.File(io.BytesIO(content.encode('utf-8')), filename='members.txt')
            return await ctx.send(file=file)

        if args.reason is None:
            return await ctx.send('`reason:` flag is required.')
        else:
            reason = await ActionReason().convert(ctx, args.reason)

        confirm = await ctx.confirm(f'This will ban **{plural(len(members)):member}**. Are you sure?')
        if not confirm:
            return await ctx.send('Aborting.')

        count = 0
    
        for member in members:
            try:
                await ctx.guild.ban(member, reason=reason)
            except discord.HTTPException:
                pass
            else:
                count += 1
        mem = ", ".join(f"{m.mention}" for m in members)
        await ctx.send(f'\nBanned {count}/{len(members)}\n{mem}')
        

    @massban.error
    async def massban_error(self, ctx: GuildContext, error: commands.CommandError):
        if isinstance(error, commands.FlagError):
            await ctx.send(str(error), ephemeral=True)

    # @commands.hybrid_command(with_app_command=True)
    # @commands.guild_only()
    # @commands.has_permissions(manage_guild=True)
    # @app_commands.describe(
    #     member='The user to mute. Can be a mention or ID.',
    #     until = 'How long the user should be muted for.',
    #     reason='The reason for the mute.'
    # )
    # @app_commands.choices(
    #     until=[
    #         app_commands.Choice(name='60 seconds', value=60),
    #         app_commands.Choice(name='5 minutes', value=5 * 60),
    #         app_commands.Choice(name='15 minutes', value=15 * 60),
    #         app_commands.Choice(name='1 hour', value=60 * 60),
    #         app_commands.Choice(name='6 hours', value=6 * 60 * 60),
    #         app_commands.Choice(name='1 day', value=24 * 60 * 60),
    #         app_commands.Choice(name='1 week', value=7 * 24 * 60 * 60),
    #         app_commands.Choice(name='1 month', value=28 * 24 * 60 * 60),
    #     ]
    # )
    # async def timeout(
    #     self,
    #     ctx: GuildContext,
    #     member: discord.Member=None,
    #     until: app_commands.Choice[int]=None,
    #     *,
    #     reason: Optional[str] = None,
    # ):
    #     """
    #     Timeout a member from the server.
        
    #     `member` can be a mention or id.
    #     `until` can be a choice or a number of seconds.
    #     `reason` is optional.
    #     """
        
    #     if member is None:
    #         return await ctx.error("You must specify a member to timeout.")
        
    #     if isinstance(member, int):
    #         member = await ctx.guild.fetch_member(member)
    #         if member is None:
    #             return await ctx.error("That member couldn't be found.")
            
    #     if ctx.interaction is None:
    #         await ctx.defer()

    #     if member.id == ctx.author.id:
    #         return await ctx.error("You can't timeout yourself!")
        
    #     if member.id == ctx.guild.owner_id:
    #         return await ctx.error("You can't timeout the owner!")
        
    #     if member.id == ctx.bot.user.id:
    #         return await ctx.error("You can't timeout me!")
        
    #     if member.top_role >= ctx.author.top_role:
    #         return await ctx.error("You can't timeout someone with a higher or equal role.")
        
    #     if member.top_role >= ctx.me.top_role:
    #         return await ctx.error("I can't timeout someone with a higher or equal role.")
        
    #     if reason is None:
    #         reason = f"Timed out by {ctx.author} (ID: {ctx.author.id}) for {until.name if until is not None else '60 seconds'}"

    #     if until is None:
    #         reason = f"Timed out by {ctx.author} (ID: {ctx.author.id}) for 60 seconds"
    #         await member.timeout(
    #             datetime.timedelta(seconds=60),
    #             reason=reason
    #         )
    #         await ctx.send(
    #             embed=discord.Embed(

    #                 description=f"Timed out {member.mention} for 60 seconds",
    #                 color=discord.Color.red()
    #             ),
    #             delete_after=60
    #         )
    #         return
        
    #     await member.timeout(
    #         datetime.timedelta(seconds=int(until.value)),
    #         reason=reason
    #     )
    #     await ctx.send(
    #         embed=discord.Embed(
    #             description=f"Timed out {member.mention} for {until.name}",
    #             color=discord.Color.red()
    #         ),
    #         delete_after=60
    #     )