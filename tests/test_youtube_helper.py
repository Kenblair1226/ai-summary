"""Unit tests for youtube_helper module."""
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestIsValidYoutubeUrl:
    """Tests for is_valid_youtube_url function."""
    
    @pytest.mark.parametrize("url,expected", [
        # Standard watch URLs
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", True),
        ("https://youtube.com/watch?v=dQw4w9WgXcQ", True),
        ("http://www.youtube.com/watch?v=dQw4w9WgXcQ", True),
        
        # Short URLs
        ("https://youtu.be/dQw4w9WgXcQ", True),
        ("http://youtu.be/dQw4w9WgXcQ", True),
        
        # Shorts URLs
        ("https://youtube.com/shorts/dQw4w9WgXcQ", True),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", True),
        
        # Live URLs
        ("https://youtube.com/live/dQw4w9WgXcQ", True),
        ("https://www.youtube.com/live/dQw4w9WgXcQ", True),
        
        # Invalid URLs
        ("https://example.com/video", False),
        ("https://vimeo.com/123456789", False),
        ("not a url at all", False),
        ("https://youtube.com/@channel", False),  # Channel, not video
        ("", False),
    ])
    def test_is_valid_youtube_url(self, url, expected):
        """Test URL validation for various YouTube URL formats."""
        from ai_summary.content.youtube_helper import is_valid_youtube_url
        assert is_valid_youtube_url(url) == expected


class TestExtractVideoId:
    """Tests for extract_video_id function."""
    
    @pytest.mark.parametrize("url,expected_id", [
        # Standard watch URLs
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtube.com/watch?v=abc123_-XYZ", "abc123_-XYZ"),
        
        # Short URLs
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        
        # Shorts URLs
        ("https://youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        
        # Live URLs
        ("https://youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        
        # With additional parameters
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=60", "dQw4w9WgXcQ"),
        
        # Invalid URLs
        ("https://example.com", None),
        ("not a url", None),
        ("", None),
    ])
    def test_extract_video_id(self, url, expected_id):
        """Test video ID extraction from various URL formats."""
        from ai_summary.content.youtube_helper import extract_video_id
        assert extract_video_id(url) == expected_id
    
    def test_extract_video_id_returns_11_char_id(self):
        """Video IDs are always 11 characters."""
        from ai_summary.content.youtube_helper import extract_video_id
        
        video_id = extract_video_id("https://youtu.be/dQw4w9WgXcQ")
        assert video_id is not None
        assert len(video_id) == 11


class TestGetYoutubeTitle:
    """Tests for get_youtube_title function."""
    
    @pytest.fixture
    def mock_yt_dlp(self):
        """Mock yt-dlp for testing."""
        with patch('ai_summary.content.youtube_helper.yt_dlp.YoutubeDL') as mock:
            yield mock
    
    def test_get_youtube_title_success(self, mock_yt_dlp):
        """get_youtube_title returns title on success."""
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl.__exit__ = Mock(return_value=False)
        mock_ydl.extract_info.return_value = {'title': 'Test Video Title'}
        mock_yt_dlp.return_value = mock_ydl
        
        from ai_summary.content.youtube_helper import get_youtube_title
        result = get_youtube_title("https://youtu.be/test123")
        
        assert result == "Test Video Title"
    
    def test_get_youtube_title_returns_none_on_error(self, mock_yt_dlp):
        """get_youtube_title returns None on error."""
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl.__exit__ = Mock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("Network error")
        mock_yt_dlp.return_value = mock_ydl
        
        from ai_summary.content.youtube_helper import get_youtube_title
        result = get_youtube_title("https://youtu.be/test123")
        
        assert result is None
    
    def test_get_youtube_title_uses_quiet_mode(self, mock_yt_dlp):
        """get_youtube_title uses quiet mode to suppress output."""
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl.__exit__ = Mock(return_value=False)
        mock_ydl.extract_info.return_value = {'title': 'Title'}
        mock_yt_dlp.return_value = mock_ydl
        
        from ai_summary.content.youtube_helper import get_youtube_title
        get_youtube_title("https://youtu.be/test123")
        
        call_args = mock_yt_dlp.call_args[0][0]
        assert call_args['quiet'] is True


class TestDownloadAudioFromYoutube:
    """Tests for download_audio_from_youtube function."""
    
    @pytest.fixture
    def mock_yt_dlp(self):
        """Mock yt-dlp for testing."""
        with patch('ai_summary.content.youtube_helper.yt_dlp.YoutubeDL') as mock:
            yield mock
    
    @pytest.fixture
    def mock_os(self):
        """Mock os functions."""
        with patch('ai_summary.content.youtube_helper.os.makedirs') as mock_makedirs:
            with patch('ai_summary.content.youtube_helper.os.path.exists', return_value=True):
                with patch('ai_summary.content.youtube_helper.os.path.getsize', return_value=1024*1024):
                    yield mock_makedirs
    
    def test_download_audio_returns_title_and_path(self, mock_yt_dlp, mock_os):
        """download_audio_from_youtube returns tuple of title and path."""
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl.__exit__ = Mock(return_value=False)
        mock_ydl.extract_info.return_value = {'title': 'Test Video'}
        mock_ydl.prepare_filename.return_value = '/output/test_video.webm'
        mock_yt_dlp.return_value = mock_ydl
        
        from ai_summary.content.youtube_helper import download_audio_from_youtube
        title, path = download_audio_from_youtube("https://youtu.be/test123", "/output")
        
        assert title == "Test Video"
        assert path.endswith('.mp3')
    
    def test_download_audio_creates_output_directory(self, mock_yt_dlp, mock_os):
        """download_audio_from_youtube creates output directory."""
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl.__exit__ = Mock(return_value=False)
        mock_ydl.extract_info.return_value = {'title': 'Test'}
        mock_ydl.prepare_filename.return_value = '/output/test.webm'
        mock_yt_dlp.return_value = mock_ydl
        
        from ai_summary.content.youtube_helper import download_audio_from_youtube
        download_audio_from_youtube("https://youtu.be/test123", "/output")
        
        mock_os.assert_called_once_with("/output", exist_ok=True)
    
    def test_download_audio_raises_on_error(self, mock_yt_dlp, mock_os):
        """download_audio_from_youtube raises on download error."""
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl.__exit__ = Mock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("Download failed")
        mock_yt_dlp.return_value = mock_ydl
        
        from ai_summary.content.youtube_helper import download_audio_from_youtube
        with pytest.raises(Exception):
            download_audio_from_youtube("https://youtu.be/test123", "/output")


class TestCheckNewVideos:
    """Tests for check_new_videos function."""
    
    @pytest.fixture
    def mock_yt_dlp(self):
        """Mock yt-dlp for testing."""
        with patch('ai_summary.content.youtube_helper.yt_dlp.YoutubeDL') as mock:
            yield mock
    
    def test_check_new_videos_returns_new_videos(self, mock_yt_dlp, temp_db):
        """check_new_videos returns list of new videos."""
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl.__exit__ = Mock(return_value=False)
        mock_ydl.extract_info.return_value = {
            'entries': [
                {'id': 'video1', 'title': 'Video 1', 'url': None},
                {'id': 'video2', 'title': 'Video 2', 'url': None},
            ]
        }
        mock_yt_dlp.return_value = mock_ydl
        
        from ai_summary.content.youtube_helper import check_new_videos
        result = check_new_videos("https://youtube.com/@channel", temp_db)
        
        assert len(result) == 2
        assert result[0]['video_id'] == 'video1'
        assert result[1]['video_id'] == 'video2'
    
    def test_check_new_videos_filters_existing(self, mock_yt_dlp, temp_db):
        """check_new_videos filters out already checked videos."""
        # First, add an existing video
        temp_db.save_checked_video_ids("https://youtube.com/@channel", ["existing_video"])
        
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl.__exit__ = Mock(return_value=False)
        mock_ydl.extract_info.return_value = {
            'entries': [
                {'id': 'existing_video', 'title': 'Existing'},
                {'id': 'new_video', 'title': 'New'},
            ]
        }
        mock_yt_dlp.return_value = mock_ydl
        
        from ai_summary.content.youtube_helper import check_new_videos
        result = check_new_videos("https://youtube.com/@channel", temp_db)
        
        assert len(result) == 1
        assert result[0]['video_id'] == 'new_video'
    
    def test_check_new_videos_returns_empty_on_no_entries(self, mock_yt_dlp, temp_db):
        """check_new_videos returns empty list when no entries found."""
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl.__exit__ = Mock(return_value=False)
        mock_ydl.extract_info.return_value = {}  # No 'entries' key
        mock_yt_dlp.return_value = mock_ydl
        
        from ai_summary.content.youtube_helper import check_new_videos
        result = check_new_videos("https://youtube.com/@channel", temp_db)
        
        assert result == []
    
    def test_check_new_videos_returns_empty_on_error(self, mock_yt_dlp, temp_db):
        """check_new_videos returns empty list on error."""
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl.__exit__ = Mock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("Network error")
        mock_yt_dlp.return_value = mock_ydl
        
        from ai_summary.content.youtube_helper import check_new_videos
        result = check_new_videos("https://youtube.com/@channel", temp_db)
        
        assert result == []
    
    def test_check_new_videos_saves_new_video_ids(self, mock_yt_dlp, temp_db):
        """check_new_videos saves new video IDs to database."""
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl.__exit__ = Mock(return_value=False)
        mock_ydl.extract_info.return_value = {
            'entries': [
                {'id': 'new_video_1', 'title': 'New 1'},
                {'id': 'new_video_2', 'title': 'New 2'},
            ]
        }
        mock_yt_dlp.return_value = mock_ydl
        
        from ai_summary.content.youtube_helper import check_new_videos
        check_new_videos("https://youtube.com/@channel", temp_db)
        
        # Verify videos were saved
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT video_id FROM videos')
            saved_ids = {row[0] for row in cursor.fetchall()}
        
        assert 'new_video_1' in saved_ids
        assert 'new_video_2' in saved_ids
    
    def test_check_new_videos_skips_none_entries(self, mock_yt_dlp, temp_db):
        """check_new_videos skips None entries in results."""
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl.__exit__ = Mock(return_value=False)
        mock_ydl.extract_info.return_value = {
            'entries': [
                None,
                {'id': 'valid_video', 'title': 'Valid'},
                None,
            ]
        }
        mock_yt_dlp.return_value = mock_ydl
        
        from ai_summary.content.youtube_helper import check_new_videos
        result = check_new_videos("https://youtube.com/@channel", temp_db)
        
        assert len(result) == 1
        assert result[0]['video_id'] == 'valid_video'
    
    def test_check_new_videos_limits_to_5(self, mock_yt_dlp, temp_db):
        """check_new_videos only processes first 5 entries."""
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl.__exit__ = Mock(return_value=False)
        
        # Return 10 entries
        entries = [{'id': f'video{i}', 'title': f'Video {i}'} for i in range(10)]
        mock_ydl.extract_info.return_value = {'entries': entries}
        mock_yt_dlp.return_value = mock_ydl
        
        from ai_summary.content.youtube_helper import check_new_videos
        result = check_new_videos("https://youtube.com/@channel", temp_db)
        
        # Should only process first 5
        assert len(result) <= 5
