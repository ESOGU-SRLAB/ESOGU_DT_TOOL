#!/usr/bin/env python3
"""
Quick test to debug the finish_reason=2 issue with small prompts.
This will help identify if it's a content issue or a token configuration issue.
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from utils.model_client import LLMClient

async def test_simple_prompt():
    """Test with a very simple prompt to isolate the issue"""
    
    client = LLMClient(model="gemini-2.5-flash", use_case="test_planning")
    
    simple_prompt = "Write a brief test plan for a simple calculator application with add and subtract functions."
    
    print(f"📏 Simple prompt length: {len(simple_prompt)} characters")
    print(f"🚀 Testing simple prompt...")
    
    try:
        # Test with different max_tokens values
        for max_tokens in [1024, 2048, 4096, 8192]:
            print(f"\n🔧 Testing with max_tokens={max_tokens}")
            response = await client.generate_response(
                simple_prompt, 
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            if response:
                print(f"✅ SUCCESS with max_tokens={max_tokens}")
                print(f"📄 Response length: {len(response)} chars")
                return True
            else:
                print(f"❌ FAILED with max_tokens={max_tokens}")
                
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

async def test_medium_structured_prompt():
    """Test with a structured prompt similar to what the services generate"""
    
    client = LLMClient(model="gemini-2.5-flash", use_case="test_planning") 
    
    structured_prompt = """
    Please analyze the following for comprehensive test planning:

    PROJECT CONTEXT:
    A web application with user authentication and basic CRUD operations.

    CODE STRUCTURE:
    - User authentication system
    - Database models for users and posts
    - REST API endpoints
    - Frontend React components

    REQUIREMENTS:
    1. Users must be able to register and login
    2. Authenticated users can create, read, update, delete posts
    3. System must validate input data
    4. Error handling must be comprehensive

    TASK:
    Generate a detailed test plan including:
    - Test strategy overview
    - Functional test cases
    - Integration test scenarios
    - Performance considerations
    - Security testing approach

    Please provide a comprehensive response with detailed explanations.
    """
    
    print(f"\n📏 Structured prompt length: {len(structured_prompt)} characters")
    print(f"🚀 Testing structured prompt...")
    
    try:
        response = await client.generate_response(
            structured_prompt, 
            max_tokens=8192,
            temperature=0.7
        )
        
        if response:
            print("✅ Structured prompt succeeded!")
            print(f"📄 Response length: {len(response)} chars")
            print(f"📝 Response preview: {response[:300]}...")
            return True
        else:
            print("❌ Structured prompt failed")
            return False
            
    except Exception as e:
        print(f"❌ Structured prompt error: {e}")
        return False

async def main():
    """Run diagnostic tests"""
    print("🔍 Debugging Gemini 2.5 Flash finish_reason=2 issue")
    print("=" * 60)
    
    # Test simple prompt first
    simple_success = await test_simple_prompt()
    
    # Test structured prompt
    structured_success = await test_medium_structured_prompt()
    
    print("\n" + "=" * 60)
    print("📊 DIAGNOSTIC RESULTS:")
    print(f"Simple prompt:     {'✅ PASS' if simple_success else '❌ FAIL'}")
    print(f"Structured prompt: {'✅ PASS' if structured_success else '❌ FAIL'}")
    
    if not simple_success:
        print("\n🚨 Issue is with basic Gemini configuration or API setup")
    elif not structured_success:
        print("\n🚨 Issue is with prompt structure or content length")
    else:
        print("\n✅ Basic prompts work - issue might be with specific service prompts")

if __name__ == "__main__":
    asyncio.run(main())