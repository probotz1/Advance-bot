import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from moviepy.editor import VideoFileClip, concatenate_videoclips
from flask import Flask, request
from config import Config

# Bot configuration
API_ID = Config.API_ID
API_HASH = Config.API_HASH
BOT_TOKEN = Config.BOT_TOKEN
WEBHOOK_URL = Config.WEBHOOK_URL

app = Flask(__name__)
bot_app = Client("video_trimmer_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Global variables to store video files for merging
video_files = []

# Start command handler
@bot_app.on_message(filters.command("start"))
def start(client, message):
    message.reply(
        "Welcome! Send me a video file and choose an action.",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Trim Video", callback_data="trim")],
                [InlineKeyboardButton("Merge Videos", callback_data="merge")],
                [InlineKeyboardButton("Remove Audio", callback_data="remove_audio")]
            ]
        )
    )

# Video file handler
@bot_app.on_message(filters.video)
def handle_video(client, message):
    video_file = message.video
    video_path = f"{message.video.file_id}.mp4"
    message.download(video_path)

    message.reply(
        "Video received. Choose an action.",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Trim Video", callback_data=f"trim|{video_path}")],
                [InlineKeyboardButton("Add to Merge", callback_data=f"add_video|{video_path}")],
                [InlineKeyboardButton("Remove Audio", callback_data=f"remove_audio|{video_path}")]
            ]
        )
    )

# Callback query handler for inline buttons
@bot_app.on_callback_query()
def callback_query(client, callback_query):
    data = callback_query.data
    action, video_path = data.split('|') if '|' in data else (data, None)

    if action == "trim":
        callback_query.message.reply("Send the start and end times in seconds (e.g., 30 60)")

    elif action == "merge":
        if len(video_files) < 2:
            callback_query.message.reply("You need to add at least two videos to merge.")
        else:
            clips = [VideoFileClip(video) for video in video_files]
            final_clip = concatenate_videoclips(clips)
            final_clip.write_videofile("merged_output.mp4", codec="libx264")
            client.send_video(callback_query.message.chat.id, video="merged_output.mp4")

    elif action == "add_video":
        video_files.append(video_path)
        callback_query.message.reply("Video added for merging. Use /merge to merge all added videos.")

    elif action == "remove_audio":
        video = VideoFileClip(video_path)
        video_without_audio = video.without_audio()
        video_without_audio.write_videofile("no_audio_output.mp4", codec="libx264")
        client.send_video(callback_query.message.chat.id, video="no_audio_output.mp4")

@bot_app.on_message(filters.text)
def trim_times(client, message):
    if ' ' in message.text:
        start_time, end_time = map(int, message.text.split())
        video_path = "input.mp4"  # The latest received video
        ffmpeg_extract_subclip(video_path, start_time, end_time, targetname="output.mp4")
        client.send_video(message.chat.id, video="output.mp4")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    bot_app.process_new_updates([data])
    return "ok"

if __name__ == '__main__':
    bot_app.start()
    bot_app.set_webhook(url=WEBHOOK_URL)
    app.run(host='0.0.0.0', port=Config.PORT)
