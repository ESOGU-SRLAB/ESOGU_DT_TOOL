#!/usr/bin/env python3
"""
Test test code generation API endpoint directly
"""

import asyncio
import aiohttp
import json
import os

async def test_test_code_generation_api():
    """Test test code generation API endpoint"""
    
    url = "http://localhost:8000/api/processes/test-code-generation"
    
    # Test data
    test_data = {
        "model": "gemini-2.5-flash",
        "api_key": os.getenv("GEMINI_API_KEY", ""),
        "session_id": "test_session_123",
        "custom_prompt": ""
    }
    
    # Create a test Python file
    test_file_content = '''def calculate_sum(a, b):
    """Calculate the sum of two numbers"""
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Arguments must be numbers")
    return a + b

def calculate_product(a, b):
    """Calculate the product of two numbers"""
    return a * b
'''
    
    try:
        # Prepare multipart form data
        form_data = aiohttp.FormData()
        
        # Add form fields
        form_data.add_field('model', test_data['model'])
        form_data.add_field('api_key', test_data['api_key'])
        form_data.add_field('session_id', test_data['session_id'])
        form_data.add_field('custom_prompt', test_data['custom_prompt'])
        
        # Add file
        form_data.add_field('files', test_file_content.encode(), 
                           filename='test_math.py', 
                           content_type='text/plain')
        
        print(f"🌐 Testing API: {url}")
        print(f"📝 Using model: {test_data['model']}")
        print(f"🔑 API key configured: {bool(test_data['api_key'])}")
        
        # Make API request
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=form_data) as response:
                
                print(f"📊 Status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print("✅ SUCCESS: Test code generation API working!")
                    
                    if 'summary' in result:
                        summary = result['summary']
                        print(f"📄 Generated {len(summary.get('generated_tests', []))} tests")
                        print(f"💾 Session saved: {summary.get('session_saved', False)}")
                        
                        if summary.get('generated_tests'):
                            first_test = summary['generated_tests'][0]
                            print(f"📝 First test preview:")
                            print("-" * 50)
                            print(f"Test case: {first_test.get('test_case_title', 'N/A')}")
                            test_code = first_test.get('generated_test_code', '')
                            print(test_code[:300] + "..." if len(test_code) > 300 else test_code)
                            print("-" * 50)
                    
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ FAILED: Status {response.status}")
                    print(f"Error: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_test_code_generation_api())
