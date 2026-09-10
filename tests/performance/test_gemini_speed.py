#!/usr/bin/env python3
"""
Gemini Code Review hız testi
"""

import asyncio
import time
import os
import sys

# Backend modüllerini import et
sys.path.append('backend')
from utils.model_client import LLMClient

async def test_gemini_speed():
    """Gemini için code review hızını test et"""
    
    print("🔮 Gemini Speed Test Starting...")
    
    # Dummy API key (gerçek çağrı yapmayacağız)
    test_api_key = "dummy-key-for-testing"
    
    # 1. Normal Gemini mode (bulk operations)
    print("\n📊 Testing Gemini NORMAL mode:")
    start_time = time.time()
    
    try:
        normal_gemini = LLMClient(model_name="gemini-2.5-flash", api_key=test_api_key, use_case="test_generation")
        await normal_gemini._check_and_apply_rate_limit()
        normal_duration = time.time() - start_time
        print(f"⏱️  Normal Gemini duration: {normal_duration:.2f}s")
    except Exception as e:
        print(f"⚠️  Normal mode error: {e}")
        normal_duration = 0
    
    # 2. Code review Gemini mode (fast)
    print("\n⚡ Testing Gemini CODE REVIEW mode:")
    start_time = time.time()
    
    try:
        review_gemini = LLMClient(model_name="gemini-2.5-flash", api_key=test_api_key, use_case="code_review")
        await review_gemini._check_and_apply_rate_limit()
        review_duration = time.time() - start_time
        print(f"⏱️  Code review Gemini duration: {review_duration:.2f}s")
    except Exception as e:
        print(f"⚠️  Code review mode error: {e}")
        review_duration = 0
    
    # 3. Karşılaştırma
    if normal_duration > 0 and review_duration > 0:
        print(f"\n📈 Gemini Speed Improvement:")
        improvement = ((normal_duration - review_duration) / normal_duration) * 100
        print(f"   Code Review is {improvement:.1f}% faster!")
        print(f"   Time saved: {normal_duration - review_duration:.2f}s")
        print(f"   Normal: {normal_duration:.2f}s vs Review: {review_duration:.2f}s")

if __name__ == "__main__":
    asyncio.run(test_gemini_speed())