#!/usr/bin/env python3
"""
Test runner for LLM provider system tests.
Provides convenient way to run all tests with different configurations.
"""

import unittest
import sys
import os
from io import StringIO

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_test_suite(test_pattern="test_llm*.py", verbosity=2):
    """Run test suite with specified pattern"""
    # Discover and run tests
    loader = unittest.TestLoader()
    suite = loader.discover('.', pattern=test_pattern)
    
    # Run tests with custom result handling
    runner = unittest.TextTestRunner(verbosity=verbosity, stream=sys.stdout)
    result = runner.run(suite)
    
    return result

def run_basic_tests():
    """Run basic functionality tests"""
    print("=== Running Basic LLM Tests ===")
    return run_test_suite("test_llm_advanced.py")

def run_performance_tests():
    """Run performance tests"""
    print("=== Running Performance Tests ===")
    return run_test_suite("test_llm_performance.py")

def run_config_tests():
    """Run configuration tests"""
    print("=== Running Configuration Tests ===")
    return run_test_suite("test_llm_config.py")

def run_all_tests():
    """Run all LLM tests"""
    print("=== Running All LLM Tests ===")
    return run_test_suite("test_llm*.py")

def main():
    """Main test runner function"""
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "basic":
            result = run_basic_tests()
        elif test_type == "performance":
            result = run_performance_tests()
        elif test_type == "config":
            result = run_config_tests()
        elif test_type == "all":
            result = run_all_tests()
        else:
            print(f"Unknown test type: {test_type}")
            print("Available options: basic, performance, config, all")
            sys.exit(1)
    else:
        result = run_all_tests()
    
    # Print summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('Exception:')[-1].strip()}")
    
    # Exit with appropriate code
    if result.failures or result.errors:
        sys.exit(1)
    else:
        print("\nAll tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()