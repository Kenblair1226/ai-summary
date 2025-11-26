#!/usr/bin/env python3
"""
Integration tests for LLM provider system with actual genai_helper functions.
Tests the integration between the LLM service and the application functions.
"""

import unittest
import os
import tempfile
import json
from unittest.mock import patch, Mock, MagicMock

# Set up test environment
os.environ['GEMINI_API_KEY'] = 'test_gemini_key'
os.environ['OPENROUTER_API_KEY'] = 'test_openrouter_key'
os.environ['LITELLM_API_KEY'] = 'test_litellm_key'
os.environ['LITELLM_MODEL'] = 'test_model'
os.environ['HEAVY_MODELS'] = 'gemini-3-pro,gpt-4-turbo'
os.environ['LIGHT_MODELS'] = 'gemini-1.5-flash,gpt-3.5-turbo'

class TestGenaiHelperIntegration(unittest.TestCase):
    """Test integration with genai_helper functions"""
    
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    def test_summarize_text_integration(self, mock_genai_model, mock_genai_configure):
        """Test summarize_text function integration"""
        # Mock the model response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "AI技術發展趨勢\n人工智能技術在近年來發展迅速，影響各個行業的運作模式。"
        mock_model.generate_content.return_value = mock_response
        mock_genai_model.return_value = mock_model
        
        # Import and test the function
        from genai_helper import summarize_text
        
        title, content = summarize_text("AI Technology", "Discussion about AI development")
        
        # Verify the function works
        self.assertEqual(title, "AI技術發展趨勢")
        self.assertIn("人工智能技術", content)
        
        # Verify heavy model tier was used
        mock_model.generate_content.assert_called_once()
        
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    def test_generate_slug_integration(self, mock_genai_model, mock_genai_configure):
        """Test generate_slug function integration"""
        # Mock the model response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "ai-technology-trends-2024"
        mock_model.generate_content.return_value = mock_response
        mock_genai_model.return_value = mock_model
        
        # Import and test the function
        from genai_helper import generate_slug
        
        slug = generate_slug("AI Technology Trends 2024")
        
        # Verify the function works
        self.assertEqual(slug, "ai-technology-trends-2024")
        
        # Verify light model tier was used
        mock_model.generate_content.assert_called_once()
        
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    @patch('llm_provider.genai.upload_file')
    def test_summarize_mp3_integration(self, mock_upload_file, mock_genai_model, mock_genai_configure):
        """Test summarize_mp3 function integration"""
        # Mock file upload
        mock_file = Mock()
        mock_upload_file.return_value = mock_file
        
        # Mock the model response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "播客討論摘要\n本集討論了人工智能的最新發展趨勢。"
        mock_model.generate_content.return_value = mock_response
        mock_genai_model.return_value = mock_model
        
        # Create temp audio file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_file_path = temp_file.name
            
        try:
            # Import and test the function
            from genai_helper import summarize_mp3
            
            response = summarize_mp3(temp_file_path)
            
            # Verify the function works
            self.assertEqual(response.text, "播客討論摘要\n本集討論了人工智能的最新發展趨勢。")
            
            # Verify media upload was called
            mock_upload_file.assert_called_once_with(temp_file_path)
            
        finally:
            os.unlink(temp_file_path)
            
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    @patch('llm_provider.genai.upload_file')
    def test_article_mp3_integration(self, mock_upload_file, mock_genai_model, mock_genai_configure):
        """Test article_mp3 function integration"""
        # Mock file upload
        mock_file = Mock()
        mock_upload_file.return_value = mock_file
        
        # Mock the model response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "AI技術深度分析\n<h3>技術發展現況</h3>\n人工智能技術在各領域的應用日益廣泛。"
        mock_model.generate_content.return_value = mock_response
        mock_genai_model.return_value = mock_model
        
        # Create temp audio file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_file_path = temp_file.name
            
        try:
            # Import and test the function
            from genai_helper import article_mp3
            
            title, content = article_mp3("AI Technology Discussion", temp_file_path)
            
            # Verify the function works
            self.assertEqual(title, "AI技術深度分析")
            self.assertIn("<h3>技術發展現況</h3>", content)
            
        finally:
            os.unlink(temp_file_path)
            
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    def test_find_relevant_tags_integration(self, mock_genai_model, mock_genai_configure):
        """Test find_relevant_tags_with_llm function integration"""
        # Mock the model response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "artificial intelligence, machine learning, technology"
        mock_model.generate_content.return_value = mock_response
        mock_genai_model.return_value = mock_model
        
        # Import and test the function
        from genai_helper import find_relevant_tags_with_llm
        
        available_tags = [
            {'name': 'Artificial Intelligence'},
            {'name': 'Machine Learning'},
            {'name': 'Technology'},
            {'name': 'Business'},
            {'name': 'Summary'}
        ]
        
        relevant_tags = find_relevant_tags_with_llm(
            "AI Technology Discussion",
            "Discussion about artificial intelligence and machine learning trends",
            available_tags
        )
        
        # Verify the function works
        self.assertEqual(len(relevant_tags), 3)
        tag_names = [tag['name'] for tag in relevant_tags]
        self.assertIn('Artificial Intelligence', tag_names)
        self.assertIn('Machine Learning', tag_names)
        self.assertIn('Technology', tag_names)

class TestMainFunctionIntegration(unittest.TestCase):
    """Test integration with main.py functions"""
    
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    def test_summarize_article_integration(self, mock_genai_model, mock_genai_configure):
        """Test summarize_article function integration"""
        # Mock the model response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "科技新聞分析\n<h3>市場動向</h3>\n科技產業持續快速發展。"
        mock_model.generate_content.return_value = mock_response
        mock_genai_model.return_value = mock_model
        
        # Import and test the function
        from genai_helper import summarize_article
        
        title, content = summarize_article(
            "Tech Industry News",
            "The technology industry continues to evolve rapidly with new innovations."
        )
        
        # Verify the function works
        self.assertEqual(title, "科技新聞分析")
        self.assertIn("<h3>市場動向</h3>", content)
        
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    def test_humanize_content_integration(self, mock_genai_model, mock_genai_configure):
        """Test humanize_content function integration"""
        # Mock the model response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "這是一個更加自然和人性化的內容版本，使用了更加親切的語調。"
        mock_model.generate_content.return_value = mock_response
        mock_genai_model.return_value = mock_model
        
        # Import and test the function
        from genai_helper import humanize_content
        
        humanized = humanize_content("This is formal AI-generated content.")
        
        # Verify the function works
        self.assertIn("更加自然和人性化", humanized)

class TestProviderFallbackIntegration(unittest.TestCase):
    """Test provider fallback in real application scenarios"""
    
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    @patch('llm_provider.OpenAI')
    def test_genai_helper_fallback_scenario(self, mock_openai, mock_genai_model, mock_genai_configure):
        """Test genai_helper functions with provider fallback"""
        # Mock Gemini with rate limit error
        mock_gemini_model = Mock()
        mock_gemini_model.generate_content.side_effect = Exception("quota exceeded")
        mock_genai_model.return_value = mock_gemini_model
        
        # Mock OpenRouter with success
        mock_openrouter_client = Mock()
        mock_openrouter_response = Mock()
        mock_openrouter_response.choices = [Mock()]
        mock_openrouter_response.choices[0].message.content = "openrouter-fallback-slug"
        mock_openrouter_client.chat.completions.create.return_value = mock_openrouter_response
        mock_openai.return_value = mock_openrouter_client
        
        # Test that generate_slug falls back to OpenRouter
        from genai_helper import generate_slug
        
        slug = generate_slug("Test Title")
        
        # Should get OpenRouter response
        self.assertEqual(slug, "openrouter-fallback-slug")
        
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    @patch('llm_provider.genai.upload_file')
    @patch('llm_provider.OpenAI')
    def test_media_function_fallback(self, mock_openai, mock_upload_file, mock_genai_model, mock_genai_configure):
        """Test media functions with provider fallback"""
        # Mock Gemini with rate limit error
        mock_gemini_model = Mock()
        mock_gemini_model.generate_content.side_effect = Exception("quota exceeded")
        mock_genai_model.return_value = mock_gemini_model
        
        # Mock OpenRouter with success
        mock_openrouter_client = Mock()
        mock_openrouter_response = Mock()
        mock_openrouter_response.choices = [Mock()]
        mock_openrouter_response.choices[0].message.content = "OpenRouter媒體分析\n替代方案成功執行"
        mock_openrouter_client.chat.completions.create.return_value = mock_openrouter_response
        mock_openai.return_value = mock_openrouter_client
        
        # Create temp audio file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_file_path = temp_file.name
            
        try:
            # Test that summarize_mp3 falls back to text-only processing
            from genai_helper import summarize_mp3
            
            response = summarize_mp3(temp_file_path)
            
            # Should get OpenRouter fallback response
            self.assertIn("OpenRouter媒體分析", response.text)
            
        finally:
            os.unlink(temp_file_path)

class TestModelTierIntegration(unittest.TestCase):
    """Test model tier selection in real functions"""
    
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    def test_heavy_tier_functions(self, mock_genai_model, mock_genai_configure):
        """Test functions that should use heavy model tier"""
        # Mock the model
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Heavy model response"
        mock_model.generate_content.return_value = mock_response
        mock_genai_model.return_value = mock_model
        
        # Import functions
        from genai_helper import summarize_text, generate_article, summarize_article, humanize_content
        
        # Test heavy tier functions
        heavy_functions = [
            lambda: summarize_text("Title", "Content"),
            lambda: generate_article("Content"),
            lambda: summarize_article("Title", "Content"),
            lambda: humanize_content("Content")
        ]
        
        for func in heavy_functions:
            with self.subTest(func=func):
                # Reset call count
                mock_model.generate_content.reset_mock()
                
                # Call function
                result = func()
                
                # Verify heavy model was used
                mock_model.generate_content.assert_called_once()
                
    @patch('llm_provider.genai.configure')
    @patch('llm_provider.genai.GenerativeModel')
    def test_light_tier_functions(self, mock_genai_model, mock_genai_configure):
        """Test functions that should use light model tier"""
        # Mock the model
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "light-model-response"
        mock_model.generate_content.return_value = mock_response
        mock_genai_model.return_value = mock_model
        
        # Import functions
        from genai_helper import generate_slug, find_relevant_tags_with_llm
        
        # Test light tier functions
        result = generate_slug("Test Title")
        self.assertEqual(result, "light-model-response")
        
        # Test find_relevant_tags_with_llm
        available_tags = [{'name': 'Test'}]
        mock_response.text = "test"
        result = find_relevant_tags_with_llm("Title", "Content", available_tags)
        self.assertEqual(len(result), 1)

if __name__ == '__main__':
    unittest.main(verbosity=2)