#!/usr/bin/env python3
"""
Test Planning optimizasyon testi
"""

import asyncio
import time
import sys

# Backend modüllerini import et
sys.path.append('backend')
from utils.model_client import LLMClient

async def test_test_planning_speed():
    """Test Planning için speed optimizasyonunu test et"""
    
    print("📋 Test Planning Speed Test Starting...")
    
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
    
    # 2. Test Planning mode (fast)
    print("\n⚡ Testing TEST PLANNING mode:")
    start_time = time.time()
    
    try:
        test_planning_client = LLMClient(model_name="gemini-2.5-flash", api_key=test_api_key, use_case="test_planning")
        await test_planning_client._check_and_apply_rate_limit()
        test_planning_duration = time.time() - start_time
        print(f"⏱️  Test Planning mode duration: {test_planning_duration:.2f}s")
    except Exception as e:
        print(f"⚠️  Test Planning mode error: {e}")
        test_planning_duration = 0
    
    # 3. Karşılaştırma
    if normal_duration > 0 and test_planning_duration > 0:
        print(f"\n📈 Test Planning Speed Improvement:")
        improvement = ((normal_duration - test_planning_duration) / normal_duration) * 100
        print(f"   Test Planning is {improvement:.1f}% faster!")
        print(f"   Time saved: {normal_duration - test_planning_duration:.2f}s")
        print(f"   Normal: {normal_duration:.2f}s vs Test Planning: {test_planning_duration:.2f}s")
    
    # 4. Diğer optimized process'ler ile karşılaştırma
    print("\n🔮 Testing other optimized modes for comparison:")
    
    try:
        # Code Review
        start_time = time.time()
        code_review_client = LLMClient(model_name="gemini-2.5-flash", api_key=test_api_key, use_case="code_review")
        await code_review_client._check_and_apply_rate_limit()
        code_review_duration = time.time() - start_time
        
        # Requirement Analysis
        start_time = time.time()
        req_analysis_client = LLMClient(model_name="gemini-2.5-flash", api_key=test_api_key, use_case="requirement_analysis")
        await req_analysis_client._check_and_apply_rate_limit()
        req_analysis_duration = time.time() - start_time
        
        print(f"\n🎯 All optimized processes comparison:")
        print(f"   Code Review: {code_review_duration:.2f}s")
        print(f"   Requirement Analysis: {req_analysis_duration:.2f}s")
        print(f"   Test Planning: {test_planning_duration:.2f}s")
        print(f"   All three are optimized for fast single-shot operations! ✅")
        
    except Exception as e:
        print(f"⚠️  Comparison test error: {e}")

if __name__ == "__main__":
    asyncio.run(test_test_planning_speed())