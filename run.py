#!/usr/bin/env python3
"""Entry point for AI Summary application."""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ai_summary.main import content_processing_loop, start_bot
import threading

if __name__ == "__main__":
    content_thread = threading.Thread(target=content_processing_loop)
    content_thread.start()
    # Run the bot in the main thread
    start_bot()
