#!/usr/bin/env python3
"""
Test Gemini API key directly without the application
"""

import asyncio
import os
import google.generativeai as genai

async def test_direct_gemini_api():
    """Test Gemini API directly"""
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required")
    
    try:
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Get model
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Simple test prompt
        prompt = "Generate a simple Python unit test for a function that adds two numbers."
        
        print("🔑 Testing configured Gemini API key")
        print(f"📝 Sending prompt: {prompt}")
        
        # Generate response
        response = model.generate_content(prompt)
        
        if response and response.text:
            print("✅ SUCCESS: Gemini API working!")
            print(f"📄 Response length: {len(response.text)} characters")
            print(f"📝 Response preview:")
            print("-" * 50)
            print(response.text[:500] + "..." if len(response.text) > 500 else response.text)
            print("-" * 50)
            return True
        else:
            print("❌ FAILED: No response text")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_direct_gemini_api())
