"""
Test Gemini Batch API with small dataset
Bu script küçük bir test case seti ile Batch API'yi test eder
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from services.parallel_optimization_service import parallel_smart_select, TestCase, TestCaseList
from pydantic import BaseModel
from typing import Optional

async def test_small_batch():
    """Test with only 5 test cases = 10 comparisons"""
    
    print("="*80)
    print("🧪 SMALL BATCH TEST")
    print("="*80)
    
    # Create 5 simple test cases
    test_cases = [
        TestCase(
            ScenarioID="S1",
            TestCaseID="TC1",
            Title="User Login",
            Description="Test user login functionality",
            Objective="Verify login works"
        ),
        TestCase(
            ScenarioID="S1",
            TestCaseID="TC2",
            Title="User Login with wrong password",
            Description="Test login with incorrect credentials",
            Objective="Verify error message"
        ),
        TestCase(
            ScenarioID="S2",
            TestCaseID="TC3",
            Title="Add product to cart",
            Description="Test adding product to shopping cart",
            Objective="Verify cart updates"
        ),
        TestCase(
            ScenarioID="S2",
            TestCaseID="TC4",
            Title="Remove product from cart",
            Description="Test removing product from cart",
            Objective="Verify cart updates correctly"
        ),
        TestCase(
            ScenarioID="S3",
            TestCaseID="TC5",
            Title="Checkout process",
            Description="Test the checkout flow",
            Objective="Verify order completion"
        )
    ]
    
    print(f"📊 Test cases: {len(test_cases)}")
    print(f"📊 Expected comparisons: {len(test_cases) * (len(test_cases) - 1) // 2}")
    print()
    
    # Get API key from user
    api_key = input("Enter your Gemini API key (or press Enter for default): ").strip()
    if not api_key:
        api_key = "AIzaSyCV-4uNhn53rh5Yp5A6IrkrG5iMvko6O4Q"
    
    print(f"🔑 Using API key: {api_key[:10]}...{api_key[-5:]}")
    print()
    
    try:
        # Create TestCaseList wrapper
        test_case_list = TestCaseList(
            test_cases=test_cases,
            process_id="test_small"
        )
        
        # Run parallel smart selection
        result = await parallel_smart_select(
            test_case_list=test_case_list,
            api_key=api_key,
            selected_model="gemini-2.5-flash",
            use_file_mode=False  # Use inline mode for small test
        )
        
        print("\n" + "="*80)
        print("✅ SUCCESS!")
        print("="*80)
        print(f"Unique test cases: {len(result.test_cases)}")
        print(f"Similar groups: {len(result.similar_groups) if hasattr(result, 'similar_groups') else 0}")
        print()
        
        print("📋 Result Test Cases:")
        for tc in result.test_cases:
            print(f"  - {tc.TestCaseID}: {tc.Title}")
        
    except Exception as e:
        print("\n" + "="*80)
        print("❌ ERROR!")
        print("="*80)
        print(f"Error: {e}")
        print()
        
        # Print more details
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_small_batch())
