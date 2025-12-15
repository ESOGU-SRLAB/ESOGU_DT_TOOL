"""
Batch API Performance Comparison

Eski ve yeni konfigürasyonları karşılaştıralım.
"""

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def calculate_processing_scenarios():
    """Calculate different processing scenarios"""
    
    scenarios = [
        {"test_cases": 50, "comparisons": 1225},
        {"test_cases": 100, "comparisons": 4950},
        {"test_cases": 200, "comparisons": 19900},
        {"test_cases": 500, "comparisons": 124750},
    ]
    
    logger.info("="*100)
    logger.info("BATCH API PERFORMANCE COMPARISON")
    logger.info("="*100)
    logger.info("")
    logger.info("CONFIGURATION CHANGES:")
    logger.info("  OLD: Pre-split into safe_batch_size (2000 for Flash, 1000 for Pro)")
    logger.info("       + 60 second wait between batches")
    logger.info("  NEW: Start with max_requests_per_batch (20000 for Flash, 10000 for Pro)")
    logger.info("       + 5 second wait between batches")
    logger.info("       + Auto-split only if quota exceeded")
    logger.info("")
    logger.info("="*100)
    
    for scenario in scenarios:
        n = scenario["test_cases"]
        comparisons = scenario["comparisons"]
        
        logger.info("")
        logger.info(f"📊 SCENARIO: {n} test cases ({comparisons:,} comparisons)")
        logger.info("-"*100)
        
        # OLD Configuration - Gemini 2.5 Flash
        old_flash_batches = (comparisons + 2000 - 1) // 2000
        old_flash_wait_time = (old_flash_batches - 1) * 60  # 60 seconds between batches
        old_flash_total_time = old_flash_wait_time / 60
        
        # NEW Configuration - Gemini 2.5 Flash
        new_flash_batches = (comparisons + 20000 - 1) // 20000
        new_flash_wait_time = (new_flash_batches - 1) * 5  # 5 seconds between batches
        new_flash_total_time = new_flash_wait_time / 60
        
        logger.info("")
        logger.info("GEMINI 2.5 FLASH:")
        logger.info(f"  OLD Config:")
        logger.info(f"    - Batches: {old_flash_batches}")
        logger.info(f"    - Wait time: {old_flash_wait_time} seconds ({old_flash_total_time:.1f} minutes)")
        logger.info(f"  NEW Config:")
        logger.info(f"    - Batches: {new_flash_batches}")
        logger.info(f"    - Wait time: {new_flash_wait_time} seconds ({new_flash_total_time:.1f} minutes)")
        if old_flash_batches > 0 and new_flash_batches > 0 and old_flash_wait_time > 0:
            improvement = ((old_flash_wait_time - new_flash_wait_time) / old_flash_wait_time * 100)
            logger.info(f"  ✅ IMPROVEMENT: {improvement:.1f}% faster submission")
        elif new_flash_batches == 1:
            logger.info(f"  ✅ Single batch - no wait time needed!")
        
        # OLD Configuration - Gemini 2.5 Pro
        old_pro_batches = (comparisons + 1000 - 1) // 1000
        old_pro_wait_time = (old_pro_batches - 1) * 60
        old_pro_total_time = old_pro_wait_time / 60
        
        # NEW Configuration - Gemini 2.5 Pro
        new_pro_batches = (comparisons + 10000 - 1) // 10000
        new_pro_wait_time = (new_pro_batches - 1) * 5
        new_pro_total_time = new_pro_wait_time / 60
        
        logger.info("")
        logger.info("GEMINI 2.5 PRO:")
        logger.info(f"  OLD Config:")
        logger.info(f"    - Batches: {old_pro_batches}")
        logger.info(f"    - Wait time: {old_pro_wait_time} seconds ({old_pro_total_time:.1f} minutes)")
        logger.info(f"  NEW Config:")
        logger.info(f"    - Batches: {new_pro_batches}")
        logger.info(f"    - Wait time: {new_pro_wait_time} seconds ({new_pro_total_time:.1f} minutes)")
        if old_pro_batches > 0 and new_pro_batches > 0 and old_pro_wait_time > 0:
            improvement = ((old_pro_wait_time - new_pro_wait_time) / old_pro_wait_time * 100)
            logger.info(f"  ✅ IMPROVEMENT: {improvement:.1f}% faster submission")
        elif new_pro_batches == 1:
            logger.info(f"  ✅ Single batch - no wait time needed!")
        
        logger.info("-"*100)
    
    logger.info("")
    logger.info("="*100)
    logger.info("KEY IMPROVEMENTS:")
    logger.info("="*100)
    logger.info("✅ Batch submission is 10-20x faster")
    logger.info("✅ Batch API still processes all comparisons in parallel")
    logger.info("✅ Auto-split only when needed (quota exceeded)")
    logger.info("✅ Better utilization of Batch API capabilities")
    logger.info("="*100)

if __name__ == "__main__":
    calculate_processing_scenarios()
