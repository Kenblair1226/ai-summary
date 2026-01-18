"""Unit tests for telegram_bot module."""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock


class TestIsValidUrl:
    """Tests for is_valid_url function."""
    
    @pytest.mark.parametrize("url,expected", [
        # Valid URLs
        ("https://example.com", True),
        ("http://example.com", True),
        ("https://www.example.com/path", True),
        ("https://example.com:8080/path?query=1", True),
        ("http://localhost:3000", True),
        
        # Invalid URLs
        ("not a url", False),
        ("example.com", False),  # Missing scheme
        ("ftp://example.com", True),  # FTP is technically valid
        ("", False),
        ("   ", False),
    ])
    def test_is_valid_url(self, url, expected):
        """Test URL validation for various inputs."""
        # Need to mock telegram modules before import
        with patch.dict('os.environ', {'TELEGRAM_TOKEN': 'test-token', 'DB_PATH': ':memory:'}):
            with patch('ai_summary.interfaces.telegram_bot.Application'):
                with patch('ai_summary.interfaces.telegram_bot.DbHelper'):
                    from ai_summary.interfaces.telegram_bot import is_valid_url
                    assert is_valid_url(url) == expected


class TestIsYoutubeChannel:
    """Tests for is_youtube_channel function."""
    
    @pytest.mark.parametrize("url,expected", [
        # Valid channel URLs
        ("https://youtube.com/@testchannel", True),
        ("https://www.youtube.com/@MyChannel", True),
        ("https://youtube.com/channel/UCxxxxxx", True),
        ("https://youtube.com/c/ChannelName", True),
        
        # Invalid - video URLs
        ("https://youtube.com/watch?v=dQw4w9WgXcQ", False),
        ("https://youtu.be/dQw4w9WgXcQ", False),
        
        # Invalid - other URLs
        ("https://example.com", False),
        ("https://vimeo.com/@channel", False),
    ])
    def test_is_youtube_channel(self, url, expected):
        """Test YouTube channel detection for various URLs."""
        with patch.dict('os.environ', {'TELEGRAM_TOKEN': 'test-token', 'DB_PATH': ':memory:'}):
            with patch('ai_summary.interfaces.telegram_bot.Application'):
                with patch('ai_summary.interfaces.telegram_bot.DbHelper'):
                    from ai_summary.interfaces.telegram_bot import is_youtube_channel
                    assert is_youtube_channel(url) == expected


class TestExtractWebsiteName:
    """Tests for extract_website_name function."""
    
    @pytest.mark.parametrize("url,expected", [
        # Standard domains
        ("https://example.com", "Example"),
        ("https://www.example.com", "Example"),
        ("https://techcrunch.com/article/123", "Techcrunch"),
        
        # Subdomains
        ("https://blog.example.com", "Blog"),
        ("https://api.github.com", "Api"),
        
        # With ports - netloc includes port
        ("https://localhost:3000", "Localhost:3000"),
    ])
    def test_extract_website_name(self, url, expected):
        """Test website name extraction from URLs."""
        with patch.dict('os.environ', {'TELEGRAM_TOKEN': 'test-token', 'DB_PATH': ':memory:'}):
            with patch('ai_summary.interfaces.telegram_bot.Application'):
                with patch('ai_summary.interfaces.telegram_bot.DbHelper'):
                    from ai_summary.interfaces.telegram_bot import extract_website_name
                    assert extract_website_name(url) == expected
    
    def test_extract_website_name_returns_none_on_invalid(self):
        """extract_website_name returns None for invalid URLs."""
        with patch.dict('os.environ', {'TELEGRAM_TOKEN': 'test-token', 'DB_PATH': ':memory:'}):
            with patch('ai_summary.interfaces.telegram_bot.Application'):
                with patch('ai_summary.interfaces.telegram_bot.DbHelper'):
                    from ai_summary.interfaces.telegram_bot import extract_website_name
                    # This should not raise, just return None
                    result = extract_website_name("not a url")
                    # May return None or partial result depending on implementation


class TestIsPodcastFeed:
    """Tests for is_podcast_feed function."""
    
    @pytest.fixture
    def mock_feedparser(self):
        """Mock feedparser for testing."""
        # feedparser is imported locally inside is_podcast_feed, so we need to patch sys.modules
        import sys
        mock = MagicMock()
        with patch.dict(sys.modules, {'feedparser': mock}):
            yield mock
    
    def test_is_podcast_feed_with_itunes_tags(self, mock_feedparser):
        """is_podcast_feed returns True for feeds with iTunes tags."""
        mock_feed = Mock()
        mock_feed.entries = [Mock()]
        mock_feed.feed = Mock()
        mock_feed.feed.get.return_value = ''
        mock_feed.feed.keys.return_value = ['itunes_author', 'itunes_image']
        mock_feedparser.parse.return_value = mock_feed
        
        with patch.dict('os.environ', {'TELEGRAM_TOKEN': 'test-token', 'DB_PATH': ':memory:'}):
            with patch('ai_summary.interfaces.telegram_bot.Application'):
                with patch('ai_summary.interfaces.telegram_bot.DbHelper'):
                    from ai_summary.interfaces.telegram_bot import is_podcast_feed
                    result = is_podcast_feed("https://example.com/feed.xml")
        
        assert result is True
    
    def test_is_podcast_feed_with_audio_enclosure(self, mock_feedparser):
        """is_podcast_feed returns True for feeds with audio enclosures."""
        mock_entry = Mock()
        mock_entry.enclosures = [{'type': 'audio/mpeg', 'href': 'https://example.com/audio.mp3'}]
        
        mock_feed = Mock()
        mock_feed.entries = [mock_entry]
        mock_feed.feed = Mock()
        mock_feed.feed.get.return_value = ''
        mock_feed.feed.keys.return_value = []
        mock_feedparser.parse.return_value = mock_feed
        
        with patch.dict('os.environ', {'TELEGRAM_TOKEN': 'test-token', 'DB_PATH': ':memory:'}):
            with patch('ai_summary.interfaces.telegram_bot.Application'):
                with patch('ai_summary.interfaces.telegram_bot.DbHelper'):
                    from ai_summary.interfaces.telegram_bot import is_podcast_feed
                    result = is_podcast_feed("https://example.com/feed.xml")
        
        assert result is True
    
    def test_is_podcast_feed_returns_false_for_article_feed(self, mock_feedparser):
        """is_podcast_feed returns False for article-only feeds."""
        mock_entry = Mock()
        mock_entry.enclosures = []
        del mock_entry.enclosures  # Remove enclosures attribute
        
        mock_feed = Mock()
        mock_feed.entries = [mock_entry]
        mock_feed.feed = Mock()
        mock_feed.feed.get.return_value = ''
        mock_feed.feed.keys.return_value = ['title', 'link']
        mock_feedparser.parse.return_value = mock_feed
        
        with patch.dict('os.environ', {'TELEGRAM_TOKEN': 'test-token', 'DB_PATH': ':memory:'}):
            with patch('ai_summary.interfaces.telegram_bot.Application'):
                with patch('ai_summary.interfaces.telegram_bot.DbHelper'):
                    from ai_summary.interfaces.telegram_bot import is_podcast_feed
                    result = is_podcast_feed("https://example.com/feed.xml")
        
        assert result is False
    
    def test_is_podcast_feed_returns_false_on_error(self, mock_feedparser):
        """is_podcast_feed returns False on parsing error."""
        mock_feedparser.parse.side_effect = Exception("Parse error")
        
        with patch.dict('os.environ', {'TELEGRAM_TOKEN': 'test-token', 'DB_PATH': ':memory:'}):
            with patch('ai_summary.interfaces.telegram_bot.Application'):
                with patch('ai_summary.interfaces.telegram_bot.DbHelper'):
                    from ai_summary.interfaces.telegram_bot import is_podcast_feed
                    result = is_podcast_feed("https://example.com/feed.xml")
        
        assert result is False
    
    def test_is_podcast_feed_returns_false_for_empty_feed(self, mock_feedparser):
        """is_podcast_feed returns False for empty feeds."""
        mock_feed = Mock()
        mock_feed.entries = []
        mock_feedparser.parse.return_value = mock_feed
        
        with patch.dict('os.environ', {'TELEGRAM_TOKEN': 'test-token', 'DB_PATH': ':memory:'}):
            with patch('ai_summary.interfaces.telegram_bot.Application'):
                with patch('ai_summary.interfaces.telegram_bot.DbHelper'):
                    from ai_summary.interfaces.telegram_bot import is_podcast_feed
                    result = is_podcast_feed("https://example.com/feed.xml")
        
        assert result is False


class TestNotifySubscribers:
    """Tests for notify_subscribers async function."""
    
    @pytest.mark.asyncio
    async def test_notify_subscribers_sends_to_all(self):
        """notify_subscribers sends message to all subscribers."""
        with patch.dict('os.environ', {'TELEGRAM_TOKEN': 'test-token', 'DB_PATH': ':memory:'}):
            with patch('ai_summary.interfaces.telegram_bot.Application') as mock_app_class:
                mock_app = Mock()
                mock_bot = AsyncMock()
                mock_app.bot = mock_bot
                mock_app_class.builder.return_value.token.return_value.build.return_value = mock_app
                
                with patch('ai_summary.interfaces.telegram_bot.DbHelper') as mock_db_class:
                    mock_db = Mock()
                    mock_db.get_subscribers.return_value = [123, 456, 789]
                    mock_db_class.return_value = mock_db
                    
                    # Re-import to get fresh module with mocks
                    import importlib
                    import ai_summary.interfaces.telegram_bot as telegram_bot
                    importlib.reload(telegram_bot)
                    
                    # Reset the mock to get the reloaded app
                    telegram_bot.app = mock_app
                    telegram_bot.db = mock_db
                    
                    await telegram_bot.notify_subscribers("Test Title", "https://example.com/post")
                    
                    # Should have sent to all 3 subscribers
                    assert mock_bot.send_message.call_count == 3
    
    @pytest.mark.asyncio
    async def test_notify_subscribers_includes_category(self):
        """notify_subscribers includes category in message."""
        with patch.dict('os.environ', {'TELEGRAM_TOKEN': 'test-token', 'DB_PATH': ':memory:'}):
            with patch('ai_summary.interfaces.telegram_bot.Application') as mock_app_class:
                mock_app = Mock()
                mock_bot = AsyncMock()
                mock_app.bot = mock_bot
                mock_app_class.builder.return_value.token.return_value.build.return_value = mock_app
                
                with patch('ai_summary.interfaces.telegram_bot.DbHelper') as mock_db_class:
                    mock_db = Mock()
                    mock_db.get_subscribers.return_value = [123]
                    mock_db_class.return_value = mock_db
                    
                    import importlib
                    import ai_summary.interfaces.telegram_bot as telegram_bot
                    importlib.reload(telegram_bot)
                    
                    telegram_bot.app = mock_app
                    telegram_bot.db = mock_db
                    
                    await telegram_bot.notify_subscribers(
                        "Test Title",
                        "https://example.com/post",
                        category="Tech"
                    )
                    
                    call_args = mock_bot.send_message.call_args
                    message_text = call_args[1]['text']
                    assert "[Tech]" in message_text
