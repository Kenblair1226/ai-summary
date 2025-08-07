#!/usr/bin/env python3
"""
Integration test for YouTube link processing via Telegram bot.
Tests the complete workflow from receiving a YouTube URL to generating and publishing an article.
"""

import os
import sys
import logging
import tempfile
import shutil
import uuid
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from dotenv import load_dotenv

# Import the modules we need to test
from telegram import Update, Message, Chat
from telegram.ext import ContextTypes
from youtube_helper import is_valid_youtube_url, extract_video_id, get_youtube_title, download_audio_from_youtube
from genai_helper import article_mp3
from summarize_and_post import post_to_wordpress, post_to_ghost
from llm_provider import LLMResponse

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MockUpdate:
    """Mock Telegram Update object"""
    def __init__(self, text=""):
        self.message = Mock()
        self.message.chat_id = 12345
        self.message.reply_text = AsyncMock()
        self.message.text = text

class MockContext:
    """Mock Telegram Context object"""
    def __init__(self, args=None):
        self.args = args or []

def create_mock_mp3_file(temp_dir):
    """Create a mock MP3 file for testing"""
    mp3_path = os.path.join(temp_dir, "test_audio.mp3")
    with open(mp3_path, 'wb') as f:
        f.write(b'fake mp3 content')
    return mp3_path

def test_youtube_url_validation():
    """Test YouTube URL validation functionality"""
    logger.info("Testing YouTube URL validation...")
    
    valid_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "www.youtube.com/watch?v=dQw4w9WgXcQ"
    ]
    
    invalid_urls = [
        "https://vimeo.com/123456",
        "https://www.google.com",
        "not-a-url",
        "",
        "https://youtube.com/channel/UC123456"
    ]
    
    # Test valid URLs
    for url in valid_urls:
        if not is_valid_youtube_url(url):
            logger.error(f"❌ Valid URL rejected: {url}")
            return False, f"Valid URL rejected: {url}"
    
    # Test invalid URLs
    for url in invalid_urls:
        if is_valid_youtube_url(url):
            logger.error(f"❌ Invalid URL accepted: {url}")
            return False, f"Invalid URL accepted: {url}"
    
    # Test video ID extraction
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    video_id = extract_video_id(test_url)
    if video_id != "dQw4w9WgXcQ":
        logger.error(f"❌ Video ID extraction failed: expected 'dQw4w9WgXcQ', got '{video_id}'")
        return False, f"Video ID extraction failed: expected 'dQw4w9WgXcQ', got '{video_id}'"
    
    logger.info("✅ YouTube URL validation tests passed")
    return True, "YouTube URL validation working correctly"

@patch('youtube_helper.get_youtube_title')
@patch('youtube_helper.download_audio_from_youtube')
@patch('genai_helper.article_mp3')
@patch('summarize_and_post.post_to_wordpress')
@patch('summarize_and_post.post_to_ghost')
def test_complete_youtube_workflow(mock_post_ghost, mock_post_wp, mock_article_mp3, 
                                   mock_download_audio, mock_get_title):
    """Test the complete YouTube processing workflow"""
    logger.info("Testing complete YouTube workflow...")
    
    # Set up mocks
    test_title = "測試 YouTube 影片標題：AI 技術分析"
    test_video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    test_temp_dir = tempfile.mkdtemp()
    test_mp3_path = create_mock_mp3_file(test_temp_dir)
    
    mock_get_title.return_value = test_title
    mock_download_audio.return_value = (test_title, test_mp3_path)
    
    # Mock article generation with realistic Traditional Chinese content
    test_article_title = "深度解析：人工智慧技術的最新趨勢與發展"
    test_article_content = """
    <h3>技術突破與創新</h3>
    <p>本影片深入討論了當前人工智慧領域的重要發展，包括大型語言模型的演進、機器學習算法的優化，以及實際應用案例的分析。</p>
    
    <h3>產業影響分析</h3>
    <p>影片中提到了 AI 技術對各行各業的深遠影響，特別是在自動化、數據分析和決策支持方面的應用。講者分享了多個成功案例，展示了技術如何改變傳統工作流程。</p>
    
    <h3>未來發展展望</h3>
    <p>討論了人工智慧技術的未來發展方向，包括倫理考量、技術標準化，以及如何平衡創新與責任的重要性。</p>
    """
    
    mock_article_mp3.return_value = (test_article_title, test_article_content)
    mock_post_ghost.return_value = "https://ghost-site.com/test-article"
    mock_post_wp.return_value = True
    
    try:
        # Import here to avoid circular imports
        from telegram_bot import yt
        
        # Create mock objects
        update = MockUpdate()
        context = MockContext(args=[test_video_url])
        
        # Mock asyncio to make this synchronous for testing
        import asyncio
        
        async def run_test():
            await yt(update, context)
            
            # Verify that all functions were called correctly
            mock_get_title.assert_called_once()
            mock_download_audio.assert_called_once()
            mock_article_mp3.assert_called_once()
            mock_post_ghost.assert_called_once()
            mock_post_wp.assert_called_once()
            
            # Check if success message was sent
            reply_calls = update.message.reply_text.call_args_list
            success_message_sent = any(
                "Summary posted:" in str(call) for call in reply_calls
            )
            
            if not success_message_sent:
                return False, "Success message not sent to user"
            
            return True, "Complete workflow executed successfully"
        
        # Run the async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success, message = loop.run_until_complete(run_test())
            logger.info(f"✅ {message}")
            return success, message
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"❌ Complete workflow test failed: {e}")
        return False, f"Complete workflow test failed: {e}"
    finally:
        # Clean up temp directory
        if os.path.exists(test_temp_dir):
            shutil.rmtree(test_temp_dir)

@patch('youtube_helper.get_youtube_title')
def test_invalid_youtube_url_handling(mock_get_title):
    """Test handling of invalid YouTube URLs"""
    logger.info("Testing invalid YouTube URL handling...")
    
    try:
        from telegram_bot import yt
        import asyncio
        
        # Test with invalid URL
        invalid_url = "https://www.google.com"
        update = MockUpdate()
        context = MockContext(args=[invalid_url])
        
        async def run_test():
            await yt(update, context)
            
            # Check if error message was sent
            reply_calls = update.message.reply_text.call_args_list
            error_message_sent = any(
                "valid YouTube video URL" in str(call) for call in reply_calls
            )
            
            if not error_message_sent:
                return False, "Error message not sent for invalid URL"
            
            # Verify that get_title was not called for invalid URL
            mock_get_title.assert_not_called()
            
            return True, "Invalid URL handled correctly"
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success, message = loop.run_until_complete(run_test())
            logger.info(f"✅ {message}")
            return success, message
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"❌ Invalid URL handling test failed: {e}")
        return False, f"Invalid URL handling test failed: {e}"

@patch('telegram_bot.get_youtube_title')
@patch('telegram_bot.download_audio_from_youtube')
def test_download_failure_handling(mock_download_audio, mock_get_title):
    """Test handling of YouTube download failures"""
    logger.info("Testing download failure handling...")
    
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    mock_get_title.return_value = "Test Video Title"
    mock_download_audio.side_effect = Exception("Download failed")
    
    try:
        from telegram_bot import yt
        import asyncio
        
        update = MockUpdate()
        context = MockContext(args=[test_url])
        
        async def run_test():
            await yt(update, context)
            
            # Check if error message was sent
            reply_calls = update.message.reply_text.call_args_list
            error_message_sent = any(
                "Failed to process" in str(call) for call in reply_calls
            )
            
            if not error_message_sent:
                return False, "Error message not sent for download failure"
            
            return True, "Download failure handled correctly"
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success, message = loop.run_until_complete(run_test())
            logger.info(f"✅ {message}")
            return success, message
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"❌ Download failure handling test failed: {e}")
        return False, f"Download failure handling test failed: {e}"

@patch('telegram_bot.get_youtube_title')
@patch('telegram_bot.download_audio_from_youtube')
@patch('telegram_bot.article_mp3')
def test_article_generation_failure(mock_article_mp3, mock_download_audio, mock_get_title):
    """Test handling of article generation failures"""
    logger.info("Testing article generation failure handling...")
    
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    test_temp_dir = tempfile.mkdtemp()
    test_mp3_path = create_mock_mp3_file(test_temp_dir)
    
    mock_get_title.return_value = "Test Video Title"
    mock_download_audio.return_value = ("Test Title", test_mp3_path)
    mock_article_mp3.return_value = ("Test Title", None)  # Simulate failure
    
    try:
        from telegram_bot import yt
        import asyncio
        
        update = MockUpdate()
        context = MockContext(args=[test_url])
        
        async def run_test():
            await yt(update, context)
            
            # Check if error message was sent
            reply_calls = update.message.reply_text.call_args_list
            error_message_sent = any(
                "Failed to generate summary" in str(call) for call in reply_calls
            )
            
            if not error_message_sent:
                return False, "Error message not sent for article generation failure"
            
            return True, "Article generation failure handled correctly"
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success, message = loop.run_until_complete(run_test())
            logger.info(f"✅ {message}")
            return success, message
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"❌ Article generation failure test failed: {e}")
        return False, f"Article generation failure test failed: {e}"
    finally:
        if os.path.exists(test_temp_dir):
            shutil.rmtree(test_temp_dir)

def test_no_arguments_handling():
    """Test handling when no YouTube URL is provided"""
    logger.info("Testing no arguments handling...")
    
    try:
        from telegram_bot import yt
        import asyncio
        
        update = MockUpdate()
        context = MockContext(args=[])  # No arguments
        
        async def run_test():
            await yt(update, context)
            
            # Check if help message was sent
            reply_calls = update.message.reply_text.call_args_list
            help_message_sent = any(
                "provide a YouTube URL" in str(call) for call in reply_calls
            )
            
            if not help_message_sent:
                return False, "Help message not sent when no arguments provided"
            
            return True, "No arguments case handled correctly"
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success, message = loop.run_until_complete(run_test())
            logger.info(f"✅ {message}")
            return success, message
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"❌ No arguments handling test failed: {e}")
        return False, f"No arguments handling test failed: {e}"

def run_all_tests():
    """Run all integration tests"""
    logger.info("=" * 80)
    logger.info("Running YouTube Telegram Integration Tests...")
    logger.info("=" * 80)
    
    tests = [
        ("URL Validation", test_youtube_url_validation),
        ("Complete Workflow", test_complete_youtube_workflow),
        ("Invalid URL Handling", test_invalid_youtube_url_handling),
        ("Download Failure", test_download_failure_handling),
        ("Article Generation Failure", test_article_generation_failure),
        ("No Arguments Handling", test_no_arguments_handling),
    ]
    
    results = []
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n{'-'*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'-'*50}")
        
        try:
            success, message = test_func()
            results.append((test_name, "PASS" if success else "FAIL", message))
            if success:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            results.append((test_name, "ERROR", str(e)))
            failed += 1
            logger.error(f"❌ {test_name} - ERROR: {e}")
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("INTEGRATION TEST RESULTS SUMMARY")
    logger.info("=" * 80)
    
    for test_name, status, message in results:
        status_icon = "✅" if status == "PASS" else "❌"
        logger.info(f"{test_name:30} : {status_icon} {status}")
        if status != "PASS":
            logger.info(f"  -> {message}")
    
    logger.info("-" * 80)
    logger.info(f"Total tests: {len(tests)}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    
    if failed == 0:
        logger.info("🎉 ALL INTEGRATION TESTS PASSED!")
        return True
    else:
        logger.error(f"💥 {failed} TEST(S) FAILED!")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)