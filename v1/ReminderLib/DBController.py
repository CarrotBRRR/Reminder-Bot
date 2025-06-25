import os, json, typing

async def load_reminders(guild_id : int) -> typing.List[typing.Dict]:
    """
    Load reminders from file
    """
    if not os.path.exists(f"data/{guild_id}/reminders.json"):
        print(f"\t[LOAD] No reminder folder found for {guild_id}.")
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

# Version 2 will not be using this, and we will ideally be handling this in a different way.
async def load_reminders_dm(user_id : int):
    if not os.path.exists(f"data/-1/{user_id}/reminders.json"):
        print(f"\t[LOAD] No reminder folder found for {user_id}.")
        return []

    with open(f"data/-1/{user_id}/reminders.json", "r") as f:
        reminders = json.load(f)

    if not len(reminders) == 0:
        print(f"\t[LOAD] Loaded {len(reminders)} reminders for {user_id}!")
    
    return reminders

async def save_reminders_dm(user_id : int, reminders : typing.List[typing.Dict]):
    print(f"\t[SAVE] Saving {len(reminders)} reminders for {user_id}...")
    if not os.path.exists(f"data/-1/{user_id}"):
        os.makedirs(f"data/-1/{user_id}")
        print(f"\t[SAVE] Created folder for user: {user_id}")

    with open(f"data/-1/{user_id}/reminders.json", "w") as f:
        json.dump(reminders, f, indent=4)
    print(f"\t[SAVE] Saved {len(reminders)} reminders for {user_id}!")