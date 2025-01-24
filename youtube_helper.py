import json
import os
from shutil import Error
import subprocess
from typing import Tuple
from pytubefix import YouTube, Channel
from db_helper import initialize_db, get_checked_video_ids, save_checked_video_ids, connect_db

def download_audio_from_youtube(video_url, output_path):
    yt = YouTube(video_url, use_po_token=True, po_token_verifier=po_token_verifier)
    title = yt.title
    audio_stream = yt.streams.filter(only_audio=True).first()
    audio_file = audio_stream.download(output_path=output_path)
    
    base, ext = os.path.splitext(audio_file)
    new_file = base + '.mp3'
    
    subprocess.run(['ffmpeg', '-i', audio_file, new_file])
    os.remove(audio_file)
    
    return title, new_file

def check_new_videos(channel_url, db):
    """Check for new videos, using DbHelper instead of raw connection"""
    # Get existing video IDs from database
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT video_id FROM videos')
        checked_video_ids = {row[0] for row in cursor.fetchall()}
    
    channel = Channel(channel_url)
    new_video_ids = [video.video_id for video in channel.videos[:5] if video.video_id not in checked_video_ids]
    
    if new_video_ids:
        # Save new video IDs using DbHelper
        db.save_checked_video_ids(channel_url, new_video_ids)
    
    return new_video_ids

def cmd(command, check=True, shell=True, capture_output=True, text=True):
    """
    Runs a command in a shell, and throws an exception if the return code is non-zero.
    :param command: any shell command.
    :return:
    """
    try:
        return subprocess.run(command, check=check, shell=shell, capture_output=capture_output, text=text)
    except subprocess.CalledProcessError as error:
        raise Error(f"\"{command}\" return exit code: {error.returncode}")

def po_token_verifier() -> Tuple[str, str]:
    token_object = generate_youtube_token()
    return token_object["visitorData"], token_object["poToken"]


def generate_youtube_token() -> dict:
    result = cmd("node scripts/youtube-token-generator.js")
    data = json.loads(result.stdout)
    return data

if __name__ == "__main__":
    video_url = "https://youtu.be/hBMoPUAeLnY"
    output_path = "test"
    audio_file = download_audio_from_youtube(video_url, output_path)
    print(f"Audio file saved to: {audio_file}")
    
    # db_path = os.getenv('DB_PATH', 'database.db')
    # conn = connect_db(db_path)
    # initialize_db(conn)
    
    # channel_url = "https://youtube.com/@sharptechpodcast"
    # new_video_ids = check_new_videos(channel_url, conn)
    # if new_video_ids:
    #     print(f"New videos found: {new_video_ids}")
    # else:
    #     print("No new videos found.")
    
    # conn.close()
