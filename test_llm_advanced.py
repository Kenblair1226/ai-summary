#!/usr/bin/env python3
"""
Advanced test suite for LLM provider system with model switching and fallback mechanisms.
Tests the enhanced features including:
- Model switching based on task types (heavy/light)
- Automatic fallback when quota limits are hit
- Provider initialization and configuration
- Media content generation
- Error handling and rate limit detection
"""

import unittest
import unittest.mock as mock
import os
import tempfile
import logging
from unittest.mock import patch, MagicMock, Mock

# Set up test environment
os.environ['GEMINI_API_KEY'] = 'test_gemini_key'
os.environ['OPENROUTER_API_KEY'] = 'test_openrouter_key'
os.environ['LITELLM_API_KEY'] = 'test_litellm_key'
os.environ['LITELLM_MODEL'] = 'test_model'
os.environ['HEAVY_MODELS'] = 'gemini-3-pro,gpt-4-turbo'
os.environ['LIGHT_MODELS'] = 'gemini-1.5-flash,gpt-3.5-turbo'

from llm_provider import LLMService, LLMResponse, GeminiProvider, OpenRouterProvider, LiteLLMProvider

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)

class TestLLMModelSwitching(unittest.TestCase):
    """Test model switching based on task types"""
    
    def setUp(self):
        """Set up test environment"""
        self.service = LLMService()
        
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    def test_heavy_model_selection(self, mock_genai_model, mock_genai_configure):
        """Test that heavy tasks use heavy models"""
        # Mock the model response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Heavy model response"
        mock_model.generate_content.return_value = mock_response
        mock_genai_model.return_value = mock_model
        
        # Test heavy model tier
        response = self.service.generate_content(
            "Complex analysis task",
            provider="gemini",
            model_tier="heavy"
        )
        
        # Verify heavy model was used
        self.assertEqual(response.text, "Heavy model response")
        # Check that the model was set to a heavy model
        heavy_models = os.getenv("HEAVY_MODELS", "").split(',')
        self.assertIn(self.service.providers["gemini"].model_name, heavy_models)
        
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    def test_light_model_selection(self, mock_genai_model, mock_genai_configure):
        """Test that light tasks use light models"""
        # Mock the model response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Light model response"
        mock_model.generate_content.return_value = mock_response
        mock_genai_model.return_value = mock_model
        
        # Test light model tier
        response = self.service.generate_content(
            "Simple task",
            provider="gemini",
            model_tier="light"
        )
        
        # Verify light model was used
        self.assertEqual(response.text, "Light model response")
        # Check that the model was set to a light model
        light_models = os.getenv("LIGHT_MODELS", "").split(',')
        self.assertIn(self.service.providers["gemini"].model_name, light_models)

class TestLLMFallbackMechanism(unittest.TestCase):
    """Test automatic fallback when quota limits are hit"""
    
    def setUp(self):
        """Set up test environment"""
        self.service = LLMService()
        
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    def test_rate_limit_fallback_to_next_model(self, mock_genai_model, mock_genai_configure):
        """Test fallback to next model when rate limited"""
        # Mock the model with rate limit error on first call, success on second
        mock_model = Mock()
        
        # First call raises rate limit error
        rate_limit_error = Exception("quota exceeded")
        success_response = Mock()
        success_response.text = "Success with fallback model"
        
        mock_model.generate_content.side_effect = [rate_limit_error, success_response]
        mock_genai_model.return_value = mock_model
        
        # Test that fallback works
        response = self.service.generate_content(
            "Test prompt",
            provider="gemini",
            model_tier="heavy",
            fallback=True
        )
        
        # Should succeed with fallback model
        self.assertEqual(response.text, "Success with fallback model")
        # Should have called generate_content twice (first failed, second succeeded)
        self.assertEqual(mock_model.generate_content.call_count, 2)
        
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    @patch('llm_provider.OpenAI')
    def test_provider_fallback_on_rate_limit(self, mock_openai, mock_genai_model, mock_genai_configure):
        """Test fallback to different provider when rate limited"""
        # Mock Gemini provider with rate limit error
        mock_gemini_model = Mock()
        mock_gemini_model.generate_content_with_media.side_effect = Exception("quota exceeded")
        mock_genai_model.return_value = mock_gemini_model
        
        # Mock OpenRouter provider with success
        mock_openrouter_client = Mock()
        mock_openrouter_response = Mock()
        mock_openrouter_response.choices = [Mock()]
        mock_openrouter_response.choices[0].message.content = "OpenRouter fallback success"
        mock_openrouter_client.chat.completions.create.return_value = mock_openrouter_response
        mock_openai.return_value = mock_openrouter_client
        
        # Create temp media file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_file_path = temp_file.name
            
        try:
            # Test media generation with fallback
            response = self.service.generate_content_with_media(
                "Analyze this audio",
                temp_file_path,
                provider="gemini",
                fallback=True
            )
            
            # Should fallback to text-only generation with OpenRouter
            self.assertEqual(response.text, "OpenRouter fallback success")
            
        finally:
            # Clean up temp file
            os.unlink(temp_file_path)

class TestProviderInitialization(unittest.TestCase):
    """Test provider initialization and configuration"""
    
    def test_provider_initialization_from_env(self):
        """Test that providers are initialized from environment variables"""
        service = LLMService()
        
        # Check that providers are initialized
        self.assertIn("gemini", service.providers)
        self.assertIn("openrouter", service.providers)
        
    @patch.dict(os.environ, {
        'DEFAULT_LLM_PROVIDER': 'openrouter',
        'GEMINI_API_KEY': 'test_key',
        'OPENROUTER_API_KEY': 'test_key'
    })
    def test_default_provider_selection(self):
        """Test default provider selection from environment"""
        service = LLMService()
        self.assertEqual(service.default_provider, "openrouter")
        
    @patch.dict(os.environ, {
        'HEAVY_MODELS': 'model1,model2,model3',
        'LIGHT_MODELS': 'light1,light2'
    })
    def test_model_configuration(self):
        """Test model configuration from environment"""
        service = LLMService()
        self.assertEqual(service.heavy_models, ['model1', 'model2', 'model3'])
        self.assertEqual(service.light_models, ['light1', 'light2'])

class TestMediaHandling(unittest.TestCase):
    """Test media content generation with different providers"""
    
    def setUp(self):
        """Set up test environment"""
        self.service = LLMService()
        
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    @patch('llm_provider.genai.upload_file')
    def test_gemini_media_handling(self, mock_upload_file, mock_genai_model, mock_genai_configure):
        """Test Gemini media content generation"""
        # Mock file upload and model response
        mock_file = Mock()
        mock_upload_file.return_value = mock_file
        
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Media analysis result"
        mock_model.generate_content.return_value = mock_response
        mock_genai_model.return_value = mock_model
        
        # Create temp media file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_file_path = temp_file.name
            
        try:
            response = self.service.generate_content_with_media(
                "Analyze this audio",
                temp_file_path,
                provider="gemini"
            )
            
            # Verify media was processed
            self.assertEqual(response.text, "Media analysis result")
            mock_upload_file.assert_called_once_with(temp_file_path)
            mock_model.generate_content.assert_called_once_with([mock_file, "Analyze this audio"])
            
        finally:
            os.unlink(temp_file_path)
            
    @patch('llm_provider.OpenAI')
    def test_openrouter_image_handling(self, mock_openai):
        """Test OpenRouter image handling"""
        # Mock OpenRouter client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Image analysis result"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        # Create temp image file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_file.write(b"fake image data")
            temp_file_path = temp_file.name
            
        try:
            response = self.service.generate_content_with_media(
                "Analyze this image",
                temp_file_path,
                provider="openrouter"
            )
            
            # Verify image was processed
            self.assertEqual(response.text, "Image analysis result")
            mock_client.chat.completions.create.assert_called_once()
            
        finally:
            os.unlink(temp_file_path)

class TestErrorHandling(unittest.TestCase):
    """Test error handling and rate limit detection"""
    
    def test_gemini_rate_limit_detection(self):
        """Test Gemini rate limit error detection"""
        provider = GeminiProvider(
            api_key="test_key",
            model_name="test_model"
        )
        
        # Test various rate limit error messages
        rate_limit_errors = [
            Exception("quota exceeded"),
            Exception("resource exhausted"),
            Exception("rate limit exceeded"),
            Exception("too many requests"),
            Exception("429 error"),
            Exception("exceeded your current quota")
        ]
        
        for error in rate_limit_errors:
            with self.subTest(error=str(error)):
                self.assertTrue(provider.is_rate_limited(error))
                
        # Test non-rate limit error
        non_rate_limit_error = Exception("invalid request")
        self.assertFalse(provider.is_rate_limited(non_rate_limit_error))
        
    def test_openrouter_rate_limit_detection(self):
        """Test OpenRouter rate limit error detection"""
        provider = OpenRouterProvider(
            api_key="test_key",
            model_name="test_model"
        )
        
        # Test rate limit error messages
        rate_limit_errors = [
            Exception("rate limit exceeded"),
            Exception("too many requests"),
            Exception("429 error"),
            Exception("quota exceeded")
        ]
        
        for error in rate_limit_errors:
            with self.subTest(error=str(error)):
                self.assertTrue(provider.is_rate_limited(error))
                
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    def test_fallback_disabled(self, mock_genai_model, mock_genai_configure):
        """Test that errors are raised when fallback is disabled"""
        # Mock model with rate limit error
        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception("quota exceeded")
        mock_genai_model.return_value = mock_model
        
        service = LLMService()
        
        # Test that exception is raised when fallback is disabled
        with self.assertRaises(Exception) as context:
            service.generate_content(
                "Test prompt",
                provider="gemini",
                fallback=False
            )
            
        self.assertIn("quota exceeded", str(context.exception))

class TestIntegrationScenarios(unittest.TestCase):
    """Test real-world integration scenarios"""
    
    def setUp(self):
        """Set up test environment"""
        self.service = LLMService()
        
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    def test_genai_helper_integration(self, mock_genai_model, mock_genai_configure):
        """Test integration with genai_helper functions"""
        # Mock the model response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Test Title\nTest content for summarization"
        mock_model.generate_content.return_value = mock_response
        mock_genai_model.return_value = mock_model
        
        # Import after mocking to avoid initialization issues
        from genai_helper import summarize_text
        
        # Test summarize_text function
        title, content = summarize_text("Test Title", "Test content")
        
        # Verify the function works with the LLM service
        self.assertEqual(title, "Test Title")
        self.assertEqual(content, "Test content for summarization")
        
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    def test_model_tier_usage_patterns(self, mock_genai_model, mock_genai_configure):
        """Test typical usage patterns with different model tiers"""
        # Mock model responses
        mock_model = Mock()
        mock_genai_model.return_value = mock_model
        
        # Test heavy model for complex tasks
        heavy_response = Mock()
        heavy_response.text = "Complex analysis result"
        mock_model.generate_content.return_value = heavy_response
        
        response = self.service.generate_content(
            "Analyze this complex topic in detail",
            model_tier="heavy"
        )
        
        self.assertEqual(response.text, "Complex analysis result")
        
        # Test light model for simple tasks
        light_response = Mock()
        light_response.text = "simple-slug-result"
        mock_model.generate_content.return_value = light_response
        
        response = self.service.generate_content(
            "Generate a slug for this title",
            model_tier="light"
        )
        
        self.assertEqual(response.text, "simple-slug-result")

if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)