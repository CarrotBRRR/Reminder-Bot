import os, json, re
import discord as dc
import typing

from datetime import datetime
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
    for guild in bot.guilds:
        await reminder_controller.load_reminders(guild.id)
        print(f"[INIT] Loaded reminders for {guild.name} - {guild.id}")

    await reminder_controller.start_reminders()
    print(f"[INIT] Loaded {len(reminder_controller.reminders)} reminders")

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
    print(f"[MAIN] Joined guild: {guild.name} - {guild.id}")
    
    # Create folder for the guild if it doesn't exist
    if not os.path.exists(f"data/{guild.id}"):
        os.makedirs(f"data/{guild.id}")
        print(f"[MAIN] Created folder for guild: {guild.name} - {guild.id}")

    # Create reminders file if it doesn't exist
    if not os.path.exists(f"data/{guild.id}/reminders.json"):
        with open(f"data/{guild.id}/reminders.json", "w") as f:
            json.dump([], f, indent=4)
        print(f"[MAIN] Created reminders file for guild: {guild.name} - {guild.id}")
    else:
        print(f"[MAIN] Reminders file already exists for guild: {guild.name} - {guild.id}")

@bot.hybrid_command(
    name="remind_at", 
    description="Set a reminder"
)
async def remind_at(
    ctx,
    title : str,
    subtitles : typing.Optional[str] = None,
    messages : typing.Optional[str] = None,
    footer : typing.Optional[str] = None,
    time : typing.Optional[str] = datetime.now().strftime("%H:%M:%S"),
    repeat : bool = False,
    user_mention : typing.Optional[dc.User] = None,
    role_mention : typing.Optional[dc.Role] = None,
):
    res = await ctx.send("Creating reminder...", ephemeral=True)
    if user_mention and role_mention is None:
        mentions = [ctx.author]
    else:
        mentions = []
        if user_mention:
            mentions.append(user_mention)
        if role_mention:
            mentions.append(role_mention)
    
    # Parse Time
    if time:
        try:
            set_time = datetime.strptime(time, "%H:%M:%S").time()
        except ValueError:
            await ctx.send("Invalid start time format.\nPlease use format 'HH:MM:SS'", ephemeral=True)
            return

    await reminder_controller.create_reminder( 
            title,
            subtitles,
            messages,
            footer,
            int(ctx.channel.id),
            set_time,
            repeat,
            mentions,
            ctx.guild.id
        )
    
    await res.edit("Reminder created!", ephemeral=True)

@bot.hybrid_command(
    name="remind_in", 
    description="Remind me in a certain amount of time"
)
async def remind_in(
    ctx,
    title : str,
    subtitles : typing.Optional[str] = None,
    messages : typing.Optional[str] = None,
    footer : typing.Optional[str] = None,
    delay : str = "10s",
    mentions : typing.Optional[dc.User] = None
):
    # Parse delay
    d = await time2seconds(ctx, delay)

    # Parse Start Time
    time = datetime.now() + datetime.timedelta(seconds=d)

    await reminder_controller.create_reminder( 
            title,
            subtitles,
            messages,
            footer,
            int(ctx.channel.id),
            time,
            False,
            mentions,
            ctx.guild.id
        )

@bot.hybrid_command(
    name="reminders", 
    description="List all reminders"
)
async def reminders(ctx):
    for reminder in reminder_controller.reminders:
        if 


async def time2seconds(ctx, duration_str : str) -> int:
    """
    Converts a time string to seconds
    """
    time_factors = {
        'w': 604800, # 1 week = 604800 seconds
        'd': 86400,  # 1 day = 86400 seconds
        'h': 3600,   # 1 hour = 3600 seconds
        'm': 60,     # 1 minute = 60 seconds
        's': 1       # 1 second = 1 second
    }

    # Find all occurrences of number followed by a letter
    matches = re.findall(r'(\d+)\s*([dhms])', duration_str.lower())
    if not matches:
        await ctx.send("Invalid time format. Please use a format '1d 2h 12m 3s' separated by spaces.", ephemeral=True)
        return 0
    
    total_seconds = 0
    for value, unit in matches:
        total_seconds += int(value) * time_factors[unit]

    return total_seconds

@bot.command(name="sync")
@commands.is_owner()
async def sync(ctx):
    """
    Syncs the bot with the guild
    """
    print("Syncing...")
    await bot.tree.sync(guild=ctx.guild)
    print("Synced!")
    await ctx.send("Synced!")

bot.run(os.getenv("TEST_TOKEN"))