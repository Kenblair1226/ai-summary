import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes
from db_helper import DbHelper
import asyncio
import logging
import re
from urllib.parse import urlparse, parse_qs
import uuid
import shutil
from youtube_helper import check_new_videos, is_valid_youtube_url, extract_video_id, get_youtube_title, download_audio_from_youtube
from summarize_and_post import post_to_wordpress, post_to_ghost
from genai_helper import summarize_youtube_video, article_mp3

# Import Gemini related components from main.py
# from main import video_model, types

load_dotenv()
db = DbHelper(os.getenv('DB_PATH', 'database.db'))
app = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()

def is_valid_url(url):
    """Check if string is a valid URL"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def is_youtube_channel(url):
    """Check if URL is a YouTube channel"""
    youtube_patterns = [
        r'youtube\.com/@[\w-]+',
        r'youtube\.com/channel/[\w-]+',
        r'youtube\.com/c/[\w-]+'
    ]
    return any(re.search(pattern, url) for pattern in youtube_patterns)

def extract_website_name(url):
    """Extract website name from URL"""
    try:
        parsed = urlparse(url)
        # Remove www. if present and get the domain
        domain = parsed.netloc.replace('www.', '')
        # Take first part of domain (before first dot)
        return domain.split('.')[0].capitalize()
    except:
        return None

def is_podcast_feed(url):
    """Check if URL is likely a podcast feed by looking for common podcast indicators"""
    try:
        import feedparser
        feed = feedparser.parse(url)
        
        # Check for common podcast feed indicators
        if feed.entries:
            # Check feed level indicators
            feed_type = feed.feed.get('type', '').lower()
            if 'podcast' in feed_type:
                return True
                
            # Check for iTunes specific tags
            itunes_present = any(key.startswith('itunes') for key in feed.feed.keys())
            if itunes_present:
                return True
            
            # Check first entry for enclosures (audio files)
            first_entry = feed.entries[0]
            if hasattr(first_entry, 'enclosures') and first_entry.enclosures:
                for enclosure in first_entry.enclosures:
                    if 'audio' in enclosure.get('type', ''):
                        return True
        
        return False
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Welcome! Available commands:\n'
        '/subscribe - Get updates\n'
        '/unsubscribe - Stop updates\n'
        '/add <url> - Add YouTube channel or RSS feed\n'
        '/yt <url> - Summarize YouTube video'
    )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    db.add_subscriber(chat_id)
    await update.message.reply_text('You have subscribed to updates.')

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    db.remove_subscriber(chat_id)
    await update.message.reply_text('You have unsubscribed from updates.')

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /add command to add RSS feed or YouTube channel"""
    if not context.args:
        await update.message.reply_text('Please provide a URL after the /add command.')
        return

    url = context.args[0]
    
    if not is_valid_url(url):
        await update.message.reply_text('Please provide a valid URL.')
        return

    try:
        with db.get_connection() as conn:
            if is_youtube_channel(url):
                cursor = conn.cursor()
                cursor.execute('INSERT OR IGNORE INTO channels (url) VALUES (?)', (url,))
                if cursor.rowcount > 0:
                    await update.message.reply_text(f'Successfully added YouTube channel: {url}')
                else:
                    await update.message.reply_text('This YouTube channel is already in the database.')
            else:
                # Extract website name from URL for RSS feed
                site_name = extract_website_name(url)
                cursor = conn.cursor()
                
                if is_podcast_feed(url):
                    cursor.execute('INSERT OR IGNORE INTO podcast_feeds (url, name) VALUES (?, ?)', (url, site_name))
                    feed_type = "podcast feed"
                else:
                    cursor.execute('INSERT OR IGNORE INTO article_feeds (url, name) VALUES (?, ?)', (url, site_name))
                    feed_type = "article feed"
                
                if cursor.rowcount > 0:
                    await update.message.reply_text(f'Successfully added {feed_type} from {site_name}: {url}')
                else:
                    await update.message.reply_text(f'This {feed_type} is already in the database.')
            conn.commit()
    except Exception as e:
        logging.error(f"Error adding URL: {e}")
        await update.message.reply_text('Failed to add the URL. Please try again later.')

async def yt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /yt command to summarize YouTube video"""
    if not context.args:
        await update.message.reply_text('Please provide a YouTube URL after the /yt command.')
        return

    url = context.args[0]
    
    if not is_valid_youtube_url(url):
        await update.message.reply_text('Please provide a valid YouTube video URL.')
        return

    await update.message.reply_text('Processing video... This may take a few minutes.')

    try:
        video_id = extract_video_id(url)
        video_url = f"https://youtu.be/{video_id}"

        # Get title using the helper from youtube_helper.py
        post_title = get_youtube_title(video_url)
        if not post_title:
             await update.message.reply_text('Could not fetch video title. Please check the URL.')
             return

        # Create a temporary directory for the audio file
        temp_dir = f"temp_{uuid.uuid4()}"
        os.makedirs(temp_dir, exist_ok=True)

        try:
            # Download audio from YouTube
            logging.info(f"Downloading audio for video: {video_url}")
            title, mp3_path = download_audio_from_youtube(video_url, temp_dir)

            # Generate summary using article_mp3
            logging.info(f"Generating summary for audio: {mp3_path}")
            post_title, article = article_mp3(title, mp3_path, provider="gemini")

            # Check if summarization failed
            if article is None:
                await update.message.reply_text('Failed to generate summary for the video. Please try again later.')
                return

            # Post to WordPress/Ghost
            ghost_response_url = post_to_ghost(post_title, article, video_url, None, "YouTube")
            post_to_wordpress(post_title, article, video_url, None, "YouTube")

            if ghost_response_url:
                await update.message.reply_text(f"Summary posted: {ghost_response_url}")
            else:
                # Provide a more generic message if Ghost posting fails but WP might succeed
                await update.message.reply_text('Summary generation complete. Check WordPress/Ghost.')

        finally:
            # Clean up temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    except Exception as e:
        logging.error(f"Error processing YouTube video via bot: {e}")
        await update.message.reply_text('Failed to process the video. Please try again later.')

async def notify_subscribers(post_title, post_url, category=None):
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            subscribers = db.get_subscribers()
            
            category_text = f"[{category}] " if category else ""
            message_text = f"New post: {category_text}{post_title}\n{post_url}"
            
            for chat_id in subscribers:
                try:
                    await app.bot.send_message(
                        chat_id=chat_id,
                        text=message_text
                    )
                except Exception as e:
                    logging.error(f"Failed to send message to {chat_id}: {e}")
                    continue
            break
        except Exception as e:
            if attempt == max_retries - 1:
                logging.error(f"Failed to notify subscribers after {max_retries} attempts: {e}")
                raise
            logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)

async def process_updates(update_queue: asyncio.Queue):
    """Process updates from the queue, similar to Golang's GetUpdatesChan"""
    while True:
        try:
            update = await update_queue.get()
            if isinstance(update, Update):
                if update.message and update.message.text:
                    try:
                        context = ContextTypes.DEFAULT_TYPE(application=app)
                        if update.message.text == '/start':
                            await start(update, context)
                        elif update.message.text == '/subscribe':
                            await subscribe(update, context)
                        elif update.message.text == '/unsubscribe':
                            await unsubscribe(update, context)
                        elif update.message.text.startswith('/add'):
                            args = update.message.text.split()[1:]
                            context.args = args
                            await add(update, context)
                        elif update.message.text.startswith('/yt'):
                            args = update.message.text.split()[1:]
                            context.args = args
                            await yt(update, context)
                    except RuntimeError as e:
                        if 'Event loop is closed' in str(e):
                            logging.error("Event loop was closed, attempting to recover...")
                            await asyncio.sleep(1)
                            continue
                        raise
            update_queue.task_done()
        except Exception as e:
            logging.error(f"Error processing update: {e}")
            await asyncio.sleep(1)  # Add delay before retry

async def get_updates(update_queue: asyncio.Queue):
    """Get updates and put them in queue, similar to Golang's GetUpdatesChan"""
    offset = 0
    while True:
        try:
            updates = await app.bot.get_updates(offset=offset, timeout=30)
            for update in updates:
                await update_queue.put(update)
                offset = update.update_id + 1
        except Exception as e:
            logging.error(f"Error getting updates: {e}")
            await asyncio.sleep(5)

async def run_bot():
    """Run bot with update channel pattern"""
    update_queue = asyncio.Queue()
    
    # Create tasks
    tasks = [
        asyncio.create_task(get_updates(update_queue)),
        asyncio.create_task(process_updates(update_queue))
    ]
    
    logging.info("Bot started with update channel pattern")
    
    try:
        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logging.error(f"Error in main bot loop: {e}")
    finally:
        # Cancel all running tasks
        for task in tasks:
            task.cancel()
        
        # Wait for all tasks to be cancelled
        await asyncio.gather(*tasks, return_exceptions=True)

async def test_send_message():
    """Test function to send a proactive message"""
    test_title = "Test Post"
    # test_article = "This is a test article content"
    test_video_url = "https://example.com/video"
    
    logging.info("Sending test message to subscribers...")
    await notify_subscribers(test_title, test_video_url)
    logging.info("Test message sent successfully")

def start_bot():
    """Entry point for the bot"""
    while True:
        try:
            asyncio.run(run_bot())
        except Exception as e:
            logging.error(f"Bot crashed: {e}")
            logging.info("Restarting bot in 5 seconds...")
            time.sleep(5)

# Add this import at the top of the file
import time

if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        asyncio.run(test_send_message())
    else:
        start_bot()
