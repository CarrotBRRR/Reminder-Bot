import os, json, re, uuid, base64
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
    print("[INIT] Loading reminders...")
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

        # Load reminders for the guild
        reminders = await load_reminders(guild.id)
        print(f"\t[INIT] Loaded reminders for {guild.name} - {guild.id}")
    print(f"[INIT] Loaded {len(reminders)} reminders!")

    # Start the reminder loop
    if not check_reminders.is_running():
        check_reminders.start()
        print("[INIT] Started reminder loop!")

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

# HELPER FUNCTIONS
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
        await ctx.send("Invalid time format. Please use a format '1d 2h 12m' separated by spaces.", ephemeral=True)
        return 0
    
    total_seconds = 0
    for value, unit in matches:
        total_seconds += int(value) * time_factors[unit]

    return total_seconds

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
        return []

    with open(f"data/{guild_id}/reminders.json", "r") as f:
        reminders = json.load(f)

    return reminders

# COMMANDS
@bot.hybrid_command(
    name="remind",
    description="Set a reminder for yourself or someone else",
    time="Scheduled time in HH:MM format",
    mentions="Mention a user or a role",
)
async def create_reminder(
    ctx : commands.Context,
    time : typing.Optional[str] = datetime.now().strftime("%H:%M"), # Inital time to remind
    title : str = "",                                               # Title of the reminder
    subtitles : str = "",                                           # Subtitle of the reminder
    messages : str = "",                                             # Message to send
    mentions : str = "",                                            # Mentions to send the reminder to
    repeat : typing.Optional[str] = None,                           # Interval to repeat the reminder in the same format as time (i.e. amount of time to add)
):
    """
    Create a reminder!
    """
    reminders = await load_reminders(ctx.guild.id)
    
    print(f"[MAIN] {ctx.author.name} creating reminder in {ctx.guild.name}")
    print(f"\t[MAIN] Parsing info...")
    print(f"\t\t[MAIN] Parsing mentions...")
    mention_str = await get_mentions(mentions, ctx.guild)

    if mention_str is []:
        mention_str = [ctx.author.mention]
    
    print(f"\t\t[MAIN] Done!")
    print(f"\t\t[MAIN] Parsing Subtitles and Messages...")
    subs = []
    for subtitle in subtitles.split("\n"):
        subs.append(subtitle)

    msgs = []
    for message in messages.split("\n"):
        msgs.append(message)

    if len(subs) != len(msgs):
        await ctx.send("The number of subtitles and messages must be the same!", ephemeral=True)
        return
    
    print(f"\t\t[MAIN] Done!")
    print(f"\t\t[MAIN] Parsing repeat time...")
    repeat_seconds = await time2seconds(ctx, repeat) if repeat else None
    print(f"\t[MAIN] Finished Parsing info!")

    print(f"\t[MAIN] Creating reminder...")
    reminders.append({
        "issuer_id": ctx.author.id,
        "guild_id": ctx.guild.id,
        "channel_id": ctx.channel.id,
        "reminder_id": base64.b64encode(uuid.uuid4().bytes).decode('utf-8').strip("=="),

        "time": datetime.strptime(time, "%H:%M").strftime("%H:%M"),
        "title": title,
        "subtitles": subtitles,
        "message": message,
        "mentions": mention_str,
        "repeat": int(repeat_seconds/60) if repeat else None,
    })

    print(f"\t[MAIN] Done!")
    print(f"\t[MAIN] Saving reminder to file...")
    # Save reminders to file
    if not os.path.exists(f"data/{ctx.guild.id}"):
        os.makedirs(f"data/{ctx.guild.id}")
        print(f"[MAIN] Created folder for guild: {ctx.guild.name} - {ctx.guild.id}")

    with open(f"data/{ctx.guild.id}/reminders.json", "w") as f:
        json.dump(reminders, f, indent=4)
    print(f"\t[MAIN] Reminder Saved!")
    print(f"\t[MAIN] Reminder ID: {reminders[-1]['reminder_id']} Created!")
    await ctx.send(f"Reminder {title} set for {mentions} at {time}", ephemeral=True)

@bot.hybrid_command(
    name="reminderlist",
    description="List all reminders for the server",
)
async def list_reminders(ctx : commands.Context):
    """
    List all reminders for the server
    """
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
        for reminder in reminders:
            em.add_field(
                name=f"Reminder for {reminder['issuer_id']}",
                value=f"> Time: {reminder['time']}\n> Title: {reminder['title']}\n> ID: {reminder['reminder_id']}",
                inline=False,
            )
    
    await ctx.send(embed=em, ephemeral=True)

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
    print(f"[MAIN] {ctx.author.name} deleting reminder {reminder_id} in {ctx.guild.name}")
    reminders = await load_reminders(ctx.guild.id)

    for reminder in reminders:
        if reminder["reminder_id"] == reminder_id:
            reminders.remove(reminder)
            with open(f"data/{ctx.guild.id}/reminders.json", "w") as f:
                json.dump(reminders, f, indent=4)
            await ctx.send("Reminder deleted!", ephemeral=True)
            print(f"[MAIN] Deleted reminder {reminder_id} in {ctx.guild.name}")
            return

    await ctx.send("Reminder not found... Please ensure you have the correct Reminder ID", ephemeral=True)

@bot.hybrid_command(
    name="get_reminder",
    description="Test a reminder",
)
async def test_reminder(
    ctx : commands.Context,
    id : str,
):
    """
    Test a reminder
    """
    print(f"[MAIN] {ctx.author.name} testing reminder {id} in {ctx.guild.name}")
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
            
            await channel.send(embed=em)
            print(f"[MAIN] Tested reminder to {channel.name} - {channel.id} in {ctx.guild.name} - {ctx.guild.id}")
            return

    await ctx.send("Reminder not found... Please ensure you have the correct Reminder ID", ephemeral=True)


# TASKS
@tasks.loop(seconds=60)
async def check_reminders():
    """
    Check reminders every minute
    """
    print("[REMI] Checking reminders...")
    now = datetime.now().strftime("%H:%M")
    for guild in bot.guilds:
        reminders = await load_reminders(guild.id)
        for reminder in reminders:
            # If reminder is in the past
            # If the reminder is set to repeat, add the repeat time (minutes) to the reminder
            if reminder["repeat"] is not None:
                reminder_time = datetime.strptime(reminder["time"], "%H:%M")
                now_time = datetime.strptime(now, "%H:%M")
                if reminder_time < now_time:
                    delta = now_time - reminder_time
                    repeats_passed = (delta.total_seconds() // 60) // reminder["repeat"] + 1
                    reminder_time += timedelta(minutes=reminder["repeat"] * repeats_passed)
                    reminder["time"] = reminder_time.strftime("%H:%M")

            else: 
                # If the reminder is not set to repeat, do it now, and remove it later
                if datetime.strptime(reminder["time"], "%H:%M") < datetime.strptime(now, "%H:%M"):
                    reminder["time"] = now

            if reminder["time"] == now:
                print(f"\t[REMI] {now} Reminder found by {reminder['issuer_id']} in {guild.name}")
                channel = bot.get_channel(reminder["channel_id"])

                # Add the mentions to the message
                payload = ""
                for mention in reminder["mentions"]:
                    payload += f"{mention} "
                
                # Create the embed
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
                
                # Send the message
                await channel.send(f"{payload}", embed=em)
                print(f"\t[REMI] Sent reminder to {channel.name} - {channel.id} in {guild.name} - {guild.id}")

                # If the reminder is set to repeat, add the repeat time (minutes) to the reminder      
                if reminder["repeat"] is not None:
                    reminder["time"] = datetime.strftime((datetime.strptime(reminder["time"], "%H:%M") + timedelta(minutes=reminder["repeat"])), "%H:%M")

                else:
                    # If the reminder is not set to repeat, remove it from the list
                    reminders.remove(reminder)
                
                # Save new
                with open(f"data/{guild.id}/reminders.json", "w") as f:
                    json.dump(reminders, f, indent=4)

    print("[REMI] Finished checking reminders!")

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
    print("[MAIN] Synced the tree!")

bot.run(os.getenv("TOKEN"))