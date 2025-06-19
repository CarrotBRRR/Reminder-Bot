import os, json, re, uuid, requests
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

# EVENTS
@bot.event
async def on_ready():
    """
    Called when the bot is ready
    """
    print(f"[INIT] Logged in as {bot.user.name}")
    print("[INIT] Checking Reminders Folders...")
    for guild in bot.guilds:
        # Create folder for the guild if it doesn't exist
        if not os.path.exists(f"data/{guild.id}"):
            os.makedirs(f"data/{guild.id}")
            print(f"[INIT] Created folder for guild: {guild.name} - {guild.id}")

        # Create reminders file if it doesn't exist
        if not os.path.exists(f"data/{guild.id}/reminders.json"):
            with open(f"data/{guild.id}/reminders.json", "w") as f:
                json.dump([], f, indent=4)
            print(f"[INIT] Created reminders file for guild: {guild.name} - {guild.id}")

    print(f"[INIT] Found {len(bot.guilds)} Guilds!")

    # Start the tasks
    print("[INIT] Starting task loops...")
    if not reminder_task.is_running():
        print("\t[INIT] Waiting for minute time...")
        await dc.utils.sleep_until(datetime.now() + timedelta(seconds=60 - datetime.now().second)) # Wait for the next minute
        reminder_task.start()
        print("\t[INIT] Started reminder loop!")

    if not heartbeat_task.is_running():
        heartbeat_task.start()
        print("\t[INIT] Started heartbeat loop!")
    
    print("[INIT] Loops Started!")

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
    print(f"[REMI] Joined guild: {guild.name} - {guild.id}")
    
    # Create folder for the guild if it doesn't exist
    if not os.path.exists(f"data/{guild.id}"):
        os.makedirs(f"data/{guild.id}")
        print(f"[REMI] Created folder for guild: {guild.name} - {guild.id}")

    # Create reminders file if it doesn't exist
    if not os.path.exists(f"data/{guild.id}/reminders.json"):
        with open(f"data/{guild.id}/reminders.json", "w") as f:
            json.dump([], f, indent=4)
        print(f"[REMI] Created reminders file for guild: {guild.name} - {guild.id}")

# HELPER FUNCTIONS
async def time2seconds(ctx, duration_str : str) -> int:
    """
    Converts a time string to seconds
    """
    time_factors = {
        'y': 31556952, # 1 year = 31536000 seconds
        'mo': 2629746, # 1 month = 2592000 seconds
        'w': 604800, # 1 week = 604800 seconds
        'd': 86400,  # 1 day = 86400 seconds
        'h': 3600,   # 1 hour = 3600 seconds
        'm': 60,     # 1 minute = 60 seconds
        's': 1       # 1 second = 1 second
    }

    # Find all occurrences of number followed by a letter
    matches = re.findall(r'(\d+)\s*([dhms])', duration_str.lower())
    if not matches:
        await ctx.send("Invalid time format. Please use a format '1d 2h 12m' separated by spaces.", ephemeral=True)
        return 0
    
    total_seconds = 0
    for value, unit in matches:
        total_seconds += int(value) * time_factors[unit]

    return total_seconds

async def seconds2time(seconds: int) -> str:
    """
    Converts seconds to a human-readable time format
    """
    if seconds < 0:
        return "Invalid time"

    time_parts = []
    time_units = {
        'y': 31556952,  # 1 year
        'mo': 2629746,  # 1 month
        'w': 604800,    # 1 week
        'd': 86400,     # 1 day
        'h': 3600,      # 1 hour
        'm': 60,        # 1 minute
        's': 1          # 1 second
    }

    for unit, factor in time_units.items():
        if seconds >= factor:
            value = seconds // factor
            seconds %= factor
            time_parts.append(f"{value}{unit}")

    return " ".join(time_parts) if time_parts else "0s"

def parse_flexible_time(time_str: str) -> datetime:
    """
    Parses a flexible time string in various formats and returns a datetime object.

    Supports formats:
    - %y-%m-%d-%H:%M
    - %Y-%m-%d-%H:%M
    - %m-%d-%H:%M
    - %d-%H:%M
    - %H:%M
    """
    now = datetime.now()

    formats = [
        ("%y-%m-%d-%H:%M", time_str),                                               # %y-%m-%d-%H:%M
        ("%Y-%m-%d-%H:%M", time_str),                                               # %Y-%m-%d-%H:%M
        ("%Y-%m-%d-%H:%M", f"{now.year}-{time_str}"),                               # %m-%d-%H:%M
        ("%Y-%m-%d-%H:%M", f"{now.year}-{now.month:02d}-{time_str}"),               # %d-%H:%M
        ("%Y-%m-%d-%H:%M", f"{now.year}-{now.month:02d}-{now.day:02d}-{time_str}")  # %H:%M
    ]

    for fmt, time_candidate in formats:
        try:
            return datetime.strptime(time_candidate, fmt)
        
        except ValueError:
            continue

    raise ValueError(f"## Time format not recognized: '{time_str}'\n### Supported formats:\n- %y-%m-%d-%H:%M\n- %Y-%m-%d-%H:%M\n- %m-%d-%H:%M\n- %d-%H:%M\n- %H:%M")

def parse_UTC(utc_str: str) -> int:
    """
    Parses a UTC offset string in the format +/-X or +/-X:XX, and returns the offset in minutes.
    """
    if not re.match(r'^[+-]\d{1,2}(:\d{2})?$', utc_str):
        raise ValueError("UTC must be in the format of +/-X or +/-X:XX")
    
    parts = utc_str.split(':')

    sign = 1 if parts[0][0] == '+' else -1
    hours = int(parts[0][1:]) if len(parts[0]) > 1 else 0
    minutes = int(parts[1]) if len(parts) > 1 else 0

    offset = sign * (hours * 60 + minutes)

    return offset

def get_timezone_offset_str(timezone: str) -> str:
    """
    Returns the UTC offset for a given timezone.
    """
    timezone = timezone.upper()
    with open("data/timezones_info.json", "r") as f:
        timezones_info = json.load(f)
    if timezone in timezones_info:
        utc = timezones_info[timezone]
    else:
        raise ValueError(f"Unknown timezone: {timezone}.\nPlease provide a valid UTC offset (e.g. ±X:XX) or timezone (e.g. GMT, MDT, EST, etc.)")
    return utc

async def time2unix(datetime_str: str) -> int:
    """
    Converts a datetime object to a Unix timestamp
    """
    datetime_obj = parse_flexible_time(datetime_str)

    return int(datetime_obj.timestamp())

def uuid_base62():
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    u = uuid.uuid4()
    num = int.from_bytes(u.bytes, byteorder='big')  # 128-bit int
    base62 = ''
    while num:
        num, rem = divmod(num, 62)
        base62 = alphabet[rem] + base62
    return base62

async def get_mentions(mentions : str, guild : dc.Guild) -> typing.List[dc.User | dc.Role]:
    """
    Get mentions from a string
    """
    mention_ids = re.findall(r'<@!?(\d+)>|<@&(\d+)>', mentions)
    mention_strs = []
    for user_id, role_id in mention_ids:
        if user_id:
            member = await guild.fetch_member(int(user_id))
            if member:
                mention_strs.append(member.mention)
        elif role_id:
            role = guild.get_role(int(role_id))
            if role:
                mention_strs.append(role.mention)

    return mention_strs

async def load_reminders(guild_id : int) -> typing.List[typing.Dict]:
    """
    Load reminders from file
    """
    if not os.path.exists(f"data/{guild_id}/reminders.json"):
        print(f"\t[LOAD] No reminder folder found for {guild_id}. Creating file...")
        return []

    with open(f"data/{guild_id}/reminders.json", "r") as f:
        reminders = json.load(f)

    if not len(reminders) == 0:
        print(f"\t[LOAD] Loaded {len(reminders)} reminders for {guild_id}!")
    
    return reminders

async def send_reminder(reminder, guild):
    """
    Sends the reminder message with embed formatting.
    """
    print(f"\t[REMI] Sending reminder {reminder['reminder_id']} in {guild.name}")
    channel = bot.get_channel(reminder["channel_id"])
    payload = " ".join(reminder["mentions"])

    embed = dc.Embed(title=reminder["title"], color=0x00ff00)
    subtitles = reminder["subtitles"].split("\\n")
    messages = reminder["message"].split("\\n")

    for subtitle, message in zip(subtitles, messages):
        embed.add_field(name=subtitle, value=message, inline=False)

    await channel.send(content=payload, embed=embed)
    print(f"\t[REMI] Sent reminder to {channel.name} - {channel.id} in {guild.name} - {guild.id}")

# COMMANDS
@bot.hybrid_command(
    name="remind",
    description="Set a reminder for yourself or someone else",
    time="Scheduled time in HH:MM format",
    title="Title of the reminder",
    subtitles="Subtitles of the reminder, separated by \\n",
    messages="Messages to send, separated by \\n",
    mentions="Mention a user or a role",
    repeat="Interval to repeat the reminder in the format of '1w 2d 3h 4m 5s'",
)
async def create_reminder(
    ctx : commands.Context,
    time : typing.Optional[str] = None,     # Inital time to remind
    title : str = "",                       # Title of the reminder
    subtitles : typing.Optional[str] = "",  # Subtitle of the reminder
    messages : typing.Optional[str] = "",   # Message to send
    mentions : typing.Optional[str] = "",   # Mentions to send the reminder to
    repeat : typing.Optional[str] = None,   # Interval to repeat the reminder in the same format as time (i.e. amount of time to add)
):
    """
    Create a reminder!
    """
    reminders = await load_reminders(ctx.guild.id)

    print(f"[REMI] {ctx.author.name} creating reminder in {ctx.guild.name}")
    print(f"\t[MAKE] Parsing info...")
    print(f"\t\t[MAKE] Parsing mentions...")
    if time is None:
        time = datetime.now().strftime("%Y-%m-%d-%H:%M")

    mention_str = await get_mentions(mentions, ctx.guild)

    if mention_str is []:
        mention_str = [ctx.author.mention]
    
    print(f"\t\t[MAKE] Done!")
    print(f"\t\t[MAKE] Parsing Subtitles and Messages...")

    # This does nothing when the string is empty, will fix later
    # New function should only need to check if there are more messages than subtitles
    subs = []
    for subtitle in subtitles.split("\n"):
        subs.append(subtitle)

    msgs = []
    for message in messages.split("\n"):
        msgs.append(message)

    if len(subs) != len(msgs):
        await ctx.send("The number of subtitles and messages must be the same!", ephemeral=True)
        return
    
    # Adding date info to the time string
    try:
        t = parse_flexible_time(time)

    except ValueError as e:
        await ctx.send(str(e), ephemeral=True)
        return

    print(f"\t\t[MAKE] Done!")
    print(f"\t\t[MAKE] Parsing repeat time...")
    repeat_seconds = await time2seconds(ctx, repeat) if repeat else None
    print(f"\t[MAKE] Finished Parsing info!")

    print(f"\t[MAKE] Creating reminder...")
    reminders.append({
        "issuer_id": ctx.author.id,
        "guild_id": ctx.guild.id,
        "channel_id": ctx.channel.id,
        "reminder_id": uuid_base62(),

        "time": t.strftime("%Y-%m-%d-%H:%M"),
        "title": title,
        "subtitles": subtitles,
        "message": message,
        "mentions": mention_str,
        "repeat": int(repeat_seconds/60) if repeat else None,
    })

    print(f"\t[MAKE] Done!")
    print(f"\t[SAVE] Saving reminder to file...")
    # Save reminders to file
    if not os.path.exists(f"data/{ctx.guild.id}"):
        os.makedirs(f"data/{ctx.guild.id}")
        print(f"[SAVE] Created folder for guild: {ctx.guild.name} - {ctx.guild.id}")

    with open(f"data/{ctx.guild.id}/reminders.json", "w") as f:
        json.dump(reminders, f, indent=4)
    print(f"\t[SAVE] Reminder Saved!")
    print(f"\t[REMI] Reminder ID: {reminders[-1]['reminder_id']} Created!")
    await ctx.send(f"Reminder {title} set for {mentions} at {time}", ephemeral=True)

@bot.hybrid_command(
    name="reminders",
    description="List all reminders for the server",
)
async def list_reminders(ctx : commands.Context):
    """
    List all reminders for the server
    """
    print(f"[LIST] {ctx.author.name} checking reminders in {ctx.guild.name}")
    reminders = await load_reminders(ctx.guild.id)

    em = dc.Embed(
        title="Reminders",
        description="List of reminders",
        color=0x00ff00,
    )

    if len(reminders) == 0:
        em.add_field(
            name="No reminders",
            value="There are no reminders set for this server.",
            inline=False,
        )
    else:
        print(f"[LIST] Parsing {len(reminders)} reminders in {ctx.guild.name}")
        for reminder in reminders:
            value_str = f"> `Next Reminder`: {reminder['time']}\
                        \n> `Local Time`: <t:{str(await time2unix(reminder['time']))}:F>\
                        \n> `Title`: {reminder['title']}\n> `ID`: {reminder['reminder_id']}\
                        \n> `Repeat every`: {await seconds2time(reminder['repeat'] * 60) if reminder['repeat'] else 'No Repeat Set'}\
                        \n> `Issuer`: <@{reminder['issuer_id']}>"

            mentions_str = ""
            for mention in reminder["mentions"]:
                
                mentions_str += f"{mention} "

            em.add_field(
                name=f"**Reminder for {mentions_str}**",
                value= value_str,
                inline=False,
            )
    
    await ctx.send(embed=em, ephemeral=True)
    print(f"[LIST] Sent reminders list of {len(reminders)} reminders in {ctx.guild.name} -> {ctx.channel.name}")

@bot.hybrid_command(
    name="delete_reminder",
    description="Delete a reminder by ID",
    reminder_id="ID of the reminder to delete",
)
async def delete_reminder(
    ctx : commands.Context,
    reminder_id : str,
):
    """
    Delete a reminder by ID
    """
    print(f"[DLET] {ctx.author.name} deleting reminder {reminder_id} in {ctx.guild.name}")
    reminders = await load_reminders(ctx.guild.id)

    for reminder in reminders:
        if reminder["reminder_id"] == reminder_id:
            if (reminder["issuer_id"] != ctx.author.id) and (ctx.author.id != ctx.guild.owner_id) and not ctx.author.guild_permissions.administrator and not await bot.is_owner(ctx.author):
                await ctx.send("You must be the Reminder Author, Server Owner, Server Admin, or Bot Owner to delete this reminder!", ephemeral=True)
                return

            reminders.remove(reminder)
            with open(f"data/{ctx.guild.id}/reminders.json", "w") as f:
                json.dump(reminders, f, indent=4)
            await ctx.send("Reminder deleted!", ephemeral=True)
            print(f"[DLET] Deleted reminder {reminder_id} in {ctx.guild.name}")
            return

    await ctx.send("Reminder not found... Please ensure you have the correct Reminder ID", ephemeral=True)

@bot.hybrid_command(
    name="show_reminder",
    description="Test a reminder",
    id="ID of the reminder to test",
)
async def test_reminder(
    ctx : commands.Context,
    id : str,
):
    """
    Test a reminder
    """
    print(f"[REMI] {ctx.author.name} testing reminder {id} in {ctx.guild.name}")
    reminders = await load_reminders(ctx.guild.id)

    for reminder in reminders:
        if reminder["reminder_id"] == id:
            channel = bot.get_channel(reminder["channel_id"])
            em = dc.Embed(
                title=reminder["title"],
                color=0x00ff00,
            )

            # Parse Subtitles and Messages
            subtitles = []
            for subtitle in reminder["subtitles"].split("\\n"):
                subtitles.append(subtitle)

            messages = []
            for message in reminder["message"].split("\\n"):
                messages.append(message)
                
            # Add the subtitles and messages to the embed
            for i, subtitle in enumerate(subtitles):
                em.add_field(
                    name=subtitle,
                    value=messages[i],
                    inline=False,
                )
            
            await channel.send(embed=em ,ephemeral=True)
            print(f"[REMI] Tested reminder {reminder['reminder_id']} to {channel.name} in {ctx.guild.name}")
            return

    await ctx.send("Reminder not found... Please ensure you have the correct Reminder ID", ephemeral=True)

@bot.hybrid_command(
    name="bottime",
    description="Get the time of the bot",
    time="Time in UTC to convert to your local time 'HH:MM' or 'MM-DD-HH:MM' or 'DD-HH:MM' or 'YY-MM-DD-HH:MM'"
)
async def bot_time(
    ctx : commands.Context, 
    time : typing.Optional[str] = None
):
    await ctx.defer(ephemeral=True)

    try:
        if time is None:
            time = datetime.now().strftime("%Y-%m-%d-%H:%M")

        datetime_obj = parse_flexible_time(time)

    except ValueError as e:
        await ctx.send(str(e), ephemeral=True)
        return
    
    time_int = int(datetime_obj.timestamp())

    await ctx.send(f"## {datetime_obj.strftime("%Y-%m-%d-%H:%M")} UTC (Bot Time) is:\n## <t:{time_int}:F> Your Time", ephemeral=True) 

@bot.hybrid_command(
    name="localtime",
    description="Convert a local time with UTC offset (e.g. -7, +2) to the bot's UTC time",
    time="Your local time you want to convert to bot time",
    utc="Your UTC offset (e.g. +2, -5, etc.)",
    timezone="Your timezone (e.g. MDT, EST, etc.)",
)
async def local_to_bot(
    ctx: commands.Context,
    time: typing.Optional[str] = None,  # Time in HH:MM or MM-DD-HH:MM or DD-HH:MM or YY-MM-DD-HH:MM
    timezone: typing.Optional[str] = None,  # e.g. MDT, EST, etc.
    utc: typing.Optional[str] = None        # Only +X or -X
):
    if utc and timezone:
        await ctx.send("Please provide either a UTC offset or a timezone, not both.", ephemeral=True)
        return
    
    await time_convert(
        ctx,
        time=time,
        timezone=timezone if timezone is not None else "UTC",
        to="UTC" if utc is None else utc
    )

@bot.hybrid_command(
    name="timeconvert",
    description="Convert a time to another timezone",
    time="Time you want to convert",
    timezone="Origin timezone (e.g. MDT, EST, etc.)",
    to="Timezone to convert to (e.g. GMT, MDT, EST, etc.)",
)
async def time_convert(
    ctx: commands.Context,
    time: typing.Optional[str] = None,  # Time in HH:MM or MM
    timezone: typing.Optional[str] = None,  # e.g. MDT, EST, etc.
    to: typing.Optional[str] = None        # e.g. GMT, MDT, EST
):
    await ctx.defer(ephemeral=True)

    # If no time is provided, use the current time
    if time is None:
        time = datetime.now().strftime("%Y-%m-%d-%H:%M")

    if timezone is not None:
        try:
            origin_utc = get_timezone_offset_str(timezone)

        except FileNotFoundError:
            await ctx.send(f"timezones_info.json file not found. Please Contact Bot Owner", ephemeral=True)
            return
        
        except ValueError as e:
            await ctx.send(str(e), ephemeral=True)
            return
    else:
        # Default to UTC if no timezone is provided
        timezone = "UTC"
        origin_utc = "+0:00"

    if to is not None:
        try:
            target_utc = get_timezone_offset_str(to)

        except FileNotFoundError:
            await ctx.send(f"timezones_info.json file not found. Please Contact Bot Owner", ephemeral=True)
            return
        
        except ValueError as e:
            await ctx.send(str(e), ephemeral=True)
            return
    else:
        # Default to UTC if no target timezone is provided
        to = "UTC"
        target_utc = "+0:00"

    try:
        origin_offset = parse_UTC(origin_utc)
        target_offset = parse_UTC(target_utc)

        # Parse the time string
        datetime_obj = parse_flexible_time(time)    # Base time in the origin timezone

        # Convert to UTC
        utc_datetime = datetime_obj - timedelta(minutes=origin_offset) # Adjust to UTC
        unix_time = int(utc_datetime.timestamp())

        # Convert to target timezone
        target_datetime = utc_datetime + timedelta(minutes=target_offset)

        await ctx.send(
            f"## {datetime_obj.strftime('%Y-%m-%d-%H:%M')} {timezone.upper()} (UTC{origin_utc}) is:\n## {target_datetime.strftime('%Y-%m-%d-%H:%M')} {to} (UTC{target_utc.upper()})\n### <t:{unix_time}:F> in your local time",
            ephemeral=True
        )

    except Exception as e:
        await ctx.send(f"Error: {str(e)}", ephemeral=True)
        return
        
# TASKS
@tasks.loop(seconds=60)
async def reminder_task():
    """
    Check reminders every minute
    """
    print("[REMI] Checking reminders...")
    now_str = datetime.now().strftime("%Y-%m-%d-%H:%M")
    now_dt = datetime.strptime(now_str, "%Y-%m-%d-%H:%M")
    print(f"\t[REMI] Current time: {now_str}")

    for guild in bot.guilds:
        reminders = await load_reminders(guild.id)
        updated = False

        for reminder in reminders[:]:  # Use a slice to avoid modifying the list during iteration
            reminder_time = datetime.strptime(reminder["time"], "%Y-%m-%d-%H:%M")
            late = reminder_time < now_dt
            do_reminder = late or reminder_time == now_dt

            if late:
                print(f"\t[REMI] Reminder {reminder['reminder_id']} is in the past!")

                if reminder["repeat"] is not None:
                    # Calculate how many repeats have passed and update time accordingly
                    delta_min = (now_dt - reminder_time).total_seconds() // 60
                    repeats_passed = int(delta_min // reminder["repeat"]) + 1
                    new_time = reminder_time + timedelta(minutes=repeats_passed * reminder["repeat"])
                    reminder["time"] = new_time.strftime("%Y-%m-%d-%H:%M")

                    print(f"\t[REMI] Reminder time updated to: {reminder['time']}")
                    updated = True

            if do_reminder:
                await send_reminder(reminder, guild)
                if reminder["repeat"] is None:
                    print(f"\t[REMI] No repeat set. Removing reminder {reminder['reminder_id']} from {guild.name}")
                    reminders.remove(reminder)
                    updated = True

                elif not late:
                    # Regular (non-late) repeating reminder; update time
                    next_time = datetime.strptime(reminder["time"], "%Y-%m-%d-%H:%M") + timedelta(minutes=reminder["repeat"])
                    reminder["time"] = next_time.strftime("%Y-%m-%d-%H:%M")
                    updated = True

                elif reminder["repeat"] is None:
                    print(f"\t[REMI] Reminder {reminder['reminder_id']} was late.")

        if updated:
            with open(f"data/{guild.id}/reminders.json", "w") as f:
                json.dump(reminders, f, indent=4)

    print("[REMI] Finished checking reminders!")

@tasks.loop(minutes=15)
async def heartbeat_task():
    """
    Send a heartbeat to the healthcheck.io every 15 minutes
    """
    print("[BEAT] Sending heartbeat to healthchecks.io...")
    heartbeat_uuid = os.getenv("HEARTBEAT_UUID")

    try:
        response = requests.get(f"https://hc-ping.com/{heartbeat_uuid}")
        if response.status_code == 200:
            print("[BEAT] Heartbeat sent successfully!")
        else:
            print(f"[BEAT] Failed to send heartbeat: {response.status_code} - {response.text}")

    except Exception as e:
        # Optional: local logging of the failure
        print(f"[BEAT] Failed to send ping: {e}")

# OWNER COMMANDS
@bot.command(
    name="sync",
    description="sync the tree",
)
@commands.is_owner()
async def sync(ctx : commands.Context):
    """
    Sync the tree
    """
    msg = await ctx.send("Syncing...", ephemeral=True)
    await bot.tree.sync()
    await ctx.message.delete()
    await msg.edit(content="Synced the tree!", delete_after=2)
    print(f"[REMI] Synced the tree!")

bot.run(os.getenv("TOKEN"))