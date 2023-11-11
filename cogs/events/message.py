from discord.ext import commands    
import discord
import re
from core import Robo

class EventMessage(commands.Cog):
    def __init__(self, bot: Robo):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if m.content == "https://youtu.be/dQw4w9WgXcQ?si=S_6Rvo7gXLDpUgF3":
            await m.channel.send("`⚠️`Rickroll detected!")
            await m.delete()
            await m.author.edit(nick="Rick Astley")
            return
        if m.content == "https://www.youtube.com/watch?v=dQw4w9WgXcQ":
            await m.channel.send("`⚠️`Rickroll detected!")
            await m.delete()
            await m.author.edit(nick="Rick Astley")
            return
        if m.content == "https://youtu.be/dQw4w9WgXcQ":
            await m.channel.send("`⚠️`Rickroll detected!")
            await m.delete()
            await m.author.edit(nick="Rick Astley")
            return
        if m.content == "https://www.youtube.com/watch?v=dQw4w9WgXcQ":
            await m.channel.send("`⚠️`Rickroll detected!")
            await m.delete()
            await m.author.edit(nick="Rick Astley")
            return
        if m.content == "https://www.youtube.com/watch?v=DLzxrzFCyOs":
            await m.channel.send("`⚠️`Rickroll detected!")
            await m.delete()
            await m.author.edit(nick="Rick Astley")
            return
        if m.content == "https://youtu.be/DLzxrzFCyOs":
            await m.channel.send("`⚠️`Rickroll detected!")
            await m.delete()
            await m.author.edit(nick="Rick Astley")
            return
        if m.content == "https://youtu.be/ub82Xb1C8os":
            await m.channel.send("`⚠️`Rickroll detected!")
            await m.delete()
            await m.author.edit(nick="Rick Astley")
            return
        if m.content == "https://www.youtube.com/watch?v=ub82Xb1C8os":
            await m.channel.send("`⚠️`Rickroll detected!")
            await m.delete()
            await m.author.edit(nick="Rick Astley")
            return

