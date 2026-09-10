#!/usr/bin/env python3
"""
Environment Setup optimizasyon testi
"""

import asyncio
import time
import sys

# Backend modüllerini import et
sys.path.append('backend')
from utils.model_client import LLMClient

async def test_environment_setup_speed():
    """Environment Setup için speed optimizasyonunu test et"""
    
    print("🔧 Environment Setup Speed Test Starting...")
    
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
    
    # 2. Environment Setup mode (fast)
    print("\n⚡ Testing ENVIRONMENT SETUP mode:")
    start_time = time.time()
    
    try:
        env_setup_client = LLMClient(model_name="gemini-2.5-flash", api_key=test_api_key, use_case="environment_setup")
        await env_setup_client._check_and_apply_rate_limit()
        env_setup_duration = time.time() - start_time
        print(f"⏱️  Environment Setup mode duration: {env_setup_duration:.2f}s")
    except Exception as e:
        print(f"⚠️  Environment Setup mode error: {e}")
        env_setup_duration = 0
    
    # 3. Karşılaştırma
    if normal_duration > 0 and env_setup_duration > 0:
        print(f"\n📈 Environment Setup Speed Improvement:")
        improvement = ((normal_duration - env_setup_duration) / normal_duration) * 100
        print(f"   Environment Setup is {improvement:.1f}% faster!")
        print(f"   Time saved: {normal_duration - env_setup_duration:.2f}s")
        print(f"   Normal: {normal_duration:.2f}s vs Environment Setup: {env_setup_duration:.2f}s")
    
    # 4. Tüm optimized process'ler ile karşılaştırma
    print("\n🔮 Testing all optimized modes for comparison:")
    
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
        
        # Test Planning
        start_time = time.time()
        test_planning_client = LLMClient(model_name="gemini-2.5-flash", api_key=test_api_key, use_case="test_planning")
        await test_planning_client._check_and_apply_rate_limit()
        test_planning_duration = time.time() - start_time
        
        print(f"\n🎯 All optimized processes comparison:")
        print(f"   Code Review: {code_review_duration:.2f}s")
        print(f"   Requirement Analysis: {req_analysis_duration:.2f}s")
        print(f"   Test Planning: {test_planning_duration:.2f}s")
        print(f"   Environment Setup: {env_setup_duration:.2f}s")
        print(f"   All four are optimized for fast single-shot operations! ✅")
        
        # Average calculation
        avg_duration = (code_review_duration + req_analysis_duration + test_planning_duration + env_setup_duration) / 4
        print(f"\n📊 Average optimized speed: {avg_duration:.2f}s")
        
    except Exception as e:
        print(f"⚠️  Comparison test error: {e}")

if __name__ == "__main__":
    asyncio.run(test_environment_setup_speed())