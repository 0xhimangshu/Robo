from core import Robo
from helpcommand import PaginatedHelpCommand

if __name__=="__main__":
    bot = Robo(help_command=PaginatedHelpCommand())
    bot.boot()
