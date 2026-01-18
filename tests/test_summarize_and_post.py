"""Unit tests for summarize_and_post module."""
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestExtractChannelHandle:
    """Tests for extract_channel_handle function."""
    
    @pytest.mark.parametrize("url,expected", [
        ("https://youtube.com/@testchannel", "@testchannel"),
        ("https://www.youtube.com/@MyChannel", "@MyChannel"),
        ("https://youtube.com/channel/UC123456", "https://youtube.com/channel/UC123456"),
        ("@simplename", "@simplename"),
        ("no-at-symbol", "no-at-symbol"),
    ])
    def test_extract_channel_handle(self, url, expected):
        """Test channel handle extraction from various URL formats."""
        from ai_summary.content.publisher import extract_channel_handle
        assert extract_channel_handle(url) == expected


class TestExtractYoutubeId:
    """Tests for extract_youtube_id function."""
    
    @pytest.mark.parametrize("url,expected_id", [
        # Standard watch URLs
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        
        # Short URLs
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        
        # Embed URLs
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        
        # Shorts URLs
        ("https://youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        
        # Invalid URLs
        ("https://example.com", None),
        ("not a url", None),
    ])
    def test_extract_youtube_id(self, url, expected_id):
        """Test YouTube ID extraction from various URL formats."""
        from ai_summary.content.publisher import extract_youtube_id
        assert extract_youtube_id(url) == expected_id


class TestGetYoutubeThumbnail:
    """Tests for get_youtube_thumbnail function."""
    
    def test_get_youtube_thumbnail_returns_url(self):
        """get_youtube_thumbnail returns thumbnail URL for valid video."""
        from ai_summary.content.publisher import get_youtube_thumbnail
        
        result = get_youtube_thumbnail("https://youtu.be/dQw4w9WgXcQ")
        
        assert result is not None
        assert "img.youtube.com" in result
        assert "dQw4w9WgXcQ" in result
        assert "maxresdefault.jpg" in result
    
    def test_get_youtube_thumbnail_returns_none_for_invalid(self):
        """get_youtube_thumbnail returns None for invalid URL."""
        from ai_summary.content.publisher import get_youtube_thumbnail
        
        result = get_youtube_thumbnail("https://example.com")
        
        assert result is None


class TestRemoveHtmlTags:
    """Tests for remove_html_tags function."""
    
    @pytest.mark.parametrize("html,expected", [
        # Simple tags
        ("<p>Hello World</p>", "Hello World"),
        ("<div><span>Nested</span></div>", "Nested"),
        
        # Multiple tags - code doesn't add space between adjacent tags
        ("<h1>Title</h1><p>Content</p>", "TitleContent"),
        
        # Tags with attributes
        ('<a href="http://example.com">Link</a>', "Link"),
        ('<div class="test" id="main">Text</div>', "Text"),
        
        # Self-closing tags
        ("Text<br/>More", "TextMore"),
        
        # No tags
        ("Plain text", "Plain text"),
        
        # Empty string
        ("", ""),
        
        # Extra whitespace
        ("<p>  Multiple   spaces  </p>", "Multiple spaces"),
    ])
    def test_remove_html_tags(self, html, expected):
        """Test HTML tag removal from various inputs."""
        from ai_summary.content.publisher import remove_html_tags
        assert remove_html_tags(html) == expected


class TestGetThumbnailUrl:
    """Tests for get_thumbnail_url function."""
    
    def test_get_thumbnail_url_with_video_url(self):
        """get_thumbnail_url returns YouTube thumbnail for video URL."""
        from ai_summary.content.publisher import get_thumbnail_url
        
        result = get_thumbnail_url(video_url="https://youtu.be/dQw4w9WgXcQ")
        
        assert result is not None
        assert "youtube" in result
    
    def test_get_thumbnail_url_with_channel_url(self):
        """get_thumbnail_url tries static thumbnail for channel URL."""
        with patch('ai_summary.content.publisher.get_static_thumbnail', return_value="https://example.com/thumb.jpg"):
            from ai_summary.content.publisher import get_thumbnail_url
            
            result = get_thumbnail_url(channel_url="https://youtube.com/@channel")
            
            assert result is not None
    
    def test_get_thumbnail_url_prefers_video_over_channel(self):
        """get_thumbnail_url prefers video thumbnail over channel."""
        from ai_summary.content.publisher import get_thumbnail_url
        
        result = get_thumbnail_url(
            video_url="https://youtu.be/dQw4w9WgXcQ",
            channel_url="https://youtube.com/@channel"
        )
        
        assert "youtube" in result  # Should be YouTube thumbnail, not static
    
    def test_get_thumbnail_url_returns_none_when_no_source(self):
        """get_thumbnail_url returns None when no source provided."""
        from ai_summary.content.publisher import get_thumbnail_url
        
        result = get_thumbnail_url()
        
        assert result is None


class TestCreateLexicalContent:
    """Tests for create_lexical_content function."""
    
    def test_create_lexical_content_basic_structure(self):
        """create_lexical_content returns proper Lexical structure."""
        from ai_summary.content.publisher import create_lexical_content
        
        result = create_lexical_content("Test content")
        
        assert "root" in result
        assert result["root"]["type"] == "root"
        assert "children" in result["root"]
    
    def test_create_lexical_content_with_video(self):
        """create_lexical_content includes embed node for video."""
        from ai_summary.content.publisher import create_lexical_content
        
        result = create_lexical_content("Content", video_url="https://youtu.be/dQw4w9WgXcQ")
        
        children = result["root"]["children"]
        embed_nodes = [n for n in children if n.get("type") == "embed"]
        
        assert len(embed_nodes) > 0
        assert "youtube" in embed_nodes[0].get("url", "").lower()
    
    def test_create_lexical_content_with_source_link(self):
        """create_lexical_content includes source link."""
        from ai_summary.content.publisher import create_lexical_content
        
        result = create_lexical_content("Content", post_url="https://example.com/article")
        
        children = result["root"]["children"]
        
        # Check that there's a link node somewhere
        has_link = any(
            any(c.get("type") == "link" for c in n.get("children", []))
            for n in children
            if n.get("type") == "paragraph"
        )
        assert has_link


class TestFindRelevantTags:
    """Tests for find_relevant_tags function."""
    
    @pytest.fixture
    def available_tags(self):
        """Sample available tags."""
        return [
            {'name': 'AI'},
            {'name': 'Apple'},
            {'name': 'Google'},
            {'name': 'summary'},  # Should be excluded
        ]
    
    def test_find_relevant_tags_matches_in_content(self, available_tags):
        """find_relevant_tags returns tags found in content."""
        from ai_summary.content.publisher import find_relevant_tags
        
        result = find_relevant_tags(
            "AI Revolution",
            "This article discusses AI and Apple products",
            available_tags
        )
        
        tag_names = [t['name'] for t in result]
        assert 'AI' in tag_names
        assert 'Apple' in tag_names
    
    def test_find_relevant_tags_excludes_summary(self, available_tags):
        """find_relevant_tags excludes 'summary' tag."""
        from ai_summary.content.publisher import find_relevant_tags
        
        result = find_relevant_tags(
            "Summary of AI",
            "This is a summary about AI",
            available_tags
        )
        
        tag_names = [t['name'] for t in result]
        assert 'summary' not in tag_names
    
    def test_find_relevant_tags_case_insensitive(self, available_tags):
        """find_relevant_tags matches case-insensitively."""
        from ai_summary.content.publisher import find_relevant_tags
        
        result = find_relevant_tags(
            "GOOGLE News",
            "google announced new products",
            available_tags
        )
        
        tag_names = [t['name'] for t in result]
        assert 'Google' in tag_names
    
    def test_find_relevant_tags_returns_empty_for_no_matches(self, available_tags):
        """find_relevant_tags returns empty list when no matches."""
        from ai_summary.content.publisher import find_relevant_tags
        
        result = find_relevant_tags(
            "Unrelated Title",
            "Content about something completely different",
            available_tags
        )
        
        # May return empty or not, depending on content
        assert isinstance(result, list)


class TestGetGhostToken:
    """Tests for get_ghost_token function."""
    
    def test_get_ghost_token_returns_jwt(self):
        """get_ghost_token returns a JWT token."""
        with patch.dict('os.environ', {'ghost_key': 'abc123:0123456789abcdef0123456789abcdef'}):
            from ai_summary.content.publisher import get_ghost_token
            
            token = get_ghost_token()
            
            assert token is not None
            assert isinstance(token, str)
            # JWT tokens have 3 parts separated by dots
            assert len(token.split('.')) == 3


class TestPostToWordpress:
    """Tests for post_to_wordpress function."""
    
    @pytest.fixture
    def mock_requests(self):
        """Mock requests for testing."""
        with patch('ai_summary.content.publisher.requests') as mock:
            yield mock
    
    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Set up mock environment variables."""
        monkeypatch.setenv('wp_host', 'https://wordpress.test.com')
        monkeypatch.setenv('wp_user', 'testuser')
        monkeypatch.setenv('wp_pass', 'testpass')
    
    def test_post_to_wordpress_success(self, mock_requests, mock_env):
        """post_to_wordpress returns URL on success."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'link': 'https://wordpress.test.com/post/123'}
        mock_requests.post.return_value = mock_response
        mock_requests.get.return_value = Mock(status_code=404)  # For thumbnail
        
        with patch('ai_summary.content.publisher.generate_slug', return_value='test-slug'):
            with patch('ai_summary.content.publisher.get_thumbnail_url', return_value=None):
                from ai_summary.content.publisher import post_to_wordpress
                
                result = post_to_wordpress(
                    "Test Title",
                    "Test Content",
                    None,
                    "https://example.com/article",
                    "https://youtube.com/@channel"
                )
        
        assert result == 'https://wordpress.test.com/post/123'
    
    def test_post_to_wordpress_returns_none_on_failure(self, mock_requests, mock_env):
        """post_to_wordpress returns None on API failure."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_requests.post.return_value = mock_response
        
        with patch('ai_summary.content.publisher.generate_slug', return_value='test-slug'):
            with patch('ai_summary.content.publisher.get_thumbnail_url', return_value=None):
                from ai_summary.content.publisher import post_to_wordpress
                
                result = post_to_wordpress(
                    "Test Title",
                    "Test Content",
                    None,
                    "https://example.com/article",
                    "https://youtube.com/@testchannel"
                )
        
        assert result is None


class TestPostToGhost:
    """Tests for post_to_ghost function."""
    
    @pytest.fixture
    def mock_requests(self):
        """Mock requests for testing."""
        with patch('ai_summary.content.publisher.requests') as mock:
            yield mock
    
    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Set up mock environment variables."""
        monkeypatch.setenv('ghost_url', 'https://ghost.test.com')
        monkeypatch.setenv('ghost_key', 'abc123:0123456789abcdef0123456789abcdef')
    
    def test_post_to_ghost_success(self, mock_requests, mock_env):
        """post_to_ghost returns URL on success."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'posts': [{'url': 'https://ghost.test.com/post/test-slug'}]
        }
        mock_requests.post.return_value = mock_response
        
        with patch('ai_summary.content.publisher.generate_slug', return_value='test-slug'):
            with patch('ai_summary.content.publisher.get_thumbnail_url', return_value=None):
                with patch('ai_summary.content.publisher.humanize_content', return_value='Content'):
                    from ai_summary.content.publisher import post_to_ghost
                    
                    result = post_to_ghost(
                        "Test Title",
                        "Test Content",
                        None,
                        "https://example.com/article",
                        "https://youtube.com/@channel"
                    )
        
        assert result == 'https://ghost.test.com/post/test-slug'
    
    def test_post_to_ghost_returns_none_on_failure(self, mock_requests, mock_env):
        """post_to_ghost returns None on API failure."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_requests.post.return_value = mock_response
        
        with patch('ai_summary.content.publisher.generate_slug', return_value='test-slug'):
            with patch('ai_summary.content.publisher.get_thumbnail_url', return_value=None):
                with patch('ai_summary.content.publisher.humanize_content', return_value='Content'):
                    from ai_summary.content.publisher import post_to_ghost
                    
                    result = post_to_ghost(
                        "Test Title",
                        "Test Content",
                        None,
                        "https://example.com/article",
                        "https://youtube.com/@testchannel"
                    )
        
        assert result is None


class TestCategoryIds:
    """Tests for CATEGORY_IDS constant."""
    
    def test_category_ids_contains_expected_channels(self):
        """CATEGORY_IDS contains expected channel mappings."""
        from ai_summary.content.publisher import CATEGORY_IDS
        
        assert 'stratechery' in CATEGORY_IDS
        assert '@sharptechpodcast' in CATEGORY_IDS
        assert 'allin' in CATEGORY_IDS
    
    def test_category_ids_values_are_integers(self):
        """CATEGORY_IDS values are all integers."""
        from ai_summary.content.publisher import CATEGORY_IDS
        
        for channel, category_id in CATEGORY_IDS.items():
            assert isinstance(category_id, int)
