"""
Handles Storage, Retrieval, and Execution of Reminders
"""

import json, os, uuid, datetime
from Reminder import Reminder
from discord.ext import commands

class ReminderController:
    async def __init__(self, bot : commands.Bot):
        self.bot = bot          # The bot instance
        self.reminders = list[Reminder]     # List of reminders

    async def load_reminders(self):
        if not self.reminders:
            if os.path.exists("reminders.json"):
                with open("reminders.json", "r") as f:
                    reminder_data = json.load(f)

                for reminder in reminder_data:
                    self.reminders.append(
                        
                    )
            else:
                self.reminders = list[Reminder]
    
    async def start_reminders(self):
        for reminder in self.reminders:
            if not reminder.running:
                reminder.start()

    async def stop_reminder(self, reminder : Reminder):
        """
        Stops the reminder and removes it from the list
        """
        reminder.stop()
        self.reminders.remove(reminder)
        self.save_reminders()

    async def create_reminder(
            self, 
            title : str | None,
            subtitles : str | None,
            messages : str | None,
            footer : str | None,
            channel_id : int,
            mention : int | list[int] | None,
            start_time : datetime.datetime | None,
            interval : str | None,
            ): # ADD PARAMETERS
        id = str(uuid.uuid4())

        reminder = Reminder(
            # PARAMETERS
        )
        
        self.reminders.append(reminder)
        self.save_reminders()

        reminder.start()

        return reminder
    
    async def save_reminders(self):
        """
        Saves the reminders to a JSON file
        """
        with open("reminders.json", "w") as f:
            json.dump([reminder.to_dict() for reminder in self.reminders], f, indent=4)

    async def delete_reminder(self, reminder : Reminder):
        """
        Stops the reminder and removes it from the list
        """
        reminder.stop()
        self.reminders.remove(reminder)
        self.save_reminders()
    
    async def get_reminders(self):
        return self.reminders
