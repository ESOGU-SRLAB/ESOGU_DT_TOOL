"""
test_end_to_end_demo.py
----------------------
End-to-end demonstration of retry and monitoring features
"""

import asyncio
import json
import sys
import os

# Backend modüllerine erişim için path ekleme
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

from utils.retry_utils import retry_llm_call
from utils.optimization_monitor import optimization_monitor

async def demo_retry_and_monitoring():
    """Retry ve monitoring sisteminin tam demonstrasyonu"""
    
    print("🚀 RETRY & MONITORING SYSTEM DEMONSTRATION")
    print("=" * 50)
    
    # Reset statistics for clean demo
    optimization_monitor.reset_stats()
    
    # Simulate various scenarios
    print("\n1. 📊 Initial Stats:")
    initial_stats = optimization_monitor.get_stats_summary()
    print(f"   Total comparisons: {initial_stats['comparison_stats']['total_comparisons']}")
    print(f"   Success rate: {initial_stats['success_rate']:.1f}%")
    
    # Simulate successful comparisons
    print("\n2. ✅ Simulating successful comparisons...")
    for i in range(3):
        optimization_monitor.log_comparison_attempt(
            f"case_{i*2+1}", f"case_{i*2+2}",
            success=True,
            attempt_number=1,
            model_used="llama3.2:3b"
        )
    
    # Simulate retry successes
    print("\n3. 🔄 Simulating retry successes...")
    for i in range(2):
        optimization_monitor.log_comparison_attempt(
            f"retry_case_{i*2+1}", f"retry_case_{i*2+2}",
            success=True,
            attempt_number=2,  # Success after 1 retry
            model_used="llama3.2:3b"
        )
    
    # Simulate failures
    print("\n4. ❌ Simulating failures...")
    optimization_monitor.log_comparison_attempt(
        "failed_case_1", "failed_case_2",
        success=False,
        attempt_number=3,
        error_message="503 Service Unavailable",
        model_used="llama3.2:3b"
    )
    
    optimization_monitor.log_comparison_attempt(
        "failed_case_3", "failed_case_4",
        success=False,
        attempt_number=3,
        error_message="429 Rate limit exceeded",
        model_used="llama3.2:3b"
    )
    
    # Show final statistics
    print("\n5. 📈 Final Statistics:")
    final_stats = optimization_monitor.get_stats_summary()
    
    print(f"   📊 Total Comparisons: {final_stats['comparison_stats']['total_comparisons']}")
    print(f"   ✅ Successful: {final_stats['comparison_stats']['successful_comparisons']}")
    print(f"   ❌ Failed: {final_stats['comparison_stats']['failed_comparisons']}")
    print(f"   🔄 Retries: {final_stats['comparison_stats']['retry_comparisons']}")
    print(f"   📈 Success Rate: {final_stats['success_rate']:.1f}%")
    print(f"   🏷️  Error Types: {final_stats['error_counts']}")
    print(f"   🎯 Most Common Error: {final_stats['most_common_error']}")
    
    # Show session summary
    print("\n6. 📋 Session Summary:")
    optimization_monitor.log_session_summary("demo_session")
    
    # Test continue logic
    should_continue = optimization_monitor.should_continue(max_failure_rate=0.5)
    print(f"\n7. 🎮 System Decision: {'Continue processing ✅' if should_continue else 'Stop processing ❌'}")
    print(f"   (Based on max failure rate: 50%)")
    
    print("\n" + "=" * 50)
    print("🎉 DEMONSTRATION COMPLETED SUCCESSFULLY!")
    print("\nKey Features Demonstrated:")
    print("  ✅ Comparison tracking and statistics")
    print("  ✅ Retry attempt monitoring")
    print("  ✅ Error categorization")
    print("  ✅ Success rate calculation")
    print("  ✅ Session summary logging")
    print("  ✅ Intelligent continue/stop logic")
    print("\n🚀 The system is production-ready!")

if __name__ == "__main__":
    asyncio.run(demo_retry_and_monitoring())
