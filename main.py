import os
import time
import uuid
import shutil
import logging
import asyncio
import schedule
import feedparser
from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv
import urllib.request
from db_helper import DbHelper
from youtube_helper import download_audio_from_youtube, check_new_videos
from genai_helper import article_mp3, summarize_article
from summarize_and_post import post_to_wordpress
from telegram_bot import notify_subscribers, start_bot
from email.utils import parsedate_to_datetime

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

db = DbHelper(os.getenv('DB_PATH', 'database.db'))
db.initialize_db()

async def process_new_videos():
    try:
        channels = db.get_channels()
        
        for channel_url in channels:
            logging.info(f"Checking new videos for channel: {channel_url}")
            new_video_ids = check_new_videos(channel_url, db)  # Pass db instead of conn
            if new_video_ids:
                logging.info(f"Found {len(new_video_ids)} new videos.")
                for video_id in new_video_ids:
                    video_url = f"https://youtu.be/{video_id}"
                    path = f"{uuid.uuid4()}"
                    for attempt in range(3):
                        try:
                            logging.info(f"Attempting to download audio from {video_url}. Attempt {attempt + 1}")
                            title, new_file = download_audio_from_youtube(video_url, path)
                            break
                        except Exception as e:
                            logging.error(f"Attempt {attempt + 1} failed: {e}")
                            time.sleep(5)
                    else:
                        logging.error(f"Failed to download audio from {video_url} after 3 attempts.")
                        continue
                    
                    logging.info(f"Generating article for video: {video_url}")
                    post_title, article = article_mp3(title, new_file)
                    response = post_to_wordpress(post_title, article, video_url, None, channel_url)
                    if response:
                        logging.info(f"Summary posted to WordPress successfully for video {video_url}.")
                        await notify_subscribers(post_title, response)  # Pass WordPress post URL
                    else:
                        logging.error(f"Failed to post summary to WordPress for video {video_url}.")
                    
                    shutil.rmtree(path)
            else:
                logging.info(f"No new videos found for channel: {channel_url}")
        
        logging.info("Finished processing new videos.")
    except Exception as e:
        logging.error(f"Error processing videos: {e}")

async def process_rss_feeds():
    """Async version of RSS feed processing"""
    logging.info("Starting process to check RSS feeds.")
    
    with db.get_connection() as conn:
        rss_feeds = conn.execute('SELECT id, url, name, last_check FROM rss_feeds').fetchall()
    
    for feed_id, feed_url, name, last_check in rss_feeds:
        if not feed_url.strip():
            continue
            
        logging.info(f"Processing RSS feed: {feed_url}")
        feed = feedparser.parse(feed_url)
        
        for entry in feed.entries:
            article_id = entry.id if hasattr(entry, 'id') else entry.link
            
            if db.is_article_processed(article_id):
                continue
                
            try:
                # Extract article content
                response = requests.get(entry.link)
                soup = BeautifulSoup(response.text, 'html.parser')
                for script in soup(["script", "style"]):
                    script.decompose()
                article_text = soup.get_text()
                
                # Generate summary using Gemini
                post_title, article = summarize_article(entry.title, article_text)
                
                # Post to WordPress
                response = post_to_wordpress(post_title, article, None, entry.link, name)
                
                if response:
                    with db.get_connection() as conn:
                        conn.execute('UPDATE rss_feeds SET last_check = CURRENT_TIMESTAMP WHERE id = ?', (feed_id,))
                        conn.commit()
                    logging.info(f"Summary posted to WordPress successfully for article: {entry.link}")
                    db.save_processed_article(article_id, entry.link, entry.title)
                    await notify_subscribers(post_title, response)  # Pass WordPress post URL
                else:
                    logging.error("Failed to post summary to WordPress")
                    
            except Exception as e:
                logging.error(f"Error processing article {entry.link}: {str(e)}")
                continue
    
    logging.info("Finished processing RSS feeds.")

def extract_mp3_url(entry):
    """Extract MP3 URL from a podcast feed entry"""
    # Try enclosures first (standard format)
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enclosure in entry.enclosures:
            if isinstance(enclosure, dict):
                if enclosure.get('type') == 'audio/mpeg' or enclosure.get('href', '').endswith('.mp3'):
                    return enclosure.get('href')
    
    # Try media:content (alternative format)
    if hasattr(entry, 'media_content'):
        for media in entry.media_content:
            if isinstance(media, dict):
                url = media.get('url', '')
                if url.endswith('.mp3') or media.get('type') == 'audio/mpeg':
                    return url
    
    # Try links (some feeds use this format)
    if hasattr(entry, 'links'):
        for link in entry.links:
            if isinstance(link, dict):
                if link.get('type') == 'audio/mpeg' or link.get('href', '').endswith('.mp3'):
                    return link.get('href')
    
    # Try direct audio_url (some feeds use this)
    if hasattr(entry, 'audio_url'):
        return entry.audio_url
    
    return None

async def process_podcast_feeds():
    """Process podcast RSS feeds to download and summarize episodes"""
    logging.info("Starting process to check podcast RSS feeds")
    
    with db.get_connection() as conn:
        podcast_feeds = conn.execute('SELECT id, url, name, last_check FROM podcast_feeds').fetchall()
    
    for feed_id, feed_url, name, last_check in podcast_feeds:
        if not feed_url.strip():
            continue
            
        logging.info(f"Processing podcast feed: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:
                logging.error(f"Error parsing feed {feed_url}: {feed.bozo_exception}")
                continue
            
            for entry in feed.entries:
                # Check publish date using pubDate attribute
                if hasattr(entry, 'published'):
                    try:
                        pub_date = parsedate_to_datetime(entry.published)
                        if pub_date.year < 2025:
                            logging.debug(f"Skipping episode {entry.title} from {pub_date.year}")
                            continue
                    except Exception as e:
                        logging.error(f"Error parsing pubDate for {entry.title}: {e}")
                        continue

                episode_id = entry.id if hasattr(entry, 'id') else entry.link
                
                if db.is_episode_processed(episode_id):
                    continue
                
                # Rest of the episode processing code remains the same
                try:
                    mp3_url = extract_mp3_url(entry)
                    
                    if not mp3_url:
                        logging.warning(f"No MP3 URL found for episode: {entry.title}")
                        continue
                    
                    logging.info(f"Found MP3 URL: {mp3_url} for episode: {entry.title}")
                    
                    # Download MP3 file
                    path = f"{uuid.uuid4()}"
                    os.makedirs(path, exist_ok=True)
                    mp3_path = f"{path}/{entry.title}.mp3"
                    
                    # Download with retry mechanism
                    for attempt in range(3):
                        try:
                            urllib.request.urlretrieve(mp3_url, mp3_path)
                            break
                        except Exception as e:
                            logging.error(f"Download attempt {attempt + 1} failed: {e}")
                            if attempt == 2:  # Last attempt failed
                                raise
                            time.sleep(5)
                    
                    # Rest of the processing
                    post_title, article = article_mp3(entry.title, mp3_path)
                
                    # Post to WordPress
                    response = post_to_wordpress(post_title, article, None, entry.link, name)
                
                    if response:
                        with db.get_connection() as conn:
                            conn.execute('UPDATE podcast_feeds SET last_check = CURRENT_TIMESTAMP WHERE id = ?', (feed_id,))
                            conn.commit()
                        logging.info(f"Summary posted to WordPress successfully for podcast: {entry.title}")
                        db.save_processed_episode(episode_id, entry.link, entry.title, feed_id)
                        await notify_subscribers(post_title, response)  # Pass WordPress post URL
                    else:
                        logging.error("Failed to post summary to WordPress")
                
                    # Cleanup
                    shutil.rmtree(path)
                    
                except Exception as e:
                    logging.error(f"Error processing episode {entry.title}: {str(e)}")
                    if os.path.exists(path):
                        shutil.rmtree(path)
                    continue
                
        except Exception as e:
            logging.error(f"Error processing feed {feed_url}: {str(e)}")
            continue
    
    logging.info("Finished processing podcast feeds")

def content_processing_loop():
    # run on startup
    try:
        asyncio.run(run_content_processor())
    except Exception as e:
        logging.error(f"Error processing content on startup:{e}")

    # Schedule jobs to run at 8 AM and 8 PM
    schedule.every().day.at("00:00").do(lambda: asyncio.run(run_content_processor()))
    schedule.every().day.at("12:00").do(lambda: asyncio.run(run_content_processor()))
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check schedule every minute

async def run_content_processor():
    """Runs video, RSS feed, and podcast processing in the same event loop"""
    await process_new_videos()
    await process_rss_feeds()
    await process_podcast_feeds()

if __name__ == "__main__":
    import threading
    content_thread = threading.Thread(target=content_processing_loop)
    content_thread.start()
    # Run the bot in the main thread
    start_bot()
