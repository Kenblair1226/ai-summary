"""Unit tests for main module."""
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestExtractMp3Url:
    """Tests for extract_mp3_url function."""
    
    def test_extract_mp3_url_from_enclosure(self):
        """extract_mp3_url finds URL in enclosures."""
        entry = Mock()
        entry.enclosures = [
            {'href': 'https://example.com/audio.mp3', 'type': 'audio/mpeg'}
        ]
        entry.media_content = []
        entry.links = []
        
        from ai_summary.main import extract_mp3_url
        result = extract_mp3_url(entry)
        
        assert result == 'https://example.com/audio.mp3'
    
    def test_extract_mp3_url_from_enclosure_by_extension(self):
        """extract_mp3_url finds URL by .mp3 extension in enclosures."""
        entry = Mock()
        entry.enclosures = [
            {'href': 'https://example.com/podcast.mp3', 'type': 'application/octet-stream'}
        ]
        entry.media_content = []
        entry.links = []
        
        from ai_summary.main import extract_mp3_url
        result = extract_mp3_url(entry)
        
        assert result == 'https://example.com/podcast.mp3'
    
    def test_extract_mp3_url_from_media_content(self):
        """extract_mp3_url finds URL in media_content."""
        entry = Mock()
        entry.enclosures = []
        entry.media_content = [
            {'url': 'https://example.com/episode.mp3', 'type': 'audio/mpeg'}
        ]
        entry.links = []
        
        from ai_summary.main import extract_mp3_url
        result = extract_mp3_url(entry)
        
        assert result == 'https://example.com/episode.mp3'
    
    def test_extract_mp3_url_from_links(self):
        """extract_mp3_url finds URL in links."""
        entry = Mock()
        entry.enclosures = []
        entry.media_content = []
        entry.links = [
            {'href': 'https://example.com/show.mp3', 'type': 'audio/mpeg'}
        ]
        
        from ai_summary.main import extract_mp3_url
        result = extract_mp3_url(entry)
        
        assert result == 'https://example.com/show.mp3'
    
    def test_extract_mp3_url_from_audio_url_attr(self):
        """extract_mp3_url finds direct audio_url attribute."""
        entry = Mock()
        entry.enclosures = []
        entry.media_content = []
        entry.links = []
        entry.audio_url = 'https://example.com/direct.mp3'
        
        from ai_summary.main import extract_mp3_url
        result = extract_mp3_url(entry)
        
        assert result == 'https://example.com/direct.mp3'
    
    def test_extract_mp3_url_returns_none_when_not_found(self):
        """extract_mp3_url returns None when no audio found."""
        entry = Mock()
        entry.enclosures = []
        entry.media_content = []
        entry.links = []
        # Remove audio_url attribute
        del entry.audio_url
        
        from ai_summary.main import extract_mp3_url
        result = extract_mp3_url(entry)
        
        assert result is None
    
    def test_extract_mp3_url_prefers_enclosure_over_others(self):
        """extract_mp3_url prefers enclosure over other sources."""
        entry = Mock()
        entry.enclosures = [
            {'href': 'https://example.com/enclosure.mp3', 'type': 'audio/mpeg'}
        ]
        entry.media_content = [
            {'url': 'https://example.com/media.mp3', 'type': 'audio/mpeg'}
        ]
        entry.links = [
            {'href': 'https://example.com/link.mp3', 'type': 'audio/mpeg'}
        ]
        entry.audio_url = 'https://example.com/direct.mp3'
        
        from ai_summary.main import extract_mp3_url
        result = extract_mp3_url(entry)
        
        assert result == 'https://example.com/enclosure.mp3'
    
    def test_extract_mp3_url_handles_missing_enclosures_attr(self):
        """extract_mp3_url handles entries without enclosures attribute."""
        entry = Mock(spec=[])  # Empty spec = no attributes
        
        from ai_summary.main import extract_mp3_url
        result = extract_mp3_url(entry)
        
        assert result is None
    
    def test_extract_mp3_url_handles_non_dict_enclosures(self):
        """extract_mp3_url handles non-dict enclosure entries."""
        entry = Mock(spec=['enclosures', 'media_content', 'links'])
        entry.enclosures = ["not a dict", None, 123]
        entry.media_content = []
        entry.links = []
        
        from ai_summary.main import extract_mp3_url
        result = extract_mp3_url(entry)
        
        # Should not crash, just return None
        assert result is None
    
    def test_extract_mp3_url_skips_non_audio_enclosures(self):
        """extract_mp3_url skips non-audio enclosures."""
        entry = Mock()
        entry.enclosures = [
            {'href': 'https://example.com/image.jpg', 'type': 'image/jpeg'},
            {'href': 'https://example.com/video.mp4', 'type': 'video/mp4'},
            {'href': 'https://example.com/audio.mp3', 'type': 'audio/mpeg'},
        ]
        entry.media_content = []
        entry.links = []
        
        from ai_summary.main import extract_mp3_url
        result = extract_mp3_url(entry)
        
        assert result == 'https://example.com/audio.mp3'


class TestStartupTime:
    """Tests for STARTUP_TIME constant."""
    
    def test_startup_time_is_set(self):
        """STARTUP_TIME is set to a datetime."""
        from ai_summary.main import STARTUP_TIME
        from datetime import datetime
        
        assert STARTUP_TIME is not None
        assert isinstance(STARTUP_TIME, datetime)
    
    def test_startup_time_has_timezone(self):
        """STARTUP_TIME has UTC timezone."""
        from ai_summary.main import STARTUP_TIME
        
        assert STARTUP_TIME.tzinfo is not None


class TestDbInitialization:
    """Tests for database initialization in main."""
    
    def test_db_is_initialized(self):
        """Database helper is initialized."""
        from ai_summary.main import db
        
        assert db is not None
        assert hasattr(db, 'get_connection')
        assert hasattr(db, 'initialize_db')
