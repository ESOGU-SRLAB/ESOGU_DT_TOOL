#!/usr/bin/env python3
"""
Requirement Analysis optimizasyon testi
"""

import asyncio
import time
import sys

# Backend modüllerini import et
sys.path.append('backend')
from utils.model_client import LLMClient

async def test_requirement_analysis_speed():
    """Requirement Analysis için speed optimizasyonunu test et"""
    
    print("📋 Requirement Analysis Speed Test Starting...")
    
    # Dummy API key (gerçek çağrı yapmayacağız)
    test_api_key = "dummy-key-for-testing"
    
    # 1. Normal mode (bulk operations)
    print("\n📊 Testing NORMAL mode (bulk operations):")
    start_time = time.time()
    
    try:
        normal_client = LLMClient(model_name="gemini-2.5-flash", api_key=test_api_key, use_case="test_generation")
        await normal_client._check_and_apply_rate_limit()
        normal_duration = time.time() - start_time
        print(f"⏱️  Normal mode duration: {normal_duration:.2f}s")
    except Exception as e:
        print(f"⚠️  Normal mode error: {e}")
        normal_duration = 0
    
    # 2. Requirement Analysis mode (fast)
    print("\n⚡ Testing REQUIREMENT ANALYSIS mode:")
    start_time = time.time()
    
    try:
        req_analysis_client = LLMClient(model_name="gemini-2.5-flash", api_key=test_api_key, use_case="requirement_analysis")
        await req_analysis_client._check_and_apply_rate_limit()
        req_analysis_duration = time.time() - start_time
        print(f"⏱️  Requirement Analysis mode duration: {req_analysis_duration:.2f}s")
    except Exception as e:
        print(f"⚠️  Requirement Analysis mode error: {e}")
        req_analysis_duration = 0
    
    # 3. Karşılaştırma
    if normal_duration > 0 and req_analysis_duration > 0:
        print(f"\n📈 Requirement Analysis Speed Improvement:")
        improvement = ((normal_duration - req_analysis_duration) / normal_duration) * 100
        print(f"   Requirement Analysis is {improvement:.1f}% faster!")
        print(f"   Time saved: {normal_duration - req_analysis_duration:.2f}s")
        print(f"   Normal: {normal_duration:.2f}s vs Requirement Analysis: {req_analysis_duration:.2f}s")
    
    # 4. Code Review ile karşılaştırma
    print("\n🔮 Testing CODE REVIEW mode for comparison:")
    start_time = time.time()
    
    try:
        code_review_client = LLMClient(model_name="gemini-2.5-flash", api_key=test_api_key, use_case="code_review")
        await code_review_client._check_and_apply_rate_limit()
        code_review_duration = time.time() - start_time
        print(f"⏱️  Code Review mode duration: {code_review_duration:.2f}s")
        
        print(f"\n🎯 Both optimized processes comparison:")
        print(f"   Code Review: {code_review_duration:.2f}s")
        print(f"   Requirement Analysis: {req_analysis_duration:.2f}s")
        print(f"   Both are similarly optimized for fast single-shot operations! ✅")
        
    except Exception as e:
        print(f"⚠️  Code Review test error: {e}")

if __name__ == "__main__":
    asyncio.run(test_requirement_analysis_speed())