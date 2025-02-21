import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pymongo import MongoClient
from datetime import datetime, timedelta
from Yumeko.database import gfilter_collection 
from config import config
from Yumeko import app

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

OWNER_ID = config.OWNER_ID

# Check if user is the owner
def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

# Create a temporary invite link for a channel
async def create_temp_invite(channel_id: int, expire_in: int = 2400):
    try:
        invite = await app.create_chat_invite_link(
            chat_id=channel_id,
            expire_date=int((datetime.now() + timedelta(seconds=expire_in)).timestamp()),
            member_limit=0
        )
        return invite.invite_link
    except Exception as e:
        logger.error(f"Error creating invite link: {e}")
        return None

# Command: /setgfilter [filter_name] [channel_id]
@app.on_message(filters.command("setgfilter") & filters.user(OWNER_ID))
async def setgfilter_handler(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.media:
        await message.reply("Please reply to a message with media (image/gif/sticker) to set a global filter.")
        return

    try:
        args = message.text.split("[")
        if len(args) < 3:
            await message.reply("Usage: /setgfilter [filter_name] [channel_id]")
            return

        filter_name = args[1].strip("] ").lower()
        channel_id = args[2].strip("] ")

        if not channel_id.lstrip("-").isdigit():
            await message.reply("Invalid channel ID! Please provide a valid numeric channel ID.")
            return

        channel_id = int(channel_id)

        # Check if bot is admin in the channel
        try:
            chat_member = await app.get_chat_member(chat_id=channel_id, user_id=client.me.id)
            if chat_member.status not in ["administrator", "creator"]:
                await message.reply("⚠️ I must be an admin in the specified channel. Please check my permissions.")
                return
        except Exception as e:
            logger.error(f"Failed to verify admin status: {e}")
            await message.reply("Failed to verify channel admin status. Make sure the channel ID is correct and I have been added.")
            return

        # Store media file ID
        media = message.reply_to_message.sticker or \
                message.reply_to_message.photo or \
                message.reply_to_message.animation or \
                message.reply_to_message.document

        if not media:
            await message.reply("Media type not supported. Use an image, gif, or sticker.")
            return

        # Save to database
        filter_data = {
            "filter_name": filter_name,
            "channel_id": channel_id,
            "media_file_id": media.file_id,
            "timestamp": datetime.now()
        }
        gfilter_collection.update_one({"filter_name": filter_name}, {"$set": filter_data}, upsert=True)
        await message.reply(f"✅ Global filter '{filter_name}' set successfully for channel {channel_id}.")

    except Exception as e:
        logger.error(f"Error in setgfilter_handler: {e}")
        await message.reply(f"An error occurred: {e}")

# Auto-trigger filter when a keyword matches
@app.on_message(filters.text & ~filters.private)
async def trigger_filter(client: Client, message: Message):
    text = message.text.strip().lower()

    try:
        filter_data = gfilter_collection.find_one({"filter_name": text})
        if not filter_data:
            return
        
        channel_id = filter_data.get("channel_id")
        media_file_id = filter_data.get("media_file_id")

        try:
            chat = await app.get_chat(chat_id=channel_id)
            channel_name = chat.title
        except Exception:
            channel_name = "Unknown Channel"

        invite_link = await create_temp_invite(channel_id) or "Unable to generate link."

        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text=channel_name, url=invite_link)]])

        try:
            if message.reply_to_message:
                await message.reply_to_message.reply_photo(photo=media_file_id, reply_markup=keyboard)
            else:
                await message.reply_photo(photo=media_file_id, reply_markup=keyboard)
        except Exception:
            try:
                await message.reply_document(document=media_file_id, reply_markup=keyboard)
            except Exception as e:
                logger.error(f"Error sending media: {e}")
                await message.reply("⚠️ Error sending media.")

    except Exception as e:
        logger.error(f"Error in trigger_filter: {e}")

# List all filters
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
            filters_list.append(f"{f['filter_name']} [{f['channel_id']}] {channel_name}")

        if not filters_list:
            await message.reply("No global filters set.")
            return

        await message.reply("\n".join(filters_list))

    except Exception as e:
        logger.error(f"Error listing global filters: {e}")
        await message.reply(f"Error listing global filters: {e}")

# Remove a filter
@app.on_message(filters.command("removegfilter") & filters.user(OWNER_ID))
async def remove_gfilter(client: Client, message: Message):
    try:
        args = message.text.split("[")
        if len(args) < 2:
            await message.reply("Usage: /removegfilter [filter_name]")
            return
        
        filter_name = args[1].strip("] ").lower()
        result = gfilter_collection.delete_one({"filter_name": filter_name})

        if result.deleted_count:
            await message.reply(f"✅ Global filter '{filter_name}' removed.")
        else:
            await message.reply("⚠️ No such global filter found.")

    except Exception as e:
        logger.error(f"Error removing filter: {e}")
        await message.reply(f"An error occurred: {e}")

