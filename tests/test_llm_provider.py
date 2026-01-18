"""Unit tests for llm_provider module."""
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestLLMResponse:
    """Tests for LLMResponse class."""
    
    def test_llm_response_init_with_text_only(self):
        """LLMResponse initializes with text only."""
        from ai_summary.core.llm_provider import LLMResponse
        
        response = LLMResponse("Test response text")
        
        assert response.text == "Test response text"
        assert response.raw_response is None
    
    def test_llm_response_init_with_raw_response(self):
        """LLMResponse initializes with text and raw response."""
        from ai_summary.core.llm_provider import LLMResponse
        
        raw = {"key": "value"}
        response = LLMResponse("Test text", raw)
        
        assert response.text == "Test text"
        assert response.raw_response == raw


class TestGeminiProviderRateLimiting:
    """Tests for Gemini provider rate limit detection."""
    
    @pytest.fixture
    def gemini_provider(self):
        """Create a mocked Gemini provider."""
        with patch('ai_summary.core.llm_provider.genai.Client'):
            from ai_summary.core.llm_provider import GeminiProvider
            provider = GeminiProvider(
                api_key="test-key",
                model_name="gemini-pro",
                generation_config={}
            )
            return provider
    
    @pytest.mark.parametrize("error_msg,expected", [
        ("429 Too Many Requests", True),
        ("quota exceeded", True),
        ("Quota Exceeded for this API", True),
        ("rate limit reached", True),
        ("resource exhausted", True),
        ("RESOURCE_EXHAUSTED", False),  # Underscore doesn't match space
        ("too many requests", True),
        ("exceeded your current quota", True),
        ("Invalid API key", False),
        ("Network error", False),
        ("Model not found", False),
        ("Internal server error", False),
    ])
    def test_is_rate_limited(self, gemini_provider, error_msg, expected):
        """Test rate limit detection for various error messages."""
        error = Exception(error_msg)
        assert gemini_provider.is_rate_limited(error) == expected


class TestLiteLLMProviderRateLimiting:
    """Tests for LiteLLM provider rate limit detection."""
    
    @pytest.fixture
    def litellm_provider(self):
        """Create a mocked LiteLLM provider."""
        with patch('ai_summary.core.llm_provider.litellm'):
            from ai_summary.core.llm_provider import LiteLLMProvider
            provider = LiteLLMProvider(
                api_key="test-key",
                model_name="gpt-4",
                generation_config={}
            )
            return provider
    
    @pytest.mark.parametrize("error_msg,expected", [
        ("rate limit exceeded", True),
        ("429", True),
        ("too many requests", True),
        ("quota exceeded", True),
        ("Authentication failed", False),
        ("Connection timeout", False),
    ])
    def test_is_rate_limited(self, litellm_provider, error_msg, expected):
        """Test rate limit detection for various error messages."""
        error = Exception(error_msg)
        assert litellm_provider.is_rate_limited(error) == expected


class TestOpenRouterProviderRateLimiting:
    """Tests for OpenRouter provider rate limit detection."""
    
    @pytest.fixture
    def openrouter_provider(self):
        """Create a mocked OpenRouter provider."""
        with patch('ai_summary.core.llm_provider.OpenAI'):
            with patch('ai_summary.core.llm_provider.OPENAI_AVAILABLE', True):
                from ai_summary.core.llm_provider import OpenRouterProvider
                provider = OpenRouterProvider(
                    api_key="test-key",
                    model_name="google/gemini-pro",
                    generation_config={}
                )
                return provider
    
    @pytest.mark.parametrize("error_msg,expected", [
        ("rate limit", True),
        ("too many requests", True),
        ("429", True),
        ("quota exceeded", True),
        ("Invalid model", False),
        ("Server error", False),
    ])
    def test_is_rate_limited(self, openrouter_provider, error_msg, expected):
        """Test rate limit detection for various error messages."""
        error = Exception(error_msg)
        assert openrouter_provider.is_rate_limited(error) == expected


class TestGeminiProviderContentGeneration:
    """Tests for Gemini provider content generation."""
    
    @pytest.fixture
    def gemini_provider(self):
        """Create a mocked Gemini provider."""
        with patch('ai_summary.core.llm_provider.genai.Client') as mock_client:
            from ai_summary.core.llm_provider import GeminiProvider
            provider = GeminiProvider(
                api_key="test-key",
                model_name="gemini-pro",
                generation_config={"temperature": 0.7}
            )
            provider.client = mock_client.return_value
            return provider
    
    def test_generate_content_with_string_prompt(self, gemini_provider):
        """Generate content with simple string prompt."""
        mock_response = Mock()
        mock_response.text = "Generated response"
        gemini_provider.client.models.generate_content.return_value = mock_response
        
        result = gemini_provider.generate_content("Test prompt")
        
        assert result.text == "Generated response"
        gemini_provider.client.models.generate_content.assert_called_once()
    
    def test_generate_content_error_propagates(self, gemini_provider):
        """Errors from API are propagated."""
        gemini_provider.client.models.generate_content.side_effect = Exception("API Error")
        
        with pytest.raises(Exception, match="API Error"):
            gemini_provider.generate_content("Test prompt")


class TestGeminiProviderChunking:
    """Tests for Gemini provider content chunking."""
    
    @pytest.fixture
    def gemini_provider(self):
        """Create a mocked Gemini provider."""
        with patch('ai_summary.core.llm_provider.genai.Client'):
            from ai_summary.core.llm_provider import GeminiProvider
            provider = GeminiProvider(
                api_key="test-key",
                model_name="gemini-pro",
                generation_config={}
            )
            provider.max_input_tokens = 100  # Small limit for testing
            return provider
    
    def test_chunk_content_short_string(self, gemini_provider):
        """Short content is not chunked."""
        content = "Short content"
        chunks = gemini_provider._chunk_content(content)
        
        assert len(chunks) == 1
        assert chunks[0] == content
    
    def test_chunk_content_dict_with_text(self, gemini_provider):
        """Dict with text key is processed correctly."""
        content = {"text": "Test content"}
        chunks = gemini_provider._chunk_content(content)
        
        assert len(chunks) >= 1
        assert chunks[0]["text"] == "Test content"
    
    def test_chunk_content_non_string_passthrough(self, gemini_provider):
        """Non-string, non-dict, non-list content passes through."""
        content = 12345
        chunks = gemini_provider._chunk_content(content)
        
        assert chunks == [12345]


class TestLLMService:
    """Tests for LLMService class."""
    
    @pytest.fixture
    def mock_providers(self):
        """Create mock providers for testing."""
        with patch.dict('os.environ', {
            'GEMINI_API_KEY': 'test-gemini-key',
            'OPENROUTER_API_KEY': 'test-openrouter-key',
            'LITELLM_API_KEY': 'test-litellm-key',
            'LITELLM_MODEL': 'gpt-4',
            'DEFAULT_LLM_PROVIDER': 'gemini',
            'HEAVY_MODELS': 'gemini-pro,gpt-4',
            'LIGHT_MODELS': 'gemini-flash,gpt-3.5-turbo',
        }):
            with patch('ai_summary.core.llm_provider.genai.Client'):
                with patch('ai_summary.core.llm_provider.OpenAI'):
                    with patch('ai_summary.core.llm_provider.litellm'):
                        yield
    
    def test_get_fallback_provider_returns_different_provider(self):
        """_get_fallback_provider returns a different provider."""
        with patch('ai_summary.core.llm_provider.genai.Client'):
            with patch('ai_summary.core.llm_provider.OpenAI'):
                with patch('ai_summary.core.llm_provider.litellm'):
                    from ai_summary.core.llm_provider import LLMService
                    
                    service = LLMService.__new__(LLMService)
                    service.providers = {
                        'gemini': Mock(),
                        'openrouter': Mock(),
                    }
                    
                    fallback = service._get_fallback_provider('gemini')
                    
                    assert fallback == 'openrouter'
    
    def test_get_fallback_provider_returns_none_if_no_alternatives(self):
        """_get_fallback_provider returns None if no alternatives."""
        with patch('ai_summary.core.llm_provider.genai.Client'):
            from ai_summary.core.llm_provider import LLMService
            
            service = LLMService.__new__(LLMService)
            service.providers = {'gemini': Mock()}
            
            fallback = service._get_fallback_provider('gemini')
            
            assert fallback is None


class TestLLMServiceContentGeneration:
    """Tests for LLMService content generation with fallback."""
    
    def test_generate_content_uses_specified_provider(self):
        """generate_content uses the specified provider."""
        from ai_summary.core.llm_provider import LLMService, LLMResponse
        
        service = LLMService.__new__(LLMService)
        mock_provider = Mock()
        mock_provider.generate_content.return_value = LLMResponse("Test response")
        mock_provider.model_name = "test-model"
        
        service.providers = {'test': mock_provider}
        service.default_provider = 'test'
        service.heavy_models = ['heavy-model']
        service.light_models = ['light-model']
        
        result = service.generate_content("Test prompt", provider='test')
        
        assert result.text == "Test response"
        mock_provider.generate_content.assert_called()
    
    def test_generate_content_falls_back_on_rate_limit(self):
        """generate_content tries next model on rate limit."""
        from ai_summary.core.llm_provider import LLMService, LLMResponse
        
        service = LLMService.__new__(LLMService)
        mock_provider = Mock()
        mock_provider.is_rate_limited.return_value = True
        mock_provider.model_name = "test-model"
        
        # First call fails with rate limit, second succeeds
        mock_provider.generate_content.side_effect = [
            Exception("rate limit"),
            LLMResponse("Success after retry")
        ]
        
        service.providers = {'test': mock_provider}
        service.default_provider = 'test'
        service.heavy_models = ['model1', 'model2']
        service.light_models = ['light-model']
        
        with patch('time.sleep'):  # Skip sleep during test
            result = service.generate_content("Test prompt", provider='test', model_tier='heavy')
        
        assert result.text == "Success after retry"
    
    def test_generate_content_raises_when_fallback_disabled(self):
        """generate_content raises error when fallback is disabled."""
        from ai_summary.core.llm_provider import LLMService
        
        service = LLMService.__new__(LLMService)
        mock_provider = Mock()
        mock_provider.is_rate_limited.return_value = False
        mock_provider.generate_content.side_effect = Exception("API Error")
        mock_provider.model_name = "test-model"
        
        service.providers = {'test': mock_provider}
        service.default_provider = 'test'
        service.heavy_models = ['model1']
        service.light_models = ['light-model']
        
        with pytest.raises(Exception, match="API Error"):
            service.generate_content("Test prompt", provider='test', fallback=False)


class TestLLMServiceMediaGeneration:
    """Tests for LLMService media content generation."""
    
    def test_generate_content_with_media_uses_provider(self):
        """generate_content_with_media uses the specified provider."""
        from ai_summary.core.llm_provider import LLMService, LLMResponse
        
        service = LLMService.__new__(LLMService)
        mock_provider = Mock()
        mock_provider.generate_content_with_media.return_value = LLMResponse("Media response")
        
        service.providers = {'test': mock_provider}
        service.default_provider = 'test'
        
        result = service.generate_content_with_media("Prompt", "/path/to/file.mp3")
        
        assert result.text == "Media response"
        mock_provider.generate_content_with_media.assert_called_once_with("Prompt", "/path/to/file.mp3")
    
    def test_generate_content_with_media_fallback_on_rate_limit(self):
        """generate_content_with_media falls back on rate limit."""
        from ai_summary.core.llm_provider import LLMService, LLMResponse
        
        service = LLMService.__new__(LLMService)
        
        primary = Mock()
        primary.is_rate_limited.return_value = True
        primary.generate_content_with_media.side_effect = Exception("rate limit")
        
        fallback = Mock()
        fallback.generate_content_with_media.return_value = LLMResponse("Fallback response")
        
        service.providers = {'primary': primary, 'fallback': fallback}
        service.default_provider = 'primary'
        
        result = service.generate_content_with_media("Prompt", "/path/to/file.mp3")
        
        assert result.text == "Fallback response"
