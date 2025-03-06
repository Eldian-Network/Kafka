from Yumeko.database import db  # Ensure this imports your MongoDB connection

NIGHTMODE_COLLECTION = db.nightmode  # Collection for night mode settings

async def enable_nightmode(chat_id, chat_title, owner_id, start_time="23:00", end_time="09:00"):
    """Enable night mode for a chat with default or custom timing."""
    await NIGHTMODE_COLLECTION.update_one(
        {"chat_id": chat_id},
        {"$set": {
            "chat_title": chat_title,
            "owner_id": owner_id,
            "nightmode_enabled": True,
            "start_time": start_time,
            "end_time": end_time
        }},
        upsert=True
    )

async def disable_nightmode(chat_id):
    """Disable night mode for a chat."""
    await NIGHTMODE_COLLECTION.update_one(
        {"chat_id": chat_id},
        {"$set": {"nightmode_enabled": False}}
    )

async def get_nightmode_chat_info(chat_id):
    """Retrieve night mode settings for a specific chat."""
    return await NIGHTMODE_COLLECTION.find_one({"chat_id": chat_id})

async def update_nightmode_timings(chat_id, start_time, end_time):
    """Update the night mode start and end time for a chat."""
    await NIGHTMODE_COLLECTION.update_one(
        {"chat_id": chat_id},
        {"$set": {"start_time": start_time, "end_time": end_time}}
    )

async def get_all_nightmode_enabled_chats():
    """Fetch all chats where night mode is enabled."""
    return await NIGHTMODE_COLLECTION.find({"nightmode_enabled": True}).to_list(None)
    
