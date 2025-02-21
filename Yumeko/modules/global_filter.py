import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pymongo import MongoClient
from datetime import datetime, timedelta
from Yumeko.database import gfilter_collection

# Import config variables from config.py
from config import config

# Import the Pyrogram app from Yumeko
from Yumeko import app

# Config imports
OWNER_ID = config.OWNER_ID

# Helper: Create a temporary invite link for a channel
async def create_temp_invite(channel_id: int, expire_in: int = 2400):
    try:
        invite = await app.create_chat_invite_link(
            chat_id=channel_id,
            expire_date=int((datetime.now() + timedelta(seconds=expire_in)).timestamp()),
            member_limit=0
        )
        return invite.invite_link
    except Exception as e:
        print(f"Error creating invite link: {e}")
        return None

# Helper: Check if the bot has access to the channel
async def is_bot_admin(channel_id: int) -> bool:
    try:
        chat = await app.get_chat(channel_id)
        return True  # If get_chat succeeds, the bot has access
    except Exception as e:
        print(f"Error checking bot access to channel {channel_id}: {e}")
        return False

# /setgfilter command (Supports multi-word filter names)
@app.on_message(filters.command("setgfilter") & filters.user(OWNER_ID))
async def setgfilter_handler(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.media:
        await message.reply("Please reply to a message with media (image/gif/sticker) to set a global filter.")
        return

    try:
        # Extract arguments inside square brackets
        matches = re.findall(r'\[(.*?)\]', message.text)
        if len(matches) < 2:
            await message.reply("Usage: /setgfilter [filter name] [channel id]")
            return

        filter_name = matches[0].strip().lower()  
        try:
            channel_id = int(matches[1].strip())
            if not str(channel_id).startswith("-100"):
                raise ValueError
        except ValueError:
            await message.reply("Invalid channel ID! Please provide a valid numeric channel ID inside brackets.")
            return

        # Check if bot has access to the channel
        if not await is_bot_admin(channel_id):
            await message.reply("I must be an admin in the specified channel. Please check my permissions and try again.")
            return

        # Extract media file ID
        media = message.reply_to_message.sticker or \
                message.reply_to_message.photo or \
                message.reply_to_message.animation or \
                message.reply_to_message.document
        if not media:
            await message.reply("Media type not supported. Use image, gif, or sticker.")
            return

        # Save filter details in the database
        filter_data = {
            "filter_name": filter_name,
            "channel_id": channel_id,
            "media_file_id": media.file_id,
            "timestamp": datetime.now()
        }
        gfilter_collection.update_one({"filter_name": filter_name}, {"$set": filter_data}, upsert=True)
        await message.reply(f"Global filter '{filter_name}' set successfully for channel {channel_id}.")
    except Exception as e:
        await message.reply(f"An error occurred: {e}")

# Triggered filter in any group chat message (not command)
@app.on_message(filters.text & ~filters.private)
async def trigger_filter(client: Client, message: Message):
    text = message.text.strip().lower()

    # Fetch filter from MongoDB (ASYNC)
    filter_data = await gfilter_collection.find_one({"filter_name": text})

    if not filter_data:
        return  

    channel_id = filter_data.get("channel_id")
    media_file_id = filter_data.get("media_file_id")

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
        # Determine media type from MongoDB and send accordingly
        if "sticker" in filter_data:
            await message.reply_sticker(sticker=media_file_id, reply_markup=keyboard)
        elif "animation" in filter_data:
            await message.reply_animation(animation=media_file_id, reply_markup=keyboard)
        elif "photo" in filter_data:
            await message.reply_photo(photo=media_file_id, reply_markup=keyboard)
        elif "video" in filter_data:
            await message.reply_video(video=media_file_id, reply_markup=keyboard)
        elif "document" in filter_data:
            await message.reply_document(document=media_file_id, reply_markup=keyboard)
        else:
            await message.reply("⚠️ Unsupported media type stored in the database.")
    except Exception as e:
        await message.reply(f"Error sending media: {e}")



# /removegfilter command to remove a global filter (only for OWNER)
@app.on_message(filters.command("removegfilter") & filters.user(OWNER_ID))
async def remove_gfilter(client: Client, message: Message):
    try:
        matches = re.findall(r'\[(.*?)\]', message.text)
        if not matches:
            await message.reply("Usage: /removegfilter [filter name]")
            return

        filter_name = matches[0].strip().lower()
        result = gfilter_collection.delete_one({"filter_name": filter_name})
        if result.deleted_count:
            await message.reply(f"Global filter '{filter_name}' removed.")
        else:
            await message.reply("No such global filter found.")
    except Exception as e:
        await message.reply(f"An error occurred: {e}")

