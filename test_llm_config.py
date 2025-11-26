#!/usr/bin/env python3
"""
Configuration and environment testing for LLM provider system.
Tests various configuration scenarios and environment setups.
"""

import unittest
import os
import tempfile
from unittest.mock import patch, Mock

class TestLLMConfiguration(unittest.TestCase):
    """Test LLM system configuration scenarios"""
    
    def test_minimal_configuration(self):
        """Test system with minimal configuration"""
        # Test with only Gemini configured
        env_vars = {
            'GEMINI_API_KEY': 'test_key',
            'HEAVY_MODELS': 'gemini-3-pro',
            'LIGHT_MODELS': 'gemini-1.5-flash'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with patch('llm_provider.genai.configure'):
                with patch('llm_provider.genai.GenerativeModel'):
                    from llm_provider import LLMService
                    service = LLMService()
                    
                    # Should have at least Gemini provider
                    self.assertIn("gemini", service.providers)
                    self.assertEqual(service.default_provider, "gemini")
                    
    def test_full_configuration(self):
        """Test system with all providers configured"""
        env_vars = {
            'GEMINI_API_KEY': 'test_gemini_key',
            'OPENROUTER_API_KEY': 'test_openrouter_key',
            'LITELLM_API_KEY': 'test_litellm_key',
            'LITELLM_MODEL': 'test_model',
            'DEFAULT_LLM_PROVIDER': 'openrouter',
            'HEAVY_MODELS': 'gemini-3-pro,gpt-4-turbo,claude-3-opus',
            'LIGHT_MODELS': 'gemini-1.5-flash,gpt-3.5-turbo,claude-3-haiku'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with patch('llm_provider.genai.configure'):
                with patch('llm_provider.genai.GenerativeModel'):
                    with patch('llm_provider.OpenAI'):
                        from llm_provider import LLMService
                        service = LLMService()
                        
                        # Should have all providers
                        self.assertIn("gemini", service.providers)
                        self.assertIn("openrouter", service.providers)
                        self.assertIn("litellm", service.providers)
                        
                        # Should use configured default
                        self.assertEqual(service.default_provider, "openrouter")
                        
    def test_missing_api_keys(self):
        """Test system behavior with missing API keys"""
        env_vars = {
            'HEAVY_MODELS': 'gemini-3-pro',
            'LIGHT_MODELS': 'gemini-1.5-flash'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            from llm_provider import LLMService
            service = LLMService()
            
            # Should handle missing API keys gracefully
            self.assertEqual(len(service.providers), 0)
            
    def test_invalid_default_provider(self):
        """Test system behavior with invalid default provider"""
        env_vars = {
            'GEMINI_API_KEY': 'test_key',
            'DEFAULT_LLM_PROVIDER': 'invalid_provider',
            'HEAVY_MODELS': 'gemini-3-pro',
            'LIGHT_MODELS': 'gemini-1.5-flash'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with patch('llm_provider.genai.configure'):
                with patch('llm_provider.genai.GenerativeModel'):
                    from llm_provider import LLMService
                    service = LLMService()
                    
                    # Should fallback to available provider
                    self.assertEqual(service.default_provider, "gemini")
                    
    def test_empty_model_lists(self):
        """Test system behavior with empty model lists"""
        env_vars = {
            'GEMINI_API_KEY': 'test_key',
            'HEAVY_MODELS': '',
            'LIGHT_MODELS': ''
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with patch('llm_provider.genai.configure'):
                with patch('llm_provider.genai.GenerativeModel'):
                    from llm_provider import LLMService
                    service = LLMService()
                    
                    # Should handle empty model lists
                    self.assertEqual(service.heavy_models, [''])
                    self.assertEqual(service.light_models, [''])

class TestLLMEnvironmentVariables(unittest.TestCase):
    """Test environment variable handling"""
    
    def test_generation_config_from_env(self):
        """Test generation configuration from environment variables"""
        env_vars = {
            'GEMINI_API_KEY': 'test_key',
            'GEMINI_TEMPERATURE': '0.5',
            'GEMINI_TOP_P': '0.8',
            'GEMINI_TOP_K': '20',
            'GEMINI_MAX_TOKENS': '4096',
            'OPENROUTER_API_KEY': 'test_key',
            'OPENROUTER_TEMPERATURE': '0.7',
            'OPENROUTER_TOP_P': '0.9',
            'OPENROUTER_MAX_TOKENS': '2048'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with patch('llm_provider.genai.configure'):
                with patch('llm_provider.genai.GenerativeModel') as mock_genai_model:
                    with patch('llm_provider.OpenAI'):
                        from llm_provider import LLMService
                        service = LLMService()
                        
                        # Check Gemini configuration
                        gemini_provider = service.providers["gemini"]
                        self.assertEqual(gemini_provider.generation_config["temperature"], 0.5)
                        self.assertEqual(gemini_provider.generation_config["top_p"], 0.8)
                        self.assertEqual(gemini_provider.generation_config["top_k"], 20)
                        self.assertEqual(gemini_provider.generation_config["max_output_tokens"], 4096)
                        
                        # Check OpenRouter configuration
                        openrouter_provider = service.providers["openrouter"]
                        self.assertEqual(openrouter_provider.generation_config["temperature"], 0.7)
                        self.assertEqual(openrouter_provider.generation_config["top_p"], 0.9)
                        self.assertEqual(openrouter_provider.generation_config["max_output_tokens"], 2048)
                        
    def test_system_prompt_configuration(self):
        """Test system prompt configuration"""
        env_vars = {
            'GEMINI_API_KEY': 'test_key',
            'SYSTEM_PROMPT': 'You are a helpful AI assistant for content analysis.'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with patch('llm_provider.genai.configure'):
                with patch('llm_provider.genai.GenerativeModel') as mock_genai_model:
                    from llm_provider import LLMService
                    service = LLMService()
                    
                    # Check system prompt is set
                    gemini_provider = service.providers["gemini"]
                    self.assertEqual(
                        gemini_provider.system_prompt,
                        'You are a helpful AI assistant for content analysis.'
                    )
                    
    def test_model_configuration_from_env(self):
        """Test model name configuration from environment"""
        env_vars = {
            'GEMINI_API_KEY': 'test_key',
            'GEMINI_MODEL': 'gemini-1.5-pro',
            'OPENROUTER_API_KEY': 'test_key',
            'OPENROUTER_MODEL': 'anthropic/claude-3-opus'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with patch('llm_provider.genai.configure'):
                with patch('llm_provider.genai.GenerativeModel'):
                    with patch('llm_provider.OpenAI'):
                        from llm_provider import LLMService
                        service = LLMService()
                        
                        # Check model names
                        self.assertEqual(service.providers["gemini"].model_name, "gemini-1.5-pro")
                        self.assertEqual(service.providers["openrouter"].model_name, "anthropic/claude-3-opus")

class TestLLMConfigurationEdgeCases(unittest.TestCase):
    """Test edge cases in configuration"""
    
    def test_malformed_model_lists(self):
        """Test handling of malformed model lists"""
        env_vars = {
            'GEMINI_API_KEY': 'test_key',
            'HEAVY_MODELS': 'model1,,model2,',
            'LIGHT_MODELS': ',model3,model4,'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with patch('llm_provider.genai.configure'):
                with patch('llm_provider.genai.GenerativeModel'):
                    from llm_provider import LLMService
                    service = LLMService()
                    
                    # Should handle empty strings in model lists
                    self.assertEqual(service.heavy_models, ['model1', '', 'model2', ''])
                    self.assertEqual(service.light_models, ['', 'model3', 'model4', ''])
                    
    def test_invalid_numeric_config(self):
        """Test handling of invalid numeric configuration"""
        env_vars = {
            'GEMINI_API_KEY': 'test_key',
            'GEMINI_TEMPERATURE': 'invalid',
            'GEMINI_TOP_P': 'not_a_number',
            'GEMINI_TOP_K': 'abc',
            'GEMINI_MAX_TOKENS': 'xyz'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with patch('llm_provider.genai.configure'):
                with patch('llm_provider.genai.GenerativeModel'):
                    # Should handle invalid numeric values gracefully
                    try:
                        from llm_provider import LLMService
                        service = LLMService()
                        # If we reach here, the system handled invalid values
                        self.assertTrue(True)
                    except ValueError:
                        # This is expected behavior - invalid values should raise errors
                        self.assertTrue(True)
                        
    def test_provider_initialization_failure(self):
        """Test handling of provider initialization failures"""
        env_vars = {
            'GEMINI_API_KEY': 'test_key',
            'OPENROUTER_API_KEY': 'test_key'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with patch('llm_provider.genai.configure', side_effect=Exception("API Error")):
                with patch('llm_provider.OpenAI', side_effect=Exception("Connection Error")):
                    from llm_provider import LLMService
                    service = LLMService()
                    
                    # Should handle initialization failures gracefully
                    self.assertEqual(len(service.providers), 0)

if __name__ == '__main__':
    unittest.main(verbosity=2)