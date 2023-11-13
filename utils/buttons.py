
from __future__ import annotations
from typing import List, NamedTuple, Optional, Union, Generic, TypeVar, Callable, Any
import discord
from discord.interactions import Interaction
import config
import asyncio
import io
from discord.ext.commands import Context
from discord.ext import commands

T = TypeVar('T')

class LinkType(NamedTuple):
    name: Optional[str] = None
    url: Optional[str] = None
    emoji: Optional[str] = None

class LinkButton(discord.ui.View):
    def __init__(self, links: Union[LinkType, List[LinkType]]):
        super().__init__()

        links = links if isinstance(links, list) else [links]

        for link in links:
            self.add_item(discord.ui.Button(label=link.name, url=link.url, emoji=link.emoji))

class ConfirmationView(discord.ui.View):
    def __init__(self, *, timeout: float, author_id: int, delete_after: bool) -> None:
        super().__init__(timeout=timeout)
        self.value: Optional[bool] = None
        self.delete_after: bool = delete_after
        self.author_id: int = author_id
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.author_id:
            return True
        else:
            await interaction.response.send_message('This confirmation dialog is not for you.', ephemeral=True)
            return False

    async def on_timeout(self) -> None:
        if self.delete_after and self.message:
            await self.message.delete()

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        await interaction.response.defer()
        if self.delete_after:
            await interaction.delete_original_response()

        self.stop()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        await interaction.response.defer()
        if self.delete_after:
            await interaction.delete_original_response()
        self.stop()

class LockView(discord.ui.View):
    def __init__(self, timeout=None):
        super().__init__(timeout=timeout)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
       if interaction.user.guild_permissions.manage_channels:
            return True
       else:
            await interaction.response.send_message("You cannot use this button.", ephemeral=True)
            return False
    
    @discord.ui.button(emoji="🔓", style=discord.ButtonStyle.grey, custom_id="lock")
    async def unlock(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = False
        overwrites = {
                    self.ctx.guild.default_role: discord.PermissionOverwrite(send_messages = True, read_message_history = True),
                    self.ctx.guild.me: discord.PermissionOverwrite(view_channel = True, send_messages = True, read_message_history = True),
                }
        await self.ctx.channel.edit(overwrites=overwrites)
        button.disabled = True
        self.lock.disabled = False
        await interaction.response.edit_message(embed=discord.Embed(description=f"Unlocked {self.ctx.channel.mention}", color=discord.Color.green()) ,view=self)

    @discord.ui.button(emoji="🔒", style=discord.ButtonStyle.grey, disabled=True, custom_id="unlock")
    async def lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        overwrites = {
                self.ctx.guild.default_role: discord.PermissionOverwrite(send_messages = False, read_message_history = False),
                self.ctx.guild.me: discord.PermissionOverwrite(view_channel = True, send_messages = True, read_message_history = True),
            }
        await self.ctx.channel.edit(overwrites=overwrites)
        button.disabled = True
        self.unlock.disabled = False
        await interaction.response.edit_message(embed=discord.Embed(description=f"Locked {self.ctx.channel.mention}", color=discord.Color.red()) ,view=self)

class SomeLinks(discord.ui.View):
    def __init__(self, *, timeout = None):
        super().__init__(timeout=timeout)
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="Support", url=config.support))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="Invite", url=config.invite))

class DisambiguatorView(discord.ui.View, Generic[T]):
    message: discord.Message
    selected: T

    def __init__(self, ctx: Context, data: list[T], entry: Callable[[T], Any]):
        super().__init__()
        self.ctx: Context = ctx
        self.data: list[T] = data

        options = []
        for i, x in enumerate(data):
            opt = entry(x)
            if not isinstance(opt, discord.SelectOption):
                opt = discord.SelectOption(label=str(opt))
            opt.value = str(i)
            options.append(opt)

        select = discord.ui.Select(options=options)

        select.callback = self.on_select_submit
        self.select = select
        self.add_item(select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message('This select menu is not meant for you, sorry.', ephemeral=True)
            return False
        return True

    async def on_select_submit(self, interaction: discord.Interaction):
        index = int(self.select.values[0])
        self.selected = self.data[index]
        await interaction.response.defer()
        if not self.message.flags.ephemeral:
            await self.message.delete()

        self.stop()