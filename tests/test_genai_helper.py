"""Unit tests for genai_helper module."""
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestGenerateSlug:
    """Tests for generate_slug function."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Mock the LLM service."""
        with patch('ai_summary.content.genai_helper.llm_service') as mock:
            yield mock
    
    def test_generate_slug_returns_valid_slug(self, mock_llm_service):
        """generate_slug returns a valid URL-friendly slug."""
        mock_response = Mock()
        mock_response.text = "ai-transformation-tech-industry"
        mock_llm_service.generate_content.return_value = mock_response
        
        from ai_summary.content.genai_helper import generate_slug
        result = generate_slug("AI Transformation in Tech Industry")
        
        assert result == "ai-transformation-tech-industry"
        assert result.islower()
        assert ' ' not in result
    
    def test_generate_slug_cleans_invalid_characters(self, mock_llm_service):
        """generate_slug removes invalid characters from result."""
        mock_response = Mock()
        mock_response.text = "test-slug!!@#"
        mock_llm_service.generate_content.return_value = mock_response
        
        from ai_summary.content.genai_helper import generate_slug
        result = generate_slug("Test Title")
        
        # Should only contain alphanumeric and hyphens
        assert all(c.isalnum() or c == '-' for c in result)
    
    def test_generate_slug_truncates_to_50_chars(self, mock_llm_service):
        """generate_slug truncates result to max 50 characters."""
        mock_response = Mock()
        mock_response.text = "a" * 60 + "-suffix"
        mock_llm_service.generate_content.return_value = mock_response
        
        from ai_summary.content.genai_helper import generate_slug
        result = generate_slug("Very Long Title")
        
        assert len(result) <= 50
    
    def test_generate_slug_retries_on_invalid_format(self, mock_llm_service):
        """generate_slug retries when regex validation fails."""
        invalid_response = Mock()
        invalid_response.text = "---invalid---"
        valid_response = Mock()
        valid_response.text = "valid-slug"
        
        mock_llm_service.generate_content.side_effect = [
            invalid_response,
            valid_response
        ]
        
        from ai_summary.content.genai_helper import generate_slug
        result = generate_slug("Test Title")
        
        # Should have retried
        assert mock_llm_service.generate_content.call_count >= 1
    
    def test_generate_slug_uses_light_model_tier(self, mock_llm_service):
        """generate_slug uses light model tier for efficiency."""
        mock_response = Mock()
        mock_response.text = "test-slug"
        mock_llm_service.generate_content.return_value = mock_response
        
        from ai_summary.content.genai_helper import generate_slug
        generate_slug("Test Title")
        
        call_args = mock_llm_service.generate_content.call_args
        assert call_args[1]['model_tier'] == 'light'


class TestFormatHtmlContent:
    """Tests for format_html_content function."""
    
    def test_format_html_content_converts_urls_to_links(self):
        """URLs are converted to anchor tags."""
        from ai_summary.content.genai_helper import format_html_content
        
        content = "Check out https://example.com for more info"
        result = format_html_content(content)
        
        assert '<a href="https://example.com"' in result
        assert 'target="_blank"' in result
    
    def test_format_html_content_handles_multiple_urls(self):
        """Multiple URLs are all converted."""
        from ai_summary.content.genai_helper import format_html_content
        
        content = "Visit https://site1.com and https://site2.com"
        result = format_html_content(content)
        
        assert 'href="https://site1.com"' in result
        assert 'href="https://site2.com"' in result
    
    def test_format_html_content_splits_paragraphs(self):
        """Content is split into paragraphs."""
        from ai_summary.content.genai_helper import format_html_content
        
        content = "First paragraph.\n\nSecond paragraph."
        result = format_html_content(content)
        
        assert "\n\n" in result
    
    def test_format_html_content_removes_extra_spaces(self):
        """Extra spaces are normalized."""
        from ai_summary.content.genai_helper import format_html_content
        
        content = "Word1    Word2     Word3"
        result = format_html_content(content)
        
        assert "    " not in result
    
    def test_format_html_content_handles_empty_string(self):
        """Empty string returns empty result."""
        from ai_summary.content.genai_helper import format_html_content
        
        result = format_html_content("")
        
        assert result == ""


class TestSummarizeText:
    """Tests for summarize_text function."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Mock the LLM service."""
        with patch('ai_summary.content.genai_helper.llm_service') as mock:
            yield mock
    
    def test_summarize_text_returns_title_and_content(self, mock_llm_service):
        """summarize_text returns tuple of title and content."""
        mock_response = Mock()
        mock_response.text = "Generated Title\nThis is the summary content."
        mock_llm_service.generate_content.return_value = mock_response
        
        from ai_summary.content.genai_helper import summarize_text
        title, content = summarize_text("Original Title", "Original Content")
        
        assert title == "Generated Title"
        assert "summary content" in content
    
    def test_summarize_text_uses_heavy_model_tier(self, mock_llm_service):
        """summarize_text uses heavy model tier for complex tasks."""
        mock_response = Mock()
        mock_response.text = "Title\nContent"
        mock_llm_service.generate_content.return_value = mock_response
        
        from ai_summary.content.genai_helper import summarize_text
        summarize_text("Title", "Content")
        
        call_args = mock_llm_service.generate_content.call_args
        assert call_args[1]['model_tier'] == 'heavy'
    
    def test_summarize_text_raises_on_error(self, mock_llm_service):
        """summarize_text propagates errors."""
        mock_llm_service.generate_content.side_effect = Exception("API Error")
        
        from ai_summary.content.genai_helper import summarize_text
        with pytest.raises(Exception):
            summarize_text("Title", "Content")


class TestSummarizeArticle:
    """Tests for summarize_article function."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Mock the LLM service."""
        with patch('ai_summary.content.genai_helper.llm_service') as mock:
            yield mock
    
    def test_summarize_article_returns_title_and_content(self, mock_llm_service):
        """summarize_article returns tuple of title and content."""
        mock_response = Mock()
        mock_response.text = "Article Summary Title\nThis is the article summary."
        mock_llm_service.generate_content.return_value = mock_response
        
        from ai_summary.content.genai_helper import summarize_article
        title, content = summarize_article("Original Title", "Article content here...")
        
        assert title == "Article Summary Title"
        assert "article summary" in content
    
    def test_summarize_article_passes_kwargs(self, mock_llm_service):
        """summarize_article passes kwargs to LLM service."""
        mock_response = Mock()
        mock_response.text = "Title\nContent"
        mock_llm_service.generate_content.return_value = mock_response
        
        from ai_summary.content.genai_helper import summarize_article
        summarize_article("Title", "Content", provider='gemini')
        
        call_args = mock_llm_service.generate_content.call_args
        assert 'provider' in call_args[1]


class TestSummarizeMp3:
    """Tests for summarize_mp3 function."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Mock the LLM service."""
        with patch('ai_summary.content.genai_helper.llm_service') as mock:
            yield mock
    
    def test_summarize_mp3_calls_generate_content_with_media(self, mock_llm_service):
        """summarize_mp3 uses generate_content_with_media."""
        mock_response = Mock()
        mock_response.text = "Audio Summary"
        mock_llm_service.generate_content_with_media.return_value = mock_response
        
        from ai_summary.content.genai_helper import summarize_mp3
        result = summarize_mp3("/path/to/audio.mp3")
        
        mock_llm_service.generate_content_with_media.assert_called_once()
        assert result.text == "Audio Summary"
    
    def test_summarize_mp3_raises_on_error(self, mock_llm_service):
        """summarize_mp3 propagates errors."""
        mock_llm_service.generate_content_with_media.side_effect = Exception("Media Error")
        
        from ai_summary.content.genai_helper import summarize_mp3
        with pytest.raises(Exception):
            summarize_mp3("/path/to/audio.mp3")


class TestHumanizeContent:
    """Tests for humanize_content function."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Mock the LLM service."""
        with patch('ai_summary.content.genai_helper.llm_service') as mock:
            yield mock
    
    def test_humanize_content_returns_formatted_content(self, mock_llm_service):
        """humanize_content returns formatted content."""
        mock_response = Mock()
        mock_response.text = "Humanized and natural content here."
        mock_llm_service.generate_content.return_value = mock_response
        
        from ai_summary.content.genai_helper import humanize_content
        result = humanize_content("Original stiff content")
        
        assert "Humanized" in result or "natural" in result
    
    def test_humanize_content_returns_original_on_error(self, mock_llm_service):
        """humanize_content returns original content on error."""
        mock_llm_service.generate_content.side_effect = Exception("API Error")
        
        from ai_summary.content.genai_helper import humanize_content
        original = "Original content"
        result = humanize_content(original)
        
        assert result == original
    
    def test_humanize_content_uses_heavy_model(self, mock_llm_service):
        """humanize_content uses heavy model tier."""
        mock_response = Mock()
        mock_response.text = "Humanized content"
        mock_llm_service.generate_content.return_value = mock_response
        
        from ai_summary.content.genai_helper import humanize_content
        humanize_content("Content")
        
        call_args = mock_llm_service.generate_content.call_args
        assert call_args[1]['model_tier'] == 'heavy'


class TestFindRelevantTagsWithLlm:
    """Tests for find_relevant_tags_with_llm function."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Mock the LLM service."""
        with patch('ai_summary.content.genai_helper.llm_service') as mock:
            yield mock
    
    @pytest.fixture
    def available_tags(self):
        """Sample available tags."""
        return [
            {'name': 'AI'},
            {'name': 'Technology'},
            {'name': 'Apple'},
            {'name': 'summary'},  # Should be excluded
        ]
    
    def test_find_relevant_tags_returns_matching_tags(self, mock_llm_service, available_tags):
        """find_relevant_tags_with_llm returns matching tag objects."""
        mock_response = Mock()
        mock_response.text = "ai, technology"
        mock_llm_service.generate_content.return_value = mock_response
        
        from ai_summary.content.genai_helper import find_relevant_tags_with_llm
        result = find_relevant_tags_with_llm("AI Article", "Content about AI", available_tags)
        
        tag_names = [t['name'] for t in result]
        assert 'AI' in tag_names
        assert 'Technology' in tag_names
    
    def test_find_relevant_tags_returns_empty_for_none(self, mock_llm_service, available_tags):
        """find_relevant_tags_with_llm returns empty list for 'none' response."""
        mock_response = Mock()
        mock_response.text = "none"
        mock_llm_service.generate_content.return_value = mock_response
        
        from ai_summary.content.genai_helper import find_relevant_tags_with_llm
        result = find_relevant_tags_with_llm("Unrelated", "Content", available_tags)
        
        assert result == []
    
    def test_find_relevant_tags_uses_low_temperature(self, mock_llm_service, available_tags):
        """find_relevant_tags_with_llm uses low temperature for consistency."""
        mock_response = Mock()
        mock_response.text = "ai"
        mock_llm_service.generate_content.return_value = mock_response
        
        from ai_summary.content.genai_helper import find_relevant_tags_with_llm
        find_relevant_tags_with_llm("Title", "Content", available_tags)
        
        call_args = mock_llm_service.generate_content.call_args
        assert call_args[1]['temperature'] == 0.1
    
    def test_find_relevant_tags_returns_empty_on_error(self, mock_llm_service, available_tags):
        """find_relevant_tags_with_llm returns empty list on error."""
        mock_llm_service.generate_content.side_effect = Exception("API Error")
        
        from ai_summary.content.genai_helper import find_relevant_tags_with_llm
        result = find_relevant_tags_with_llm("Title", "Content", available_tags)
        
        assert result == []


class TestFetchWebContextForArticle:
    """Tests for fetch_web_context_for_article function."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Mock the LLM service."""
        with patch('ai_summary.content.genai_helper.llm_service') as mock:
            yield mock
    
    def test_fetch_web_context_returns_search_queries(self, mock_llm_service):
        """fetch_web_context_for_article returns list of search queries."""
        mock_response = Mock()
        mock_response.text = "query 1\nquery 2\nquery 3"
        mock_llm_service.generate_content.return_value = mock_response
        
        from ai_summary.content.genai_helper import fetch_web_context_for_article
        result = fetch_web_context_for_article("Title", "Content snippet")
        
        assert len(result) <= 3
        assert "query 1" in result
    
    def test_fetch_web_context_limits_to_3_queries(self, mock_llm_service):
        """fetch_web_context_for_article limits to 3 queries max."""
        mock_response = Mock()
        mock_response.text = "query 1\nquery 2\nquery 3\nquery 4\nquery 5"
        mock_llm_service.generate_content.return_value = mock_response
        
        from ai_summary.content.genai_helper import fetch_web_context_for_article
        result = fetch_web_context_for_article("Title", "Content")
        
        assert len(result) <= 3
    
    def test_fetch_web_context_returns_empty_on_error(self, mock_llm_service):
        """fetch_web_context_for_article returns empty list on error."""
        mock_llm_service.generate_content.side_effect = Exception("API Error")
        
        from ai_summary.content.genai_helper import fetch_web_context_for_article
        result = fetch_web_context_for_article("Title", "Content")
        
        assert result == []
    
    def test_fetch_web_context_uses_light_model(self, mock_llm_service):
        """fetch_web_context_for_article uses light model for efficiency."""
        mock_response = Mock()
        mock_response.text = "query"
        mock_llm_service.generate_content.return_value = mock_response
        
        from ai_summary.content.genai_helper import fetch_web_context_for_article
        fetch_web_context_for_article("Title", "Content")
        
        call_args = mock_llm_service.generate_content.call_args
        assert call_args[1]['model_tier'] == 'light'
