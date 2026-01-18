import os
import re
import logging
import yt_dlp


def get_youtube_title(video_url):
    """Fetches the title of a YouTube video using yt-dlp."""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return info.get('title')
    except Exception as e:
        logging.error(f"Error fetching title for {video_url}: {e}")
        return None


def download_audio_from_youtube(video_url, output_path):
    """Downloads audio from YouTube video as MP3 using yt-dlp."""
    try:
        # Ensure output directory exists
        os.makedirs(output_path, exist_ok=True)
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': False,
            'no_warnings': False,
            # Use android client to avoid SABR streaming issues
            'extractor_args': {'youtube': {'player_client': ['android_creator', 'ios', 'web']}},
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logging.info(f"Downloading audio from {video_url}")
            info = ydl.extract_info(video_url, download=True)
            title = info.get('title')
            
            # yt-dlp converts to mp3, construct the output filename
            # The file will be named based on the title
            safe_title = ydl.prepare_filename(info)
            base, _ = os.path.splitext(safe_title)
            new_file = base + '.mp3'
            
            # Log the size of the downloaded MP3 file
            if os.path.exists(new_file):
                file_size = os.path.getsize(new_file)
                size_mb = file_size / (1024 * 1024)
                logging.info(f"Downloaded MP3 file size: {size_mb:.2f} MB ({file_size:,} bytes)")
            
            return title, new_file
            
    except Exception as e:
        logging.error(f"Error downloading audio from {video_url}: {e}")
        raise


def check_new_videos(channel_url, db):
    """Check for new videos using yt-dlp, using DbHelper instead of raw connection"""
    # Get existing video IDs from database
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT video_id FROM videos')
        checked_video_ids = {row[0] for row in cursor.fetchall()}
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'playlistend': 5,  # Only check last 5 videos
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            
            if 'entries' not in info:
                logging.warning(f"No entries found for channel: {channel_url}")
                return []
            
            new_videos = []
            new_video_ids = []
            
            for entry in info['entries'][:5]:
                if entry is None:
                    continue
                video_id = entry.get('id')
                if video_id and video_id not in checked_video_ids:
                    new_videos.append({
                        'video_id': video_id,
                        'title': entry.get('title'),
                        'url': entry.get('url') or f"https://www.youtube.com/watch?v={video_id}"
                    })
                    new_video_ids.append(video_id)
            
            if new_video_ids:
                # Save new video IDs using DbHelper
                db.save_checked_video_ids(channel_url, new_video_ids)
            
            return new_videos
            
    except Exception as e:
        logging.error(f"Error checking new videos for {channel_url}: {e}")
        return []

def is_valid_youtube_url(url):
    """Check if URL is a valid YouTube video URL"""
    # Patterns for standard video URLs (watch?v=), shorts, and live streams
    youtube_patterns = [
        r'(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/|live/)|youtu\.be/)([a-zA-Z0-9_-]{11})'
    ]
    return any(re.match(pattern, url) for pattern in youtube_patterns)

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    # Patterns matching is_valid_youtube_url patterns, capturing the ID
    patterns = [
        r'(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/|live/)|youtu\.be/)([a-zA-Z0-9_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            # Return the captured group (the video ID)
            return match.group(1)
    return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    video_url = "https://youtu.be/hBMoPUAeLnY"
    output_path = "test"
    
    # Test getting title
    title = get_youtube_title(video_url)
    print(f"Video title: {title}")
    
    # Test downloading audio
    title, audio_file = download_audio_from_youtube(video_url, output_path)
    print(f"Audio file saved to: {audio_file}")
