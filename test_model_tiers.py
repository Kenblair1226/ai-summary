import os
import unittest
from unittest.mock import patch, MagicMock
from llm_provider import LLMService, LLMResponse
from genai_helper import summarize_text, generate_slug

class TestModelTiers(unittest.TestCase):

    def setUp(self):
        # Set up environment variables for model tiers
        os.environ['HEAVY_MODELS'] = 'mock-heavy-1,mock-heavy-2'
        os.environ['LIGHT_MODELS'] = 'mock-light-1,mock-light-2'
        os.environ['LITELLM_API_KEY'] = 'test-key'
        os.environ['LITELLM_MODEL'] = 'test-model'

        # Initialize the LLMService
        self.llm_service = LLMService()

    @patch('llm_provider.llm_service.generate_content')
    def test_heavy_model_tier(self, mock_generate_content):
        # Configure the mock to return a successful response
        mock_generate_content.return_value = LLMResponse('Heavy summary')

        # Call a function that uses the heavy model tier
        summarize_text("Test Title", "Test Content")

        # Assert that generate_content was called with the correct model_tier
        mock_generate_content.assert_called_with(unittest.mock.ANY, model_tier='heavy')

    @patch('llm_provider.llm_service.generate_content')
    def test_light_model_tier(self, mock_generate_content):
        # Configure the mock to return a successful response
        mock_generate_content.return_value = LLMResponse('test-slug')

        # Call a function that uses the light model tier
        generate_slug("Test Title")

        # Assert that generate_content was called with the correct model_tier
        mock_generate_content.assert_called_with(unittest.mock.ANY, model_tier='light')

    @patch('llm_provider.LiteLLMProvider.generate_content')
    def test_fallback_within_tier(self, mock_generate_content):
        # Configure the mock to raise an exception on the first call and return a response on the second
        mock_generate_content.side_effect = [
            Exception("Rate limit error"),
            LLMResponse('Fallback summary')
        ]

        # Call a function that uses the heavy model tier
        response = self.llm_service.generate_content("Test prompt", model_tier="heavy")

        # Assert that the correct response is returned after fallback
        self.assertEqual(response.text, 'Fallback summary')

        # Assert that generate_content was called twice (once for each model in the tier)
        self.assertEqual(mock_generate_content.call_count, 2)

    @patch('llm_provider.LiteLLMProvider.generate_content')
    def test_all_models_in_tier_fail(self, mock_generate_content):
        # Configure the mock to raise an exception on all calls
        mock_generate_content.side_effect = Exception("Rate limit error")

        # Assert that an exception is raised when all models in the tier fail
        with self.assertRaises(Exception):
            self.llm_service.generate_content("Test prompt", model_tier="heavy")

if __name__ == '__main__':
    unittest.main()
