from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaVideo
import os
import glob
import random
import yt_dlp
import re
from Yumeko import app
from Yumeko.helper.on_start import clear_downloads_folder
from config import config 
from Yumeko.decorator.save import save
from Yumeko.decorator.errors import error 
from youtubesearchpython.__future__ import VideosSearch
from pyrogram.enums import ParseMode

# Regex to detect URLs in messages
URL_REGEX = r'(https?://[^\s]+)'

def cookie_txt_file():
    folder_path = f"{os.getcwd()}/cookies"
    filename = f"{os.getcwd()}/cookies/logs.csv"
    txt_files = glob.glob(os.path.join(folder_path, '*.txt'))
    if not txt_files:
        raise FileNotFoundError("No .txt files found in the specified folder.")
    cookie_txt_file = random.choice(txt_files)
    with open(filename, 'a') as file:
        file.write(f'Chosen File: {cookie_txt_file}\n')
    return f"cookies/{str(cookie_txt_file).split('/')[-1]}"

class Downloader:
    def __init__(self, download_path='downloads'):
        self.download_path = download_path
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

    def download(self, url):
        ydl_opts = {
            'format': 'best',
            'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
            'writethumbnail': True,
            "cookiefile": cookie_txt_file(),
            'postprocessors': [
                {'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'},
                {'key': 'EmbedThumbnail', 'already_have_thumbnail': True},
            ],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)

            # Find the thumbnail
            thumb_path = None
            for file in os.listdir(self.download_path):
                if file.startswith(info['title']) and file.endswith('.jpg'):
                    thumb_path = os.path.join(self.download_path, file)
                    break

            video_info = {
                'video_path': video_path,
                'thumb_path': thumb_path,
                'duration': info.get('duration'),
                'quality': info.get('format_note'),
                'height': info.get('height'),
                'width': info.get('width'),
                'title': info.get('title'),
            }
            return video_info

downloader = Downloader()

@app.on_message(filters.command("ytdl", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def download_video(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("Please provide a link.")
        return

    url = message.command[1]
    a = await message.reply_text("**Downloading, please wait...**")

    try:
        video_info = downloader.download(url)
        await a.delete()
        await message.reply_video(
            video=video_info['video_path'],
            thumb=video_info['thumb_path'],
            caption=f"**{video_info['title']}**",
            width=video_info['width'],
            height=video_info['height'],
            supports_streaming=True,
            parse_mode=ParseMode.MARKDOWN
        )
        clear_downloads_folder()
    except Exception as e:
        await a.edit(f"An error occurred: {str(e)}")

# Automatic URL detection and downloading
@app.on_message(filters.text & ~filters.command("ytdl", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def auto_download(client: Client, message: Message):
    urls = re.findall(URL_REGEX, message.text)  # Extract URLs from message

    if not urls:
        return  # No URLs found, ignore message

    for url in urls:
        try:
            # Check if the URL is downloadable
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info:
                    info = info['entries'][0]  # Handle playlists

                if not info.get('url'):
                    continue  # Skip if not downloadable

            a = await message.reply_text("**Downloading video, please wait...**")

            # Download the video
            video_info = downloader.download(url)

            await a.delete()
            await message.reply_video(
                video=video_info['video_path'],
                thumb=video_info['thumb_path'],
                caption=f"**{video_info['title']}**",
                width=video_info['width'],
                height=video_info['height'],
                supports_streaming=True,
                parse_mode=ParseMode.MARKDOWN
            )
            clear_downloads_folder()
        except Exception as e:
            continue  # Ignore non-downloadable URLs

# Song Downloader Class
class SongDownloader:
    def __init__(self, download_path='downloads'):
        self.download_path = download_path
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

    async def search_song(self, query):
        videos_search = VideosSearch(query, limit=1)
        results = await videos_search.next()
        if results['result']:
            video = results['result'][0]
            return {
                'title': video['title'],
                'url': video['link'],
                'duration': video['duration'],
                'channel': video['channel']['name'],
            }
        return None

    def download_song(self, url):
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
            "cookiefile": cookie_txt_file(),
            'postprocessors': [
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
                {'key': 'EmbedThumbnail'},
            ],
            'writethumbnail': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            audio_path = ydl.prepare_filename(info).replace('.webm', '.mp3')

            # Find the thumbnail
            thumb_path = None
            for file in os.listdir(self.download_path):
                if file.startswith(info['title']) and file.endswith('.jpg'):
                    thumb_path = os.path.join(self.download_path, file)
                    break

            song_info = {
                'audio_path': audio_path,
                'thumb_path': thumb_path,
                'duration': info.get('duration'),
                'title': info.get('title'),
                'artist': info.get('artist', info.get('uploader')),
            }
            return song_info

song_downloader = SongDownloader()

@app.on_message(filters.command("song", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def download_song(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("Please provide a song name.")
        return

    query = " ".join(message.command[1:])
    a = await message.reply_text("**Searching for the song...**")

    try:
        search_result = await song_downloader.search_song(query)
        if not search_result:
            await a.edit("Could not find the song.")
            return

        await a.edit("**Downloading the song...**")

        song_info = song_downloader.download_song(search_result['url'])
        await a.delete()
        await message.reply_audio(
            audio=song_info['audio_path'],
            thumb=song_info['thumb_path'],
            caption=(
                f"**{song_info['title']}**\n"
                f"**Artist:** {song_info['artist']}\n"
                f"**Duration:** {search_result['duration']}\n"
                f"**Channel:** {search_result['channel']}"
            ),
            title=song_info['title'],
            performer=song_info['artist'],
        )
        clear_downloads_folder()
    except Exception as e:
        await a.edit(f"An error occurred: {str(e)}")


__module__ = "𝖣𝗈𝗐𝗇𝗅𝗈𝖺𝖽𝖾𝗋"


__help__ = """**𝖵𝗂𝖽𝖾𝗈 𝖣𝗈𝗐𝗇𝗅𝗈𝖺𝖽𝖾𝗋:**

- **𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**
 ✧ `/𝗒𝗍𝖽𝗅 <𝗅𝗂𝗇𝗄>` : 𝖣𝗈𝗐𝗇𝗅𝗈𝖺𝖽𝗌 𝗍𝗁𝖾 𝖸𝗈𝗎𝖳𝗎𝖻𝖾/𝖨𝗇𝗌𝗍𝖺𝗀𝗋𝖺𝗆/𝖮𝗍𝗁𝖾𝗋𝗌 𝗏𝗂𝖽𝖾𝗈 𝖿𝗋𝗈𝗆 𝗍𝗁𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾𝖽 𝗅𝗂𝗇𝗄 𝖺𝗇𝖽 𝗎𝗉𝗅𝗈𝖺𝖽𝗌 𝗂𝗍 𝗐𝗂𝗍𝗁 𝗆𝖾𝗍𝖺𝖽𝖺𝗍𝖺.
 
- **𝖴𝗌𝖺𝗀𝖾:**
   𝟣. 𝖴𝗌𝖾 𝗍𝗁𝖾 `/𝗒𝗍𝖽𝗅` 𝖼𝗈𝗆𝗆𝖺𝗇𝖽 𝖿𝗈𝗅𝗅𝗈𝗐𝖾𝖽 𝖻𝗒 𝖺 𝗏𝖺𝗅𝗂𝖽 𝖵𝗂𝖽𝖾𝗈 𝗅𝗂𝗇𝗄.
 """
