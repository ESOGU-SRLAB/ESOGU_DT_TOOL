import asyncio
import sys
import os
sys.path.append('./backend')

from backend.services.review_service import ReviewService
from backend.utils.model_client import LLMClient

async def test_gemini_fix():
    try:
        print("🧪 Testing Gemini API fix for finish_reason=2 error...")
        
        # Test the Gemini client with a simple prompt
        client = LLMClient('gemini-2.5-flash', use_case='code_review')
        
        # Test with a simple code review prompt
        test_prompt = """Please review this simple C++ code:

#include <iostream>
using namespace std;

int main() {
    cout << "Hello World" << endl;
    return 0;
}

Provide feedback on code quality and best practices."""
        
        print('📤 Testing Gemini API with sanitized prompt...')
        result = await client.generate_response(test_prompt)
        print('✅ Success! Response received:')
        print(result[:200] + '...' if len(result) > 200 else result)
        
    except Exception as e:
        print(f'❌ Error: {e}')
        return False
        
    return True

if __name__ == "__main__":
    success = asyncio.run(test_gemini_fix())
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n💥 Test failed!")