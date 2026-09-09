#!/usr/bin/env python3
"""
Code Review hız testi - Cooldown optimizasyonunu test et
"""

import asyncio
import time
from backend.utils.model_client import LLMClient

async def test_code_review_speed():
    """Code review için hızlı çalışmayı test et"""
    
    print("🚀 Code Review Speed Test Starting...")
    
    # 1. Normal mode (bulk operations için)
    print("\n📊 Testing NORMAL mode (bulk operations):")
    start_time = time.time()
    
    normal_client = LLMClient(model_name="llama-3.2-1b-instruct", use_case="test_generation")
    await normal_client._check_and_apply_rate_limit()
    
    normal_duration = time.time() - start_time
    print(f"⏱️  Normal mode duration: {normal_duration:.2f}s")
    
    # 2. Code review mode (hızlı)
    print("\n⚡ Testing CODE REVIEW mode (fast):")
    start_time = time.time()
    
    review_client = LLMClient(model_name="llama-3.2-1b-instruct", use_case="code_review")
    await review_client._check_and_apply_rate_limit()
    
    review_duration = time.time() - start_time
    print(f"⏱️  Code review mode duration: {review_duration:.2f}s")
    
    # 3. Karşılaştırma
    print(f"\n📈 Speed Improvement:")
    if normal_duration > 0:
        improvement = ((normal_duration - review_duration) / normal_duration) * 100
        print(f"   Code Review is {improvement:.1f}% faster!")
        print(f"   Time saved: {normal_duration - review_duration:.2f}s")
    
    # 4. Gemini ile test (API key varsa)
    try:
        print("\n🔮 Testing with Gemini (simulated):")
        gemini_start = time.time()
        
        # Bu test için gerçek API çağrısı yapmayacağız, sadece rate limit kontrolü
        # API key olmadan test etmek için local model kullan
        gemini_client = LLMClient(model_name="llama-3.2-1b-instruct", use_case="code_review")
        await gemini_client._check_and_apply_rate_limit()
        
        gemini_duration = time.time() - gemini_start
        print(f"⏱️  Code review optimized mode: {gemini_duration:.2f}s")
        
    except Exception as e:
        print(f"⚠️  Test skipped: {e}")

if __name__ == "__main__":
    asyncio.run(test_code_review_speed())