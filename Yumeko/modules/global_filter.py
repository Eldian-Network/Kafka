import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pymongo import MongoClient
from datetime import datetime, timedelta
from Yumeko.database import gfilter_collection 

# Import config variables from config.py
from config import config

# Import the Pyrogram app from Yumeko
from Yumeko import app

# cfg imports
OWNER_ID = config.OWNER_ID

# Helper: Check if a user is the owner
def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

# Helper: Create a temporary invite link for a channel
async def create_temp_invite(channel_id: int, expire_in: int = 2400):  # 2400 sec = 40 min
    try:
        invite = await app.create_chat_invite_link(
            chat_id=channel_id,
            expire_date=int((datetime.now() + timedelta(seconds=expire_in)).timestamp()),
            member_limit=0  # unlimited joins
        )
        return invite.invite_link
    except Exception as e:
        print(f"Error creating invite link: {e}")
        return None

# /setgfilter command
@app.on_message(filters.command("setgfilter") & filters.user(OWNER_ID))
async def setgfilter_handler(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.media:
        await message.reply("Please reply to a media message (image/gif/sticker) to set a global filter.")
        return

    try:
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            await message.reply("Usage: /setgfilter <filter_name> <channel_id>")
            return

        filter_name = args[1].strip().lower()
        try:
            channel_id = int(args[2].strip())
        except ValueError:
            await message.reply("Invalid channel ID! Please provide a valid numeric channel ID.")
            return

        # Check if the bot is an admin of the channel
        try:
            chat_member = await app.get_chat_member(chat_id=channel_id, user_id=client.me.id)
            if chat_member.status not in ["administrator", "creator"]:
                await message.reply("I must be an admin in the specified channel.")
                return
        except Exception:
            await message.reply("Failed to verify channel admin status. Ensure the channel ID is correct and I am added.")
            return

        media = message.reply_to_message.sticker or \
                message.reply_to_message.photo or \
                message.reply_to_message.animation or \
                message.reply_to_message.document
        if not media:
            await message.reply("Unsupported media type. Use image, gif, or sticker.")
            return

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

@app.on_message(filters.text & ~filters.private)
async def trigger_filter(client: Client, message: Message):
    text = message.text.strip().lower()
    filter_data = gfilter_collection.find_one({"filter_name": text})
    if filter_data:
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
            await message.reply_sticker(sticker=media_file_id, reply_markup=keyboard)
        except Exception:
            await message.reply_document(document=media_file_id, reply_markup=keyboard)

@app.on_message(filters.command("gfilters") & filters.user(OWNER_ID))
async def list_gfilters(client: Client, message: Message):
    try:
        filters_list = list(gfilter_collection.find())
        if not filters_list:
            await message.reply("No global filters set.")
            return

        text_lines = []
        for f in filters_list:
            try:
                chat = await app.get_chat(chat_id=f["channel_id"])
                channel_name = chat.title
            except Exception:
                channel_name = "Unknown"
            text_lines.append(f"{f['filter_name']} - {channel_name} ({f['channel_id']})")

        await message.reply("\n".join(text_lines))
    except Exception as e:
        await message.reply(f"Error listing global filters: {e}")

@app.on_message(filters.command("removegfilter") & filters.user(OWNER_ID))
async def remove_gfilter(client: Client, message: Message):
    try:
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("Usage: /removegfilter <filter_name>")
            return
        
        filter_name = args[1].strip().lower()
        result = gfilter_collection.delete_one({"filter_name": filter_name})
        if result.deleted_count:
            await message.reply(f"Global filter '{filter_name}' removed.")
        else:
            await message.reply("No such global filter found.")
    except Exception as e:
        await message.reply(f"An error occurred: {e}")

