# AGENTS.md

Guidelines for AI coding agents working in this repository.

## Project Overview

Content aggregation and AI summarization system that monitors YouTube channels, RSS feeds, and podcasts, processes content through multi-provider LLM summarization, and publishes to WordPress, Ghost, and Telegram.

## Build & Run Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run main application
python main.py

# Test LLM provider abstraction
python test_llm_provider.py

# Initialize database only
python db_helper.py
```

### Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# Manual Docker build
docker build -t ai-summary .
docker run -v ./data:/data --env-file .env ai-summary
```

### Testing

No formal test framework is configured. Tests are run as standalone scripts:

```bash
# Run LLM provider tests
python test_llm_provider.py

# Run a single test file
python <test_file>.py
```

For future test additions, use `pytest` with `unittest.mock`:
```bash
pytest tests/test_module.py -v
pytest tests/test_module.py::TestClass::test_method -v  # Single test
```

## Code Style Guidelines

### Python Version

- Python 3.9+ (Docker uses 3.13)

### Import Organization

Order imports as follows (no blank lines between groups in existing code):

```python
# 1. Standard library imports
import os
import re
import abc
import logging
import asyncio
import threading
from typing import Dict, List, Optional, Any, Union
from contextlib import contextmanager

# 2. Third-party imports
import schedule
import feedparser
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# 3. Local module imports
from db_helper import DbHelper
from llm_provider import llm_service, LLMResponse
from youtube_helper import check_new_videos, download_audio_from_youtube
```

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Classes | PascalCase | `DbHelper`, `LLMProvider`, `GeminiProvider` |
| Functions | snake_case | `get_youtube_title`, `process_new_videos` |
| Variables | snake_case | `video_url`, `post_title`, `channel_handle` |
| Constants | UPPER_SNAKE_CASE | `CATEGORY_IDS`, `STARTUP_TIME` |
| Private methods | underscore prefix | `_get_fallback_provider`, `_chunk_content` |

### Type Hints

Type hints are encouraged but not strictly enforced. When used:

```python
from typing import Dict, List, Optional, Union, Any

def generate_content(
    self, 
    prompt: Union[str, List, Dict],
    provider: str = None,
    fallback: bool = True,
    **kwargs
) -> LLMResponse:
    """Generate content with the LLM provider."""
    pass

def get_connection(self) -> Optional[sqlite3.Connection]:
    pass
```

### Docstrings

Use simple docstrings with Args/Returns sections for public functions:

```python
def article_mp3(title, path, **kwargs):
    """Generates an article from an MP3 file using the configured LLM provider.
    
    Args:
        title: Title of the audio content
        path: Path to the MP3 file
        **kwargs: Additional arguments to pass to the LLM service
    
    Returns:
        Tuple containing (title, article_content)
    """
```

### Error Handling

Use try-except with logging. Either re-raise or return None/empty values:

```python
def process_content(url):
    try:
        # operation
        result = do_something(url)
        return result
    except Exception as e:
        logging.error(f"Error processing {url}: {e}")
        raise  # or return None
```

For rate limiting detection, check error strings:

```python
def is_rate_limited(self, error: Exception) -> bool:
    error_str = str(error).lower()
    return any(phrase in error_str for phrase in [
        "rate limit", 
        "too many requests", 
        "429", 
        "quota exceeded"
    ])
```

### Logging

Use Python's built-in logging module:

```python
import logging

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Suppress noisy HTTP loggers
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)

# Usage
logging.info(f"Processing video: {video_url}")
logging.error(f"Error generating summary: {e}")
logging.warning("Rate limit hit, trying fallback provider")
logging.debug(f"Response: {response.text[:200]}...")
```

### String Formatting

Use f-strings throughout:

```python
logging.info(f"Found {len(new_videos)} new videos.")
url = f"https://youtu.be/{video.video_id}"
```

### Async Patterns

Use `async/await` with `asyncio` for concurrent operations:

```python
async def process_new_videos():
    try:
        for video in videos:
            await process_video(video)
    except Exception as e:
        logging.error(f"Error: {e}")

# Run async from sync context
asyncio.run(run_content_processor())
```

### Class Design Patterns

**Abstract base classes:**
```python
class LLMProvider(abc.ABC):
    @abc.abstractmethod
    def generate_content(self, prompt) -> LLMResponse:
        pass
```

**Context managers for resources:**
```python
@contextmanager
def get_connection(self):
    if not hasattr(self._local, 'connection'):
        self._local.connection = sqlite3.connect(self.db_path)
    try:
        yield self._local.connection
    finally:
        pass  # Keep connection for thread reuse
```

**Thread-local storage:**
```python
self._local = threading.local()
```

## Architecture Notes

### Key Modules

- `main.py` - Entry point, scheduled tasks at 00:00 and 12:00 daily
- `llm_provider.py` - LLM abstraction layer (Gemini, OpenRouter, LiteLLM)
- `genai_helper.py` - AI summarization functions
- `db_helper.py` - Thread-safe SQLite with connection pooling
- `youtube_helper.py` - YouTube API and audio extraction
- `summarize_and_post.py` - WordPress/Ghost publishing
- `telegram_bot.py` - User notifications

### LLM Provider System

Uses abstraction layer with automatic fallback on rate limiting:

```python
from llm_provider import llm_service

# Text generation
response = llm_service.generate_content(prompt, model_tier="heavy")

# With media (audio/video)
response = llm_service.generate_content_with_media(prompt, media_path)
```

Model tiers: `"heavy"` for complex tasks, `"light"` for simple queries.

### Database

Thread-safe SQLite with `DbHelper` class:

```python
db = DbHelper(os.getenv('DB_PATH', 'database.db'))
db.initialize_db()

with db.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM channels')
```

### Environment Configuration

All secrets and configuration via `.env` file:
- `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `LITELLM_API_KEY`
- `DEFAULT_LLM_PROVIDER`, `HEAVY_MODELS`, `LIGHT_MODELS`
- `DB_PATH`, `TELEGRAM_BOT_TOKEN`
- WordPress/Ghost credentials

### Content Output

All AI-generated summaries are output in **Traditional Chinese**.
