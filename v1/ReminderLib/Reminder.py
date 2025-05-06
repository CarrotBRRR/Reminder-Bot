"""
Reminder.py
"""

import datetime
import discord as dc
from discord.ext import tasks, commands

class Reminder:  
    def __init__(
            self, 
            bot : commands.Bot, 
            id : str,
            title : str | None,
            subtitles : str | None,
            messages : str | None,
            footer : str | None,
            channel_id : int,
            time : datetime.datetime,
            repeat : bool,
            mentions : int | list[dc.User | dc.Role] | None,
        ):
        # Bot instance
        self.bot = bot                  # The bot instance
        
        # Reminder attributes
        self.id = id                    # Unique ID for the reminder UUIDv4 String
        self.title = title              # Title of the reminder
        self.subtitles = subtitles      # Message to send
        self.messages = messages        # Value to send (if any)
        self.footer = footer            # Footer to send (if any)

        # Reminder Options
        self.mentions = mentions          # User ID or Role ID to mention
        self.time = time                # Start time of the reminder (if any)
        self.repeat = repeat            # Whether the reminder should repeat or not

        # Guild and Channel IDs
        self.channel_id = channel_id    # Channel ID to send the message
        self.task = None       # Reminder task
    
    async def init_task(self):
        """
        Initializes the task for the reminder
        """
        print(f"[REMI] Initializing reminder task for {self.id}...")
        @tasks.loop(time=self.time, count=None if self.repeat else 1)
        async def reminder_task():

            # Set up Embed
            em = dc.Embed(
                title=self.title,
                description=self.message,
                color=0x00ff00
            )

            # Parse the message and title
            subtitles = self.subtitles.split("\n")
            messages = self.messages.split("\n")
            for i, subtitle in enumerate(subtitles):
                em.add_field(
                    name=subtitle,
                    value=messages[i],
                    inline=False
                )

            if self.footer:
                em.set_footer(text=self.footer)

            # Get the channel
            channel = self.bot.get_channel(self.channel_id)
            if not channel:
                print(f"[REMI] ERROR: Channel {self.channel_id} not found")
                return
            
            # Parse the mentions
            for mention in self.mentions:
                payload_txt += mention.mention + " "

            # Send the message
            channel.send(
                content=payload_txt,
                embed=em
            )
            
        print(f"[REMI] Reminder task for {self.id} initialized!")  
        reminder_task.start()
        self.task = reminder_task

    async def start(self):
        """
        Starts the reminder task
        """
        self.task.start()
        print(f"[REMI] Reminder {self.id} started!")

    async def stop(self):
        """
        Stops the reminder task
        """
        if self.task.is_running():
            self.task.cancel()
            print(f"[REMI] Reminder {self.id} stopped!")
        else:
            print(f"[REMI] Reminder {self.id} is not running!")
    
    def toDict(self) -> dict:
        """
        Converts the reminder to a dictionary
        """
        return {
            "id": self.id,
            "title": self.title,
            "subtitles": self.subtitles,
            "messages": self.messages,
            "footer": self.footer,
            "channel_id": self.channel_id,
            "time": self.time.strftime("%H:%M:%S"),
            "repeat": self.repeat,
            "mentions": [mention.id for mention in self.mentions] if self.mentions else None
        }
    