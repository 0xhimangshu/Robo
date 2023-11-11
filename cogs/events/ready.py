import discord
import json
from discord.ext import commands
from core import Robo
from utils.buttons import LockView
from utils.webhook import send_webhook2
from discord.gateway import DiscordWebSocket

async def identify(self) -> None:
    """Sends the IDENTIFY packet."""
    payload = {
        'op': self.IDENTIFY,
        'd': {
            'token': self.token,
            'properties': {
                'os': "Discord Android",
                'browser': 'Discord Android',
                'device': 'himangshu\'s machine',
            },
            'compress': True,
            'large_threshold': 250,
        },
    }

    if self.shard_id is not None and self.shard_count is not None:
        payload['d']['shard'] = [self.shard_id, self.shard_count]

    state = self._connection

    if state._intents is not None:
        payload['d']['intents'] = state._intents.value

    await self.call_hooks('before_identify', self.shard_id, initial=self._initial_identify)
    await self.send_as_json(payload)

DiscordWebSocket.identify = identify

class EvnetReady(commands.Cog):
    def __init__(self, bot: Robo):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.logger.info(f"Logged in as {self.bot.user}")

        self.bot.add_view(LockView())

        # await send_webhook2(
        #     f"Logged in as {self.bot.user}"
        # )


        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="You 👀"
            )
        )

        with open("data/stats.json", "r") as f:
            data = json.load(f)

        if data["boot_m"]["sent"] == "true":
            return
        else:
            for g in self.bot.guilds:
                for c in g.text_channels:
                    if c.id == data["boot_m"]["id"]:
                        try:
                            await c.send("Rebooted successfully!")
                            data["boot_m"]["sent"] = "true"
                            data["boot_m"]["id"] = "null"
                            with open("data/stats.json", "w") as f:
                                json.dump(data, f, indent=4)
                        except Exception as e:
                            print(e)
                            pass