import discord
import json
from discord.ext import commands
from core import Robo
from utils.buttons import LockView
from utils.webhook import send_webhook2
from discord.gateway import DiscordWebSocket

never = """
#  NNNNNNNN        NNNNNNNNEEEEEEEEEEEEEEEEEEEEEEVVVVVVVV           VVVVVVVVEEEEEEEEEEEEEEEEEEEEEERRRRRRRRRRRRRRRRR   
#  N:::::::N       N::::::NE::::::::::::::::::::EV::::::V           V::::::VE::::::::::::::::::::ER::::::::::::::::R  
#  N::::::::N      N::::::NE::::::::::::::::::::EV::::::V           V::::::VE::::::::::::::::::::ER::::::RRRRRR:::::R 
#  N:::::::::N     N::::::NEE::::::EEEEEEEEE::::EV::::::V           V::::::VEE::::::EEEEEEEEE::::ERR:::::R     R:::::R
#  N::::::::::N    N::::::N  E:::::E       EEEEEE V:::::V           V:::::V   E:::::E       EEEEEE  R::::R     R:::::R
#  N:::::::::::N   N::::::N  E:::::E               V:::::V         V:::::V    E:::::E               R::::R     R:::::R
#  N:::::::N::::N  N::::::N  E::::::EEEEEEEEEE      V:::::V       V:::::V     E::::::EEEEEEEEEE     R::::RRRRRR:::::R 
#  N::::::N N::::N N::::::N  E:::::::::::::::E       V:::::V     V:::::V      E:::::::::::::::E     R:::::::::::::RR  
#  N::::::N  N::::N:::::::N  E:::::::::::::::E        V:::::V   V:::::V       E:::::::::::::::E     R::::RRRRRR:::::R 
#  N::::::N   N:::::::::::N  E::::::EEEEEEEEEE         V:::::V V:::::V        E::::::EEEEEEEEEE     R::::R     R:::::R
#  N::::::N    N::::::::::N  E:::::E                    V:::::V:::::V         E:::::E               R::::R     R:::::R
#  N::::::N     N:::::::::N  E:::::E       EEEEEE        V:::::::::V          E:::::E       EEEEEE  R::::R     R:::::R
#  N::::::N      N::::::::NEE::::::EEEEEEEE:::::E         V:::::::V         EE::::::EEEEEEEE:::::ERR:::::R     R:::::R
#  N::::::N       N:::::::NE::::::::::::::::::::E          V:::::V          E::::::::::::::::::::ER::::::R     R:::::R
#  N::::::N        N::::::NE::::::::::::::::::::E           V:::V           E::::::::::::::::::::ER::::::R     R:::::R
#  NNNNNNNN         NNNNNNNEEEEEEEEEEEEEEEEEEEEEE            VVV            EEEEEEEEEEEEEEEEEEEEEERRRRRRRR     RRRRRRR
"""
gonna = """
#          GGGGGGGGGGGGG     OOOOOOOOO     NNNNNNNN        NNNNNNNNNNNNNNNN        NNNNNNNN               AAA               
#       GGG::::::::::::G   OO:::::::::OO   N:::::::N       N::::::NN:::::::N       N::::::N              A:::A              
#     GG:::::::::::::::G OO:::::::::::::OO N::::::::N      N::::::NN::::::::N      N::::::N             A:::::A             
#    G:::::GGGGGGGG::::GO:::::::OOO:::::::ON:::::::::N     N::::::NN:::::::::N     N::::::N            A:::::::A            
#   G:::::G       GGGGGGO::::::O   O::::::ON::::::::::N    N::::::NN::::::::::N    N::::::N           A:::::::::A           
#  G:::::G              O:::::O     O:::::ON:::::::::::N   N::::::NN:::::::::::N   N::::::N          A:::::A:::::A          
#  G:::::G              O:::::O     O:::::ON:::::::N::::N  N::::::NN:::::::N::::N  N::::::N         A:::::A A:::::A         
#  G:::::G    GGGGGGGGGGO:::::O     O:::::ON::::::N N::::N N::::::NN::::::N N::::N N::::::N        A:::::A   A:::::A        
#  G:::::G    G::::::::GO:::::O     O:::::ON::::::N  N::::N:::::::NN::::::N  N::::N:::::::N       A:::::A     A:::::A       
#  G:::::G    GGGGG::::GO:::::O     O:::::ON::::::N   N:::::::::::NN::::::N   N:::::::::::N      A:::::AAAAAAAAA:::::A      
#  G:::::G        G::::GO:::::O     O:::::ON::::::N    N::::::::::NN::::::N    N::::::::::N     A:::::::::::::::::::::A     
#   G:::::G       G::::GO::::::O   O::::::ON::::::N     N:::::::::NN::::::N     N:::::::::N    A:::::AAAAAAAAAAAAA:::::A    
#    G:::::GGGGGGGG::::GO:::::::OOO:::::::ON::::::N      N::::::::NN::::::N      N::::::::N   A:::::A             A:::::A   
#     GG:::::::::::::::G OO:::::::::::::OO N::::::N       N:::::::NN::::::N       N:::::::N  A:::::A               A:::::A  
#       GGG::::::GGG:::G   OO:::::::::OO   N::::::N        N::::::NN::::::N        N::::::N A:::::A                 A:::::A 
#          GGGGGG   GGGG     OOOOOOOOO     NNNNNNNN         NNNNNNNNNNNNNNN         NNNNNNNAAAAAAA                   AAAAAAA
"""
give = """
#          GGGGGGGGGGGGGIIIIIIIIIIVVVVVVVV           VVVVVVVVEEEEEEEEEEEEEEEEEEEEEE
#       GGG::::::::::::GI::::::::IV::::::V           V::::::VE::::::::::::::::::::E
#     GG:::::::::::::::GI::::::::IV::::::V           V::::::VE::::::::::::::::::::E
#    G:::::GGGGGGGG::::GII::::::IIV::::::V           V::::::VEE::::::EEEEEEEEE::::E
#   G:::::G       GGGGGG  I::::I   V:::::V           V:::::V   E:::::E       EEEEEE
#  G:::::G                I::::I    V:::::V         V:::::V    E:::::E             
#  G:::::G                I::::I     V:::::V       V:::::V     E::::::EEEEEEEEEE   
#  G:::::G    GGGGGGGGGG  I::::I      V:::::V     V:::::V      E:::::::::::::::E   
#  G:::::G    G::::::::G  I::::I       V:::::V   V:::::V       E:::::::::::::::E   
#  G:::::G    GGGGG::::G  I::::I        V:::::V V:::::V        E::::::EEEEEEEEEE   
#  G:::::G        G::::G  I::::I         V:::::V:::::V         E:::::E             
#   G:::::G       G::::G  I::::I          V:::::::::V          E:::::E       EEEEEE
#    G:::::GGGGGGGG::::GII::::::II         V:::::::V         EE::::::EEEEEEEE:::::E
#     GG:::::::::::::::GI::::::::I          V:::::V          E::::::::::::::::::::E
#       GGG::::::GGG:::GI::::::::I           V:::V           E::::::::::::::::::::E
#          GGGGGG   GGGGIIIIIIIIII            VVV            EEEEEEEEEEEEEEEEEEEEEE
"""
you = """
#  YYYYYYY       YYYYYYY     OOOOOOOOO     UUUUUUUU     UUUUUUUU
#  Y:::::Y       Y:::::Y   OO:::::::::OO   U::::::U     U::::::U
#  Y:::::Y       Y:::::Y OO:::::::::::::OO U::::::U     U::::::U
#  Y::::::Y     Y::::::YO:::::::OOO:::::::OUU:::::U     U:::::UU
#  YYY:::::Y   Y:::::YYYO::::::O   O::::::O U:::::U     U:::::U 
#     Y:::::Y Y:::::Y   O:::::O     O:::::O U:::::D     D:::::U 
#      Y:::::Y:::::Y    O:::::O     O:::::O U:::::D     D:::::U 
#       Y:::::::::Y     O:::::O     O:::::O U:::::D     D:::::U 
#        Y:::::::Y      O:::::O     O:::::O U:::::D     D:::::U 
#         Y:::::Y       O:::::O     O:::::O U:::::D     D:::::U 
#         Y:::::Y       O:::::O     O:::::O U:::::D     D:::::U 
#         Y:::::Y       O::::::O   O::::::O U::::::U   U::::::U 
#         Y:::::Y       O:::::::OOO:::::::O U:::::::UUU:::::::U 
#      YYYY:::::YYYY     OO:::::::::::::OO   UU:::::::::::::UU  
#      Y:::::::::::Y       OO:::::::::OO       UU:::::::::UU    
#      YYYYYYYYYYYYY         OOOOOOOOO           UUUUUUUUU      
"""

up = """
#  UUUUUUUU     UUUUUUUUPPPPPPPPPPPPPPPPP   
#  U::::::U     U::::::UP::::::::::::::::P  
#  U::::::U     U::::::UP::::::PPPPPP:::::P 
#  UU:::::U     U:::::UUPP:::::P     P:::::P
#   U:::::U     U:::::U   P::::P     P:::::P
#   U:::::D     D:::::U   P::::P     P:::::P
#   U:::::D     D:::::U   P::::PPPPPP:::::P 
#   U:::::D     D:::::U   P:::::::::::::PP  
#   U:::::D     D:::::U   P::::PPPPPPPPP    
#   U:::::D     D:::::U   P::::P            
#   U:::::D     D:::::U   P::::P            
#   U::::::U   U::::::U   P::::P            
#   U:::::::UUU:::::::U PP::::::PP          
#    UU:::::::::::::UU  P::::::::P          
#      UU:::::::::UU    P::::::::P          
#        UUUUUUUUU      PPPPPPPPPP          
"""

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
        # print(never)
        # print(gonna)
        # print(give)
        # print(you)
        # print(up)


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