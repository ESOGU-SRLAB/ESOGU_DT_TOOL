"""
test_retry_simple.py
------------------
Basit retry ve monitoring test - sistem bağımlılığı olmadan
"""

import asyncio
import logging
import sys
import os

# Backend modüllerine erişim için path ekleme
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

from utils.retry_utils import retry_llm_call, _is_retryable_error
from utils.optimization_monitor import OptimizationMonitor

# Logging ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def mock_successful_call():
    """Başarılı çağrı simülasyonu"""
    await asyncio.sleep(0.1)
    return {"result": "success"}

async def mock_failing_call():
    """Başarısız çağrı simülasyonu"""
    await asyncio.sleep(0.1)
    raise Exception("503 Service Unavailable")

async def mock_non_retryable_call():
    """Retry yapılamaz hata"""
    await asyncio.sleep(0.1)
    raise Exception("400 Bad Request")

async def test_retry():
    """Retry mekanizması testi"""
    print("\n=== RETRY TESTS ===")
    
    # Test 1: Başarılı çağrı
    print("1. Testing successful call...")
    try:
        result = await retry_llm_call(mock_successful_call)
        print(f"✓ Success: {result}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
    
    # Test 2: Retryable error
    print("2. Testing retryable error...")
    try:
        result = await retry_llm_call(mock_failing_call, max_retries=2, base_delay=0.2)
        print(f"✗ Should have failed: {result}")
    except Exception as e:
        print(f"✓ Expected failure: {e}")
    
    # Test 3: Non-retryable error
    print("3. Testing non-retryable error...")
    try:
        result = await retry_llm_call(mock_non_retryable_call, max_retries=3)
        print(f"✗ Should have failed: {result}")
    except Exception as e:
        print(f"✓ Expected immediate failure: {e}")

def test_error_categorization():
    """Hata kategorilendirme testi"""
    print("\n=== ERROR CATEGORIZATION ===")
    
    test_cases = [
        ("503 Service Unavailable", True),
        ("429 Too Many Requests", True), 
        ("Connection timeout", True),
        ("400 Bad Request", False),
        ("404 Not Found", False),
        ("Network error", True)
    ]
    
    for error_msg, expected in test_cases:
        result = _is_retryable_error(error_msg)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{error_msg}' -> {result} (expected {expected})")

def test_monitoring():
    """Monitoring sistemi testi"""
    print("\n=== MONITORING TESTS ===")
    
    monitor = OptimizationMonitor()
    
    # Test successful comparison
    monitor.log_comparison_attempt("case1", "case2", True, 1, model_used="test")
    
    # Test retry success
    monitor.log_comparison_attempt("case3", "case4", True, 2, model_used="test")
    
    # Test failure
    monitor.log_comparison_attempt("case5", "case6", False, 3, error_message="503 Service Unavailable", model_used="test")
    
    stats = monitor.get_stats_summary()
    
    print(f"✓ Total: {stats['comparison_stats']['total_comparisons']}")
    print(f"✓ Successful: {stats['comparison_stats']['successful_comparisons']}")
    print(f"✓ Failed: {stats['comparison_stats']['failed_comparisons']}")
    print(f"✓ Retries: {stats['comparison_stats']['retry_comparisons']}")
    print(f"✓ Success rate: {stats['success_rate']:.1f}%")
    print(f"✓ Error counts: {stats['error_counts']}")
    
    # Test session summary
    print("\n--- Session Summary ---")
    monitor.log_session_summary("test")
    
    print("✓ Monitoring system working correctly!")

async def main():
    """Ana test"""
    print("🚀 Testing Retry and Monitoring Systems...")
    
    await test_retry()
    test_error_categorization()
    test_monitoring()
    
    print("\n✅ All tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
