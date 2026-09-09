#!/usr/bin/env python3
"""
Test script to monitor LLM calls in bulk optimization
"""

import sys
import os
import asyncio
import logging
import json
from datetime import datetime

# Add backend directory to path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.append(backend_dir)

from services.test_case_optimization_service import TestCase, TestCaseList, bulk_smart_select
from utils.model_client import LLMClient

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class LLMCallCounter:
    def __init__(self):
        self.call_count = 0
        self.calls = []
    
    def log_call(self, prompt_preview):
        self.call_count += 1
        call_info = {
            "call_number": self.call_count,
            "timestamp": datetime.now().isoformat(),
            "prompt_preview": prompt_preview[:100] + "..." if len(prompt_preview) > 100 else prompt_preview
        }
        self.calls.append(call_info)
        print(f"\n🔥 LLM CALL #{self.call_count}")
        print(f"📝 Prompt Preview: {call_info['prompt_preview']}")
        print("-" * 50)

# Create global counter
call_counter = LLMCallCounter()

# Monkey patch LLMClient to count calls
original_generate_response = LLMClient.generate_response

async def counting_generate_response(self, prompt, temperature=0.7, max_tokens=4096, response_format=None):
    call_counter.log_call(prompt)
    return await original_generate_response(self, prompt, temperature, max_tokens, response_format)

LLMClient.generate_response = counting_generate_response

async def test_bulk_optimization_calls():
    """Test bulk optimization and count LLM calls"""
    print("🚀 Testing Bulk Optimization LLM Call Count")
    print("=" * 60)
    
    # Create test cases
    test_cases = [
        TestCase(
            ScenarioID="TC001",
            TestCaseID="TC001", 
            Title="User Login with Valid Credentials",
            Description="Test successful login with correct username and password",
            Objective="Verify that user can login successfully with valid credentials"
        ),
        TestCase(
            ScenarioID="TC002",
            TestCaseID="TC002",
            Title="Valid User Authentication", 
            Description="Test login functionality with valid user credentials",
            Objective="Ensure successful authentication with correct login details"
        ),
        TestCase(
            ScenarioID="TC003",
            TestCaseID="TC003",
            Title="User Logout Functionality",
            Description="Test user logout process",
            Objective="Verify that user can logout successfully"
        ),
        TestCase(
            ScenarioID="TC004",
            TestCaseID="TC004",
            Title="Invalid Password Login Test",
            Description="Test login with wrong password",
            Objective="Verify system rejects invalid credentials"
        )
    ]
    
    test_case_list = TestCaseList(test_cases=test_cases)
    
    print(f"📊 Total test cases: {len(test_cases)}")
    print(f"🎯 Expected for BULK: 1 LLM call")
    print(f"⚠️  If bulk fails, it will show specific error instead of falling back")
    print("\n🔍 Starting bulk optimization...")
    
    try:
        result = await bulk_smart_select(
            test_case_list, 
            selected_model="llama3.2:3b"
        )
        
        print("\n" + "=" * 60)
        print("📈 RESULTS:")
        print(f"✅ Process completed successfully")
        print(f"🔢 Total LLM calls made: {call_counter.call_count}")
        print(f"📋 Unique test cases found: {len(result.test_cases)}")
        print(f"🔄 Duplicates found: {len(result.duplicates)}")
        
        if call_counter.call_count == 1:
            print("✅ BULK OPTIMIZATION WORKING CORRECTLY - Only 1 LLM call made")
        else:
            print(f"❌ BULK OPTIMIZATION ISSUE - {call_counter.call_count} LLM calls made (should be 1)")
            print("\n🔍 Detailed call information:")
            for call in call_counter.calls:
                print(f"  - Call {call['call_number']}: {call['timestamp']}")
                print(f"    Preview: {call['prompt_preview']}")
        
        return call_counter.call_count
        
    except (ValueError, RuntimeError) as e:
        print(f"\n❌ BULK OPTIMIZATION SPECIFIC ERROR: {e}")
        print(f"🔢 LLM calls made before error: {call_counter.call_count}")
        print("✅ This is expected behavior - no fallback to individual processing")
        return call_counter.call_count
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return -1

if __name__ == "__main__":
    asyncio.run(test_bulk_optimization_calls())
