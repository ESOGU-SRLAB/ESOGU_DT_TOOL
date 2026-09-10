#!/usr/bin/env python3
"""
Test script to verify Gemini integration in test code generation service.
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from utils.model_client import LLMClient

async def test_gemini_test_code_generation():
    """Test Gemini model for test code generation"""
    
    print("🧪 Testing Gemini 2.5 Flash for Test Code Generation...")
    
    # Test with a sample code snippet and test case
    test_code_prompt = """
    Based on the following source code and test case, generate a comprehensive unit test:

    SOURCE CODE:
    ```python
    def calculate_discount(price, discount_percentage):
        if price <= 0:
            raise ValueError("Price must be positive")
        if discount_percentage < 0 or discount_percentage > 100:
            raise ValueError("Discount percentage must be between 0 and 100")
        
        discount_amount = price * (discount_percentage / 100)
        final_price = price - discount_amount
        return final_price
    ```

    TEST CASE:
    - Test Case ID: TC001
    - Title: Test valid discount calculation
    - Description: Verify that discount is calculated correctly for valid inputs
    - Input: price=100, discount_percentage=20
    - Expected Output: 80.0

    REQUIREMENTS:
    Generate a complete Python unit test using pytest framework that includes:
    1. Test setup
    2. Test execution with the given input values  
    3. Assertions to verify the expected output
    4. Proper test naming and documentation
    """
    
    try:
        # Initialize Gemini client  
        import os
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY environment variable not set!")
            return False
            
        client = LLMClient(model_name="gemini-2.5-flash", api_key=api_key, use_case="test_code_generation")
        
        # Generate test code
        print("📝 Generating test code with Gemini...")
        response = await client.generate_response(
            test_code_prompt,
            temperature=0.3,  # Lower temperature for code generation
            max_tokens=2048
        )
        
        if response:
            print("✅ SUCCESS: Test code generated!")
            print(f"📄 Generated test code length: {len(response)} characters")
            print(f"📝 Generated test code preview:")
            print("-" * 50)
            print(response[:800] + "..." if len(response) > 800 else response)
            print("-" * 50)
            return True
        else:
            print("❌ FAILED: No response generated")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

async def main():
    """Run the test"""
    print("🚀 Testing Gemini Integration for Test Code Generation")
    print("=" * 60)
    
    success = await test_gemini_test_code_generation()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Gemini integration test PASSED!")
        print("✅ Gemini can be used for test code generation")
    else:
        print("❌ Gemini integration test FAILED!")
        print("🔧 Check API keys and model configuration")

if __name__ == "__main__":
    asyncio.run(main())