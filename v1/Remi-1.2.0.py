# Remi-refactor.py
import os
import json
import uuid
import requests
import asyncio
import typing

import discord as dc

from datetime import datetime, timedelta
from discord.ext import tasks, commands
from dotenv import load_dotenv

# Local libraries (keep your existing ReminderLib)
from ReminderLib.Paginator import Paginator
from ReminderLib.Parser import *
# DB: use PyStoreJSON implementation directly
from PyStoreJSONLib import PyStoreJSONDB

### GLOBALS
print("[INFO] REMI v1.2.0 - Reminder Bot (Refactor using PyStoreJSONDB)")
load_dotenv()

intents = dc.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True

bot = commands.Bot(command_prefix="rm.", intents=intents)

# Database directory
REMINDER_DB = "data/reminders"
os.makedirs(REMINDER_DB, exist_ok=True)

# Helper: create or return DB instance for a guild
def get_db_for_guild(guild_id: int) -> PyStoreJSONDB:
    path = os.path.join(REMINDER_DB, f"guild_{guild_id}.json")
    return PyStoreJSONDB(path)

# UUID base62 generator
def uuid_base62():
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    u = uuid.uuid4()
    num = int.from_bytes(u.bytes, byteorder='big')  # 128-bit int
    base62 = ''
    while num:
        num, rem = divmod(num, 62)
        base62 = alphabet[rem] + base62
    return base62

# Database read/write helpers (async signatures kept for compatibility)
async def load_reminders(guild_id: int) -> list:
    db = get_db_for_guild(guild_id)
    return db.get_all()

async def save_reminders_full(guild_id: int, reminders: list):
    """
    Overwrite the entire reminders DB for the guild with the provided list.
    Uses the DB's internal _save to preserve schema behaviour.
    """
    db = get_db_for_guild(guild_id)
    # Use db._save (internal) to replace entire file atomically
    db._save(reminders)

async def upsert_reminder(guild_id: int, reminder: dict):
    """
    Insert a new reminder row. If a reminder with same reminder_id exists, update it.
    """
    db = get_db_for_guild(guild_id)
    # If reminder_id exists, update_by; otherwise insert
    if reminder.get("reminder_id") and db.find_by("reminder_id", reminder["reminder_id"]):
        db.update_by("reminder_id", reminder["reminder_id"], reminder)
    else:
        db.insert(reminder)

async def delete_reminder_by_id(guild_id: int, reminder_id: str) -> int:
    db = get_db_for_guild(guild_id)
    return db.delete_by("reminder_id", reminder_id)

# Sending reminder embed
async def send_reminder(reminder, guild):
    """
    Sends the reminder message with embed formatting.
    """
    try:
        print(f"\t[REMI] Sending reminder {reminder['reminder_id']} in {guild.name}")
        channel = bot.get_channel(reminder["channel_id"])
        if channel is None:
            print(f"\t[WARN] Channel {reminder['channel_id']} not found for guild {guild.name}")
            return

        # mentions stored as list
        payload = " ".join(reminder.get("mentions", [])) if reminder.get("mentions") else ""

        embed = dc.Embed(title=reminder.get("title", ""), color=0x00ff00)
        subtitles = str(reminder.get("subtitles", "")).split("\\n")
        messages = str(reminder.get("message", "")).split("\\n")

        # Pair up subtitles and messages safely
        for i, subtitle in enumerate(subtitles):
            message_text = messages[i] if i < len(messages) else ""
            embed.add_field(name=subtitle, value=message_text, inline=False)

        await channel.send(content=payload if payload else None, embed=embed)
        print(f"\t[REMI] Sent reminder to {channel.name} - {channel.id} in {guild.name} - {guild.id}")
    except Exception as e:
        print(f"\t[ERROR] Failed to send reminder {reminder.get('reminder_id')}: {e}")

# EVENTS
@bot.event
async def on_ready():
    """
    Called when the bot is ready
    """
    print(f"[INIT] Logged in as {bot.user.name}")
    print("[INIT] Ensuring DB directory and per-guild DBs exist...")

    # Ensure data folders and DB files exist for each guild
    for guild in bot.guilds:
        # Ensure classic per-guild data directory exists (some other resources may use it)
        os.makedirs(f"data/{guild.id}", exist_ok=True)
        db = get_db_for_guild(guild.id)
        # db initialization is handled by PyStoreJSONDB constructor

    print(f"[INIT] Found {len(bot.guilds)} Guilds!")

    # Start tasks
    print("[INIT] Starting task loops...")
    if not reminder_task.is_running():
        print("\t[INIT] Waiting for minute time...")
        # Wait until the next minute boundary to align checks to minute resolution
        await dc.utils.sleep_until(datetime.now() + timedelta(seconds=60 - datetime.now().second))
        reminder_task.start()
        print("\t[INIT] Started reminder loop!")
    else:
        print("\t[INIT] Reminder loop already running!")

    if not heartbeat_task.is_running():
        heartbeat_task.start()
        print("\t[INIT] Started heartbeat loop!")
    else:
        print("\t[INIT] Heartbeat loop already running!")

    print("[INIT] Loops Started!")

@bot.event
async def on_message(message: dc.Message):
    """
    Called when a message is sent in a channel
    """
    await bot.process_commands(message)

@bot.event
async def on_guild_join(guild: dc.Guild):
    """
    Called when the bot joins a new guild
    """
    print(f"[REMI] Joined guild: {guild.name} - {guild.id}")

    # Create folder for the guild if it doesn't exist
    os.makedirs(f"data/{guild.id}", exist_ok=True)
    # Ensure DB file exists (constructor will make file if not present)
    get_db_for_guild(guild.id)
    print(f"[REMI] Prepared DB and folders for guild: {guild.name} - {guild.id}")

# COMMANDS
@bot.hybrid_command(
    name="remind",
    description="Set a reminder for yourself or someone else",
    time="Scheduled time in HH:MM format or flexible formats supported by parser",
    title="Title of the reminder",
    subtitles="Subtitles of the reminder, separated by \\n",
    messages="Messages to send, separated by \\n",
    mentions="Mention a user or a role",
    repeat="Interval to repeat the reminder in the format of '1w 2d 3h 4m 5s'",
)
async def create_reminder(
    ctx: commands.Context,
    time: typing.Optional[str] = None,     # Initial time to remind
    title: str = "",                      # Title of the reminder
    subtitles: typing.Optional[str] = "",  # Subtitle of the reminder
    messages: typing.Optional[str] = "",   # Messages to send
    mentions: typing.Optional[str] = "",   # Mentions to send the reminder to
    repeat: typing.Optional[str] = None,   # Interval to repeat the reminder
):
    """
    Create a reminder.
    """
    print(f"[REMI] {ctx.author.name} creating reminder in {ctx.guild.name}")
    print(f"\t[MAKE] Parsing info...")

    if time is None:
        # Default to the current bot time
        time = datetime.now().strftime("%Y-%m-%d-%H:%M")

    mention_str = await get_mentions(mentions, ctx.guild)
    if mention_str == []:
        mention_str = [ctx.author.mention]

    # Parse subtitles and messages into stored string form (keep literal \n as separators)
    subs = "\\n".join([s for s in subtitles.split("\n")]) if subtitles else ""
    msgs = "\\n".join([m for m in messages.split("\n")]) if messages else ""

    # Validate number of subtitles vs messages: messages must be <= subtitles
    subs_list = subs.split("\\n") if subs else []
    msgs_list = msgs.split("\\n") if msgs else []
    if len(msgs_list) > len(subs_list) and subs:
        await ctx.send("The number of messages must be less than or equal to number of subtitles!", ephemeral=True)
        return

    # Parse time using existing parser utilities
    try:
        t = parse_flexible_time(time)
    except ValueError as e:
        await ctx.send(str(e), ephemeral=True)
        return

    # Parse repeat into seconds (use existing helper)
    repeat_seconds = await time2seconds(ctx, repeat) if repeat else None

    # Create reminder object
    reminder_obj = {
        "issuer_id": ctx.author.id,
        "guild_id": ctx.guild.id,
        "channel_id": ctx.channel.id,
        "reminder_id": uuid_base62(),
        "time": t.strftime("%Y-%m-%d-%H:%M"),
        "title": title,
        "subtitles": subs,
        "message": msgs,
        "mentions": mention_str,
        "repeat": int(repeat_seconds / 60) if repeat_seconds else None,  # store repeat in minutes
    }

    # Persist using DB
    await upsert_reminder(ctx.guild.id, reminder_obj)

    print(f"\t[MAKE] Reminder ID: {reminder_obj['reminder_id']} Created!")
    await ctx.send(f"Reminder {title} set for {mentions} at {time}", ephemeral=True)

@bot.hybrid_command(
    name="reminders",
    description="List all reminders for the server",
)
async def list_reminders(ctx: commands.Context):
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

    if not reminders:
        em.add_field(
            name="No reminders",
            value="There are no reminders set for this server.",
            inline=False,
        )
    else:
        print(f"[LIST] Parsing {len(reminders)} reminders in {ctx.guild.name}")
        for reminder in reminders:
            # next reminder time and local time rendering
            next_unix = int(datetime.strptime(reminder["time"], "%Y-%m-%d-%H:%M").timestamp())
            repeat_text = await seconds2time(reminder["repeat"] * 60) if reminder.get("repeat") else "No Repeat Set"

            value_str = (
                f"> `Next Reminder`: {reminder['time']}\n"
                f"> `Local Time`: <t:{next_unix}:F>\n"
                f"> `Title`: {reminder.get('title','')}\n"
                f"> `ID`: {reminder['reminder_id']}\n"
                f"> `Repeat every`: {repeat_text}\n"
                f"> `Issuer`: <@{reminder['issuer_id']}>"
            )

            mentions_str = " ".join(reminder.get("mentions", []))

            em.add_field(
                name=f"Reminder for {mentions_str}",
                value=value_str,
                inline=False,
            )

    await ctx.send(embed=em, ephemeral=True)
    print(f"[LIST] Sent reminders list of {len(reminders)} reminders in {ctx.guild.name} -> {ctx.channel.name}")

@bot.hybrid_command(
    name="delete_reminder",
    description="Delete a reminder by ID",
    reminder_id="ID of the reminder to delete",
)
async def delete_reminder(ctx: commands.Context, reminder_id: str):
    """
    Delete a reminder by ID
    """
    print(f"[DLET] {ctx.author.name} deleting reminder {reminder_id} in {ctx.guild.name}")

    # Ensure permission: only issuer, server owner, admin, or bot owner
    reminders = await load_reminders(ctx.guild.id)
    found = None
    for r in reminders:
        if r["reminder_id"] == reminder_id:
            found = r
            break

    if not found:
        await ctx.send("Reminder not found... Please ensure you have the correct Reminder ID", ephemeral=True)
        return

    # Permission checks
    if (found["issuer_id"] != ctx.author.id) and (ctx.author.id != ctx.guild.owner_id) and not ctx.author.guild_permissions.administrator and not await bot.is_owner(ctx.author):
        await ctx.send("You must be the Reminder Author, Server Owner, Server Admin, or Bot Owner to delete this reminder!", ephemeral=True)
        return

    deleted = await delete_reminder_by_id(ctx.guild.id, reminder_id)
    if deleted > 0:
        await ctx.send("Reminder deleted!", ephemeral=True)
        print(f"[DLET] Deleted reminder {reminder_id} in {ctx.guild.name}")
    else:
        await ctx.send("Reminder not found... Please ensure you have the correct Reminder ID", ephemeral=True)

@bot.hybrid_command(
    name="show_reminder",
    description="Test a reminder",
    id="ID of the reminder to test",
)
async def test_reminder(ctx: commands.Context, id: str):
    """
    Test a reminder: sends the reminder embed to the stored channel (non-ephemeral).
    """
    try:
        print(f"[REMI] {ctx.author.name} testing reminder {id} in {ctx.guild.name}")
        reminders = await load_reminders(ctx.guild.id)

        for reminder in reminders:
            if reminder["reminder_id"] == id:
                channel = bot.get_channel(reminder["channel_id"])
                if channel is None:
                    await ctx.send("Channel for this reminder cannot be found.", ephemeral=True)
                    return

                em = dc.Embed(
                    title=reminder.get("title", ""),
                    color=0x00ff00,
                )

                subtitles = str(reminder.get("subtitles", "")).split("\\n")
                messages = str(reminder.get("message", "")).split("\\n")

                for i, subtitle in enumerate(subtitles):
                    em.add_field(
                        name=subtitle,
                        value=messages[i] if i < len(messages) else "",
                        inline=False,
                    )

                await ctx.send(ephemeral=True, embed=em, content=" ".join(reminder.get("mentions", [])) if reminder.get("mentions") else None)
                print(f"[REMI] Tested reminder {reminder['reminder_id']} to {channel.name} in {ctx.guild.name}")
                return

        await ctx.send("Reminder not found... Please ensure you have the correct Reminder ID", ephemeral=True)
    except Exception as e:
        await ctx.send(f"Error testing reminder: {str(e)}", ephemeral=True)

@bot.hybrid_command(
    name="bottime",
    description="Get the time of the bot",
    time="Time in UTC to convert to your local time 'HH:MM' or 'MM-DD-HH:MM' or 'DD-HH:MM' or 'YY-MM-DD-HH:MM'"
)
async def bot_time(ctx: commands.Context, time: typing.Optional[str] = None):
    await ctx.defer(ephemeral=True)

    try:
        if time is None:
            time = datetime.now().strftime("%Y-%m-%d-%H:%M")

        datetime_obj = parse_flexible_time(time)
    except ValueError as e:
        await ctx.send(str(e), ephemeral=True)
        return

    time_int = int(datetime_obj.timestamp())
    await ctx.send(f"## {datetime_obj.strftime('%Y-%m-%d-%H:%M')} UTC (Bot Time) is:\n## <t:{time_int}:F> Your Time", ephemeral=True)

@bot.hybrid_command(
    name="localtime",
    description="Convert a local time with UTC offset (e.g. -7, +2) to the bot's UTC time or your timezone code",
    time="Your local time you want to convert to bot time",
    utc="Your UTC offset (e.g. +2, -5, etc.)",
    timezone="Your timezone (e.g. MDT, EST, etc.)",
)
async def local_to_bot(ctx: commands.Context, time: typing.Optional[str] = None, timezone: typing.Optional[str] = None, utc: typing.Optional[str] = None):
    if (utc and timezone) or (not utc and not timezone):
        await ctx.send("Please provide either a UTC offset or a timezone, but not both.", ephemeral=True)
        return

    if timezone:
        try:
            utc = get_timezone_offset_str(timezone)
        except FileNotFoundError:
            await ctx.send(f"timezones_info.json file not found. Please Contact Bot Owner", ephemeral=True)
            return
        except ValueError as e:
            await ctx.send(str(e), ephemeral=True)
            return

        await time_convert(
            ctx,
            time=time if time is not None else (datetime.now() + timedelta(minutes=parse_UTC(utc))).strftime("%Y-%m-%d-%H:%M"),
            timezone=timezone if timezone is not None else "UTC",
            to=None
        )
    elif utc:
        try:
            utc_offset = parse_UTC(utc)
            if time is None:
                time = datetime.now().strftime("%Y-%m-%d-%H:%M")
            bot_time_offset = (parse_flexible_time(time) + timedelta(minutes=utc_offset)).strftime("%Y-%m-%d-%H:%M")
            await ctx.send(f"## {time} UTC{utc} is:\n## {bot_time_offset} UTC", ephemeral=True)
        except ValueError as e:
            await ctx.send(str(e), ephemeral=True)
            return

@bot.hybrid_command(
    name="timeconvert",
    description="Convert a time to another timezone",
    time="Time you want to convert",
    timezone="Origin timezone (e.g. MDT, EST, etc.)",
    to="Timezone to convert to (e.g. GMT, MDT, EST, etc.)",
)
async def time_convert(ctx: commands.Context, time: typing.Optional[str] = None, timezone: typing.Optional[str] = None, to: typing.Optional[str] = None):
    await ctx.defer(ephemeral=True)

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
        to = "UTC"
        target_utc = "+0:00"

    try:
        origin_offset = parse_UTC(origin_utc)
        target_offset = parse_UTC(target_utc)
        if time is None:
            time = (datetime.now() + timedelta(minutes=origin_offset)).strftime("%Y-%m-%d-%H:%M")

        origin_datetime = parse_flexible_time(time)
        utc_datetime = origin_datetime - timedelta(minutes=origin_offset)
        unix_time = int(utc_datetime.timestamp())
        target_datetime = utc_datetime + timedelta(minutes=target_offset)

        await ctx.send(
            f"## {origin_datetime.strftime('%Y-%m-%d-%H:%M')} {timezone.upper()} (UTC{origin_utc}) is:\n"
            f"## {target_datetime.strftime('%Y-%m-%d-%H:%M')} {to.upper()} (UTC{target_utc})\n"
            f"### <t:{unix_time}:F> in your local time",
            ephemeral=True
        )
    except Exception as e:
        await ctx.send(f"Error: {str(e)}", ephemeral=True)
        return

@bot.hybrid_command(
    name="timezones",
    description="List all accepted timezones",
)
async def list_timezones(ctx: commands.Context):
    """
    List all accepted timezones
    """
    ems = []

    try:
        with open("data/timezones_info.json", "r") as f:
            timezones_info: dict[str, str] = json.load(f)
    except FileNotFoundError:
        await ctx.send("timezones_info.json file not found. Please Contact Bot Owner", ephemeral=True)
        return

    em = dc.Embed(
        title="Available Timezones",
        description="List of available timezones with their UTC offsets",
        color=0x00ff00
    )
    for i, (timezone, utc) in enumerate(timezones_info.items()):
        em.add_field(
            name=f"{timezone:>5}",
            value=f"UTC{utc}",
            inline=True
        )

        if (i + 1) % 24 == 0:
            em.set_footer(text=f"Page {len(ems) + 1} of {len(timezones_info) // 24 + 1}")
            ems.append(em)
            em = dc.Embed(
                title="Available Timezones",
                description="List of available timezones with their UTC offsets",
                color=0x00ff00
            )

    em.set_footer(text=f"Page {len(ems) + 1} of {len(ems) + 1}")
    ems.append(em)

    pages = Paginator(ems)
    msg = await ctx.send(embed=ems[0], view=pages, ephemeral=True)
    pages.message = msg

# TASKS
@tasks.loop(seconds=60)
async def reminder_task():
    """
    Check reminders every minute and handle sending/updating/deleting via DB
    """
    print("[REMI] Checking reminders...")
    now_str = datetime.now().strftime("%Y-%m-%d-%H:%M")
    now_dt = datetime.strptime(now_str, "%Y-%m-%d-%H:%M")
    print(f"\t[REMI] Current time: {now_str}")

    for guild in bot.guilds:
        db = get_db_for_guild(guild.id)
        reminders = db.get_all()
        updated_any = False

        # Iterate over a copy to safely modify DB
        for reminder in list(reminders):
            try:
                reminder_time = datetime.strptime(reminder["time"], "%Y-%m-%d-%H:%M")
            except Exception:
                # Skip malformed entries
                continue

            late = reminder_time < now_dt
            do_reminder = late or (reminder_time == now_dt)

            if late:
                print(f"\t[REMI] Reminder {reminder['reminder_id']} is in the past!")
                if reminder.get("repeat") is not None:
                    # Calculate how many repeats have passed and update time accordingly
                    delta_min = (now_dt - reminder_time).total_seconds() // 60
                    repeats_passed = int(delta_min // reminder["repeat"]) + 1
                    new_time = reminder_time + timedelta(minutes=repeats_passed * reminder["repeat"])
                    reminder["time"] = new_time.strftime("%Y-%m-%d-%H:%M")
                    db.update_by("reminder_id", reminder["reminder_id"], {"time": reminder["time"]})
                    updated_any = True

            if do_reminder:
                await send_reminder(reminder, guild)

                if reminder.get("repeat") is None:
                    # Not repeating, delete from DB
                    db.delete_by("reminder_id", reminder["reminder_id"])
                    updated_any = True
                    print(f"\t[REMI] No repeat set. Removing reminder {reminder['reminder_id']} from {guild.name}")
                elif not late:
                    # Regular non-late repeating reminder; update next time by adding repeat minutes
                    next_time = datetime.strptime(reminder["time"], "%Y-%m-%d-%H:%M") + timedelta(minutes=reminder["repeat"])
                    reminder["time"] = next_time.strftime("%Y-%m-%d-%H:%M")
                    db.update_by("reminder_id", reminder["reminder_id"], {"time": reminder["time"]})
                    updated_any = True
                # if late and has repeat handled above

        if updated_any:
            print(f"\t[REMI] Updated reminders stored for guild {guild.name} ({guild.id})")

    print("[REMI] Finished checking reminders!")

@tasks.loop(minutes=15)
async def heartbeat_task():
    """
    Send a heartbeat to the healthcheck service every 15 minutes
    """
    print("[BEAT] Sending heartbeat to healthchecks.io...")
    heartbeat_uuid = os.getenv("HEARTBEAT_UUID")
    if not heartbeat_uuid:
        print("[BEAT] No HEARTBEAT_UUID set; skipping heartbeat.")
        return

    try:
        response = requests.get(f"https://hc-ping.com/{heartbeat_uuid}")
        if response.status_code == 200:
            print("[BEAT] Heartbeat sent successfully!")
            if not reminder_task.is_running():
                reminder_task.start()
                print("\t[BEAT] Restarted reminder task successfully.")
        else:
            print(f"[BEAT] Failed to send heartbeat: {response.status_code} - {response.text}")
            if reminder_task.is_running():
                reminder_task.cancel()
                print("\t[BEAT] Stopped reminder task successfully.")
    except Exception as e:
        print(f"[BEAT] Failed to send ping: {e}")

# OWNER COMMANDS
@bot.command(
    name="sync",
    description="sync the tree",
)
@commands.is_owner()
async def sync(ctx: commands.Context):
    """
    Sync the tree
    """
    msg = await ctx.send("Syncing...", ephemeral=True)
    await bot.tree.sync()
    try:
        await ctx.message.delete()
    except Exception:
        pass
    await msg.edit(content="Synced the tree!", delete_after=2)
    print(f"[REMI] Synced the tree!")

# Runner
async def run_bot(token: str):
    while True:
        try:
            await bot.start(token)
        except (dc.ConnectionClosed, dc.GatewayNotFound, dc.HTTPException) as e:
            print(f"[WARN] Lost connection: {e}. Retrying in 10s...")
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            print("[INFO] Bot shutdown requested!")
            break
        except Exception as e:
            with open(f"error_{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.log", "a") as f:
                f.write(f"{str(e)}\n")

async def sleep_forever():
    while True:
        await asyncio.sleep(3600)

if os.getenv("TEST_ENV") == "TRUE":
    print("[INFO] Running in test environment!")
    token = os.getenv("TEST_TOKEN")
elif os.getenv("TEST_ENV") == "FALSE":
    token = os.getenv("TOKEN")
else:
    print("[ERROR] TEST_ENV not set!")
    try:
        asyncio.run(sleep_forever())
    except asyncio.CancelledError:
        print("[INFO] Sleep Cancelled!")

try:
    asyncio.run(run_bot(token))
except Exception as e:
    # Append to error logs
    with open(f"fatal_error_{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.log", "a") as f:
        f.write(f"{str(e)}\n")
