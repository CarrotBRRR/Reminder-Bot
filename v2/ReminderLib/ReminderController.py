"""
Handles Storage, Retrieval, and Execution of Reminders
"""

import json, os, uuid, datetime
import discord as dc
from ReminderLib.Reminder import Reminder
from discord.ext import commands

class ReminderController:
    def __init__(self, bot : commands.Bot):
        self.bot = bot          # The bot instance
        self.reminders = []     # List of reminders

    async def load_reminders(self, guild_id : int):
        """
        Loads Reminders from a JSON file
        """
        guild_folder = f"data/{guild_id}"
        if not os.path.exists(guild_folder):
            print(f"[REMC] Creating new folder for guild {guild_id}...")
            os.makedirs(guild_folder)
            print(f"[REMC] Created folder for guild {guild_id}...")

        filepath = f"data/{guild_id}/reminders.json"
        if not os.path.exists(filepath):
            print(f"[REMC] Creating new reminders file for guild {guild_id}...")
            with open(filepath, "w") as f:
                json.dump([], f, indent=4)
            return
        
        else:
            print(f"[REMC] Loading reminders from {filepath}...")

        with open(filepath, "r") as f:
            data = json.load(f)

        if not data:
            print(f"[REMC] No reminders found for guild {self.bot.get_guild(guild_id).name}.")
            return

        mentions = []
        for mention in data["mentions"]:
            try:
                mentions.append(await self.bot.fetch_user(mention))
            except dc.NotFound:
                try:
                    role = self.bot.get_guild(guild_id).get_role(mention)
                    if role:
                        mentions.append(role)
                        break
                except dc.NotFound:
                    print(f"[REMC] Could not find mention {mention}.")
                
        for reminder_data in data:
            if reminder_data["repeat"]:
                self.reminders.append(
                    Reminder(
                        self.bot,
                        reminder_data["id"],
                        reminder_data["title"],
                        reminder_data["subtitles"],
                        reminder_data["messages"],
                        reminder_data["footer"],
                        reminder_data["channel_id"],
                        reminder_data["length"],
                        datetime.datetime.fromisoformat(reminder_data["starttime"]),
                        reminder_data["repeat"],
                        mentions
                    )
                )
            elif reminder_data["starttime"] > datetime.datetime.now():
                self.reminders.append(
                    Reminder(
                        self.bot,
                        reminder_data["id"],
                        reminder_data["title"],
                        reminder_data["subtitles"],
                        reminder_data["messages"],
                        reminder_data["footer"],
                        reminder_data["channel_id"],
                        reminder_data["length"],
                        datetime.datetime.fromisoformat(reminder_data["time"]),
                        reminder_data["repeat"],
                        mentions
                    )
                )
            elif reminder_data["starttime"] <= datetime.datetime.now() and not reminder_data["repeat"]:
                print(f"[REMC] Ignoring reminder {reminder_data['id']} because it has already passed.")

    async def start_reminders(self):
        for reminder in self.reminders:
            if not reminder.reminder_task.is_running():
                print(f"[REMC] Starting reminder {reminder.id}...")
                reminder.start()

    async def stop_reminder(self, reminder : Reminder):
        """
        Stops the reminder and removes it from the list
        """
        reminder.stop()
        self.reminders.remove(reminder)
        self.save_reminders()

    async def create_reminder(self, 
            title : str,
            subtitles : str,
            messages : str,
            footer : str,
            channel_id : int,
            starttime : datetime.datetime,
            repeat : bool,
            mentions : int | list[dc.User | dc.Role] | None,
            guild_id : int
        ):
        """
        Creates a new reminder and adds it to the list
        """
        reminder = Reminder(
            self.bot,
            str(uuid.uuid4()),
            title,
            subtitles,
            messages,
            footer,
            channel_id,
            starttime,
            repeat,
            mentions
        )

        self.reminders.append(reminder)

        print(f"[REMC] Creating reminder {reminder.id} for channel {channel_id}...")
        await reminder.init_task()
        await reminder.start()
        await self.save_reminders(guild_id)
        print(f"[REMC] Reminder {reminder.id} created in channel {channel_id}.")

        return reminder
    
    async def save_reminders(self, guild_id : int):
        """
        Saves the reminders to a JSON file
        """
        reminder_data = []
        for reminder in self.reminders:
            reminder_data.append(reminder.toDict())
        
        filepath = f"data/{guild_id}/reminders.json"
        with open(filepath, "w") as f:
            json.dump(reminder_data, f, indent=4)
        print(f"[REMC] Saved reminders to {filepath}.")
    
    async def get_reminders(self):
        return self.reminders
