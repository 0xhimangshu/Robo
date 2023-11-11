from typing import Optional
import discord
import json
import chat_exporter
import random
from discord.ext import commands
from core import Robo

class TicketReason(discord.ui.Modal, title="Ticket Reason"):
    reason = discord.ui.TextInput(
        label="Reason",
        placeholder="Enter your reason here",
        min_length=10,
        max_length=100,
    )
    def __init__(self, bot: Robo, user: discord.Member):
        super().__init__(timeout=None)
        self.user = user
        self.bot = bot
    

    async def on_submit(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)
        async with self.bot.db.cursor() as cur:
            await cur.execute("SELECT * FROM tickets WHERE ticket_guild_id = ?", (interaction.guild.id,))
            data = await cur.fetchall()
 
        data = data[0]
        category = discord.utils.get(interaction.guild.categories, id=data[1])
        role = interaction.guild.get_role(data[3])
        ticket = await interaction.guild.create_text_channel(f"ticket-{interaction.user.name}", category=category)
        await ticket.set_permissions(interaction.user, read_messages=True, send_messages=True)
        await ticket.set_permissions(interaction.guild.default_role, read_messages=False, send_messages=False)
        await ticket.set_permissions(interaction.guild.me, read_messages=True, send_messages=True)
        await interaction.followup.send(f"Your ticket has been created at {ticket.mention}", ephemeral=True)
        await ticket.send(embed=discord.Embed(
            title="Ticket Created",
            description=(
                f"Hello {interaction.user.mention},\n"
                f"Thank you for creating a ticket, Please wait for our staff to respond to your ticket.\n"
                f"Reason: {self.reason.value}"
            )
        ), 
        view=TicketClose(user=interaction.user)
        )
        if role is not None:
            await ticket.send(f"{role.mention} check this ticket")
        await ticket.send(f"{interaction.user.mention} please wait for our staff to respond to your ticket", delete_after=30)
        
class TicketCreate(discord.ui.View):
    def __init__(self, bot: Robo):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.green, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(TicketReason(user=interaction.user, bot=self.bot))
        except Exception as e:
            print(e)

        
class TicketClose(discord.ui.View):
    def __init__(self, user: discord.Member):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        string = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890"
        idx = ""
        for i in range(5):
            idx += random.choice(string)

        data = await chat_exporter.export(interaction.channel)
        with open(f"transcripts/{interaction.user.id}-{idx}.html", "w") as f:
            f.write(data)

        await interaction.user.send(f"Your ticket has been closed", file=discord.File(f"transcripts/{interaction.user.id}-{idx}.html"))
        await interaction.channel.delete()