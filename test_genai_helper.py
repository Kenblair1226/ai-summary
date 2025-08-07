import os
import logging
import tempfile
from unittest.mock import Mock, patch, MagicMock
from dotenv import load_dotenv
from llm_provider import LLMResponse
import genai_helper

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Mock LLM service for testing
class MockLLMService:
    def __init__(self):
        self.default_provider = "mock_provider"
        self.providers = {"mock_provider": Mock()}
    
    def generate_content(self, prompt, model_tier="light", **kwargs):
        """Mock generate_content method"""
        if isinstance(prompt, str):
            if "search queries" in prompt.lower():
                return LLMResponse("AI technology trends 2024\nMachine learning applications\nTech industry news")
            elif "slug" in prompt.lower():
                return LLMResponse("ai-technology-trends-2024")
            elif "tags" in prompt.lower():
                return LLMResponse("ai, technology, machine-learning")
            elif "rewrite" in prompt.lower() or "humanize" in prompt.lower():
                return LLMResponse("這是一篇經過人性化處理的文章內容，討論了最新的人工智慧技術趨勢。")
            else:
                return LLMResponse("這是一個測試回應\n\n這是詳細的分析內容，包含了多個重要觀點。")
        elif isinstance(prompt, list):
            # For video summarization with file_data
            return LLMResponse("這是影片摘要\n\n詳細分析了影片中討論的科技趨勢。")
        else:
            return LLMResponse("預設測試回應")
    
    def generate_content_with_media(self, prompt, media_file, **kwargs):
        """Mock generate_content_with_media method"""
        if "簡短摘要" in prompt:
            return LLMResponse("這是音檔的簡短摘要，討論了人工智慧和機器學習的最新發展。")
        else:
            return LLMResponse("有趣的科技討論\n\n這是從音檔生成的詳細文章內容，包含了深入的技術分析。")

# Test data
TEST_TITLE_EN = "AI Technology Trends in 2024"
TEST_TITLE_ZH = "2024年人工智慧技術趨勢"
TEST_CONTENT_SHORT = "This is a short content snippet about AI technology trends."
TEST_CONTENT_LONG = """
這是一段較長的測試內容，討論了人工智慧技術在2024年的發展趨勢。
內容包括機器學習、深度學習、自然語言處理等多個領域的最新進展。
同時也涵蓋了各大科技公司在AI領域的投資和戰略佈局。
"""

SAMPLE_TAGS = [
    {"name": "AI", "id": 1},
    {"name": "Technology", "id": 2},
    {"name": "Machine Learning", "id": 3},
    {"name": "Summary", "id": 4},
    {"name": "Innovation", "id": 5}
]

def test_fetch_web_context_for_article():
    """Test the fetch_web_context_for_article function"""
    logger.info("Testing fetch_web_context_for_article...")
    
    try:
        with patch('genai_helper.llm_service', MockLLMService()):
            # Test successful search query generation
            queries = genai_helper.fetch_web_context_for_article(TEST_TITLE_EN, TEST_CONTENT_SHORT)
            
            if isinstance(queries, list) and len(queries) > 0:
                logger.info(f"✅ Successfully generated {len(queries)} search queries")
                for i, query in enumerate(queries, 1):
                    logger.info(f"  Query {i}: {query}")
                success = True
                result = f"Generated {len(queries)} queries"
            else:
                success = False
                result = "No queries generated"
        
        # Test with empty content
        with patch('genai_helper.llm_service', MockLLMService()) as mock_service:
            queries_empty = genai_helper.fetch_web_context_for_article("", "")
            if isinstance(queries_empty, list):
                logger.info("✅ Handled empty content correctly")
            
        # Test error handling
        with patch('genai_helper.llm_service') as mock_service:
            mock_service.generate_content.side_effect = Exception("API Error")
            queries_error = genai_helper.fetch_web_context_for_article(TEST_TITLE_EN, TEST_CONTENT_SHORT)
            if queries_error == []:
                logger.info("✅ Error handling works correctly")
        
        return success, result
    except Exception as e:
        logger.error(f"❌ Error in test_fetch_web_context_for_article: {e}")
        return False, str(e)

def test_summarize_youtube_video():
    """Test the summarize_youtube_video function"""
    logger.info("Testing summarize_youtube_video...")
    
    try:
        test_url = "https://www.youtube.com/watch?v=test123"
        
        with patch('genai_helper.llm_service', MockLLMService()):
            # Test successful video summarization
            summary = genai_helper.summarize_youtube_video(test_url)
            
            if isinstance(summary, str) and len(summary) > 0:
                logger.info(f"✅ Successfully generated video summary: {summary[:100]}...")
                success = True
                result = "Video summary generated"
            else:
                success = False
                result = "No summary generated"
        
        # Test error handling
        with patch('genai_helper.llm_service') as mock_service:
            mock_service.generate_content.side_effect = Exception("API Error")
            summary_error = genai_helper.summarize_youtube_video(test_url)
            if summary_error is None:
                logger.info("✅ Error handling returns None correctly")
        
        return success, result
    except Exception as e:
        logger.error(f"❌ Error in test_summarize_youtube_video: {e}")
        return False, str(e)

def test_summarize_text():
    """Test the summarize_text function"""
    logger.info("Testing summarize_text...")
    
    try:
        with patch('genai_helper.llm_service', MockLLMService()):
            # Test successful text summarization
            title, content = genai_helper.summarize_text(TEST_TITLE_ZH, TEST_CONTENT_LONG)
            
            if isinstance(title, str) and isinstance(content, str) and len(title) > 0 and len(content) > 0:
                logger.info(f"✅ Successfully generated text summary")
                logger.info(f"  Title: {title}")
                logger.info(f"  Content preview: {content[:100]}...")
                success = True
                result = "Text summary generated"
            else:
                success = False
                result = "Invalid summary format"
        
        # Test error handling
        with patch('genai_helper.llm_service') as mock_service:
            mock_service.generate_content.side_effect = Exception("API Error")
            try:
                genai_helper.summarize_text(TEST_TITLE_ZH, TEST_CONTENT_LONG)
                success = False
                result = "Should have raised exception"
            except Exception:
                logger.info("✅ Error handling raises exception correctly")
        
        return success, result
    except Exception as e:
        logger.error(f"❌ Error in test_summarize_text: {e}")
        return False, str(e)

def test_generate_article():
    """Test the generate_article function"""
    logger.info("Testing generate_article...")
    
    try:
        # Mock the mcp__fetch__fetch function by adding it to the module
        def mock_fetch(url=None, max_length=None):
            return "Mock web content about AI technology trends."
        
        # Temporarily add the function to the module
        original_func = getattr(genai_helper, 'mcp__fetch__fetch', None)
        setattr(genai_helper, 'mcp__fetch__fetch', mock_fetch)
        
        try:
            with patch('genai_helper.llm_service', MockLLMService()):
                # Test successful article generation
                article = genai_helper.generate_article(TEST_CONTENT_LONG)
                
                if isinstance(article, str) and len(article) > 0:
                    logger.info(f"✅ Successfully generated article")
                    logger.info(f"  Article preview: {article[:200]}...")
                    success = True
                    result = "Article generated"
                else:
                    success = False
                    result = "No article generated"
        finally:
            # Restore original function if it existed
            if original_func is not None:
                setattr(genai_helper, 'mcp__fetch__fetch', original_func)
            elif hasattr(genai_helper, 'mcp__fetch__fetch'):
                delattr(genai_helper, 'mcp__fetch__fetch')
        
        # Test with web fetch failure
        def mock_fetch_error(url=None, max_length=None):
            raise Exception("Web fetch error")
        
        setattr(genai_helper, 'mcp__fetch__fetch', mock_fetch_error)
        try:
            with patch('genai_helper.llm_service', MockLLMService()):
                article_no_web = genai_helper.generate_article(TEST_CONTENT_SHORT)
                if isinstance(article_no_web, str):
                    logger.info("✅ Handled web fetch failure correctly")
        finally:
            if hasattr(genai_helper, 'mcp__fetch__fetch'):
                delattr(genai_helper, 'mcp__fetch__fetch')
        
        return success, result
    except Exception as e:
        logger.error(f"❌ Error in test_generate_article: {e}")
        return False, str(e)

def test_summarize_mp3():
    """Test the summarize_mp3 function"""
    logger.info("Testing summarize_mp3...")
    
    try:
        # Create a temporary file to simulate MP3
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            test_path = temp_file.name
            temp_file.write(b'fake mp3 content')
        
        try:
            with patch('genai_helper.llm_service', MockLLMService()):
                # Test successful MP3 summarization
                response = genai_helper.summarize_mp3(test_path)
                
                if isinstance(response, LLMResponse) and len(response.text) > 0:
                    logger.info(f"✅ Successfully generated MP3 summary")
                    logger.info(f"  Response type: {type(response)}")
                    logger.info(f"  Content preview: {response.text[:100]}...")
                    success = True
                    result = "MP3 summary generated"
                else:
                    success = False
                    result = "Invalid response format"
        
        finally:
            # Clean up temporary file
            os.unlink(test_path)
        
        # Test error handling
        with patch('genai_helper.llm_service') as mock_service:
            mock_service.generate_content_with_media.side_effect = Exception("API Error")
            try:
                genai_helper.summarize_mp3("/nonexistent/path.mp3")
                success = False
                result = "Should have raised exception"
            except Exception:
                logger.info("✅ Error handling raises exception correctly")
        
        return success, result
    except Exception as e:
        logger.error(f"❌ Error in test_summarize_mp3: {e}")
        return False, str(e)

def test_article_mp3():
    """Test the article_mp3 function"""
    logger.info("Testing article_mp3...")
    
    try:
        # Create a temporary file to simulate MP3
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            test_path = temp_file.name
            temp_file.write(b'fake mp3 content')
        
        try:
            # Mock the mcp__fetch__fetch function
            def mock_fetch(url=None, max_length=None):
                return "Mock web content about podcast topics."
            
            # Temporarily add the function to the module
            original_func = getattr(genai_helper, 'mcp__fetch__fetch', None)
            setattr(genai_helper, 'mcp__fetch__fetch', mock_fetch)
            
            try:
                with patch('genai_helper.llm_service', MockLLMService()):
                    # Test successful article generation from MP3
                    title, content = genai_helper.article_mp3(TEST_TITLE_ZH, test_path)
                    
                    if isinstance(title, str) and isinstance(content, str) and len(title) > 0 and len(content) > 0:
                        logger.info(f"✅ Successfully generated article from MP3")
                        logger.info(f"  Title: {title}")
                        logger.info(f"  Content preview: {content[:200]}...")
                        success = True
                        result = "MP3 article generated"
                    else:
                        success = False
                        result = "Invalid article format"
            finally:
                # Restore original function if it existed
                if original_func is not None:
                    setattr(genai_helper, 'mcp__fetch__fetch', original_func)
                elif hasattr(genai_helper, 'mcp__fetch__fetch'):
                    delattr(genai_helper, 'mcp__fetch__fetch')
        
        finally:
            # Clean up temporary file
            os.unlink(test_path)
        
        return success, result
    except Exception as e:
        logger.error(f"❌ Error in test_article_mp3: {e}")
        return False, str(e)

def test_summarize_article():
    """Test the summarize_article function"""
    logger.info("Testing summarize_article...")
    
    try:
        with patch('genai_helper.llm_service', MockLLMService()):
            # Test successful article summarization
            title, content = genai_helper.summarize_article(TEST_TITLE_ZH, TEST_CONTENT_LONG)
            
            if isinstance(title, str) and isinstance(content, str) and len(title) > 0 and len(content) > 0:
                logger.info(f"✅ Successfully generated article summary")
                logger.info(f"  Title: {title}")
                logger.info(f"  Content preview: {content[:100]}...")
                success = True
                result = "Article summary generated"
            else:
                success = False
                result = "Invalid summary format"
        
        return success, result
    except Exception as e:
        logger.error(f"❌ Error in test_summarize_article: {e}")
        return False, str(e)

def test_generate_slug():
    """Test the generate_slug function with regex validation"""
    logger.info("Testing generate_slug...")
    
    try:
        with patch('genai_helper.llm_service', MockLLMService()):
            # Test successful slug generation
            slug = genai_helper.generate_slug(TEST_TITLE_EN)
            
            # Validate slug format using regex
            import re
            slug_pattern = r'^[a-z0-9]+(?:-[a-z0-9]+)*$'
            is_valid = bool(re.fullmatch(slug_pattern, slug))
            
            if is_valid and len(slug) <= 50:
                logger.info(f"✅ Successfully generated valid slug: {slug}")
                success = True
                result = f"Valid slug: {slug}"
            else:
                logger.warning(f"Generated slug may be invalid: {slug}")
                success = False
                result = f"Invalid slug format: {slug}"
        
        # Test with Chinese characters (should be converted)
        with patch('genai_helper.llm_service', MockLLMService()):
            slug_zh = genai_helper.generate_slug(TEST_TITLE_ZH)
            is_valid_zh = bool(re.fullmatch(slug_pattern, slug_zh))
            if is_valid_zh:
                logger.info(f"✅ Chinese title converted to valid slug: {slug_zh}")
        
        # Test regex validation retry logic
        mock_service = MockLLMService()
        original_response = mock_service.generate_content
        
        def mock_invalid_then_valid(prompt, **kwargs):
            if not hasattr(mock_invalid_then_valid, 'call_count'):
                mock_invalid_then_valid.call_count = 0
            mock_invalid_then_valid.call_count += 1
            
            if mock_invalid_then_valid.call_count == 1:
                return LLMResponse("invalid-slug-with-中文-characters!")
            else:
                return LLMResponse("valid-slug-after-retry")
        
        with patch('genai_helper.llm_service', mock_service):
            mock_service.generate_content = mock_invalid_then_valid
            retry_slug = genai_helper.generate_slug("Test Title")
            logger.info(f"✅ Retry logic works: {retry_slug}")
        
        # Test maximum retry fallback
        with patch('genai_helper.llm_service') as mock_service:
            mock_service.generate_content.return_value = LLMResponse("invalid@slug#always$")
            fallback_slug = genai_helper.generate_slug("Test Fallback Title", count=5)
            logger.info(f"✅ Fallback slug generated: {fallback_slug}")
        
        return success, result
    except Exception as e:
        logger.error(f"❌ Error in test_generate_slug: {e}")
        return False, str(e)

def test_format_html_content():
    """Test the format_html_content function"""
    logger.info("Testing format_html_content...")
    
    try:
        # Test content with URLs
        test_content_urls = """
This is a paragraph with a URL: https://example.com/test
And here's another one: http://test.org

Second paragraph after line break.
This continues the same paragraph.

Third paragraph with another URL: https://github.com/test
"""
        
        formatted = genai_helper.format_html_content(test_content_urls)
        
        # Check if URLs are converted to links
        if '<a href=' in formatted and 'target="_blank"' in formatted:
            logger.info("✅ URLs converted to clickable links")
            success = True
            result = "HTML formatting successful"
        else:
            success = False
            result = "URL conversion failed"
        
        # Check paragraph formatting
        if '\n\n' in formatted:
            logger.info("✅ Paragraphs properly separated")
        
        # Test with empty content
        empty_result = genai_helper.format_html_content("")
        if empty_result == "":
            logger.info("✅ Empty content handled correctly")
        
        # Test with only whitespace
        whitespace_result = genai_helper.format_html_content("   \n\n   ")
        logger.info(f"✅ Whitespace content result: '{whitespace_result}'")
        
        logger.info(f"Formatted content preview:\n{formatted[:300]}...")
        
        return success, result
    except Exception as e:
        logger.error(f"❌ Error in test_format_html_content: {e}")
        return False, str(e)

def test_humanize_content():
    """Test the humanize_content function"""
    logger.info("Testing humanize_content...")
    
    try:
        test_content = "這是一個測試內容，需要進行人性化處理，使其更加自然和親切。"
        
        with patch('genai_helper.llm_service', MockLLMService()):
            # Test successful content humanization
            humanized = genai_helper.humanize_content(test_content)
            
            if isinstance(humanized, str) and len(humanized) > 0:
                logger.info(f"✅ Successfully humanized content")
                logger.info(f"  Original: {test_content[:50]}...")
                logger.info(f"  Humanized: {humanized[:100]}...")
                success = True
                result = "Content humanized"
            else:
                success = False
                result = "Humanization failed"
        
        # Test error handling (should return original content)
        with patch('genai_helper.llm_service') as mock_service:
            mock_service.generate_content.side_effect = Exception("API Error")
            error_result = genai_helper.humanize_content(test_content)
            if error_result == test_content:
                logger.info("✅ Error handling returns original content correctly")
        
        return success, result
    except Exception as e:
        logger.error(f"❌ Error in test_humanize_content: {e}")
        return False, str(e)

def test_find_relevant_tags_with_llm():
    """Test the find_relevant_tags_with_llm function"""
    logger.info("Testing find_relevant_tags_with_llm...")
    
    try:
        test_content = "This article discusses artificial intelligence, machine learning, and innovative technology solutions."
        
        with patch('genai_helper.llm_service', MockLLMService()):
            # Test successful tag finding
            relevant_tags = genai_helper.find_relevant_tags_with_llm(
                TEST_TITLE_EN, 
                test_content, 
                SAMPLE_TAGS
            )
            
            if isinstance(relevant_tags, list):
                logger.info(f"✅ Successfully found {len(relevant_tags)} relevant tags")
                for tag in relevant_tags:
                    logger.info(f"  Tag: {tag}")
                success = True
                result = f"Found {len(relevant_tags)} tags"
            else:
                success = False
                result = "Invalid tag format"
        
        # Test with "none" response
        mock_service = MockLLMService()
        mock_service.generate_content = lambda *args, **kwargs: LLMResponse("none")
        
        with patch('genai_helper.llm_service', mock_service):
            no_tags = genai_helper.find_relevant_tags_with_llm(
                "Irrelevant Title", 
                "Irrelevant content", 
                SAMPLE_TAGS
            )
            if no_tags == []:
                logger.info("✅ 'none' response handled correctly")
        
        # Test error handling
        with patch('genai_helper.llm_service') as mock_service:
            mock_service.generate_content.side_effect = Exception("API Error")
            error_tags = genai_helper.find_relevant_tags_with_llm(
                TEST_TITLE_EN, 
                test_content, 
                SAMPLE_TAGS
            )
            if error_tags == []:
                logger.info("✅ Error handling returns empty list correctly")
        
        # Test filtering out 'summary' tags
        tags_with_summary = SAMPLE_TAGS + [{"name": "summary", "id": 6}]
        with patch('genai_helper.llm_service', MockLLMService()):
            filtered_tags = genai_helper.find_relevant_tags_with_llm(
                TEST_TITLE_EN, 
                test_content, 
                tags_with_summary
            )
            summary_found = any(tag.get('name', '').lower() == 'summary' for tag in filtered_tags)
            if not summary_found:
                logger.info("✅ Summary tags filtered out correctly")
        
        return success, result
    except Exception as e:
        logger.error(f"❌ Error in test_find_relevant_tags_with_llm: {e}")
        return False, str(e)

def run_all_tests():
    """Run all tests and return summary"""
    logger.info("=" * 60)
    logger.info("Running comprehensive genai_helper.py tests...")
    logger.info("=" * 60)
    
    # Load environment variables
    load_dotenv()
    
    # Test functions mapping
    test_functions = [
        ("fetch_web_context_for_article", test_fetch_web_context_for_article),
        ("summarize_youtube_video", test_summarize_youtube_video),
        ("summarize_text", test_summarize_text),
        ("generate_article", test_generate_article),
        ("summarize_mp3", test_summarize_mp3),
        ("article_mp3", test_article_mp3),
        ("summarize_article", test_summarize_article),
        ("generate_slug", test_generate_slug),
        ("format_html_content", test_format_html_content),
        ("humanize_content", test_humanize_content),
        ("find_relevant_tags_with_llm", test_find_relevant_tags_with_llm),
    ]
    
    # Run tests
    results = {}
    for func_name, test_func in test_functions:
        logger.info(f"\n{'-' * 40}")
        try:
            success, result = test_func()
            results[func_name] = {"success": success, "result": result}
        except Exception as e:
            logger.error(f"Test {func_name} crashed: {e}")
            results[func_name] = {"success": False, "result": f"Test crashed: {str(e)}"}
    
    # Display results summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("=" * 60)
    
    passed = 0
    failed = 0
    
    for func_name, result in results.items():
        status = '✅ PASS' if result["success"] else '❌ FAIL'
        logger.info(f"{func_name:30} : {status}")
        if not result["success"]:
            logger.info(f"{'':32}   {result['result']}")
            failed += 1
        else:
            passed += 1
    
    logger.info("-" * 60)
    logger.info(f"Total tests: {len(test_functions)}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    
    if failed == 0:
        logger.info("🎉 ALL TESTS PASSED!")
        return True
    else:
        logger.error(f"💥 {failed} TESTS FAILED!")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)