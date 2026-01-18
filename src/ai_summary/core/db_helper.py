import sqlite3
from contextlib import contextmanager
import threading
from typing import Optional, Dict

class DbHelper:
    def __init__(self, db_path):
        self.db_path = db_path
        self._local = threading.local()
        
    @contextmanager
    def get_connection(self):
        """Get a thread-local database connection"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(self.db_path)
        try:
            yield self._local.connection
        finally:
            pass  # Keep connection open for thread reuse
    
    def close_all(self):
        """Close connection if it exists"""
        if hasattr(self._local, 'connection') and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None

    # Modified methods to use thread-safe connections
    def get_channels(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT url FROM channels')
            return [row[0] for row in cursor.fetchall()]

    def save_checked_video_ids(self, channel_url, video_ids):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO channels (url) VALUES (?)', (channel_url,))
            cursor.execute('SELECT id FROM channels WHERE url = ?', (channel_url,))
            channel_id = cursor.fetchone()[0]
            cursor.executemany('INSERT OR IGNORE INTO videos (video_id, channel_id) VALUES (?, ?)', 
                             [(video_id, channel_id) for video_id in video_ids])
            conn.commit()

    def initialize_db(self):
        with self.get_connection() as conn:
            initialize_db(conn)
    
    def add_subscriber(self, chat_id):
        with self.get_connection() as conn:
            add_subscriber(conn, chat_id)
    
    def remove_subscriber(self, chat_id):
        with self.get_connection() as conn:
            remove_subscriber(conn, chat_id)
    
    def get_subscribers(self):
        with self.get_connection() as conn:
            return get_subscribers(conn)
    
    def save_processed_article(self, article_id, source_url, title, feed_id=None):
        with self.get_connection() as conn:
            save_processed_article(conn, article_id, source_url, title, feed_id)
    
    def is_article_processed(self, article_id):
        with self.get_connection() as conn:
            return is_article_processed(conn, article_id)

    def save_processed_episode(self, episode_id, source_url, title, feed_id):
        with self.get_connection() as conn:
            save_processed_episode(conn, episode_id, source_url, title, feed_id)
    
    def is_episode_processed(self, episode_id):
        with self.get_connection() as conn:
            return is_episode_processed(conn, episode_id)

    def __del__(self):
        """Cleanup connections on object destruction"""
        self.close_all()

def connect_db(db_path):
    return sqlite3.connect(db_path)

def initialize_db(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT UNIQUE NOT NULL,
            channel_id INTEGER,
            FOREIGN KEY (channel_id) REFERENCES channels (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            chat_id INTEGER PRIMARY KEY
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rss_feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            name TEXT,
            last_check TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id TEXT UNIQUE NOT NULL,
            processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_url TEXT,
            title TEXT,
            feed_id INTEGER,
            FOREIGN KEY (feed_id) REFERENCES rss_feeds (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS podcast_feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            name TEXT NOT NULL,
            last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            episode_id TEXT UNIQUE NOT NULL,
            processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_url TEXT,
            title TEXT,
            feed_id INTEGER,
            FOREIGN KEY (feed_id) REFERENCES podcast_feeds (id)
        )
    ''')
    
    conn.commit()


def get_checked_video_ids(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT video_id FROM videos')
    checked_video_ids = {row[0] for row in cursor.fetchall()}
    return checked_video_ids

def save_checked_video_ids(conn, channel_url, video_ids):
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO channels (url) VALUES (?)', (channel_url,))
    cursor.execute('SELECT id FROM channels WHERE url = ?', (channel_url,))
    channel_id = cursor.fetchone()[0]
    cursor.executemany('INSERT OR IGNORE INTO videos (video_id, channel_id) VALUES (?, ?)', [(video_id, channel_id) for video_id in video_ids])
    conn.commit()

def get_channels(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT url FROM channels')
    channels = [row[0] for row in cursor.fetchall()]
    return channels

def add_subscriber(conn, chat_id):
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO subscribers (chat_id) VALUES (?)', (chat_id,))
    conn.commit()

def remove_subscriber(conn, chat_id):
    cursor = conn.cursor()
    cursor.execute('DELETE FROM subscribers WHERE chat_id = ?', (chat_id,))
    conn.commit()

def get_subscribers(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id FROM subscribers')
    subscribers = [row[0] for row in cursor.fetchall()]
    return subscribers

def get_processed_articles(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT article_id FROM processed_articles")
    return {row[0] for row in cursor.fetchall()}

def save_processed_article(conn, article_id, source_url, title, feed_id=None):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO processed_articles (article_id, source_url, title, feed_id) VALUES (?, ?, ?, ?)",
        (article_id, source_url, title, feed_id)
    )
    conn.commit()

def is_article_processed(conn, article_id):
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM processed_articles WHERE article_id = ?", (article_id,))
    return cursor.fetchone() is not None

def save_processed_episode(conn, episode_id, source_url, title, feed_id):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO processed_episodes (episode_id, source_url, title, feed_id) VALUES (?, ?, ?, ?)",
        (episode_id, source_url, title, feed_id)
    )
    conn.commit()

def is_episode_processed(conn, episode_id):
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM processed_episodes WHERE episode_id = ?", (episode_id,))
    return cursor.fetchone() is not None

def add_rss_feed(conn, url, name=None):
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO rss_feeds (url, name) VALUES (?, ?)', (url, name))
    conn.commit()

def remove_rss_feed(conn, url):
    cursor = conn.cursor()
    cursor.execute('DELETE FROM rss_feeds WHERE url = ?', (url,))
    conn.commit()

def get_rss_feeds(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT id, url, name, last_check FROM rss_feeds')
    return cursor.fetchall()

def update_feed_last_check(conn, feed_id):
    cursor = conn.cursor()
    cursor.execute('UPDATE rss_feeds SET last_check = CURRENT_TIMESTAMP WHERE id = ?', (feed_id,))
    conn.commit()

if __name__ == '__main__':
    import os
    
    # Default database path in the same directory as the script
    default_db_path = os.path.join(os.path.dirname(__file__), 'database.db')
    
    # Connect and initialize the database
    db = DbHelper(default_db_path)
    db.initialize_db()
    print(f"Database initialized at: {default_db_path}")
