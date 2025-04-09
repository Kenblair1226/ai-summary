import os
import logging
from dotenv import load_dotenv
from llm_provider import llm_service

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_simple_prompt(provider=None):
    """Test a simple text prompt with the specified provider."""
    prompt = "Write a short paragraph about artificial intelligence in Traditional Chinese."
    
    try:
        logger.info(f"Testing simple prompt with provider: {provider or llm_service.default_provider}")
        response = llm_service.generate_content(prompt, provider=provider)
        logger.info(f"Response received:\n{response.text[:200]}...")
        return True, response.text
    except Exception as e:
        logger.error(f"Error testing simple prompt: {e}")
        return False, str(e)

def test_explicit_fallback(from_provider="gemini", to_provider="openrouter"):
    """Directly test the fallback mechanism between two providers."""
    # Create a simple prompt that will work
    prompt = "Write a very short greeting in Traditional Chinese."
    
    if from_provider not in llm_service.providers or to_provider not in llm_service.providers:
        logger.error(f"Cannot test fallback: one of the providers is not available")
        return False, "Required providers not available"
    
    logger.info(f"Testing explicit fallback from {from_provider} to {to_provider}")
    
    # Create a wrapper function that raises a rate limit exception for the first provider
    original_generate = llm_service.providers[from_provider].generate_content
    
    def mock_rate_limit(*args, **kwargs):
        logger.info(f"Simulating rate limit for {from_provider}")
        # Raise an exception that will be detected as a rate limit
        error_msg = "429 You exceeded your current quota, please check your plan and billing details."
        raise Exception(error_msg)
    
    try:
        # Replace the generate_content method with our mock
        llm_service.providers[from_provider].generate_content = mock_rate_limit
        
        # Call with fallback enabled
        logger.info(f"Attempting to generate content with {from_provider} (will fail) and fallback to {to_provider}")
        response = llm_service.generate_content(prompt, provider=from_provider, fallback=True)
        
        logger.info(f"Fallback succeeded! Response from {to_provider}:\n{response.text[:200]}...")
        return True, response.text
    except Exception as e:
        logger.error(f"Fallback mechanism failed: {e}")
        return False, str(e)
    finally:
        # Restore the original method
        llm_service.providers[from_provider].generate_content = original_generate

def test_providers():
    """Test each available provider."""
    results = {}
    
    # Test each available provider
    for provider_name in llm_service.providers.keys():
        logger.info(f"Testing provider: {provider_name}")
        success, result = test_simple_prompt(provider_name)
        results[provider_name] = {"success": success, "result": result}
    
    # Display results
    logger.info("Provider test results:")
    for provider, result in results.items():
        status = 'SUCCESS' if result["success"] else 'FAILED'
        logger.info(f"  {provider}: {status}")
    
    # Test fallback if we have multiple providers
    if len(llm_service.providers) > 1:
        logger.info("Testing fallback mechanism with mocked rate limit")
        if "gemini" in llm_service.providers and "openrouter" in llm_service.providers:
            success, result = test_explicit_fallback("gemini", "openrouter")
            logger.info(f"Fallback test (gemini->openrouter): {'SUCCESS' if success else 'FAILED'}")
            if not success:
                logger.error(f"Fallback failure reason: {result}")
        else:
            logger.warning("Cannot test fallback: need both gemini and openrouter providers")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Display available providers
    logger.info("Available LLM providers:")
    for provider_name in llm_service.providers.keys():
        logger.info(f"  - {provider_name}")
    logger.info(f"Default provider: {llm_service.default_provider}")
    
    # Run tests
    results = {}
    
    # Test each available provider
    for provider_name in llm_service.providers.keys():
        logger.info(f"Testing provider: {provider_name}")
        success, result = test_simple_prompt(provider_name)
        results[provider_name] = {"success": success, "result": result}
    
    # Display results
    logger.info("Provider test results:")
    for provider, result in results.items():
        status = 'SUCCESS' if result["success"] else 'FAILED'
        logger.info(f"  {provider}: {status}")
    
    # Test fallback if we have multiple providers
    fallback_success = None
    if len(llm_service.providers) > 1:
        logger.info("Testing fallback mechanism with mocked rate limit")
        if "gemini" in llm_service.providers and "openrouter" in llm_service.providers:
            fallback_success, fallback_result = test_explicit_fallback("gemini", "openrouter")
            logger.info(f"Fallback test (gemini->openrouter): {'SUCCESS' if fallback_success else 'FAILED'}")
            if not fallback_success:
                logger.error(f"Fallback failure reason: {fallback_result}")
        else:
            logger.warning("Cannot test fallback: need both gemini and openrouter providers")
    
    # Check if all tests passed
    all_passed = all(result["success"] for provider, result in results.items())
    if fallback_success is not None:
        all_passed = all_passed and fallback_success
    
    if all_passed:
        logger.info("✅ All tests PASSED!")
    else:
        logger.error("❌ Some tests FAILED! See above for details.")