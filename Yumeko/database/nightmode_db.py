from Yumeko.database import nightmode_collection

async def enable_nightmode(chat_id: int, chat_title: str, owner_id: int, start_time: str = "23:00", end_time: str = "09:00"):
    """Enable night mode for a specific chat and save its settings."""
    await nightmode_collection.update_one(
        {"chat_id": chat_id},
        {
            "$set": {
                "nightmode_enabled": True,
                "chat_title": chat_title,
                "owner_id": owner_id,
                "nightmode_start": start_time,
                "nightmode_end": end_time,
            }
        },
        upsert=True
    )

async def disable_nightmode(chat_id: int):
    """Disable night mode for a specific chat."""
    await nightmode_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"nightmode_enabled": False}},
        upsert=True
    )

async def set_nightmode_time(chat_id: int, start_time: str, end_time: str):
    """Update night mode start and end time for a chat."""
    await nightmode_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"nightmode_start": start_time, "nightmode_end": end_time}},
        upsert=True
    )

async def get_nightmode_settings(chat_id: int):
    """Retrieve night mode settings for a specific chat."""
    return await nightmode_collection.find_one({"chat_id": chat_id})

async def get_all_nightmode_enabled_chats():
    """Retrieve all chats with night mode enabled and their settings."""
    cursor = nightmode_collection.find({"nightmode_enabled": True})
    return [chat async for chat in cursor]
    
