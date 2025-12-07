"""
Parser module for the Reminder Bot
===
This module provides a parser for handling command arguments and options in the Reminder Bot
as well as conversions for various time segments
"""
import re, json
import discord as dc
import typing

from datetime import datetime

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
    Converts a datetime string to a Unix timestamp
    """
    datetime_obj = parse_flexible_time(datetime_str)

    return int(datetime_obj.timestamp())

async def get_mentions(mentions : str, guild : dc.Guild) -> typing.List[dc.User | dc.Role]:
    """
    Parses mentions from a string
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