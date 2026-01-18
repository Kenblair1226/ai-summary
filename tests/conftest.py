"""Shared test fixtures for all test modules."""
import sys
import os
from unittest.mock import MagicMock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

# Mock external dependencies before importing the modules
# This is necessary because the actual libraries may not be installed or configured

# Mock google.genai (the new Google AI SDK)
mock_genai = MagicMock()
mock_genai.Client = MagicMock()
mock_genai.types = MagicMock()
sys.modules['google.genai'] = mock_genai

# Also mock at 'google' level if needed
if 'google' not in sys.modules:
    mock_google = MagicMock()
    mock_google.genai = mock_genai
    sys.modules['google'] = mock_google
else:
    sys.modules['google'].genai = mock_genai

# Mock litellm
mock_litellm = MagicMock()
mock_litellm.completion = MagicMock()
sys.modules['litellm'] = mock_litellm

# Mock openai
mock_openai = MagicMock()
mock_openai.OpenAI = MagicMock()
sys.modules['openai'] = mock_openai

# Mock telegram
mock_telegram = MagicMock()
mock_telegram.Bot = MagicMock()
mock_telegram.Update = MagicMock()
mock_telegram.ext = MagicMock()
sys.modules['telegram'] = mock_telegram
sys.modules['telegram.ext'] = mock_telegram.ext

import pytest
import tempfile

from ai_summary.core import DbHelper


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    db = DbHelper(db_path)
    db.initialize_db()
    
    yield db
    
    db.close_all()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def mock_env(monkeypatch):
    """Set up mock environment variables."""
    env_vars = {
        'GEMINI_API_KEY': 'test-gemini-key',
        'OPENROUTER_API_KEY': 'test-openrouter-key',
        'LITELLM_API_KEY': 'test-litellm-key',
        'LITELLM_MODEL': 'gpt-4',
        'LITELLM_API_BASE': 'https://api.test.com',
        'DEFAULT_LLM_PROVIDER': 'gemini',
        'HEAVY_MODELS': 'gemini-pro,gpt-4',
        'LIGHT_MODELS': 'gemini-flash,gpt-3.5-turbo',
        'DB_PATH': ':memory:',
        'TELEGRAM_TOKEN': 'test-telegram-token',
        'ghost_url': 'https://ghost.test.com',
        'ghost_key': 'test-id:test-secret-hex',
        'wp_host': 'https://wordpress.test.com',
        'wp_user': 'test-user',
        'wp_pass': 'test-pass',
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def sample_feed_entry():
    """Create a sample feed entry for testing."""
    class MockEnclosure:
        def __init__(self, href, type_):
            self.href = href
            self.type = type_
        
        def get(self, key, default=None):
            if key == 'href':
                return self.href
            if key == 'type':
                return self.type
            return default
    
    class MockEntry:
        def __init__(self):
            self.id = 'test-episode-123'
            self.title = 'Test Episode'
            self.link = 'https://example.com/episode/123'
            self.published = 'Mon, 01 Jan 2024 00:00:00 GMT'
            self.enclosures = [
                {'href': 'https://example.com/audio.mp3', 'type': 'audio/mpeg'}
            ]
            self.media_content = []
            self.links = []
    
    return MockEntry()


@pytest.fixture
def sample_video_url():
    """Sample YouTube video URL for testing."""
    return "https://youtu.be/dQw4w9WgXcQ"


@pytest.fixture
def sample_channel_url():
    """Sample YouTube channel URL for testing."""
    return "https://www.youtube.com/@sharptechpodcast"
