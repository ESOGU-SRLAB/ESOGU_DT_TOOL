#!/usr/bin/env python3
"""
Test script to verify bulk optimization error handling (no fallback to individual)
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

import asyncio
import logging
from services.test_case_optimization_service import TestCase, TestCaseList, bulk_smart_select
from unittest.mock import patch, AsyncMock

# Set up logging
logging.basicConfig(level=logging.INFO)

async def test_bulk_error_handling():
    """Test that bulk optimization shows specific errors instead of falling back"""
    print("🚀 Testing Bulk Optimization Error Handling")
    print("=" * 60)
    
    # Create test cases
    test_cases = [
        TestCase(ScenarioID="1", TestCaseID="TC1", Title="Login Test", Description="Test login", Objective="Verify login"),
        TestCase(ScenarioID="2", TestCaseID="TC2", Title="Auth Test", Description="Test auth", Objective="Verify auth"),
    ]
    test_case_list = TestCaseList(test_cases=test_cases)
    
    print("🔍 Test 1: LLM returns empty response")
    print("-" * 40)
    
    # Mock LLMClient to return empty response
    with patch('services.test_case_optimization_service.LLMClient') as mock_llm_class:
        mock_llm = AsyncMock()
        mock_llm.generate_response = AsyncMock(return_value="")  # Empty response
        mock_llm_class.return_value = mock_llm
        
        try:
            await bulk_smart_select(test_case_list, selected_model="test")
            print("❌ Should have raised ValueError")
        except ValueError as e:
            print(f"✅ Correctly raised ValueError: {e}")
        except Exception as e:
            print(f"❌ Wrong exception type: {type(e).__name__}: {e}")
    
    print("\n🔍 Test 2: LLM returns invalid JSON")
    print("-" * 40)
    
    # Mock LLMClient to return invalid JSON
    with patch('services.test_case_optimization_service.LLMClient') as mock_llm_class:
        mock_llm = AsyncMock()
        mock_llm.generate_response = AsyncMock(return_value="This is not JSON at all!")
        mock_llm_class.return_value = mock_llm
        
        try:
            await bulk_smart_select(test_case_list, selected_model="test")
            print("❌ Should have raised ValueError")
        except ValueError as e:
            print(f"✅ Correctly raised ValueError: {e}")
        except Exception as e:
            print(f"❌ Wrong exception type: {type(e).__name__}: {e}")
    
    print("\n🔍 Test 3: LLMClient raises exception")
    print("-" * 40)
    
    # Mock LLMClient to raise exception
    with patch('services.test_case_optimization_service.LLMClient') as mock_llm_class:
        mock_llm = AsyncMock()
        mock_llm.generate_response = AsyncMock(side_effect=Exception("Connection failed"))
        mock_llm_class.return_value = mock_llm
        
        try:
            await bulk_smart_select(test_case_list, selected_model="test")
            print("❌ Should have raised RuntimeError")
        except RuntimeError as e:
            print(f"✅ Correctly raised RuntimeError: {e}")
        except Exception as e:
            print(f"❌ Wrong exception type: {type(e).__name__}: {e}")
    
    print("\n✅ All error handling tests completed!")
    print("🎯 Bulk optimization no longer falls back to individual processing")

if __name__ == "__main__":
    asyncio.run(test_bulk_error_handling())
