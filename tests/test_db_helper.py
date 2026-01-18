"""Unit tests for db_helper module."""
import pytest
import threading
import sqlite3


class TestDbHelperInitialization:
    """Tests for DbHelper initialization and database setup."""
    
    def test_initialize_db_creates_all_tables(self, temp_db):
        """Verify all required tables are created during initialization."""
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
        
        expected_tables = {
            'channels', 'videos', 'subscribers',
            'rss_feeds', 'processed_articles',
            'podcast_feeds', 'processed_episodes'
        }
        assert expected_tables.issubset(tables)
    
    def test_get_connection_returns_context_manager(self, temp_db):
        """Verify get_connection returns a working context manager."""
        with temp_db.get_connection() as conn:
            assert conn is not None
            assert isinstance(conn, sqlite3.Connection)


class TestDbHelperChannels:
    """Tests for channel-related database operations."""
    
    def test_get_channels_empty_database(self, temp_db):
        """Get channels returns empty list for empty database."""
        channels = temp_db.get_channels()
        assert channels == []
    
    def test_save_and_get_channels(self, temp_db):
        """Save video IDs and verify channel is retrievable."""
        channel_url = 'https://youtube.com/@testchannel'
        video_ids = ['video1', 'video2']
        
        temp_db.save_checked_video_ids(channel_url, video_ids)
        channels = temp_db.get_channels()
        
        assert channel_url in channels
    
    def test_save_duplicate_channel_ignored(self, temp_db):
        """Duplicate channel insertions are ignored."""
        channel_url = 'https://youtube.com/@testchannel'
        
        temp_db.save_checked_video_ids(channel_url, ['video1'])
        temp_db.save_checked_video_ids(channel_url, ['video2'])
        
        channels = temp_db.get_channels()
        assert channels.count(channel_url) == 1
    
    def test_save_multiple_video_ids(self, temp_db):
        """Multiple video IDs are saved correctly."""
        channel_url = 'https://youtube.com/@testchannel'
        video_ids = ['video1', 'video2', 'video3']
        
        temp_db.save_checked_video_ids(channel_url, video_ids)
        
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT video_id FROM videos')
            saved_ids = {row[0] for row in cursor.fetchall()}
        
        assert saved_ids == set(video_ids)


class TestDbHelperSubscribers:
    """Tests for subscriber-related database operations."""
    
    def test_get_subscribers_empty_database(self, temp_db):
        """Get subscribers returns empty list for empty database."""
        subscribers = temp_db.get_subscribers()
        assert subscribers == []
    
    def test_add_subscriber(self, temp_db):
        """Add subscriber and verify it's retrievable."""
        chat_id = 12345
        temp_db.add_subscriber(chat_id)
        
        subscribers = temp_db.get_subscribers()
        assert chat_id in subscribers
    
    def test_add_duplicate_subscriber_ignored(self, temp_db):
        """Duplicate subscriber additions are ignored."""
        chat_id = 12345
        temp_db.add_subscriber(chat_id)
        temp_db.add_subscriber(chat_id)
        
        subscribers = temp_db.get_subscribers()
        assert subscribers.count(chat_id) == 1
    
    def test_remove_subscriber(self, temp_db):
        """Remove subscriber and verify it's gone."""
        chat_id = 12345
        temp_db.add_subscriber(chat_id)
        temp_db.remove_subscriber(chat_id)
        
        subscribers = temp_db.get_subscribers()
        assert chat_id not in subscribers
    
    def test_remove_nonexistent_subscriber_no_error(self, temp_db):
        """Removing non-existent subscriber doesn't raise error."""
        temp_db.remove_subscriber(99999)  # Should not raise


class TestDbHelperArticles:
    """Tests for article processing database operations."""
    
    def test_is_article_processed_returns_false_for_new(self, temp_db):
        """New article returns False for is_article_processed."""
        assert temp_db.is_article_processed('new-article-id') is False
    
    def test_is_article_processed_returns_true_after_save(self, temp_db):
        """Saved article returns True for is_article_processed."""
        article_id = 'test-article-123'
        temp_db.save_processed_article(
            article_id=article_id,
            source_url='https://example.com/article',
            title='Test Article'
        )
        
        assert temp_db.is_article_processed(article_id) is True
    
    def test_save_processed_article_with_feed_id(self, temp_db):
        """Save article with feed_id parameter."""
        temp_db.save_processed_article(
            article_id='article-with-feed',
            source_url='https://example.com/article',
            title='Test Article',
            feed_id=1
        )
        
        assert temp_db.is_article_processed('article-with-feed') is True


class TestDbHelperEpisodes:
    """Tests for episode processing database operations."""
    
    def test_is_episode_processed_returns_false_for_new(self, temp_db):
        """New episode returns False for is_episode_processed."""
        assert temp_db.is_episode_processed('new-episode-id') is False
    
    def test_is_episode_processed_returns_true_after_save(self, temp_db):
        """Saved episode returns True for is_episode_processed."""
        episode_id = 'test-episode-123'
        temp_db.save_processed_episode(
            episode_id=episode_id,
            source_url='https://example.com/episode',
            title='Test Episode',
            feed_id=1
        )
        
        assert temp_db.is_episode_processed(episode_id) is True


class TestDbHelperThreadSafety:
    """Tests for thread-safety of database operations."""
    
    def test_same_thread_gets_same_connection(self, temp_db):
        """Same thread should get the same connection instance."""
        with temp_db.get_connection() as conn1:
            with temp_db.get_connection() as conn2:
                assert conn1 is conn2
    
    def test_different_threads_get_different_connections(self, temp_db):
        """Different threads should get different connections."""
        connections = []
        
        def get_conn():
            with temp_db.get_connection() as conn:
                connections.append(id(conn))
        
        thread1 = threading.Thread(target=get_conn)
        thread2 = threading.Thread(target=get_conn)
        
        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()
        
        # Each thread should have a unique connection
        assert len(connections) == 2
        assert connections[0] != connections[1]
    
    def test_concurrent_writes_dont_corrupt_data(self, temp_db):
        """Concurrent writes from multiple threads don't corrupt data."""
        num_threads = 5
        videos_per_thread = 10
        
        def add_videos(thread_id):
            channel_url = f'https://youtube.com/@channel{thread_id}'
            video_ids = [f'video_{thread_id}_{i}' for i in range(videos_per_thread)]
            temp_db.save_checked_video_ids(channel_url, video_ids)
        
        threads = [
            threading.Thread(target=add_videos, args=(i,))
            for i in range(num_threads)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Verify all channels were saved
        channels = temp_db.get_channels()
        assert len(channels) == num_threads


class TestDbHelperCleanup:
    """Tests for connection cleanup."""
    
    def test_close_all_closes_connection(self, temp_db):
        """close_all should close the connection."""
        # First, establish a connection
        with temp_db.get_connection() as conn:
            conn.execute('SELECT 1')
        
        # Close all connections
        temp_db.close_all()
        
        # The internal connection should be None
        assert not hasattr(temp_db._local, 'connection') or temp_db._local.connection is None
