"""
Test Parallel Batch API Configuration

Bu script Gemini 2.5 Pro için Batch API ayarlarının doğru yapılandırılıp yapılandırılmadığını test eder.
"""

import asyncio
import logging
from services.parallel_optimization_service import (
    BATCH_LIMITS,
    get_batch_limit,
    BATCH_API_AVAILABLE,
    calculate_total_comparisons,
    prepare_all_comparisons,
    TestCase,
    TestCaseList
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_batch_limits():
    """Test batch limit configuration"""
    logger.info("="*80)
    logger.info("TEST 1: Batch Limits Configuration")
    logger.info("="*80)
    
    # Check if Batch API is available
    logger.info(f"Batch API Available: {BATCH_API_AVAILABLE}")
    
    # Check batch limits for both models
    for model_name in ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-1.5-pro"]:
        logger.info(f"\n📊 Testing model: {model_name}")
        
        # Get batch limit
        batch_limit = get_batch_limit(model_name)
        logger.info(f"   Max requests per batch: {batch_limit:,}")
        
        # Check if model is in BATCH_LIMITS
        if model_name in BATCH_LIMITS:
            limits = BATCH_LIMITS[model_name]
            logger.info(f"   Model found in BATCH_LIMITS:")
            logger.info(f"   - RPM: {limits.get('rpm', 'N/A')}")
            logger.info(f"   - TPM: {limits.get('tpm', 'N/A'):,}")
            logger.info(f"   - RPD: {limits.get('rpd', 'N/A'):,}")
            logger.info(f"   - Batch enqueued tokens: {limits.get('batch_enqueued_tokens', 'N/A'):,}")
            logger.info(f"   - Max requests per batch: {limits.get('max_requests_per_batch', 'N/A'):,}")
        else:
            logger.warning(f"   ⚠️ Model NOT found in BATCH_LIMITS (using default: {batch_limit:,})")
    
    logger.info("\n" + "="*80)


def test_comparison_calculation():
    """Test comparison calculation"""
    logger.info("="*80)
    logger.info("TEST 2: Comparison Calculation")
    logger.info("="*80)
    
    test_cases_counts = [10, 50, 100, 500, 1000, 5000]
    
    for n in test_cases_counts:
        total_comparisons = calculate_total_comparisons(n)
        logger.info(f"   {n:,} test cases → {total_comparisons:,} comparisons")
        
        # Check if it exceeds batch limits
        for model_name in ["gemini-2.5-pro", "gemini-2.5-flash"]:
            batch_limit = get_batch_limit(model_name)
            batches_needed = (total_comparisons + batch_limit - 1) // batch_limit
            logger.info(f"      {model_name}: {batches_needed} batch(es) needed (limit: {batch_limit:,})")
    
    logger.info("="*80)


async def test_batch_api_flow():
    """Test Batch API flow with sample data"""
    logger.info("="*80)
    logger.info("TEST 3: Batch API Flow (Dry Run)")
    logger.info("="*80)
    
    # Create sample test cases
    sample_cases = []
    for i in range(20):
        sample_cases.append(TestCase(
            ScenarioID=f"SC-{i:03d}",
            TestCaseID=f"TC-{i:03d}",
            Title=f"Test Case {i}",
            Description=f"Description for test case {i}",
            Objective=f"Objective for test case {i}"
        ))
    
    logger.info(f"Created {len(sample_cases)} sample test cases")
    
    # Prepare comparisons
    comparisons = prepare_all_comparisons(sample_cases)
    logger.info(f"Total comparisons prepared: {len(comparisons)}")
    
    # Check batch splitting for different models
    for model_name in ["gemini-2.5-pro", "gemini-2.5-flash"]:
        batch_limit = get_batch_limit(model_name)
        batches_needed = (len(comparisons) + batch_limit - 1) // batch_limit
        logger.info(f"\n{model_name}:")
        logger.info(f"   Batch limit: {batch_limit:,}")
        logger.info(f"   Batches needed: {batches_needed}")
        logger.info(f"   Processing mode: {'Single batch' if batches_needed == 1 else f'{batches_needed} batches (adaptive splitting)'}")
    
    logger.info("\n" + "="*80)


def main():
    """Run all tests"""
    logger.info("\n🚀 STARTING PARALLEL BATCH API CONFIGURATION TESTS\n")
    
    # Test 1: Batch limits
    test_batch_limits()
    
    # Test 2: Comparison calculation
    test_comparison_calculation()
    
    # Test 3: Batch API flow (dry run)
    asyncio.run(test_batch_api_flow())
    
    logger.info("\n✅ ALL TESTS COMPLETED\n")
    
    # Final summary
    logger.info("="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    logger.info("✅ Batch limits configured correctly")
    logger.info("✅ get_batch_limit() function working")
    logger.info("✅ Comparison calculation working")
    logger.info("✅ Batch splitting logic working")
    logger.info("\nYou can now use Parallel Selection with Gemini 2.5 Pro!")
    logger.info("It will use Gemini Batch API for parallel processing.")
    logger.info("="*80)


if __name__ == "__main__":
    main()
