import wavelink
import discord
from discord.ext import commands

from core import Robo
from wavelink.ext import spotify
from utils.context import Context

class Music(commands.Cog):
    def __init__(self, bot: Robo):
        self.bot = bot

    async def cog_load(self):
        # node1: wavelink.Node = wavelink.Node(
        #     id="Robo Music 1",
        #     uri=f"{self.bot.config.lavalink_host}:{self.bot.config.lavalink_port}",
        #     password=self.bot.config.lavalink_password,
        #     session=self.bot.session,
        # )
        # node2: wavelink.Node = wavelink.Node(
        #     id="Robo Music 2",
        #     uri="lava.link:80",
        #     password="youshallnotpass",
        #     session=self.bot.session,
        # )
        # node3: wavelink.Node = wavelink.Node(
        #     id="Robo Music 3",
        #     uri="localhost:80",
        #     password="youshallnotpass",
        #     session=self.bot.session,
        # )
        node4: wavelink.Node = wavelink.Node(
            id="Robo Music 4",
            uri="3.87.33.56:8746",
            password="notherhacker",
            session=self.bot.session,
            use_http=True,
        )
        sp: spotify.SpotifyClient =  spotify.SpotifyClient(
            client_id=self.bot.config.spotify_client_id,
            client_secret=self.bot.config.spotify_client_secret,
        )
        await wavelink.NodePool.connect(client=self.bot, nodes=[node4], spotify=sp)

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        self.bot.logger.info(f"Node {node.id} is ready!")

    @commands.Cog.listener()
    async def on_wavelink_node_error(self, node: wavelink.Node, error: Exception):
        self.bot.logger.error(f"Node {node.id} has error: {error}")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEventPayload):
        self.bot.logger.info(f"Track {payload.track.title} ended")
        try:
            await payload.player.play(payload.player.queue.get())
        except Exception as e:
            self.bot.logger.error(f"Error while playing next track: {e}")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackEventPayload):
        self.bot.logger.info(f"Track {payload.track.title} started")

    @commands.hybrid_command()
    async def play(
        self, 
        ctx: Context,
        query: str,
    ):
        """
        Play a song 

        `query`: The song name or url
        
        Example:
        `rxplay <query>`
        """
        if query is None:
            return await ctx.send("Please provide a song name or url")
        
        if ctx.voice_client is None:
            vc : wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player, self_deaf=True)
        else:
            vc : wavelink.Player = ctx.voice_client

        try:
            tracks = await wavelink.YouTubeTrack.search(query)
            if not tracks:
                return await ctx.send("No tracks found")
            
        except Exception as e:
            self.bot.logger.error(f"Error while searching for track: {e}")
            return await ctx.send("Error while searching for track")
        
        else:
            await vc.play(tracks[0])
            await ctx.send(f"Playing [{tracks[0].title}]({tracks[0].uri})")

