#!/usr/bin/env python3
"""
Basic functionality test for LLM provider system.
This script tests core functionality without requiring external dependencies.
"""

import os
import sys
import unittest
from unittest.mock import patch, Mock, MagicMock

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_basic_imports():
    """Test that basic imports work"""
    try:
        # Set up minimal environment
        os.environ['GEMINI_API_KEY'] = 'test_key'
        os.environ['HEAVY_MODELS'] = 'gemini-2.5-pro-exp-03-25'
        os.environ['LIGHT_MODELS'] = 'gemini-1.5-flash'
        
        # Mock external dependencies
        with patch('llm_provider.load_dotenv'):
            with patch('llm_provider.genai.configure'):
                with patch('llm_provider.genai.GenerativeModel'):
                    # Try to import LLM components
                    from llm_provider import LLMService, LLMResponse, GeminiProvider
                    print("✅ Successfully imported LLM provider components")
                    
                    # Test basic service creation
                    service = LLMService()
                    print("✅ Successfully created LLM service")
                    
                    # Test basic response creation
                    response = LLMResponse("test text", None)
                    print("✅ Successfully created LLM response")
                    
                    return True
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_model_switching_logic():
    """Test model switching logic"""
    try:
        os.environ['HEAVY_MODELS'] = 'model1,model2'
        os.environ['LIGHT_MODELS'] = 'model3,model4'
        
        with patch('llm_provider.load_dotenv'):
            with patch('llm_provider.genai.configure'):
                with patch('llm_provider.genai.GenerativeModel'):
                    from llm_provider import LLMService
                    
                    service = LLMService()
                    
                    # Test model configuration
                    assert service.heavy_models == ['model1', 'model2']
                    assert service.light_models == ['model3', 'model4']
                    
                    print("✅ Model switching configuration works")
                    return True
    except Exception as e:
        print(f"❌ Model switching test failed: {e}")
        return False

def test_provider_fallback_logic():
    """Test provider fallback logic"""
    try:
        with patch('llm_provider.load_dotenv'):
            with patch('llm_provider.genai.configure'):
                with patch('llm_provider.genai.GenerativeModel'):
                    from llm_provider import LLMService, GeminiProvider
                    
                    # Test rate limit detection
                    provider = GeminiProvider("test_key", "test_model")
                    
                    # Test various rate limit errors
                    rate_limit_errors = [
                        Exception("quota exceeded"),
                        Exception("resource exhausted"),
                        Exception("rate limit exceeded"),
                        Exception("too many requests")
                    ]
                    
                    for error in rate_limit_errors:
                        assert provider.is_rate_limited(error), f"Should detect rate limit: {error}"
                    
                    # Test non-rate limit error
                    normal_error = Exception("invalid request")
                    assert not provider.is_rate_limited(normal_error), "Should not detect as rate limit"
                    
                    print("✅ Provider fallback logic works")
                    return True
    except Exception as e:
        print(f"❌ Provider fallback test failed: {e}")
        return False

def test_genai_helper_integration():
    """Test genai_helper integration"""
    try:
        # Mock the LLM service
        with patch('llm_provider.load_dotenv'):
            with patch('llm_provider.genai.configure'):
                with patch('llm_provider.genai.GenerativeModel') as mock_model:
                    # Mock model response
                    mock_response = Mock()
                    mock_response.text = "Test Title\nTest content"
                    mock_model.return_value.generate_content.return_value = mock_response
                    
                    # Import genai_helper after mocking
                    from genai_helper import summarize_text
                    
                    # Test function
                    title, content = summarize_text("Test", "Test content")
                    
                    assert title == "Test Title"
                    assert content == "Test content"
                    
                    print("✅ genai_helper integration works")
                    return True
    except Exception as e:
        print(f"❌ genai_helper integration test failed: {e}")
        return False

def main():
    """Run all basic tests"""
    print("🧪 Running Basic LLM Provider Tests...")
    print("=" * 50)
    
    tests = [
        test_basic_imports,
        test_model_switching_logic,
        test_provider_fallback_logic,
        test_genai_helper_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        print(f"\n🔍 Running {test.__name__}...")
        if test():
            passed += 1
        else:
            print(f"❌ {test.__name__} failed")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All basic tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())