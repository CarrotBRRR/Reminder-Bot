import os, json, sys
import discord as dc
import typing

from discord.ext import commands
from dotenv import load_dotenv

from ReminderLib.ReminderController import ReminderController

### GLOBALS
load_dotenv()

intents = dc.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True

bot = commands.Bot(command_prefix="rm.", intents=intents)

reminder_controller = ReminderController(bot)

@bot.event
async def on_ready():
    """
    Called when the bot is ready
    """

    print(f"[INIT] Logged in as {bot.user.name}")
    print("{INIT] Bot is ready to receive commands.")

    await reminder_controller.load_reminders()
    await reminder_controller.start_reminders()

@bot.event
async def on_message(message : dc.Message):
    """
    Called when a message is sent in a channel
    """

    await bot.process_commands(message)

@bot.event
async def on_guild_join(guild : dc.Guild):
    """
    Called when the bot joins a new guild
    """
    print(f"[INFO] Joined guild: {guild.name} - {guild.id}")
    
    # Create folder for the guild if it doesn't exist
    if not os.path.exists(f"data/{guild.id}"):
        os.makedirs(f"data/{guild.id}")
        print(f"[INFO] Created folder for guild: {guild.name} - {guild.id}")