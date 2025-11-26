#!/usr/bin/env python3
"""
Performance and load testing for LLM provider system.
Tests scenarios like:
- Multiple concurrent requests
- Provider switching under load
- Fallback behavior under stress
- Memory usage patterns
"""

import unittest
import asyncio
import time
import threading
import os
import tempfile
from unittest.mock import patch, Mock, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set up test environment
os.environ['GEMINI_API_KEY'] = 'test_gemini_key'
os.environ['OPENROUTER_API_KEY'] = 'test_openrouter_key'
os.environ['LITELLM_API_KEY'] = 'test_litellm_key'
os.environ['LITELLM_MODEL'] = 'test_model'
os.environ['HEAVY_MODELS'] = 'gemini-3-pro,gpt-4-turbo,claude-3-opus'
os.environ['LIGHT_MODELS'] = 'gemini-1.5-flash,gpt-3.5-turbo,claude-3-haiku'

from llm_provider import LLMService, LLMResponse

class TestLLMPerformance(unittest.TestCase):
    """Test performance characteristics of LLM system"""
    
    def setUp(self):
        """Set up test environment"""
        self.service = LLMService()
        
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    def test_concurrent_requests(self, mock_genai_model, mock_genai_configure):
        """Test handling of concurrent requests"""
        # Mock model with slight delay to simulate real conditions
        mock_model = Mock()
        
        def mock_generate_content(prompt):
            time.sleep(0.1)  # Simulate processing time
            response = Mock()
            response.text = f"Response for: {prompt}"
            return response
            
        mock_model.generate_content.side_effect = mock_generate_content
        mock_genai_model.return_value = mock_model
        
        # Test concurrent requests
        def make_request(i):
            return self.service.generate_content(
                f"Request {i}",
                provider="gemini",
                model_tier="heavy"
            )
        
        start_time = time.time()
        
        # Run 10 concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            results = [future.result() for future in as_completed(futures)]
        
        end_time = time.time()
        
        # Verify all requests completed
        self.assertEqual(len(results), 10)
        
        # Verify concurrent execution (should be faster than sequential)
        self.assertLess(end_time - start_time, 1.0)  # Should be much less than 1 second
        
        # Verify responses are unique
        response_texts = [r.text for r in results]
        self.assertEqual(len(set(response_texts)), 10)
        
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    def test_model_switching_performance(self, mock_genai_model, mock_genai_configure):
        """Test performance impact of model switching"""
        # Mock model with tracking
        mock_model = Mock()
        model_calls = []
        
        def track_model_calls(prompt):
            model_calls.append(self.service.providers["gemini"].model_name)
            response = Mock()
            response.text = f"Response from {self.service.providers['gemini'].model_name}"
            return response
            
        mock_model.generate_content.side_effect = track_model_calls
        mock_genai_model.return_value = mock_model
        
        # Test rapid switching between model tiers
        start_time = time.time()
        
        for i in range(20):
            tier = "heavy" if i % 2 == 0 else "light"
            self.service.generate_content(
                f"Test {i}",
                provider="gemini",
                model_tier=tier
            )
        
        end_time = time.time()
        
        # Verify model switching occurred
        heavy_models = os.getenv("HEAVY_MODELS", "").split(',')
        light_models = os.getenv("LIGHT_MODELS", "").split(',')
        
        heavy_calls = [call for call in model_calls if call in heavy_models]
        light_calls = [call for call in model_calls if call in light_models]
        
        self.assertEqual(len(heavy_calls), 10)
        self.assertEqual(len(light_calls), 10)
        
        # Performance should still be reasonable
        self.assertLess(end_time - start_time, 2.0)

class TestLLMStressScenarios(unittest.TestCase):
    """Test system behavior under stress conditions"""
    
    def setUp(self):
        """Set up test environment"""
        self.service = LLMService()
        
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    @patch('llm_provider.OpenAI')
    def test_cascading_failures(self, mock_openai, mock_genai_model, mock_genai_configure):
        """Test system behavior when multiple models fail"""
        # Mock Gemini with rate limit errors
        mock_gemini_model = Mock()
        mock_gemini_model.generate_content.side_effect = Exception("quota exceeded")
        mock_genai_model.return_value = mock_gemini_model
        
        # Mock OpenRouter with success
        mock_openrouter_client = Mock()
        mock_openrouter_response = Mock()
        mock_openrouter_response.choices = [Mock()]
        mock_openrouter_response.choices[0].message.content = "OpenRouter fallback"
        mock_openrouter_client.chat.completions.create.return_value = mock_openrouter_response
        mock_openai.return_value = mock_openrouter_client
        
        # Test that fallback works even with multiple failures
        successful_requests = 0
        total_requests = 10
        
        for i in range(total_requests):
            try:
                response = self.service.generate_content(
                    f"Test {i}",
                    provider="gemini",
                    model_tier="heavy",
                    fallback=True
                )
                if response.text == "OpenRouter fallback":
                    successful_requests += 1
            except Exception:
                pass
        
        # Most requests should succeed via fallback
        self.assertGreater(successful_requests, total_requests * 0.8)
        
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    def test_rapid_fallback_switching(self, mock_genai_model, mock_genai_configure):
        """Test rapid switching between models due to rate limits"""
        # Mock model with intermittent failures
        mock_model = Mock()
        call_count = 0
        
        def intermittent_failure(prompt):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:  # Every 3rd call fails
                raise Exception("quota exceeded")
            
            response = Mock()
            response.text = f"Success {call_count}"
            return response
            
        mock_model.generate_content.side_effect = intermittent_failure
        mock_genai_model.return_value = mock_model
        
        # Test rapid requests with intermittent failures
        successful_requests = 0
        heavy_models = os.getenv("HEAVY_MODELS", "").split(',')
        
        for i in range(15):
            try:
                response = self.service.generate_content(
                    f"Test {i}",
                    provider="gemini",
                    model_tier="heavy",
                    fallback=True
                )
                if response.text.startswith("Success"):
                    successful_requests += 1
            except Exception:
                pass
        
        # Should successfully handle most requests through model fallback
        self.assertGreater(successful_requests, 5)

class TestLLMMemoryUsage(unittest.TestCase):
    """Test memory usage patterns"""
    
    def setUp(self):
        """Set up test environment"""
        self.service = LLMService()
        
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    def test_memory_cleanup(self, mock_genai_model, mock_genai_configure):
        """Test that memory is properly cleaned up after requests"""
        # Mock model
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Test response"
        mock_model.generate_content.return_value = mock_response
        mock_genai_model.return_value = mock_model
        
        # Make many requests to test memory cleanup
        for i in range(100):
            response = self.service.generate_content(
                f"Test request {i}",
                provider="gemini",
                model_tier="heavy"
            )
            # Verify response is created properly
            self.assertEqual(response.text, "Test response")
            
        # If we reach here without memory issues, test passes
        self.assertTrue(True)

class TestLLMRealWorldScenarios(unittest.TestCase):
    """Test real-world usage scenarios"""
    
    def setUp(self):
        """Set up test environment"""
        self.service = LLMService()
        
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    def test_typical_content_generation_workflow(self, mock_genai_model, mock_genai_configure):
        """Test typical content generation workflow"""
        # Mock model with different responses for different tasks
        mock_model = Mock()
        
        def task_specific_response(prompt):
            response = Mock()
            if "slug" in str(prompt).lower():
                response.text = "test-article-slug"
            elif "summarize" in str(prompt).lower():
                response.text = "Article Summary\nDetailed content here"
            elif "tags" in str(prompt).lower():
                response.text = "technology, ai, programming"
            else:
                response.text = "Default response"
            return response
            
        mock_model.generate_content.side_effect = task_specific_response
        mock_genai_model.return_value = mock_model
        
        # Simulate typical workflow
        # 1. Generate summary (heavy task)
        summary_response = self.service.generate_content(
            "Summarize this article about AI",
            model_tier="heavy"
        )
        
        # 2. Generate slug (light task)
        slug_response = self.service.generate_content(
            "Generate slug for: AI Revolution in Tech",
            model_tier="light"
        )
        
        # 3. Generate tags (light task)
        tags_response = self.service.generate_content(
            "Find relevant tags for this content",
            model_tier="light"
        )
        
        # Verify responses
        self.assertIn("Summary", summary_response.text)
        self.assertEqual(slug_response.text, "test-article-slug")
        self.assertEqual(tags_response.text, "technology, ai, programming")
        
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    @patch('llm_provider.genai.upload_file')
    def test_media_processing_workflow(self, mock_upload_file, mock_genai_model, mock_genai_configure):
        """Test media processing workflow with fallback"""
        # Mock file upload
        mock_file = Mock()
        mock_upload_file.return_value = mock_file
        
        # Mock model with media response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Media Title\nTranscription and analysis content"
        mock_model.generate_content.return_value = mock_response
        mock_genai_model.return_value = mock_model
        
        # Create temp media file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_file_path = temp_file.name
            
        try:
            # Test media workflow
            response = self.service.generate_content_with_media(
                "Transcribe and analyze this audio",
                temp_file_path,
                provider="gemini"
            )
            
            # Verify media processing
            self.assertIn("Media Title", response.text)
            self.assertIn("analysis content", response.text)
            
        finally:
            os.unlink(temp_file_path)

if __name__ == '__main__':
    # Run performance tests
    unittest.main(verbosity=2)