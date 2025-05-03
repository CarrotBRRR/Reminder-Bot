"""

"""

import datetime
import discord as dc
from discord.ext import tasks, commands

class Reminder:  
    async def __init__(
            self, 
            bot : commands.Bot, 
            id : str,

            title : str | None,
            subtitles : str | None,
            messages : str | None,
            footer : str | None,

            channel_id : int,

            length : int,
            starttime : datetime.datetime,
            repeat : bool,
            mentions : int | list[int] | None,
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
        self.length = length            # Length of time to wait before sending the reminder in seconds
        self.starttime = starttime        # Start time of the reminder (if any)
        self.repeat = repeat            # Whether the reminder should repeat or not

        # Guild and Channel IDs
        self.channel_id = channel_id    # Channel ID to send the message

        self.reminder_task = self.init_task()                   # Initialize the task
    
    async def init_task(self):
        """
        Initializes the task for the reminder
        """
        
        if datetime.datetime.now() > self.starttime && se:
            print(f"[ERROR] Start time is in the past")
            self.reminder_task = None
            return None
            
        @tasks.loop(seconds=self.length, time=self.starttime)
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
                print(f"[ERROR] Channel {self.channel_id} not found")
                return
            
            # Parse the mentions
            for mention in self.mentions:
                payload_txt += f"<@{mention}>"

            # Send the message
            channel.send(
                content=payload_txt,
                embed=em
            )
            # Check if the reminder should repeat
            if not self.repeat:
                self.reminder_task.stop()
                self.reminder_task = None
                return
                
        return reminder_task

    async def start(self):
        """
        Starts the reminder task
        """
        self.reminder_task.start()

    async def stop(self):
        """
        Stops the reminder task
        """
        if self.reminder_task.is_running():
            self.reminder_task.stop()
    