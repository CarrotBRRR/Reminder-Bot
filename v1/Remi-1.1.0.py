import os, json, uuid, requests, typing, base64
import discord as dc
from datetime import datetime, timedelta
from discord.ext import tasks, commands
from dotenv import load_dotenv

from ReminderLib.Paginator import Paginator
from ReminderLib.Parser import *
from ReminderLib.DBController import *

print("[INFO] REMI v1.1.0 - Reminder Bot")
load_dotenv()

intents = dc.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True

bot = commands.Bot(command_prefix="rm.", intents=intents)

# Utilities
def ensure_guild_storage(guild: dc.Guild):
    path = f"data/{guild.id}"
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"[INIT] Created folder for guild: {guild.name} - {guild.id}")

    file_path = f"{path}/reminders.json"
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            json.dump([], f, indent=4)
        print(f"[INIT] Created reminders file for guild: {guild.name} - {guild.id}")

def uuid_base62() -> str:
    return base64.b64encode(uuid.uuid4().bytes).decode("utf-8").rstrip("=\n").replace("/", "").replace("+", "")

def create_reminder_embed(reminder: dict) -> dc.Embed:
    embed = dc.Embed(title=reminder["title"], color=0x00ff00)
    subtitles = reminder["subtitles"].split("\\n")
    messages = reminder["message"].split("\\n")
    for subtitle, message in zip(subtitles, messages):
        embed.add_field(name=subtitle, value=message, inline=False)
    return embed

# Events
@bot.event
async def on_ready():
    print(f"[INIT] Logged in as {bot.user.name}")
    for guild in bot.guilds:
        ensure_guild_storage(guild)

    if not reminder_task.is_running():
        await dc.utils.sleep_until(datetime.now() + timedelta(seconds=60 - datetime.now().second))
        reminder_task.start()
    if not heartbeat_task.is_running():
        heartbeat_task.start()
    print("[INIT] All loops started!")

@bot.event
async def on_guild_join(guild: dc.Guild):
    ensure_guild_storage(guild)
    print(f"[REMI] Joined guild: {guild.name} - {guild.id}")

# Reminder Tasks
@tasks.loop(seconds=60)
async def reminder_task():
    now = datetime.now().replace(second=0, microsecond=0)
    now_str = now.strftime("%Y-%m-%d-%H:%M")
    for guild in bot.guilds:
        reminders = await load_reminders(guild.id)
        updated = False
        for reminder in reminders[:]:
            rt = datetime.strptime(reminder["time"], "%Y-%m-%d-%H:%M")
            due = rt <= now
            if due:
                await send_reminder(reminder, guild)
                if reminder["repeat"] is None:
                    reminders.remove(reminder)
                else:
                    delta_min = (now - rt).total_seconds() // 60
                    cycles = int(delta_min // reminder["repeat"]) + 1
                    new_time = rt + timedelta(minutes=cycles * reminder["repeat"])
                    reminder["time"] = new_time.strftime("%Y-%m-%d-%H:%M")
                updated = True
        if updated:
            with open(f"data/{guild.id}/reminders.json", "w") as f:
                json.dump(reminders, f, indent=4)

@tasks.loop(minutes=15)
async def heartbeat_task():
    try:
        hb_id = os.getenv("HEARTBEAT_UUID")
        res = requests.get(f"https://hc-ping.com/{hb_id}")
        print("[BEAT] Heartbeat status:", res.status_code)
    except Exception as e:
        print(f"[BEAT] Heartbeat failed: {e}")

# Reminder Sending
async def send_reminder(reminder, guild):
    channel = bot.get_channel(reminder["channel_id"])
    mentions = " ".join(reminder["mentions"])
    embed = create_reminder_embed(reminder)
    await channel.send(content=mentions, embed=embed)

# Commands
@bot.hybrid_command(name="remind", description="Set a reminder")
async def create_reminder(
    ctx: commands.Context,
    time: typing.Optional[str] = None,
    title: str = "",
    subtitles: typing.Optional[str] = "",
    messages: typing.Optional[str] = "",
    mentions: typing.Optional[str] = "",
    repeat: typing.Optional[str] = None,
):
    reminders = await load_reminders(ctx.guild.id)
    if time is None:
        time = datetime.now().strftime("%Y-%m-%d-%H:%M")
    try:
        remind_time = parse_flexible_time(time)
    except ValueError as e:
        await ctx.send(str(e), ephemeral=True)
        return

    mention_str = await get_mentions(mentions, ctx.guild) or [ctx.author.mention]

    subtitle_list = subtitles.split("\n")
    message_list = messages.split("\n")
    if len(subtitle_list) < len(message_list):
        await ctx.send("Number of subtitles must be greater than or equal to number of messages.", ephemeral=True)
        return

    repeat_sec = await time2seconds(ctx, repeat) if repeat else None

    reminder = {
        "issuer_id": ctx.author.id,
        "guild_id": ctx.guild.id,
        "channel_id": ctx.channel.id,
        "reminder_id": uuid_base62(),
        "time": remind_time.strftime("%Y-%m-%d-%H:%M"),
        "title": title,
        "subtitles": subtitles,
        "message": messages,
        "mentions": mention_str,
        "repeat": int(repeat_sec / 60) if repeat_sec else None,
    }
    reminders.append(reminder)
    save_reminders(ctx.guild.id, reminders)
    await ctx.send(f"Reminder **{title}** set for {time} (mentions: {' '.join(mention_str)})", ephemeral=True)

@bot.hybrid_command(name="reminders", description="List all reminders")
async def list_reminders(ctx: commands.Context):
    reminders = await load_reminders(ctx.guild.id)
    em = dc.Embed(title="Reminders", description="List of reminders", color=0x00ff00)
    if not reminders:
        em.add_field(name="No reminders", value="No reminders are currently set.", inline=False)
    else:
        for reminder in reminders:
            time_unix = await time2unix(reminder['time'])
            repeat_str = await seconds2time(reminder['repeat'] * 60) if reminder['repeat'] else 'No Repeat'
            mention_str = ' '.join(reminder['mentions'])
            value = f"> **Time**: {reminder['time']} | <t:{time_unix}:F>\n> **Title**: {reminder['title']}\n> **ID**: {reminder['reminder_id']}\n> **Repeat**: {repeat_str}\n> **Issuer**: <@{reminder['issuer_id']}>"
            em.add_field(name=f"Reminder for {mention_str}", value=value, inline=False)
    await ctx.send(embed=em, ephemeral=True)

@bot.hybrid_command(name="delete_reminder", description="Delete a reminder by ID")
async def delete_reminder(ctx: commands.Context, reminder_id: str):
    reminders = await load_reminders(ctx.guild.id)
    for r in reminders:
        if r["reminder_id"] == reminder_id:
            if (r["issuer_id"] != ctx.author.id and
                ctx.author.id != ctx.guild.owner_id and
                not ctx.author.guild_permissions.administrator and
                not await bot.is_owner(ctx.author)):
                await ctx.send("Insufficient permissions to delete this reminder.", ephemeral=True)
                return
            reminders.remove(r)
            save_reminders(ctx.guild.id, reminders)
            await ctx.send("Reminder deleted.", ephemeral=True)
            return
    await ctx.send("Reminder ID not found.", ephemeral=True)

@bot.hybrid_command(name="bottime", description="Get current UTC time of the bot")
async def bot_time(ctx: commands.Context, time: typing.Optional[str] = None):
    await ctx.defer(ephemeral=True)
    if time is None:
        time = datetime.utcnow().strftime("%Y-%m-%d-%H:%M")
    try:
        dt = parse_flexible_time(time)
        unix = int(dt.timestamp())
        await ctx.send(f"## {dt.strftime('%Y-%m-%d-%H:%M')} UTC (Bot Time)\n### <t:{unix}:F> Your Local Time", ephemeral=True)
    except ValueError as e:
        await ctx.send(str(e), ephemeral=True)

@bot.hybrid_command(name="timeconvert", description="Convert time between timezones")
async def time_convert(ctx: commands.Context, time: typing.Optional[str] = None, timezone: typing.Optional[str] = None, to: typing.Optional[str] = None):
    await ctx.defer(ephemeral=True)
    try:
        origin_offset_str = get_timezone_offset_str(timezone or "UTC")
        target_offset_str = get_timezone_offset_str(to or "UTC")
        origin_offset = parse_UTC(origin_offset_str)
        target_offset = parse_UTC(target_offset_str)
        if time is None:
            base_time = datetime.utcnow()
        else:
            base_time = parse_flexible_time(time)
        utc_time = base_time - timedelta(minutes=origin_offset)
        target_time = utc_time + timedelta(minutes=target_offset)
        unix = int(utc_time.timestamp())
        await ctx.send(f"## {base_time.strftime('%Y-%m-%d-%H:%M')} {timezone or 'UTC'}\n### ➤ {target_time.strftime('%Y-%m-%d-%H:%M')} {to or 'UTC'}\n### <t:{unix}:F> in your local time", ephemeral=True)
    except Exception as e:
        await ctx.send(f"Error: {str(e)}", ephemeral=True)

@bot.hybrid_command(name="timezones", description="List all accepted timezones")
async def list_timezones(ctx: commands.Context):
    """
    List timezones grouped by UTC offset and paginated.
    """
    try:
        with open("data/timezones_info.json", "r") as f:
            timezones_info: dict[str, str] = json.load(f)
    except FileNotFoundError:
        await ctx.send("⚠️ `timezones_info.json` not found. Please contact the bot owner.", ephemeral=True)
        return

    # Group timezones by offset
    grouped: dict[str, list[str]] = {}
    for tz, offset in timezones_info.items():
        grouped.setdefault(offset, []).append(tz)

    # Sort offsets numerically (handles ±HH:MM)
    def offset_sort_key(offset: str) -> int:
        sign = -1 if offset.startswith("-") else 1
        h, m = map(int, offset.strip("+-").split(":"))
        return sign * (h * 60 + m)

    sorted_offsets = sorted(grouped.keys(), key=offset_sort_key)

    embeds: list[dc.Embed] = []
    for i, offset in enumerate(sorted_offsets):
        tz_list = sorted(grouped[offset])
        embed = dc.Embed(
            title=f"Timezones (UTC{offset})",
            description=f"{len(tz_list)} timezones in this group",
            color=0x00ff00
        )
        # Group 3 per line
        lines = [", ".join(tz_list[j:j+3]) for j in range(0, len(tz_list), 3)]
        embed.add_field(name="Timezones", value="\n".join(lines), inline=False)
        embed.set_footer(text=f"Page {i+1} of {len(sorted_offsets)}")
        embeds.append(embed)

    paginator = Paginator(embeds)
    msg = await ctx.send(embed=embeds[0], view=paginator, ephemeral=True)
    paginator.message = msg


@bot.command(name="sync", description="Sync command tree")
@commands.is_owner()
async def sync(ctx: commands.Context):
    msg = await ctx.send("Syncing...", ephemeral=True)
    await bot.tree.sync()
    await msg.edit(content="Synced.", delete_after=2)

bot.run(os.getenv("TOKEN"))
