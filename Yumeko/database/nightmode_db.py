from Yumeko.database import nightmode_collection

async def enable_nightmode(chat_id: int, chat_title: str, owner_id: int, start_time: str, end_time: str, chat_username: str = None, chat_link: str = None):
    """Enable night mode for a specific chat and save details along with timing."""
    await nightmode_collection.update_one(
        {"chat_id": chat_id},
        {
            "$set": {
                "nightmode_enabled": True,
                "chat_title": chat_title,
                "owner_id": owner_id,
                "start_time": start_time,
                "end_time": end_time,
                "chat_username": chat_username,
                "chat_link": chat_link,
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

async def is_nightmode_enabled(chat_id: int) -> bool:
    """Check if night mode is enabled for a specific chat."""
    chat_data = await nightmode_collection.find_one({"chat_id": chat_id})
    return chat_data["nightmode_enabled"] if chat_data else False

async def get_nightmode_chat_info(chat_id: int):
    """Retrieve information about a specific chat in night mode."""
    return await nightmode_collection.find_one({"chat_id": chat_id})

async def update_nightmode_timings(chat_id: int, start_time: str, end_time: str):
    """Update night mode start and end times for a chat."""
    await nightmode_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"start_time": start_time, "end_time": end_time}},
        upsert=True
    )

async def get_all_nightmode_enabled_chats():
    """Retrieve all chat IDs with night mode enabled."""
    cursor = nightmode_collection.find({"nightmode_enabled": True}, {"chat_id": 1, "start_time": 1, "end_time": 1, "_id": 0})
    return [chat async for chat in cursor]

