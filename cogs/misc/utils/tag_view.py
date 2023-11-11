import discord
from discord import TextStyle
from discord.interactions import Interaction
import aiosqlite
from discord.ext import commands

class TagEdit(discord.ui.Modal, title="Tag Edit Form"):
    content=discord.ui.TextInput(
        label="Content",
        style=TextStyle.short,
        placeholder="Content of the tag",
        min_length=2,
        max_length=1990,
        required=True,
        )
    def __init__(self, bot: commands.Bot, tag_name: str):
        super().__init__(timeout=None)
        self.tag_name = tag_name
        self.bot = bot
    
    async def on_submit(self, interaction: Interaction) -> None:
        # async with self.bot.db.cursor() as cursor:
        #     await cursor.execute("SELECT * FROM tags WHERE tag_name=? or tag_id=?", (self.name.value, self.name.value))
        #     if await cursor.fetchone() is not None:
        #         await interaction.response.send_message("A tag with that name already exists!", ephemeral=True)
        #         return
        #     data = await cursor.fetchone()

        embed = discord.Embed(
            title="Tag Edited", 
            description=(
                f"**Content:** `{self.content.value}`\n"
            ),
            color=self.bot.color
            )
        await interaction.response.send_message(embed=embed)

        async with self.bot.db.cursor() as cursor:
            await cursor.execute("UPDATE tags SET tag_content=? WHERE tag_name=?", (self.content.value, self.tag_name))

        await self.bot.db.commit()

class TagEditButton(discord.ui.View):
    def __init__(self, bot: commands.Bot, tag_name: str, user: discord.Member):
        super().__init__(timeout=None)
        self.tag_name = tag_name
        self.user = user
        self.bot = bot

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id == self.user.id:
            return True
        await interaction.response.send_message("You can't do this!", ephemeral=True)

    @discord.ui.button(label="Edit", style=discord.ButtonStyle.green)
    async def edit(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TagEdit(bot=self.bot, tag_name=self.tag_name))
