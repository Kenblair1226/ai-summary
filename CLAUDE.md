# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

This is a content aggregation and AI summarization system that monitors multiple content sources (YouTube channels, RSS feeds, podcasts), processes them through AI summarization, and publishes to various platforms.

### Core Components

**Entry Point**: `main.py` - Main application with scheduled tasks running at 00:00 and 12:00 daily

**LLM Abstraction Layer**: Sophisticated provider abstraction with automatic fallback
- `llm_provider.py` - Base abstraction and provider implementations
- `LLMService` manages multiple providers (Gemini, OpenRouter) with intelligent switching
- Automatic fallback on rate limiting with standardized `LLMResponse` format

**Content Processing Pipeline**:
1. **Source Monitoring** - YouTube channels, RSS feeds, podcast feeds
2. **Content Extraction** - Audio download via `pytubefix`/`yt-dlp`, text extraction
3. **AI Summarization** - Multi-provider LLM processing with Traditional Chinese output
4. **Publishing** - WordPress, Ghost, Telegram notifications

**Key Modules**:
- `genai_helper.py` - AI summarization functions using LLM abstraction
- `youtube_helper.py` - YouTube API interactions and audio extraction
- `db_helper.py` - Thread-safe SQLite with connection pooling
- `telegram_bot.py` - User interface and subscription management
- `summarize_and_post.py` - Content publishing to WordPress/Ghost

### Database Architecture

SQLite with thread-safe connection pooling and thread-local storage:
- `channels` - YouTube channel monitoring
- `videos` - Processed video content
- `rss_feeds`/`podcast_feeds` - Feed configurations
- `processed_articles`/`processed_episodes` - Content tracking
- `subscribers` - Telegram bot user management

### Technical Patterns

**Multi-threaded Event-driven Processing**: Asyncio for concurrent content processing with scheduled monitoring

**Provider Abstraction**: LLM provider abstraction with environment-based configuration and automatic fallback handling

**Content Filtering**: Date-based filtering (podcast episodes after 2025/05/27) and intelligent deduplication

**Error Handling**: Comprehensive logging with robust error recovery and provider switching

### Configuration

**Environment Variables**: Configure via `.env` file for API keys and provider settings

**Docker**: Multi-stage build with Python 3.9, Node.js (for YouTube token generation), and ffmpeg for audio processing

**Content Sources**: System supports YouTube channels, RSS article feeds, and podcast RSS feeds with MP3 extraction

### Documentation References

Detailed LLM abstraction documentation available in:
- `LLM_ABSTRACTION_README.md` - Comprehensive usage guide
- `llm_provider_implementation.md` - Technical implementation details
- `llm_abstraction_testing.md` - Testing documentation