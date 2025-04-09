# Testing Guide for LLM Provider Abstraction

This document provides guidelines for testing the LLM provider abstraction to ensure it functions correctly across different scenarios.

## 1. Unit Testing

### 1.1 Provider Implementation Tests

Test each LLM provider implementation in isolation:

```python
# test_llm_provider.py
import unittest
import os
from unittest.mock import patch, MagicMock
from llm_provider import GeminiProvider, OpenRouterProvider, LLMResponse

class TestGeminiProvider(unittest.TestCase):
    def setUp(self):
        # Set up test environment variables
        os.environ['GEMINI_API_KEY'] = 'test_key'
        self.provider = GeminiProvider(
            api_key='test_key',
            model_name='gemini-test',
            generation_config={
                "temperature": 0.7,
                "top_p": 0.95,
                "max_output_tokens": 1024,
            },
            system_prompt="You are a test assistant."
        )
    
    @patch('google.generativeai.GenerativeModel')
    def test_generate_content(self, mock_model):
        # Mock the Gemini API response
        mock_instance = mock_model.return_value
        mock_response = MagicMock()
        mock_response.text = "Test response"
        mock_instance.generate_content.return_value = mock_response
        
        # Call the method
        response = self.provider.generate_content("Test prompt")
        
        # Assert results
        self.assertEqual(response.text, "Test response")
        mock_instance.generate_content.assert_called_once_with("Test prompt")
    
    def test_is_rate_limited(self):
        # Test rate limit detection
        rate_limit_error = Exception("Resource exhausted: Quota exceeded")
        self.assertTrue(self.provider.is_rate_limited(rate_limit_error))
        
        # Test non-rate limit error
        other_error = Exception("Some other error")
        self.assertFalse(self.provider.is_rate_limited(other_error))

class TestOpenRouterProvider(unittest.TestCase):
    # Similar tests for OpenRouter provider
    pass
```

### 1.2 LLM Service Tests

Test the service layer's functionality:

```python
class TestLLMService(unittest.TestCase):
    def setUp(self):
        # Set up environment and service with mock providers
        self.gemini_provider = MagicMock()
        self.openrouter_provider = MagicMock()
        
        with patch('llm_provider.GeminiProvider', return_value=self.gemini_provider), \
             patch('llm_provider.OpenRouterProvider', return_value=self.openrouter_provider):
            self.service = LLMService()
            # Manually set providers for testing
            self.service.providers = {
                'gemini': self.gemini_provider,
                'openrouter': self.openrouter_provider
            }
            self.service.default_provider = 'gemini'
    
    def test_generate_content_default_provider(self):
        # Set up expected response
        self.gemini_provider.generate_content.return_value = LLMResponse("Gemini response")
        
        # Call the method
        response = self.service.generate_content("Test prompt")
        
        # Assert results
        self.assertEqual(response.text, "Gemini response")
        self.gemini_provider.generate_content.assert_called_once_with("Test prompt")
    
    def test_fallback_on_rate_limit(self):
        # Set up gemini to raise rate limit error
        rate_limit_error = Exception("Resource exhausted: Quota exceeded")
        self.gemini_provider.generate_content.side_effect = rate_limit_error
        self.gemini_provider.is_rate_limited.return_value = True
        
        # Set up openrouter expected response
        self.openrouter_provider.generate_content.return_value = LLMResponse("OpenRouter response")
        
        # Call the method with fallback enabled
        response = self.service.generate_content("Test prompt", fallback=True)
        
        # Assert results
        self.assertEqual(response.text, "OpenRouter response")
        self.gemini_provider.generate_content.assert_called_once_with("Test prompt")
        self.openrouter_provider.generate_content.assert_called_once_with("Test prompt")
    
    def test_specified_provider(self):
        # Set up expected response
        self.openrouter_provider.generate_content.return_value = LLMResponse("OpenRouter response")
        
        # Call the method with specific provider
        response = self.service.generate_content("Test prompt", provider="openrouter")
        
        # Assert results
        self.assertEqual(response.text, "OpenRouter response")
        self.openrouter_provider.generate_content.assert_called_once_with("Test prompt")
        self.gemini_provider.generate_content.assert_not_called()
```

## 2. Integration Testing

### 2.1 Setup Test Environment

Create test configuration with separate API keys and rate limits for testing:

```
# .env.test
GEMINI_API_KEY=your_test_gemini_key
OPENROUTER_API_KEY=your_test_openrouter_key
DEFAULT_LLM_PROVIDER=gemini
```

### 2.2 Basic Integration Tests

Test actual API calls to verify integration:

```python
# integration_tests.py
import os
import unittest
from dotenv import load_dotenv
from llm_provider import llm_service

class TestLLMIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load test environment
        load_dotenv('.env.test')
        
    def test_gemini_integration(self):
        # Test actual Gemini API call
        response = llm_service.generate_content(
            "Write a one-sentence test response.",
            provider="gemini"
        )
        self.assertIsNotNone(response.text)
        self.assertTrue(len(response.text) > 0)
    
    def test_openrouter_integration(self):
        # Test actual OpenRouter API call
        response = llm_service.generate_content(
            "Write a one-sentence test response.",
            provider="openrouter"
        )
        self.assertIsNotNone(response.text)
        self.assertTrue(len(response.text) > 0)
```

### 2.3 Fallback Testing

Test the fallback mechanism with force-triggered rate limits:

```python
def test_forced_fallback():
    # Create a prompt that will trigger rate limits
    # This could be a very large prompt or one that
    # we know will trigger Gemini's rate limits
    large_prompt = "Generate a detailed essay about AI" * 100
    
    try:
        response = llm_service.generate_content(
            large_prompt,
            provider="gemini",
            fallback=True
        )
        print(f"Fallback succeeded: {response.text[:100]}...")
    except Exception as e:
        self.fail(f"Fallback should have prevented exception: {e}")
```

## 3. Application-Level Testing

### 3.1 Test Refactored Functions

Test the refactored helper functions in your application:

```python
# test_genai_helper.py
import unittest
from genai_helper import summarize_text, generate_slug, humanize_content

class TestGenAIHelper(unittest.TestCase):
    def test_summarize_text(self):
        title = "Test Title"
        content = "This is sample content for testing the summarize_text function."
        result_title, result_content = summarize_text(title, content)
        
        self.assertIsNotNone(result_title)
        self.assertIsNotNone(result_content)
        self.assertTrue(len(result_title) > 0)
        self.assertTrue(len(result_content) > 0)
    
    def test_generate_slug(self):
        title = "This is a test title 測試標題"
        slug = generate_slug(title)
        
        self.assertIsNotNone(slug)
        self.assertTrue(len(slug) > 0)
        # Check that slug is URL-friendly
        self.assertTrue(all(c.isalnum() or c == '-' for c in slug))
    
    # Add more tests for each function in genai_helper.py
```

### 3.2 End-to-End Testing

Test complete workflows in your application:

```python
# test_workflow.py
import unittest
from unittest.mock import patch
import os
import uuid
import shutil
from summarize_and_post import post_to_ghost
from genai_helper import article_mp3
from youtube_helper import download_audio_from_youtube

class TestWorkflow(unittest.TestCase):
    def test_youtube_to_article_workflow(self):
        # Use a short, public test video
        video_url = "https://youtu.be/test_video_id"
        
        # Mock YouTube download to avoid actual API calls
        with patch('youtube_helper.download_audio_from_youtube') as mock_download:
            # Set up mock return
            test_dir = f"{uuid.uuid4()}"
            os.makedirs(test_dir, exist_ok=True)
            test_file = f"{test_dir}/test_video.mp3"
            with open(test_file, 'w') as f:
                f.write("Test audio content")
            
            mock_download.return_value = ("Test Video Title", test_file)
            
            # Mock article generation to test provider switching
            with patch('genai_helper.article_mp3') as mock_article:
                mock_article.return_value = ("Generated Title", "Generated Content")
                
                # Mock posting to avoid actual API calls
                with patch('summarize_and_post.post_to_ghost') as mock_post:
                    mock_post.return_value = "https://example.com/test-post"
                    
                    # Execute workflow function (implement this in your code)
                    from main import process_single_video
                    result = process_single_video(video_url)
                    
                    # Assert expected behavior
                    self.assertTrue(result)
                    mock_download.assert_called_once()
                    mock_article.assert_called_once()
                    mock_post.assert_called_once()
            
            # Clean up
            shutil.rmtree(test_dir)
```

## 4. Rate Limit Testing

### 4.1 Simulated Rate Limit Testing

Create a test that simulates rate limit scenarios:

```python
class RateLimitTests(unittest.TestCase):
    def test_gemini_rate_limit_detection(self):
        # Create a provider instance
        provider = GeminiProvider(
            api_key="test_key",
            model_name="gemini-test"
        )
        
        # Test various error messages
        self.assertTrue(provider.is_rate_limited(Exception("Quota exceeded")))
        self.assertTrue(provider.is_rate_limited(Exception("Resource exhausted")))
        self.assertTrue(provider.is_rate_limited(Exception("Too many requests")))
        self.assertFalse(provider.is_rate_limited(Exception("Invalid input")))
    
    @patch('llm_provider.GeminiProvider.generate_content')
    def test_service_fallback_behavior(self, mock_generate):
        # Set up mock to raise rate limit error first call, then succeed second call
        rate_limit_error = Exception("Resource exhausted: Quota exceeded")
        mock_generate.side_effect = [
            rate_limit_error,  # First call fails
            LLMResponse("Success after fallback")  # Second call succeeds
        ]
        
        # Set up the service with mock providers
        service = LLMService()
        service.providers = {
            'gemini': self.gemini_provider,
            'openrouter': self.openrouter_provider
        }
        
        # Test the fallback behavior
        response = service.generate_content("Test prompt", fallback=True)
        self.assertEqual(response.text, "Success after fallback")
```

### 4.2 Load Testing

For production environments, consider load testing to find actual rate limits:

```python
import time
from concurrent.futures import ThreadPoolExecutor

def load_test_provider(provider_name, num_requests=100, concurrency=10):
    """Run a load test against a specific provider"""
    results = {"success": 0, "rate_limited": 0, "other_error": 0}
    
    def single_request(i):
        try:
            response = llm_service.generate_content(
                f"Test request {i}. Generate a short sentence.",
                provider=provider_name,
                fallback=False
            )
            return ("success", response.text)
        except Exception as e:
            error_str = str(e).lower()
            if any(phrase in error_str for phrase in ["rate limit", "quota", "resource exhausted"]):
                return ("rate_limited", str(e))
            return ("other_error", str(e))
    
    # Execute requests in parallel
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        for result_type, message in executor.map(single_request, range(num_requests)):
            results[result_type] += 1
    
    elapsed = time.time() - start_time
    
    # Report results
    print(f"Load test results for {provider_name}:")
    print(f"Total requests: {num_requests}")
    print(f"Successful: {results['success']}")
    print(f"Rate limited: {results['rate_limited']}")
    print(f"Other errors: {results['other_error']}")
    print(f"Total time: {elapsed:.2f} seconds")
    print(f"Requests per second: {num_requests/elapsed:.2f}")
    
    return results
```

## 5. Debugging Tips

When issues arise during testing:

1. Enable detailed logging to trace request/response cycles:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. For OpenRouter debugging, examine raw responses:
   ```python
   response = llm_service.generate_content("Test prompt", provider="openrouter")
   print(f"Raw response: {response.raw_response}")
   ```

3. Test error handling by deliberately triggering errors:
   ```python
   # Invalid API key test
   os.environ['GEMINI_API_KEY'] = 'invalid_key'
   try:
       llm_service.generate_content("Test with invalid key")
   except Exception as e:
       print(f"Expected error: {e}")
   ```

## 6. Environment Setup for Testing

Create a `pytest.ini` file for test configuration:

```ini
[pytest]
env =
    GEMINI_API_KEY=test_key
    OPENROUTER_API_KEY=test_key
    DEFAULT_LLM_PROVIDER=gemini
    TESTING=true
```

Create a test runner script:

```python
# run_tests.py
import unittest
import sys

# Discover and run tests
loader = unittest.TestLoader()
start_dir = 'tests'
suite = loader.discover(start_dir)

runner = unittest.TextTestRunner()
result = runner.run(suite)

# Exit with non-zero code if tests failed
sys.exit(not result.wasSuccessful())