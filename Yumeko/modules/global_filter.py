import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pymongo import MongoClient
from datetime import datetime, timedelta
from Yumeko.database import gfilter_collection
from config import config
from Yumeko import app

# Configure Logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

OWNER_ID = config.OWNER_ID

# Helper: Check if user is the owner
def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

# Helper: Create a temporary invite link
async def create_temp_invite(channel_id: int, expire_in: int = 2400):
    try:
        invite = await app.create_chat_invite_link(
            chat_id=channel_id,
            expire_date=int((datetime.now() + timedelta(seconds=expire_in)).timestamp()),
            member_limit=0
        )
        return invite.invite_link
    except Exception as e:
        logging.error(f"Error creating invite link: {e}")
        return None

# /setgfilter [filter name] [channel id]
@app.on_message(filters.command("setgfilter") & filters.user(OWNER_ID))
async def setgfilter_handler(client: Client, message: Message):
    try:
        if not message.reply_to_message or not message.reply_to_message.media:
            await message.reply("⚠️ Please reply to a media message (photo/gif/sticker) to set a global filter.")
            return

        # Extract filter name and channel ID using square brackets
        import re
        match = re.search(r"\[(.+?)\]\s*\[(.+?)\]", message.text)
        if not match:
            await message.reply("⚠️ Usage: /setgfilter [filter name] [channel id]")
            return

        filter_name = match.group(1).strip().lower()
        channel_id = match.group(2).strip()

        if not channel_id.startswith("-100"):
            await message.reply("⚠️ Invalid channel ID! Channel IDs must start with `-100`.")
            return

        channel_id = int(channel_id)

        # Check if bot is an admin in the channel
        try:
            chat_member = await app.get_chat_member(chat_id=channel_id, user_id=client.me.id)
            if chat_member.status not in ["administrator", "creator"]:
                await message.reply("⚠️ I must be an **admin** in the specified channel.")
                return
        except Exception as e:
            logging.error(f"Failed to verify admin status: {e}")
            await message.reply("⚠️ Failed to verify channel admin status. Ensure the **channel ID is correct** and I am added.")
            return

        # Identify media type and store file ID
        media = None
        media_type = None
        if message.reply_to_message.sticker:
            media = message.reply_to_message.sticker.file_id
            media_type = "sticker"
        elif message.reply_to_message.photo:
            media = message.reply_to_message.photo.file_id
            media_type = "photo"
        elif message.reply_to_message.animation:
            media = message.reply_to_message.animation.file_id
            media_type = "animation"
        elif message.reply_to_message.video:
            media = message.reply_to_message.video.file_id
            media_type = "video"
        elif message.reply_to_message.document:
            media = message.reply_to_message.document.file_id
            media_type = "document"

        if not media:
            await message.reply("⚠️ Unsupported media type. Use **image, gif, sticker, or video**.")
            return

        # Save filter to the database
        filter_data = {
            "filter_name": filter_name,
            "channel_id": channel_id,
            "media_file_id": media,
            "media_type": media_type,
            "timestamp": datetime.now()
        }
        gfilter_collection.update_one({"filter_name": filter_name}, {"$set": filter_data}, upsert=True)
        logging.info(f"✅ Global filter '{filter_name}' set for channel {channel_id}.")
        await message.reply(f"✅ **Global filter '{filter_name}'** set successfully for channel **{channel_id}**.")

    except Exception as e:
        logging.error(f"Error setting global filter: {e}")
        await message.reply(f"⚠️ An error occurred: {e}")

# Trigger filter
@app.on_message(filters.text & ~filters.private)
async def trigger_filter(client: Client, message: Message):
    text = message.text.strip().lower()

    # Fetch filter from MongoDB (ASYNC)
    filter_data = await gfilter_collection.find_one({"filter_name": text})

    if not filter_data:
        return  

    channel_id = filter_data.get("channel_id")
    media_file_id = filter_data.get("media_file_id")
    media_type = filter_data.get("media_type")

    try:
        chat = await app.get_chat(chat_id=channel_id)
        channel_name = chat.title
    except Exception:
        channel_name = "Unknown Channel"

    invite_link = await create_temp_invite(channel_id)
    if not invite_link:
        invite_link = "Unable to generate link."

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text=channel_name, url=invite_link)]])

    try:
        # Send media based on type
        if media_type == "sticker":
            await message.reply_sticker(sticker=media_file_id, reply_markup=keyboard)
        elif media_type == "animation":
            await message.reply_animation(animation=media_file_id, reply_markup=keyboard)
        elif media_type == "photo":
            await message.reply_photo(photo=media_file_id, reply_markup=keyboard)
        elif media_type == "video":
            await message.reply_video(video=media_file_id, reply_markup=keyboard)
        elif media_type == "document":
            await message.reply_document(document=media_file_id, reply_markup=keyboard)
        else:
            await message.reply("⚠️ Unsupported media type stored in the database.")
    except Exception as e:
        logging.error(f"Error sending media: {e}")
        await message.reply(f"⚠️ Error sending media: {e}")

# /gfilters command
@app.on_message(filters.command("gfilters") & filters.user(OWNER_ID))
async def list_gfilters(client: Client, message: Message):
    try:
        filters_cursor = gfilter_collection.find()
        filters_list = []

        async for f in filters_cursor:
            try:
                chat = await app.get_chat(chat_id=f["channel_id"])
                channel_name = chat.title
            except Exception:
                channel_name = "Unknown"

            filters_list.append(f"📌 `{f['filter_name']}` → {channel_name}")

        if not filters_list:
            await message.reply("❌ No global filters set.")
            return

        await message.reply("\n".join(filters_list))
    except Exception as e:
        logging.error(f"Error listing filters: {e}")
        await message.reply(f"⚠️ Error listing global filters: {e}")

# /removegfilter command
@app.on_message(filters.command("removegfilter") & filters.user(OWNER_ID))
async def remove_gfilter(client: Client, message: Message):
    try:
        match = re.search(r"\[(.+?)\]", message.text)
        if not match:
            await message.reply("⚠️ Usage: /removegfilter [filter name]")
            return

        filter_name = match.group(1).strip().lower()
        result = gfilter_collection.delete_one({"filter_name": filter_name})

        if result.deleted_count:
            await message.reply(f"✅ Global filter '{filter_name}' removed.")
        else:
            await message.reply("❌ No such global filter found.")
    except Exception as e:
        logging.error(f"Error removing filter: {e}")
        await message.reply(f"⚠️ An error occurred: {e}")

