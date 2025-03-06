from pyrogram import Client, filters
from pyrogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
from Yumeko import app
from Yumeko.database.nightmode_db import (
    enable_nightmode,
    disable_nightmode,
    get_nightmode_chat_info,
    update_nightmode_timings,
    get_all_nightmode_enabled_chats,
)

# Define Chat Permissions
CLOSE_CHAT = ChatPermissions(can_send_messages=False)
OPEN_CHAT = ChatPermissions(
    can_send_messages=True,
    can_send_media_messages=True,
    can_send_polls=True,
    can_add_web_page_previews=True,
    can_invite_users=True,
    can_send_stickers=True,
    can_send_videos=True,
    can_send_voices=True,
    can_send_photos=True,
    can_send_docs=True,
    can_send_gifs=True
)

# Night Mode Buttons
buttons = InlineKeyboardMarkup([
    [InlineKeyboardButton("Enable", callback_data="add_night"),
     InlineKeyboardButton("Disable", callback_data="rm_night")],
    [InlineKeyboardButton("Set Timing", callback_data="set_night_time")]
])

# 📌 Command to Manage Night Mode
@app.on_message(filters.command("nightmode") & filters.group)
async def nightmode_cmd(_, message):
    await message.reply_photo(
        photo="https://telegra.ph//file/06649d4d0bbf4285238ee.jpg",
        caption="**Click the buttons below to enable, disable, or set night mode timings for this chat.**",
        reply_markup=buttons
    )

# 📌 Handling Button Clicks
@app.on_callback_query(filters.regex("^(add_night|rm_night|set_night_time)$"))
async def nightmode_callback(_, query: CallbackQuery):
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    chat_info = await get_nightmode_chat_info(chat_id)

    if not chat_info:
        return await query.answer("Night mode is not set up for this group.", show_alert=True)

    if chat_info["owner_id"] != user_id:
        return await query.answer("Only the chat owner can modify night mode settings!", show_alert=True)

    if query.data == "add_night":
        if chat_info.get("nightmode_enabled", False):
            await query.message.edit_caption("**Night mode is already enabled.**")
        else:
            await enable_nightmode(chat_id, query.message.chat.title, user_id, "23:00", "09:00")
            await query.message.edit_caption("**Night mode is enabled. Default timing: 11:00 PM - 9:00 AM [IST].**")
            await schedule_nightmode()  # Reschedule after enabling

    elif query.data == "rm_night":
        if chat_info.get("nightmode_enabled", False):
            await disable_nightmode(chat_id)
            await query.message.edit_caption("**Night mode has been disabled for this group.**")
            await schedule_nightmode()  # Reschedule after disabling
        else:
            await query.message.edit_caption("**Night mode is already off.**")

    elif query.data == "set_night_time":
        await query.message.edit_caption("**Send the new night mode start and end time in 24-hour format (HH:MM-HH:MM).**")

# 📌 Setting Night Mode Timing
@app.on_message(filters.regex(r"^\d{2}:\d{2}-\d{2}:\d{2}$") & filters.group)
async def set_nightmode_timing(_, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    chat_info = await get_nightmode_chat_info(chat_id)

    if not chat_info:
        return await message.reply("Night mode is not set up for this group.")

    if chat_info["owner_id"] != user_id:
        return await message.reply("Only the chat owner can set night mode timings!")

    start_time, end_time = message.text.split("-")
    await update_nightmode_timings(chat_id, start_time, end_time)
    await message.reply(f"**Night mode timings updated:**\nStart: {start_time}\nEnd: {end_time}")
    await schedule_nightmode()  # Reschedule after updating times

# 🔄 Functions to Handle Night Mode Restrictions
async def start_nightmode(chat_id):
    try:
        await app.send_photo(
            chat_id,
            photo="https://telegra.ph//file/06649d4d0bbf4285238ee.jpg",
            caption="**Group is closing for night mode. Good night!**"
        )
        await app.set_chat_permissions(chat_id, CLOSE_CHAT)
    except Exception as e:
        print(f"Failed to close group {chat_id} - {e}")

async def close_nightmode(chat_id):
    try:
        await app.send_photo(
            chat_id,
            photo="https://telegra.ph//file/14ec9c3ff42b59867040a.jpg",
            caption="**Group is opening. Have a great day!**"
        )
        await app.set_chat_permissions(chat_id, OPEN_CHAT)
    except Exception as e:
        print(f"Failed to open group {chat_id} - {e}")

# 🔄 Scheduler Setup
scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

async def schedule_nightmode():
    scheduler.remove_all_jobs()  # Remove old jobs
    chats = await get_all_nightmode_enabled_chats()

    for chat in chats:
        start_hour, start_minute = map(int, chat["start_time"].split(":"))
        end_hour, end_minute = map(int, chat["end_time"].split(":"))
        
        scheduler.add_job(start_nightmode, trigger="cron", hour=start_hour, minute=start_minute, args=[chat["chat_id"]])
        scheduler.add_job(close_nightmode, trigger="cron", hour=end_hour, minute=end_minute, args=[chat["chat_id"]])

scheduler.start()  # Start the scheduler

# Ensure scheduler runs on bot startup
async def main():
    await schedule_nightmode()

asyncio.create_task(main())  # Schedule night mode updates

