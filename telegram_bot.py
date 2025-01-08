import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes
from db_helper import DbHelper
import asyncio
import logging
import re
from urllib.parse import urlparse
import uuid
import shutil
from youtube_helper import download_audio_from_youtube
from genai_helper import article_mp3
from summarize_and_post import post_to_wordpress

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

def is_valid_youtube_url(url):
    """Check if URL is a valid YouTube video URL"""
    youtube_patterns = [
        r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/live\/)([a-zA-Z0-9_-]+)',
    ]
    return any(re.search(pattern, url) for pattern in youtube_patterns)

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/live\/)([a-zA-Z0-9_-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1).split('?')[0]  # Remove query parameters
    return None

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
                cursor.execute('INSERT OR IGNORE INTO rss_feeds (url, name) VALUES (?, ?)', (url, site_name))
                if cursor.rowcount > 0:
                    await update.message.reply_text(f'Successfully added RSS feed from {site_name}: {url}')
                else:
                    await update.message.reply_text('This RSS feed is already in the database.')
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
        path = f"{uuid.uuid4()}"
        
        # Download audio
        title, new_file = download_audio_from_youtube(video_url, path)
        
        # Generate summary
        post_title, article = article_mp3(title, new_file)
        
        # Post to WordPress
        response = post_to_wordpress(post_title, article, video_url, None, "YouTube")
        
        if response:
            await update.message.reply_text(f"Summary posted: {response}")
        else:
            await update.message.reply_text('Failed to post summary to WordPress.')
        
        # Cleanup
        shutil.rmtree(path)
        
    except Exception as e:
        logging.error(f"Error processing YouTube video: {e}")
        await update.message.reply_text('Failed to process the video. Please try again later.')

async def notify_subscribers(post_title, video_url):
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            subscribers = db.get_subscribers()
            
            for chat_id in subscribers:
                try:
                    await app.bot.send_message(
                        chat_id=chat_id,
                        text=f"New post: {post_title}\n{video_url}"
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
                    context = ContextTypes.DEFAULT_TYPE(application=app)
                    if update.message.text == '/start':
                        await start(update, context)
                    elif update.message.text == '/subscribe':
                        await subscribe(update, context)
                    elif update.message.text == '/unsubscribe':
                        await unsubscribe(update, context)
                    elif update.message.text.startswith('/add'):
                        # Extract URL from message and create args
                        args = update.message.text.split()[1:]
                        context.args = args
                        await add(update, context)
                    elif update.message.text.startswith('/yt'):
                        args = update.message.text.split()[1:]
                        context.args = args
                        await yt(update, context)
            update_queue.task_done()
        except Exception as e:
            logging.error(f"Error processing update: {e}")

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
    
    # Start update fetcher and processor
    asyncio.create_task(get_updates(update_queue))
    asyncio.create_task(process_updates(update_queue))
    
    logging.info("Bot started with update channel pattern")
    
    # Keep the bot running
    while True:
        await asyncio.sleep(60)

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
    asyncio.run(run_bot())

if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        asyncio.run(test_send_message())
    else:
        start_bot()
