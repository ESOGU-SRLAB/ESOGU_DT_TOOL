"""
Test script to verify Gemini 503 error handling and cooldown mechanism
"""

import asyncio
import logging
import sys
import os

# Add backend directory to path
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.append(backend_dir)

try:
    from utils.model_client import LLMClient
    from services.test_case_optimization_service import TestCase, _query_llm_similarity_with_retry
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please run this script from the STLC-Manager root directory")
    sys.exit(1)

# Setup logging to see our enhanced logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_gemini_cooldown():
    """Test Gemini API with cooldown mechanism"""
    print("🚀 Testing Gemini 2.5 Pro with Enhanced Cooldown Mechanism")
    print("=" * 60)
    
    # Test with a real API key (you should replace this)
    api_key = input("Enter your Gemini API key: ")
    if not api_key.strip():
        print("❌ API key is required for testing")
        return
    
    # Create test cases
    case1 = TestCase(
        ScenarioID="test1",
        TestCaseID="case1", 
        Title="User Login Test",
        Description="Test user login with valid credentials",
        Objective="Verify successful login"
    )
    
    case2 = TestCase(
        ScenarioID="test2",
        TestCaseID="case2",
        Title="User Authentication Test", 
        Description="Test user authentication with correct username and password",
        Objective="Ensure login works properly"
    )
    
    print(f"📝 Test Case 1: {case1.Title}")
    print(f"📝 Test Case 2: {case2.Title}")
    print()
    
    try:
        # Test with Gemini 2.5 Pro
        print("🔄 Starting LLM comparison with enhanced cooldown...")
        result = await _query_llm_similarity_with_retry(
            case1, case2,
            custom_prompt=None,
            selected_model="gemini-2.5-pro",
            api_key=api_key
        )
        
        print(f"✅ Comparison completed successfully!")
        print(f"📊 Result: Cases are {'SIMILAR' if result else 'DIFFERENT'}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    print("=" * 60)
    print("🏁 Test completed!")

async def test_multiple_requests():
    """Test multiple requests to verify cooldown behavior"""
    print("\n🔄 Testing Multiple Requests with Cooldown")
    print("=" * 60)
    
    api_key = input("Enter your Gemini API key for multiple request test: ")
    if not api_key.strip():
        print("❌ API key is required for testing")
        return
    
    # Create multiple test case pairs
    test_pairs = [
        (
            TestCase(ScenarioID="t1", TestCaseID="c1", Title="Login Test", Description="Test login"),
            TestCase(ScenarioID="t2", TestCaseID="c2", Title="Authentication Test", Description="Test auth")
        ),
        (
            TestCase(ScenarioID="t3", TestCaseID="c3", Title="Logout Test", Description="Test logout"),
            TestCase(ScenarioID="t4", TestCaseID="c4", Title="Session End Test", Description="Test session end")
        ),
        (
            TestCase(ScenarioID="t5", TestCaseID="c5", Title="Password Reset", Description="Reset password"),
            TestCase(ScenarioID="t6", TestCaseID="c6", Title="Forgot Password", Description="Recover password")
        )
    ]
    
    for i, (case1, case2) in enumerate(test_pairs, 1):
        print(f"\n🔄 Request {i}/3: Comparing {case1.Title} vs {case2.Title}")
        try:
            result = await _query_llm_similarity_with_retry(
                case1, case2,
                selected_model="gemini-2.5-pro",
                api_key=api_key
            )
            print(f"✅ Request {i} completed: {'SIMILAR' if result else 'DIFFERENT'}")
        except Exception as e:
            print(f"❌ Request {i} failed: {e}") 
    
    print("🏁 Multiple request test completed!")

if __name__ == "__main__":
    print("🧪 Gemini 503 Error Handling Test Suite")
    print("This test will demonstrate the enhanced cooldown mechanism")
    print("with 30s base + 2-30s random delays for Gemini API requests")
    print()
    
    try:
        asyncio.run(test_gemini_cooldown())
        asyncio.run(test_multiple_requests())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
