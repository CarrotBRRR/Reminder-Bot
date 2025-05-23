import os, json, re, uuid, base64, requests
import discord as dc
import typing

from datetime import datetime, timedelta
from discord.ext import tasks, commands
from dotenv import load_dotenv

### GLOBALS
load_dotenv()

reminders = []

intents = dc.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True

bot = commands.Bot(command_prefix="rm.", intents=intents)