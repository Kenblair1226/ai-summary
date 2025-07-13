# LLM Provider System Test Guide

This guide covers the comprehensive test suite for the enhanced LLM provider system with model switching and automatic fallback capabilities.

## Test Files Overview

### 1. `test_llm_advanced.py`
**Core functionality tests** covering:
- ✅ Model switching based on task types (heavy/light)
- ✅ Automatic fallback when quota limits are hit
- ✅ Provider initialization and configuration
- ✅ Media content generation with different providers
- ✅ Error handling and rate limit detection
- ✅ Real-world integration scenarios

### 2. `test_llm_performance.py`
**Performance and load testing** including:
- ✅ Concurrent request handling
- ✅ Model switching performance impact
- ✅ Cascading failure scenarios
- ✅ Memory usage patterns
- ✅ Typical content generation workflows

### 3. `test_llm_config.py`
**Configuration and environment testing**:
- ✅ Various configuration scenarios
- ✅ Environment variable handling
- ✅ Edge cases in configuration
- ✅ Provider initialization failures

### 4. `test_llm_integration.py`
**Integration tests with genai_helper**:
- ✅ Real function integration
- ✅ Provider fallback in applications
- ✅ Model tier selection verification
- ✅ End-to-end workflow testing

### 5. `test_runner.py`
**Test runner utility** providing:
- ✅ Selective test execution
- ✅ Comprehensive reporting
- ✅ Easy CI/CD integration

## Running Tests

### Quick Start
```bash
# Run all tests
python test_runner.py

# Run specific test categories
python test_runner.py basic        # Core functionality
python test_runner.py performance  # Performance tests
python test_runner.py config      # Configuration tests
python test_runner.py all         # Everything
```

### Individual Test Files
```bash
# Run specific test file
python -m unittest test_llm_advanced.py -v
python -m unittest test_llm_performance.py -v
python -m unittest test_llm_config.py -v
python -m unittest test_llm_integration.py -v
```

### Specific Test Classes
```bash
# Run specific test class
python -m unittest test_llm_advanced.TestLLMModelSwitching -v
python -m unittest test_llm_performance.TestLLMPerformance -v
```

## Test Coverage

### Model Switching Tests
- ✅ Heavy model selection for complex tasks
- ✅ Light model selection for simple tasks
- ✅ Model tier configuration from environment
- ✅ Performance impact of model switching

### Fallback Mechanism Tests
- ✅ Rate limit detection and fallback
- ✅ Provider fallback on quota exceeded
- ✅ Cascading failure handling
- ✅ Multiple model fallback within tier

### Provider Tests
- ✅ Gemini provider functionality
- ✅ OpenRouter provider functionality
- ✅ LiteLLM provider functionality
- ✅ Provider initialization from environment

### Media Handling Tests
- ✅ Audio file processing with Gemini
- ✅ Image processing with OpenRouter
- ✅ Media fallback scenarios
- ✅ File upload and processing

### Error Handling Tests
- ✅ Rate limit error detection
- ✅ Network error handling
- ✅ Invalid configuration handling
- ✅ Graceful degradation

### Integration Tests
- ✅ genai_helper function integration
- ✅ Real application workflow testing
- ✅ End-to-end content generation
- ✅ Provider fallback in real scenarios

## Test Environment Setup

### Environment Variables
```bash
# Required for testing
export GEMINI_API_KEY="your_gemini_key"
export OPENROUTER_API_KEY="your_openrouter_key"
export LITELLM_API_KEY="your_litellm_key"
export LITELLM_MODEL="your_litellm_model"

# Model configuration
export HEAVY_MODELS="gemini-2.5-pro-exp-03-25,gpt-4-turbo,claude-3-opus"
export LIGHT_MODELS="gemini-1.5-flash,gpt-3.5-turbo,claude-3-haiku"

# Optional configuration
export DEFAULT_LLM_PROVIDER="gemini"
export SYSTEM_PROMPT="You are a helpful AI assistant."
```

### Dependencies
```bash
# Install test dependencies
pip install -r requirements.txt

# Additional test dependencies (if needed)
pip install unittest-xml-reporting coverage
```

## Test Scenarios Covered

### 1. Model Switching Scenarios
- **Heavy Tasks**: Article summarization, detailed analysis, content generation
- **Light Tasks**: Slug generation, tag extraction, simple formatting
- **Mixed Workflows**: Typical content processing pipelines

### 2. Fallback Scenarios
- **Rate Limit Fallback**: Automatic switching to next model in tier
- **Provider Fallback**: Switching to different provider on failure
- **Graceful Degradation**: Handling complete provider failures

### 3. Configuration Scenarios
- **Minimal Setup**: Single provider configuration
- **Full Setup**: All providers configured
- **Edge Cases**: Invalid configuration handling

### 4. Performance Scenarios
- **Concurrent Load**: Multiple simultaneous requests
- **Memory Management**: Long-running test scenarios
- **Stress Testing**: High-volume request handling

## Key Test Features

### Comprehensive Mocking
- ✅ Full provider API mocking
- ✅ File system operations mocking
- ✅ Network request mocking
- ✅ Environment variable mocking

### Real Integration Testing
- ✅ Actual genai_helper function testing
- ✅ End-to-end workflow validation
- ✅ Provider fallback in real scenarios
- ✅ Model tier selection verification

### Performance Validation
- ✅ Concurrent request handling
- ✅ Memory usage patterns
- ✅ Response time validation
- ✅ Scalability testing

### Error Scenario Testing
- ✅ Rate limit handling
- ✅ Network failure scenarios
- ✅ Invalid input handling
- ✅ Configuration error handling

## Expected Test Results

### Success Criteria
- All core functionality tests pass
- Performance tests complete within reasonable time
- Configuration tests handle edge cases gracefully
- Integration tests verify real-world usage

### Common Test Patterns
- **Setup**: Environment configuration and mocking
- **Execution**: Function calls with various parameters
- **Verification**: Response validation and behavior checking
- **Cleanup**: Resource cleanup and state reset

## Continuous Integration

### CI/CD Integration
```bash
# In your CI pipeline
python test_runner.py all
```

### Coverage Reporting
```bash
# Generate coverage report
coverage run --source=. test_runner.py all
coverage report -m
coverage html
```

## Troubleshooting Tests

### Common Issues
1. **Import Errors**: Ensure all dependencies are installed
2. **Environment Variables**: Check required env vars are set
3. **Mock Failures**: Verify mock configurations match actual APIs
4. **File Permissions**: Ensure test files can be created/deleted

### Debug Mode
```bash
# Run with debug logging
python -m unittest test_llm_advanced.py -v --debug
```

## Adding New Tests

### Test Structure
```python
def test_new_feature(self):
    """Test description"""
    # Setup
    # Execute
    # Verify
    # Cleanup (if needed)
```

### Best Practices
- Use descriptive test names
- Include docstrings for complex tests
- Mock external dependencies
- Test both success and failure scenarios
- Verify expected behavior thoroughly

This comprehensive test suite ensures the LLM provider system works correctly with model switching, automatic fallback, and all integrated functionality.