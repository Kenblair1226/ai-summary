# AGENTS.md

Guidelines for AI coding agents working in this repository.

## Project Overview

Content aggregation and AI summarization system that monitors YouTube channels, RSS feeds, and podcasts, processes content through multi-provider LLM summarization, and publishes to WordPress, Ghost, and Telegram.

## Project Structure

```
ai-summary/
├── src/
│   └── ai_summary/              # Main package
│       ├── __init__.py
│       ├── main.py              # Entry point, scheduled tasks
│       ├── core/                # Core infrastructure
│       │   ├── __init__.py
│       │   ├── llm_provider.py  # LLM abstraction layer
│       │   └── db_helper.py     # Database operations
│       ├── content/             # Content processing
│       │   ├── __init__.py
│       │   ├── youtube_helper.py
│       │   ├── genai_helper.py  # AI summarization
│       │   └── publisher.py     # WordPress/Ghost publishing
│       └── interfaces/          # External interfaces
│           ├── __init__.py
│           └── telegram_bot.py
├── tests/                       # Test suite
│   ├── conftest.py              # Shared fixtures
│   └── fixtures/
├── docs/                        # Documentation
│   ├── LLM_ABSTRACTION_README.md
│   └── llm_provider_implementation.md
├── data/                        # Database storage
├── public/                      # Static assets (thumbnails)
├── run.py                       # Application entry point
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Build & Run Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run main application
python run.py

# Or run directly from module
PYTHONPATH=src python -m ai_summary.main

# Initialize database only
PYTHONPATH=src python -c "from ai_summary.core import DbHelper; db = DbHelper('database.db'); db.initialize_db()"
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

```bash
# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_module.py -v

# Run specific test
pytest tests/test_module.py::TestClass::test_method -v
```

## Code Style Guidelines

### Python Version

- Python 3.9+ (Docker uses 3.13)

### Import Organization

Order imports as follows:

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

# 3. Local package imports
from ai_summary.core import DbHelper, llm_service, LLMResponse
from ai_summary.content import check_new_videos, download_audio_from_youtube
from ai_summary.interfaces import notify_subscribers
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

### Package Structure

- `ai_summary.core` - Core infrastructure (LLM providers, database)
- `ai_summary.content` - Content processing (YouTube, AI summarization, publishing)
- `ai_summary.interfaces` - External interfaces (Telegram bot)

### LLM Provider System

Uses abstraction layer with automatic fallback on rate limiting:

```python
from ai_summary.core import llm_service

# Text generation
response = llm_service.generate_content(prompt, model_tier="heavy")

# With media (audio/video)
response = llm_service.generate_content_with_media(prompt, media_path)
```

Model tiers: `"heavy"` for complex tasks, `"light"` for simple queries.

### Database

Thread-safe SQLite with `DbHelper` class:

```python
from ai_summary.core import DbHelper

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
