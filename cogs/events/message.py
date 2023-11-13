from discord.ext import commands    
import discord
import re
from core import Robo
import json

class EventMessage(commands.Cog):
    def __init__(self, bot: Robo):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        try:
            with open("data/guild.json", "r") as f:
                data = json.load(f)

            if m.author.bot:
                return

            # Check if guild exists
            guild_id = str(m.guild.id)
            if guild_id not in data["guilds"]:
                data["guilds"][guild_id] = {"channels": {}}

            # Check if channel exists in the guild
            channel_id = str(m.channel.id)
            if channel_id not in data["guilds"][guild_id]["channels"]:
                data["guilds"][guild_id]["channels"][channel_id] = {"members": {}}

            # Check if author exists in the channel
            author_id = str(m.author.id)
            if author_id not in data["guilds"][guild_id]["channels"][channel_id]["members"]:
                data["guilds"][guild_id]["channels"][channel_id]["members"][author_id] = {
                    "messages": 0,
                    "commands": 0,
                }

            with open("data/guild.json", "w") as f:
                json.dump(data, f, indent=4)

            # Reload data after writing to file
            with open("data/guild.json", "r") as f:
                data = json.load(f)

            for p in self.bot.config.prefixes:
                if m.content.startswith(p):
                    data["guilds"][guild_id]["channels"][channel_id]["members"][author_id]["commands"] += 1
                    break
            else:
                data["guilds"][guild_id]["channels"][channel_id]["members"][author_id]["messages"] += 1

            with open("data/guild.json", "w") as f:
                json.dump(data, f, indent=4)
                
        except Exception as e:
            self.bot.logger.info(f"Error in on_message: {e}")
