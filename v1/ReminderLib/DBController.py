import os, json, typing

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

async def save_reminders(guild_id : int, reminders : typing.List[typing.Dict]):
    """
    Save reminders to file
    """
    print(f"\t[SAVE] Saving {len(reminders)} reminders for {guild_id}...")
    if not os.path.exists(f"data/{guild_id}"):
        os.makedirs(f"data/{guild_id}")
        print(f"\t[SAVE] Created folder for guild: {guild_id}")

    with open(f"data/{guild_id}/reminders.json", "w") as f:
        json.dump(reminders, f, indent=4)
    print(f"\t[SAVE] Saved {len(reminders)} reminders for {guild_id}!")