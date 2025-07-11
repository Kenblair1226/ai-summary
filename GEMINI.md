# GEMINI.md

This file provides guidance to Google Gemini when working with code in this repository.

## Commands

### Development and Testing
```bash
# Install dependencies
pip install -r requirements.txt

# Test LLM provider abstraction
python test_llm_provider.py

# Run main application
python main.py
```

### Docker Operations
```bash
# Build and run with Docker Compose
docker-compose up --build

# Manual Docker build and run
docker build -t ai-summary .
docker run -v ./data:/data --env-file .env ai-summary
```

## Architecture Overview

This is a content aggregation and AI summarization system that monitors multiple content sources (YouTube channels, RSS feeds, podcasts), processes them through AI summarization, and publishes to various platforms like WordPress, Ghost, and Telegram.

### Core Components

**Entry Point**: `main.py` - The main application which contains scheduled tasks that run at 00:00 and 12:00 daily.

**LLM Abstraction Layer**: A key feature is the sophisticated provider abstraction with automatic fallback to handle rate limiting.
- `llm_provider.py`: Contains the base abstraction (`LLMProvider`), concrete implementations for different providers (`GeminiProvider`, `OpenRouterProvider`), a service manager (`LLMService`), and a standardized response object (`LLMResponse`).
- `LLMService` manages multiple providers and can intelligently switch between them, for example, falling back to another provider when one is rate-limited.

**Content Processing Pipeline**:
1.  **Source Monitoring**: Monitors YouTube channels, RSS feeds, and podcast feeds.
2.  **Content Extraction**: Downloads audio using `pytubefix`/`yt-dlp` and extracts text.
3.  **AI Summarization**: Uses the multi-provider LLM abstraction layer to generate summaries, primarily in Traditional Chinese.
4.  **Publishing**: Publishes the summarized content to WordPress, Ghost, and sends notifications via Telegram.

**Key Modules**:
- `genai_helper.py`: Contains AI summarization functions that now use the LLM abstraction layer.
- `youtube_helper.py`: Handles YouTube API interactions and audio extraction.
- `db_helper.py`: Manages a thread-safe SQLite database with connection pooling.
- `telegram_bot.py`: Provides a user interface for interaction and subscription management.
- `summarize_and_post.py`: Responsible for publishing content to WordPress and Ghost.

### Database Architecture

The application uses SQLite with thread-safe connection pooling and thread-local storage. Key tables include:
- `channels`: For YouTube channel monitoring.
- `videos`: For processed video content.
- `rss_feeds`/`podcast_feeds`: For feed configurations.
- `processed_articles`/`processed_episodes`: For tracking processed content.
- `subscribers`: For managing Telegram bot users.

### Technical Patterns

- **Multi-threaded and Event-driven Processing**: Uses `asyncio` for concurrent content processing with scheduled monitoring tasks.
- **Provider Abstraction**: The LLM provider abstraction allows for flexible, environment-based configuration and automatic fallback to handle errors like rate limiting.
- **Content Filtering**: Implements date-based filtering (e.g., for podcast episodes) and deduplication of content.
- **Error Handling**: Features comprehensive logging, robust error recovery mechanisms, and intelligent provider switching.

### Configuration

- **Environment Variables**: The application is configured via a `.env` file, which holds API keys and provider settings. See `.env.example` for a template.
- **Docker**: A multi-stage Dockerfile is provided, which sets up Python 3.9, Node.js (for YouTube token generation), and ffmpeg for audio processing.
- **Content Sources**: The system is designed to handle YouTube channels, RSS article feeds, and podcast RSS feeds (with MP3 extraction).

### Documentation References

For more detailed information on the LLM abstraction layer, refer to the following documents:
- `LLM_ABSTRACTION_README.md`: A comprehensive guide on how to use the abstraction layer.
- `llm_provider_implementation.md`: Detailed technical information on the implementation.
- `llm_abstraction_testing.md`: Documentation on how to test the abstraction layer.
- `llm_abstraction_plan.md`: The original plan for the abstraction layer.
