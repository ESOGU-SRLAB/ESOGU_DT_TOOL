#!/usr/bin/env python3
"""
Test script to verify Gemini 2.5 Flash can handle large prompts with new token limits.
This simulates the large prompts that were causing finish_reason=2 errors.
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from utils.model_client import LLMClient

async def test_large_prompt():
    """Test Gemini 2.5 with a very large prompt similar to real use case"""
    
    # Initialize Gemini client
    client = LLMClient(model="gemini-2.5-flash", use_case="test_planning")
    
    # Create a large prompt similar to what requirement analysis would send
    # This simulates a large code file + requirements document
    large_code_content = """
    class TestApplication:
        def __init__(self):
            self.database = Database()
            self.user_service = UserService()
            self.auth_service = AuthenticationService()
            
        def process_user_request(self, request):
            if not self.auth_service.validate_token(request.token):
                raise UnauthorizedError("Invalid token")
            
            user = self.user_service.get_user(request.user_id)
            if not user:
                raise UserNotFoundError("User not found")
            
            # Process the request based on type
            if request.type == "CREATE":
                return self.create_resource(request)
            elif request.type == "UPDATE":
                return self.update_resource(request)
            elif request.type == "DELETE":
                return self.delete_resource(request)
            else:
                raise InvalidRequestError("Unknown request type")
    """ * 100  # Repeat 100 times to make it large
    
    large_requirements = """
    Business Requirements:
    1. The system must handle user authentication securely
    2. All user data must be encrypted in transit and at rest
    3. The system must support CRUD operations for all resources
    4. Error handling must be comprehensive and user-friendly
    5. The system must log all security-related events
    6. Performance requirements: response time < 2 seconds for 95% of requests
    7. The system must support concurrent users up to 1000 simultaneous connections
    8. Data backup must be performed daily with retention period of 30 days
    9. The system must comply with GDPR regulations for data privacy
    10. Integration with third-party services must be fault-tolerant
    """ * 50  # Repeat 50 times
    
    test_prompt = f"""
    Please analyze the following code and requirements for comprehensive test planning:
    
    CODE FILES:
    {large_code_content}
    
    REQUIREMENTS DOCUMENT:
    {large_requirements}
    
    Please provide:
    1. Detailed test strategy
    2. Test scenarios for each requirement
    3. Risk analysis
    4. Test data requirements
    5. Test environment setup
    6. Acceptance criteria
    """
    
    print(f"📏 Test prompt length: {len(test_prompt)} characters")
    print(f"📊 Estimated tokens: ~{len(test_prompt.split())}")
    
    try:
        print("🚀 Testing Gemini 2.5 Flash with large prompt...")
        response = await client.generate_response(test_prompt, max_tokens=8192)
        
        if response:
            print("✅ SUCCESS: Large prompt processed successfully!")
            print(f"📄 Response length: {len(response)} characters")
            print(f"📝 Response preview: {response[:500]}...")
            return True
        else:
            print("❌ FAILED: No response received")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

async def test_medium_prompt():
    """Test with a medium-sized prompt to verify normal operation"""
    
    client = LLMClient(model="gemini-2.5-flash", use_case="requirement_analysis")
    
    medium_prompt = """
    Analyze the following simple application for requirements:
    
    class Calculator:
        def add(self, a, b):
            return a + b
        
        def subtract(self, a, b):
            return a - b
    
    Requirements:
    - The calculator should perform basic arithmetic
    - All operations should handle numeric inputs
    - Error handling for invalid inputs is required
    
    Please provide a detailed analysis.
    """
    
    print("\n🚀 Testing medium-sized prompt...")
    try:
        response = await client.generate_response(medium_prompt, max_tokens=4096)
        if response:
            print("✅ Medium prompt test succeeded!")
            print(f"📄 Response preview: {response[:200]}...")
            return True
        else:
            print("❌ Medium prompt test failed")
            return False
    except Exception as e:
        print(f"❌ Medium prompt error: {e}")
        return False

async def main():
    """Run all tests"""
    print("🧪 Testing Gemini 2.5 Flash with improved token limits...")
    print("=" * 60)
    
    # Test medium prompt first (should always work)
    medium_success = await test_medium_prompt()
    
    # Test large prompt (this was failing before)
    large_success = await test_large_prompt()
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    print(f"Medium prompt: {'✅ PASS' if medium_success else '❌ FAIL'}")
    print(f"Large prompt:  {'✅ PASS' if large_success else '❌ FAIL'}")
    
    if medium_success and large_success:
        print("\n🎉 All tests passed! Token limit improvements are working.")
    elif medium_success:
        print("\n⚠️  Medium prompts work, but large prompts still have issues.")
    else:
        print("\n❌ Tests failed. There may be configuration issues.")

if __name__ == "__main__":
    asyncio.run(main())