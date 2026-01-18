# LLM Provider Abstraction Layer

This implementation adds an abstraction layer for LLM providers to help you deal with rate limits by allowing you to switch between different providers like Google Gemini and OpenRouter.

## Implementation Overview

The abstraction layer consists of the following components:

1. **`llm_provider.py`** - The core abstraction layer:
   - `LLMProvider` - Abstract base class defining the interface for all providers
   - `GeminiProvider` - Google Gemini implementation
   - `OpenRouterProvider` - OpenRouter implementation
   - `LLMService` - Service to manage providers and handle fallbacks
   - `LLMResponse` - Standardized response object

2. **Refactored `genai_helper.py`**:
   - All functions updated to use the LLM service
   - Added optional `provider` parameter to all functions
   - Maintained backward compatibility with existing code

## Configuration

Configure your LLM providers in the `.env` file. You can use the `.env.example` as a template:

```bash
# LLM Providers Configuration
# -----------------------------

# Google Gemini Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3-pro
GEMINI_TEMPERATURE=1.0
GEMINI_TOP_P=0.95
GEMINI_TOP_K=40
GEMINI_MAX_TOKENS=8192

# OpenRouter Configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=anthropic/claude-3-opus
OPENROUTER_TEMPERATURE=1.0
OPENROUTER_TOP_P=0.95
OPENROUTER_MAX_TOKENS=8192

# Default LLM Provider (gemini or openrouter)
DEFAULT_LLM_PROVIDER=gemini
```

## Usage

### Basic Usage

The existing functions in `genai_helper.py` now accept an optional `provider` parameter:

```python
from genai_helper import summarize_text

# Use default provider
title, content = summarize_text("Original Title", "Text content to summarize")

# Specify a provider
title, content = summarize_text("Original Title", "Text content to summarize", provider="openrouter")
```

### Handling Rate Limits

The system will automatically handle rate limits:

1. If you don't specify a fallback preference, it follows the `fallback=True` default
2. When a rate limit is hit, it tries the next available provider
3. If all providers are rate-limited, it raises the exception

```python
try:
    # This will automatically fall back if the default provider hits a rate limit
    result = summarize_youtube_video(video_url)
except Exception as e:
    # All providers hit rate limits or other errors
    print(f"Error: {e}")
```

### Direct Usage of LLM Service

You can also use the LLM service directly for custom prompts:

```python
from llm_provider import llm_service

# Simple text prompt
response = llm_service.generate_content("Write me a short poem")
print(response.text)

# With media
response = llm_service.generate_content_with_media("Describe this image", "path/to/image.jpg")
print(response.text)

# Specify provider
response = llm_service.generate_content("Write me a short poem", provider="openrouter")
print(response.text)

# Disable fallback
response = llm_service.generate_content("Write me a short poem", fallback=False)
print(response.text)
```

## Testing

Run the included test script to verify the implementation:

```bash
python test_llm_provider.py
```

This will:
1. Test each available provider
2. Test the fallback mechanism (if multiple providers are configured)
3. Display the results

## Provider Support Details

### Google Gemini
- Supports text and media inputs (images, audio, video)
- Configuration via `GEMINI_*` environment variables
- Default model: `gemini-3-pro`

### OpenRouter
- Primarily supports text inputs
- Limited media support (images only, no audio/video)
- Configuration via `OPENROUTER_*` environment variables
- Default model: `anthropic/claude-3-opus`
- Requires OpenAI Python package (v1.0.0 or higher)

## Extending

To add a new provider:

1. Create a new class that inherits from `LLMProvider`
2. Implement the required methods
3. Add initialization logic to the `LLMService.init_providers()` method

Example:

```python
class NewProvider(LLMProvider):
    def setup(self) -> None:
        # Initialize the provider
        pass
    
    def generate_content(self, prompt) -> LLMResponse:
        # Generate content
        pass
    
    def generate_content_with_media(self, prompt, media_file) -> LLMResponse:
        # Generate content with media
        pass
    
    def is_rate_limited(self, error) -> bool:
        # Check if error is due to rate limiting
        pass
```

## Troubleshooting

If you encounter issues:

1. Check your API keys in the `.env` file
2. Ensure required packages are installed: `pip install -r requirements.txt`
3. Check the logs for error messages
4. Try testing each provider individually with simple prompts
5. Verify your internet connection and API endpoint access