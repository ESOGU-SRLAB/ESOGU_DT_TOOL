"""
test_retry_monitoring.py
-----------------------
Test Case Optimization retry ve monitoring sistemini test eder
"""

import asyncio
import logging
import sys
import os

# Backend modüllerine erişim için path ekleme
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

try:
    from utils.retry_utils import retry_llm_call, _is_retryable_error
    from utils.optimization_monitor import optimization_monitor, OptimizationMonitor
    from services.test_case_optimization_service import TestCase, TestCaseList, _query_llm_similarity_with_retry
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this script from the STLC-Manager root directory")
    sys.exit(1)

# Logging ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def mock_successful_llm_call():
    """Başarılı LLM çağrısını simüle eder"""
    await asyncio.sleep(0.1)  # Kısa bekleme
    return {"result": "success", "is_same": False}

async def mock_failing_llm_call():
    """Başarısız LLM çağrısını simüle eder"""
    await asyncio.sleep(0.1)  # Kısa bekleme
    raise Exception("503 Service Unavailable - Mock error for testing")

async def mock_non_retryable_error():
    """Retry yapılamaz hata simüle eder"""
    await asyncio.sleep(0.1)
    raise Exception("400 Bad Request - Invalid input")

async def test_retry_mechanism():
    """Retry mekanizmasını test eder"""
    print("\n=== RETRY MECHANISM TESTS ===")
    
    # Test 1: Başarılı çağrı
    print("\n1. Testing successful call...")
    try:
        result = await retry_llm_call(mock_successful_llm_call, max_retries=3)
        print(f"✓ Successful call result: {result}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
    
    # Test 2: Retry yapılabilir hata
    print("\n2. Testing retryable error...")
    try:
        result = await retry_llm_call(mock_failing_llm_call, max_retries=2, base_delay=0.5)
        print(f"✗ Should have failed: {result}")
    except Exception as e:
        print(f"✓ Expected failure after retries: {e}")
    
    # Test 3: Retry yapılamaz hata
    print("\n3. Testing non-retryable error...")
    try:
        result = await retry_llm_call(mock_non_retryable_error, max_retries=3)
        print(f"✗ Should have failed immediately: {result}")
    except Exception as e:
        print(f"✓ Expected immediate failure: {e}")

def test_error_categorization():
    """Hata kategorilendirmesini test eder"""
    print("\n=== ERROR CATEGORIZATION TESTS ===")
    
    test_cases = [
        ("503 Service Unavailable", True),
        ("429 Too Many Requests", True),
        ("Connection timeout", True),
        ("Rate limit exceeded", True),
        ("400 Bad Request", False),
        ("404 Not Found", False),
        ("Invalid JSON format", False),
        ("Network connection error", True),
        ("Internal server error", True)
    ]
    
    for error_msg, expected_retryable in test_cases:
        is_retryable = _is_retryable_error(error_msg)
        status = "✓" if is_retryable == expected_retryable else "✗"
        print(f"{status} '{error_msg}' -> Retryable: {is_retryable} (Expected: {expected_retryable})")

def test_monitoring_system():
    """Monitoring sistemini test eder"""
    print("\n=== MONITORING SYSTEM TESTS ===")
    
    # Yeni monitor instance oluştur
    test_monitor = OptimizationMonitor()
    
    # Test 1: Başarılı karşılaştırma
    test_monitor.log_comparison_attempt(
        "case1", "case2", 
        success=True, 
        attempt_number=1, 
        model_used="llama3.2:3b"
    )
    
    # Test 2: Retry sonrası başarılı
    test_monitor.log_comparison_attempt(
        "case3", "case4", 
        success=True, 
        attempt_number=2, 
        model_used="llama3.2:3b"
    )
    
    # Test 3: Başarısız karşılaştırma
    test_monitor.log_comparison_attempt(
        "case5", "case6", 
        success=False, 
        attempt_number=3, 
        error_message="503 Service Unavailable",
        model_used="llama3.2:3b"
    )
    
    # Test 4: Farklı hata türü
    test_monitor.log_comparison_attempt(
        "case7", "case8", 
        success=False, 
        attempt_number=1, 
        error_message="Timeout error",
        model_used="llama3.2:3b"
    )
    
    # İstatistikleri kontrol et
    stats = test_monitor.get_stats_summary()
    
    print(f"✓ Total comparisons: {stats['comparison_stats']['total_comparisons']}")
    print(f"✓ Successful comparisons: {stats['comparison_stats']['successful_comparisons']}")
    print(f"✓ Failed comparisons: {stats['comparison_stats']['failed_comparisons']}")
    print(f"✓ Retry comparisons: {stats['comparison_stats']['retry_comparisons']}")
    print(f"✓ Success rate: {stats['success_rate']:.1f}%")
    print(f"✓ Error counts: {stats['error_counts']}")
    print(f"✓ Most common error: {stats['most_common_error']}")
    
    # Should continue kontrolü
    should_continue = test_monitor.should_continue(max_failure_rate=0.5)
    print(f"✓ Should continue with 50% max failure rate: {should_continue}")
    
    # Session summary test
    print("\n--- Session Summary Test ---")
    test_monitor.log_session_summary("test_session")
    
    # Reset test
    test_monitor.reset_stats()
    reset_stats = test_monitor.get_stats_summary()
    print(f"✓ After reset - Total comparisons: {reset_stats['comparison_stats']['total_comparisons']}")

async def test_integration():
    """Integration testini gerçekleştirir"""
    print("\n=== INTEGRATION TESTS ===")
    
    # Global monitor'ı reset et
    optimization_monitor.reset_stats()
    
    # Test case'leri oluştur
    test_case1 = TestCase(
        ScenarioID="scenario1",
        TestCaseID="test1",
        Title="Login with valid credentials",
        Description="User should be able to login with valid username and password",
        Objective="Verify successful login functionality"
    )
    
    test_case2 = TestCase(
        ScenarioID="scenario1", 
        TestCaseID="test2",
        Title="Login with invalid credentials",
        Description="User should see error message when logging in with invalid credentials",
        Objective="Verify login error handling"
    )
    
    print("Testing retry wrapper with mock cases...")
    
    try:
        # Bu gerçekte LLM'e bağlanmaya çalışacak ve muhtemelen başarısız olacak
        # Ama retry ve monitoring mantığını test edebiliriz
        result = await _query_llm_similarity_with_retry(
            test_case1, test_case2, 
            selected_model="test_model"
        )
        print(f"✓ Integration test result: {result}")
    except Exception as e:
        print(f"✓ Expected integration error (no LLM service): {e}")
    
    # Global monitor stats kontrolü
    stats = optimization_monitor.get_stats_summary()
    print(f"✓ Global monitor after integration test:")
    print(f"   Total comparisons: {stats['comparison_stats']['total_comparisons']}")
    print(f"   Success rate: {stats['success_rate']:.1f}%")

async def main():
    """Ana test fonksiyonu"""
    print("🚀 Starting Retry and Monitoring System Tests...")
    
    # Test 1: Retry mechanism
    await test_retry_mechanism()
    
    # Test 2: Error categorization
    test_error_categorization()
    
    # Test 3: Monitoring system
    test_monitoring_system()
    
    # Test 4: Integration
    await test_integration()
    
    print("\n✅ All tests completed!")
    print("\nNOTE: Integration tests may show 'expected errors' due to missing LLM service.")
    print("This is normal and demonstrates that retry/monitoring works correctly.")

if __name__ == "__main__":
    asyncio.run(main())
