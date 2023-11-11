from typing import Optional
import discord
from discord.ext import commands

class PermissionInput(discord.ui.Modal, title="Permission Input"):
    permission = discord.ui.TextInput(
        label="Permission",
        placeholder="Permissions integer",
        min_length=1,
        max_length=30,
        style=discord.TextStyle.short,
        default=None,
    )

    permissions_dict = {
        "1": "CREATE_INSTANT_INVITE",
        "2": "KICK_MEMBERS",
        "4": "BAN_MEMBERS",
        "8": "ADMINISTRATOR",
        "16": "MANAGE_CHANNELS",
        "32": "MANAGE_GUILD",
        "64": "ADD_REACTIONS",
        "128": "VIEW_AUDIT_LOG",
        "256": "PRIORITY_SPEAKER",
        "512": "STREAM",
        "1024": "VIEW_CHANNEL",
        "2048": "SEND_MESSAGES",
        "4096": "SEND_TTS_MESSAGES",
        "8192": "MANAGE_MESSAGES",
        "16384": "EMBED_LINKS",
        "32768": "ATTACH_FILES",
        "65536": "READ_MESSAGE_HISTORY",
        "131072": "MENTION_EVERYONE",
        "262144": "USE_EXTERNAL_EMOJIS",
        "524288": "VIEW_GUILD_INSIGHTS",
        "1048576": "CONNECT",
        "2097152": "SPEAK",
        "4194304": "MUTE_MEMBERS",
        "8388608": "DEAFEN_MEMBERS",
        "16777216": "MOVE_MEMBERS",
        "33554432": "USE_VAD",
        "67108864": "CHANGE_NICKNAME",
        "134217728": "MANAGE_NICKNAMES",
        "268435456": "MANAGE_ROLES",
        "536870912": "MANAGE_WEBHOOKs",
        "1073741824": "MANAGE_GUILD_EXPRESSIONS",
        "2147483648": "USE_APPLICATION_COMMANDS",
        "4294967296": "REQUEST_TO_SPEAK",
        "8589934592": "MANAGE_EVENTS",
        "17179869184": "MANAGE_THREADS",
        "34359738368": "CREATE_PUBLIC_THREADS",
        "68719476736": "CREATE_PRIVATE_THREADS",
        "137438953472": "USE_EXTERNAL_STICKERS",
        "274877906944": "SEND_MESSAGES_IN_THREADS",
        "549755813888": "USE_EMBEDDED_ACTIVITIES",
        "1099511627776": "MODERATE_MEMBERS",
        "2199023255552": "VIEW_CREATOR_MONETIZATION_ANALYTICS",
        "4398046511104": "USE_SOUNDBOARD",
        "8796093022208": "USE_EXTERNAL_SOUNDS",
        "17592186044416": "SEND_VOICE_MESSAGES"
}
    

    async def on_submit(self, interaction: discord.Interaction):
        self.value = self.permission.value
        if self.value in self.permissions_dict:
            return discord.Permissions(value=int(self.value))
        else:
            return await interaction.response.send_message(f"Invalid permission: {self.value}", ephemeral=True)
    
    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        return await interaction.response.send_message(f"Error: {error}", ephemeral=True)
    
class PermissionView(discord.ui.View):
    def __init__(self, *, timeout=None):
        super().__init__(timeout=timeout)

    @discord.ui.button(label="Edit Permissions", style=discord.ButtonStyle.blurple)
    async def edit_permissions(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PermissionInput())

class PingRoleSelect(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.message: Optional[discord.Message] = None

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Select a role", custom_id="role_select")
    async def role_select(self, interaction: discord.Interaction, role: discord.ui.RoleSelect):
        await interaction.response.defer()
        async with self.bot.db.cursor() as cur: 
            await cur.execute("SELECT * FROM tickets WHERE ticket_guild_id = ?", (interaction.guild.id,))
            data = await cur.fetchone()
            ping_role = interaction.guild.get_role(data[4])
            if ping_role is None:
                # await cur.execute("UPDATE tickets SET ticket_ping_role_id = ? WHERE ticket_guild_id = ?", (role.values[0], interaction.guild.id))   
                # await self.message.edit(embed=discord.Embed(title="Ticket Pingrole Setup", description=f"> Successfully set ping role to {role.values[0]}", color=self.bot.color))
                await interaction.followup.send(f"Successfully set ping role to {role.values[0]}")
            else:
                # await cur.execute("UPDATE tickets SET ticket_ping_role_id = ? WHERE ticket_guild_id = ?", (role.values[0], interaction.guild.id))
                # await interaction.response.send_message(f"Successfully updated ping role to {role.values[0]}", ephemeral=True)
                await interaction.followup.send(f"Successfully updated ping role to {role.values[0]}")
            await self.message.edit(embed=discord.Embed(title="Ticket Pingrole Setup", description=f"> Successfully set ping role to {role.values}", color=self.bot.color))
        await self.bot.db.commit()

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: role_select) -> None:
        return await interaction.channel.send(f"Error: {error}")