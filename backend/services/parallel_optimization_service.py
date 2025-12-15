"""
Parallel Smart Selection Service for Test Case Optimization
GEMINI BATCH API IMPLEMENTATION

Bu servis Gemini Batch API kullanarak test case optimizasyonunu gerçekleştirir.

AVANTAJLAR:
- %50 daha ucuz (standard fiyatın yarısı)
- GERÇEK paralel işlem (tüm istekler aynı anda işlenir)
- Rate limit sorunu yok
- Binlerce karşılaştırmayı tek seferde gönder

ALGORITHM:
1. Tüm n*(n-1)/2 karşılaştırmayı hesapla
2. Her karşılaştırma için Gemini request oluştur
3. Inline requests veya JSONL file ile batch job oluştur
4. Job durumunu poll et (30 saniyede bir kontrol)
5. JOB_STATE_SUCCEEDED olunca sonuçları al
6. Similar/unique ayır ve validation yap
"""

import asyncio
import logging
import time
import json
import tempfile
import os
from typing import List, Dict, Any, Tuple, Optional, Set
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Try to import google-genai (Batch API SDK)
try:
    from google import genai
    from google.genai import types
    BATCH_API_AVAILABLE = True
except ImportError:
    logger.warning("google-genai not installed. Install: pip install google-genai")
    BATCH_API_AVAILABLE = False


# GEMINI BATCH API RATE LIMITS
# https://ai.google.dev/gemini-api/docs/rate-limits
# Note: Batch API handles rate limiting internally, so we can use large batch sizes
BATCH_LIMITS = {
    "gemini-2.5-pro": {
        "rpm": 150,  # Requests per minute (for standard API)
        "tpm": 2_000_000,  # Tokens per minute
        "rpd": 10_000,  # Requests per day
        "batch_enqueued_tokens": 5_000_000,  # Max tokens in batch
        "max_requests_per_batch": 10000  # Maximum requests per batch for Batch API
    },
    "gemini-2.5-flash": {
        "rpm": 1000,  # Requests per minute (for standard API)
        "tpm": 1_000_000,  # Tokens per minute
        "rpd": 10_000,  # Requests per day
        "batch_enqueued_tokens": 3_000_000,  # Max tokens in batch
        "max_requests_per_batch": 20000  # Maximum requests per batch for Batch API
    }
}

# Default limits for unknown models
DEFAULT_BATCH_LIMIT = 500


# Import TestCase and TestCaseList from test_case_optimization_service to ensure compatibility
# This prevents Pydantic validation errors due to different class instances
try:
    from services.test_case_optimization_service import TestCase, TestCaseList
except ImportError:
    # Fallback: define locally if import fails
    class TestCase(BaseModel):
        ScenarioID: str
        TestCaseID: str
        Title: str
        Description: Optional[str] = None
        Objective: Optional[str] = None

    class TestCaseList(BaseModel):
        test_cases: List[TestCase]
        comparison_logs: List[dict] = []
        duplicates: List[dict] = []


# Comparison pair structure - using Dict to avoid circular validation
class ComparisonPair(BaseModel):
    index1: int
    index2: int
    case1: Dict[str, Any]  # TestCase as dict to avoid validation issues
    case2: Dict[str, Any]  # TestCase as dict to avoid validation issues


def calculate_total_comparisons(n: int) -> int:
    """Calculate total pairwise comparisons: n*(n-1)/2"""
    return n * (n - 1) // 2


def prepare_all_comparisons(test_cases: List[TestCase]) -> List[ComparisonPair]:
    """Prepare all pairwise comparisons upfront"""
    comparisons = []
    n = len(test_cases)
    
    for i in range(n):
        for j in range(i + 1, n):
            comparisons.append(ComparisonPair(
                index1=i,
                index2=j,
                case1=test_cases[i].model_dump(),  # Convert to dict
                case2=test_cases[j].model_dump()   # Convert to dict
            ))
    
    logger.info(f"📊 Prepared {len(comparisons)} comparisons for {n} test cases")
    return comparisons


def get_batch_limit(model_name: str) -> int:
    """Get maximum requests per batch for a given model"""
    # Normalize model name
    model_lower = model_name.lower()
    
    # Check each key in BATCH_LIMITS
    for key, limits in BATCH_LIMITS.items():
        # Match model name with key (e.g., "gemini-2.5-pro" matches "gemini-2.5-pro")
        if key.lower() in model_lower or model_lower in key.lower():
            max_requests = limits.get("max_requests_per_batch", DEFAULT_BATCH_LIMIT)
            logger.info(f"📊 Model '{model_name}' matched with '{key}': max_requests_per_batch = {max_requests}")
            return max_requests
    
    logger.warning(f"⚠️ Unknown model '{model_name}', using default limit {DEFAULT_BATCH_LIMIT}")
    return DEFAULT_BATCH_LIMIT


def split_comparisons_into_batches(
    comparisons: List[ComparisonPair],
    model_name: str
) -> List[List[ComparisonPair]]:
    """
    Split comparisons into multiple batches based on model rate limits
    
    Returns list of batches, where each batch respects the model's limits
    """
    max_per_batch = get_batch_limit(model_name)
    total = len(comparisons)
    
    if total <= max_per_batch:
        logger.info(f"✅ Single batch: {total:,} comparisons (limit: {max_per_batch:,})")
        return [comparisons]
    
    # Split into multiple batches
    batches = []
    for i in range(0, total, max_per_batch):
        batch = comparisons[i:i + max_per_batch]
        batches.append(batch)
    
    logger.info(f"📦 Split into {len(batches)} batches:")
    for idx, batch in enumerate(batches, 1):
        logger.info(f"   Batch {idx}: {len(batch):,} comparisons")
    
    return batches


def build_comparison_prompt(case1: Dict[str, Any], case2: Dict[str, Any], custom_prompt: Optional[str] = None) -> str:
    """Build the prompt for comparing two test cases"""
    if custom_prompt:
        prompt = custom_prompt.format(
            title1=case1.get("Title", ""),
            description1=case1.get("Description") or "",
            objective1=case1.get("Objective") or "",
            title2=case2.get("Title", ""),
            description2=case2.get("Description") or "",
            objective2=case2.get("Objective") or ""
        )
    else:
        prompt = f"""Compare these two test cases and determine if they are testing the same functionality.

Test Case 1:
Title: {case1.get("Title", "N/A")}
Description: {case1.get("Description") or 'N/A'}
Objective: {case1.get("Objective") or 'N/A'}

Test Case 2:
Title: {case2.get("Title", "N/A")}
Description: {case2.get("Description") or 'N/A'}
Objective: {case2.get("Objective") or 'N/A'}

Are these test cases testing the same functionality? Answer ONLY with 'yes' or 'no'."""
    
    return prompt


def create_batch_requests_inline(
    comparisons: List[ComparisonPair],
    custom_prompt: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Create inline batch requests for Gemini Batch API"""
    requests = []
    
    for idx, pair in enumerate(comparisons):
        prompt = build_comparison_prompt(pair.case1, pair.case2, custom_prompt)
        
        request = {
            'contents': [{
                'parts': [{'text': prompt}],
                'role': 'user'
            }]
        }
        
        requests.append(request)
    
    logger.info(f"📝 Created {len(requests)} inline batch requests")
    return requests


def create_batch_requests_jsonl(
    comparisons: List[ComparisonPair],
    custom_prompt: Optional[str] = None,
    output_file: Optional[str] = None
) -> str:
    """Create JSONL file for Gemini Batch API"""
    if output_file is None:
        fd, output_file = tempfile.mkstemp(suffix='.jsonl', prefix='batch_requests_')
        os.close(fd)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for idx, pair in enumerate(comparisons):
            prompt = build_comparison_prompt(pair.case1, pair.case2, custom_prompt)
            
            request_obj = {
                'key': f'comparison-{idx}',
                'request': {
                    'contents': [{
                        'parts': [{'text': prompt}],
                        'role': 'user'
                    }]
                }
            }
            
            f.write(json.dumps(request_obj, ensure_ascii=False) + '\n')
    
    logger.info(f"📄 Created JSONL file with {len(comparisons)} requests: {output_file}")
    return output_file


async def create_batch_job_inline(
    requests: List[Dict[str, Any]],
    model: str,
    api_key: str,
    display_name: str = "test-case-optimization-batch"
) -> Any:
    """Create a batch job with inline requests"""
    if not BATCH_API_AVAILABLE:
        raise ImportError("google-genai package not installed")
    
    client = genai.Client(api_key=api_key)
    
    logger.info(f"🚀 CREATING GEMINI BATCH API JOB (PARALLEL PROCESSING)")
    logger.info(f"   Requests: {len(requests)} comparisons")
    logger.info(f"   Model: {model}")
    logger.info(f"   Mode: Inline Batch (all requests sent to Batch API)")
    logger.info(f"   This is NOT serial processing - all comparisons will be processed in parallel")
    
    batch_job = client.batches.create(
        model=f"models/{model}",
        src=requests,
        config={'display_name': display_name}
    )
    
    logger.info(f"✅ Batch job created successfully: {batch_job.name}")
    logger.info(f"   Job will process {len(requests)} comparisons in parallel via Batch API")
    return batch_job


async def create_batch_job_from_file(
    jsonl_file: str,
    model: str,
    api_key: str,
    display_name: str = "test-case-optimization-batch"
) -> Any:
    """Create a batch job from JSONL file"""
    if not BATCH_API_AVAILABLE:
        raise ImportError("google-genai package not installed")
    
    client = genai.Client(api_key=api_key)
    
    logger.info(f"📤 Uploading JSONL file: {jsonl_file}")
    uploaded_file = client.files.upload(
        file=jsonl_file,
        config=types.UploadFileConfig(
            display_name='batch-requests',
            mime_type='application/jsonl'
        )
    )
    logger.info(f"✅ File uploaded: {uploaded_file.name}")
    
    logger.info(f"🚀 Creating batch job from uploaded file...")
    batch_job = client.batches.create(
        model=f"models/{model}",
        src=uploaded_file.name,
        config={'display_name': display_name}
    )
    
    logger.info(f"✅ Batch job created: {batch_job.name}")
    return batch_job


async def poll_batch_job(
    job_name: str,
    api_key: str,
    poll_interval: int = 30,
    max_wait_time: int = 86400
) -> Any:
    """Poll batch job until completion"""
    if not BATCH_API_AVAILABLE:
        raise ImportError("google-genai package not installed")
    
    client = genai.Client(api_key=api_key)
    
    completed_states = {
        'JOB_STATE_SUCCEEDED',
        'JOB_STATE_FAILED',
        'JOB_STATE_CANCELLED',
        'JOB_STATE_EXPIRED',
    }
    
    logger.info(f"⏳ POLLING BATCH JOB: {job_name}")
    
    start_time = time.time()
    poll_count = 0
    
    while True:
        poll_count += 1
        elapsed = time.time() - start_time
        
        if elapsed > max_wait_time:
            raise TimeoutError(f"Batch job polling exceeded {max_wait_time}s")
        
        batch_job = client.batches.get(name=job_name)
        state = batch_job.state.name
        
        logger.info(f"📊 Poll #{poll_count} ({elapsed:.0f}s): {state}")
        
        if state in completed_states:
            logger.info(f"🏁 JOB COMPLETED: {state} ({elapsed:.1f}s)")
            
            if state == 'JOB_STATE_FAILED':
                raise RuntimeError(f"Batch job failed: {batch_job.error}")
            if state == 'JOB_STATE_CANCELLED':
                raise RuntimeError("Batch job was cancelled")
            if state == 'JOB_STATE_EXPIRED':
                raise RuntimeError("Batch job expired")
            
            return batch_job
        
        logger.info(f"⏳ Waiting {poll_interval}s...")
        await asyncio.sleep(poll_interval)


def parse_batch_response(response_text: str) -> bool:
    """Parse batch response to determine if test cases are similar"""
    text = response_text.lower().strip()
    
    if 'yes' in text:
        return True
    if 'no' in text:
        return False
    
    logger.warning(f"Unclear response: {response_text}")
    return False


async def retrieve_batch_results(
    batch_job: Any,
    api_key: str,
    comparisons: List[ComparisonPair]
) -> List[Dict[str, Any]]:
    """Retrieve and parse batch job results"""
    if not BATCH_API_AVAILABLE:
        raise ImportError("google-genai package not installed")
    
    client = genai.Client(api_key=api_key)
    
    logger.info(f"📥 Retrieving batch job results...")
    
    comparison_results = []
    
    if batch_job.dest and batch_job.dest.inlined_responses:
        logger.info(f"📋 Processing inline responses...")
        
        for i, inline_response in enumerate(batch_job.dest.inlined_responses):
            pair = comparisons[i]
            
            if inline_response.response:
                response_text = inline_response.response.text
                is_same = parse_batch_response(response_text)
            elif inline_response.error:
                logger.error(f"Error in response {i}: {inline_response.error}")
                is_same = False
                response_text = None
            else:
                logger.warning(f"No response for {i}")
                is_same = False
                response_text = None
            
            comparison_results.append({
                "index1": pair.index1,
                "index2": pair.index2,
                "case1": pair.case1,  # Already a dict
                "case2": pair.case2,  # Already a dict
                "is_same": is_same,
                "timestamp": datetime.now().isoformat(),
                "response_text": response_text
            })
    
    elif batch_job.dest and batch_job.dest.file_name:
        logger.info(f"📄 Processing file-based responses...")
        
        result_file_name = batch_job.dest.file_name
        file_content = client.files.download(file=result_file_name)
        
        lines = file_content.decode('utf-8').strip().split('\n')
        
        for line in lines:
            result_obj = json.loads(line)
            
            key = result_obj.get('key', '')
            idx = int(key.split('-')[-1]) if key else 0
            
            pair = comparisons[idx]
            
            if 'response' in result_obj:
                response_text = result_obj['response'].get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                is_same = parse_batch_response(response_text)
            elif 'error' in result_obj:
                logger.error(f"Error in {key}: {result_obj['error']}")
                is_same = False
                response_text = None
            else:
                logger.warning(f"No response for {key}")
                is_same = False
                response_text = None
            
            comparison_results.append({
                "index1": pair.index1,
                "index2": pair.index2,
                "case1": pair.case1,  # Already a dict
                "case2": pair.case2,  # Already a dict
                "is_same": is_same,
                "timestamp": datetime.now().isoformat(),
                "response_text": response_text
            })
    
    else:
        raise RuntimeError("No results found in batch job")
    
    logger.info(f"✅ Retrieved {len(comparison_results)} results")
    return comparison_results


def extract_unique_and_similar(
    test_cases: List[TestCase],
    comparison_results: List[Dict[str, Any]]
) -> Tuple[List[TestCase], List[dict]]:
    """
    Extract unique and similar test cases from comparison results
    
    Algorithm:
    1. Build similar pairs set from comparison results
    2. For each pair (i,j), if i is not already removed, mark j as duplicate
    3. Each test case can only be removed once (no duplicate entries)
    """
    logger.info(f"🔍 EXTRACTING UNIQUE AND SIMILAR TEST CASES")
    
    n = len(test_cases)
    
    # Build set of similar pairs
    similar_pairs = set()
    for result in comparison_results:
        if result["is_same"]:
            i, j = result["index1"], result["index2"]
            # Always store as (smaller, larger) to avoid duplicates
            similar_pairs.add((min(i, j), max(i, j)))
    
    logger.info(f"📊 Found {len(similar_pairs)} similar pairs from {len(comparison_results)} comparisons")
    
    # Track which indices to remove (will become duplicates)
    to_remove = set()
    # Track which index each duplicate matched with
    duplicate_matches = {}  # {removed_index: kept_index}
    
    # Process pairs in sorted order for consistency
    for pair_i, pair_j in sorted(similar_pairs):
        # If pair_i is already removed, skip (it's a duplicate itself)
        if pair_i in to_remove:
            continue
        
        # If pair_j is not yet removed, mark it as duplicate of pair_i
        if pair_j not in to_remove:
            to_remove.add(pair_j)
            duplicate_matches[pair_j] = pair_i
    
    # Build unique and duplicate lists
    unique_cases = []
    duplicates = []
    
    for idx, case in enumerate(test_cases):
        if idx in to_remove:
            # This is a duplicate
            matched_with_idx = duplicate_matches[idx]
            duplicates.append({
                "DuplicateCase": case.model_dump(),
                "MatchedWith": test_cases[matched_with_idx].model_dump(),
                "OriginalIndex": idx,
                "MatchedWithIndex": matched_with_idx
            })
        else:
            # This is unique
            unique_cases.append(case)
    
    # Validation
    logger.info(f"✅ Unique: {len(unique_cases)}, Similar: {len(duplicates)}")
    logger.info(f"📊 Total check: {len(unique_cases)} + {len(duplicates)} = {len(unique_cases) + len(duplicates)} (should be {n})")
    
    if len(unique_cases) + len(duplicates) != n:
        logger.error(f"❌ VALIDATION FAILED: Count mismatch!")
        logger.error(f"   Expected: {n}, Got: {len(unique_cases) + len(duplicates)}")
    else:
        logger.info(f"✅ VALIDATION PASSED: All test cases accounted for")
    
    logger.info(f"📊 Reduction: {n} → {len(unique_cases)} ({len(unique_cases)/n*100:.1f}%)")
    
    return unique_cases, duplicates


async def process_single_batch(
    comparisons: List[ComparisonPair],
    custom_prompt: Optional[str] = None,
    selected_model: str = "gemini-2.5-flash",
    api_key: str = None,
    batch_name: str = "batch"
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Process a single batch of comparisons
    
    Returns:
        Tuple of (comparison_results, error_message)
        If successful: (results, None)
        If 429 error: ([], "QUOTA_EXCEEDED")
        If other error: ([], error_message)
    """
    try:
        # Create batch requests (always use inline for simplicity)
        inline_requests = create_batch_requests_inline(comparisons, custom_prompt)
        
        # Create batch job
        batch_job = await create_batch_job_inline(
            inline_requests,
            selected_model,
            api_key,
            batch_name
        )
        
        logger.info(f"✅ Batch job created: {batch_job.name}")
        
        # Poll until completed
        completed_job = await poll_batch_job(batch_job.name, api_key)
        
        # Retrieve results
        comparison_results = await retrieve_batch_results(completed_job, api_key, comparisons)
        
        return comparison_results, None
        
    except Exception as e:
        error_str = str(e)
        
        # Check if it's a quota error
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
            logger.warning(f"⚠️ Quota exceeded for batch {batch_name}")
            return [], "QUOTA_EXCEEDED"
        else:
            logger.error(f"❌ Error processing batch {batch_name}: {e}")
            return [], error_str


async def process_with_auto_split(
    comparisons: List[ComparisonPair],
    test_cases: List[TestCase],
    custom_prompt: Optional[str] = None,
    selected_model: str = "gemini-2.5-flash",
    api_key: str = None,
    process_id: str = None,
    max_retries: int = 3
) -> Tuple[List[TestCase], List[dict], List[Dict[str, Any]]]:
    """
    Process comparisons with automatic batch splitting if quota exceeded
    
    Algorithm:
    1. Check model's safe batch size (based on RPM limits)
    2. Pre-split into conservative batches (2000 for Flash)
    3. Add delays between batches to respect RPM
    4. If 429 error, split in half and retry with exponential backoff
    
    Returns:
        Tuple of (unique_cases, duplicates, comparison_logs)
    """
    logger.info("="*80)
    logger.info("🚀 GEMINI BATCH API - ADAPTIVE BATCH PROCESSING")
    logger.info(f"   Total comparisons: {len(comparisons):,}")
    logger.info(f"   Model: {selected_model}")
    logger.info(f"   Processing Mode: BATCH API (NOT Serial)")
    logger.info("="*80)
    
    # Get model limits - use max_requests_per_batch for initial batch size
    model_limits = BATCH_LIMITS.get(selected_model, {})
    max_batch_size = model_limits.get("max_requests_per_batch", DEFAULT_BATCH_LIMIT)
    
    logger.info(f"📊 Maximum batch size: {max_batch_size:,} requests/batch")
    logger.info(f"📊 Strategy: Start with maximum batch size, split only if quota exceeded")
    
    # Start with maximum possible batch sizes (don't pre-split conservatively)
    initial_batches = []
    if len(comparisons) > max_batch_size:
        logger.info(f"📊 Splitting {len(comparisons):,} comparisons into batches of {max_batch_size:,}")
        for i in range(0, len(comparisons), max_batch_size):
            batch = comparisons[i:i + max_batch_size]
            initial_batches.append(batch)
        logger.info(f"   Created {len(initial_batches)} initial batches")
    else:
        initial_batches = [comparisons]
        logger.info(f"   Single batch (within batch limit)")
    
    all_results = []
    batches_to_process = initial_batches
    retry_count = 0
    
    while batches_to_process and retry_count < max_retries:
        current_batches = batches_to_process.copy()
        batches_to_process = []
        
        for batch_idx, batch in enumerate(current_batches, 1):
            # Add minimal delay between batches (Batch API handles rate limiting internally)
            if batch_idx > 1:
                wait_time = 5  # Short delay to avoid overwhelming the API submission
                logger.info(f"⏳ Brief pause: {wait_time} seconds before next batch submission...")
                await asyncio.sleep(wait_time)
            
            logger.info(f"\n📦 Processing batch {batch_idx}/{len(current_batches)}: {len(batch):,} comparisons")
            logger.info(f"   This batch will be processed in PARALLEL via Batch API")
            
            results, error = await process_single_batch(
                batch,
                custom_prompt,
                selected_model,
                api_key,
                f"batch{batch_idx}-{process_id or 'unknown'}"
            )
            
            if error is None:
                # Success!
                logger.info(f"✅ Batch {batch_idx} completed: {len(results)} results")
                all_results.extend(results)
                
            elif error == "QUOTA_EXCEEDED":
                # Need to split this batch
                if len(batch) <= 10:
                    # Too small to split further
                    logger.error(f"❌ Cannot split batch further (only {len(batch)} comparisons)")
                    raise Exception("Quota exceeded even with minimal batch size")
                
                # Split in half
                mid = len(batch) // 2
                batch1 = batch[:mid]
                batch2 = batch[mid:]
                
                logger.warning(f"⚠️ Splitting batch into 2 parts: {len(batch1)} + {len(batch2)}")
                batches_to_process.extend([batch1, batch2])
                retry_count += 1
                
                # Wait longer before retry to avoid hitting rate limit again
                wait_time = 20 + (retry_count * 10)  # Exponential backoff
                logger.info(f"⏳ Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
                
            else:
                # Other error
                raise Exception(f"Batch processing failed: {error}")
        
        if batches_to_process:
            logger.info(f"\n🔄 Retry {retry_count}/{max_retries}: {len(batches_to_process)} batches remaining")
    
    if batches_to_process:
        raise Exception(f"Max retries ({max_retries}) exceeded")
    
    logger.info("="*80)
    logger.info(f"✅ ALL BATCHES COMPLETED")
    logger.info(f"   Total results: {len(all_results)}")
    logger.info("="*80)
    
    # Extract unique and similar from ALL results combined
    logger.info(f"🔍 Extracting unique and similar test cases...")
    unique_cases, duplicates = extract_unique_and_similar(test_cases, all_results)
    
    return unique_cases, duplicates, all_results


def validate_unique_not_in_similar(
    unique_cases: List[TestCase],
    duplicates: List[dict]
) -> bool:
    """Validate unique cases not in similar list"""
    logger.info(f"🔍 VALIDATION")
    
    unique_ids = {case.TestCaseID for case in unique_cases}
    duplicate_ids = {dup["DuplicateCase"]["TestCaseID"] for dup in duplicates}
    
    intersection = unique_ids & duplicate_ids
    
    if intersection:
        logger.error(f"❌ VALIDATION FAILED: {len(intersection)} conflicts")
        logger.error(f"   Conflicting IDs: {sorted(list(intersection))[:10]}...")  # Show first 10
        return False
    
    logger.info(f"✅ VALIDATION PASSED")
    return True


async def serial_final_check(
    unique_cases_batch1: List[TestCase],
    unique_cases_batch2: List[TestCase],
    custom_prompt: Optional[str] = None,
    selected_model: str = "gemini-2.5-flash",
    api_key: str = None
) -> Tuple[List[TestCase], List[dict]]:
    """
    Serial final check between unique cases from two batches
    
    Bu fonksiyon iki batch'in unique sonuçlarını karşılaştırır.
    Eğer batch1'den bir test case ile batch2'den bir test case
    aynı çıkarsa, batch2'deki silinir.
    
    Returns:
        Tuple of (final_unique_cases, cross_batch_duplicates)
    """
    logger.info("="*80)
    logger.info("🔍 SERIAL FINAL CHECK - Cross-batch comparison")
    logger.info(f"   Batch 1 unique: {len(unique_cases_batch1)}")
    logger.info(f"   Batch 2 unique: {len(unique_cases_batch2)}")
    logger.info("="*80)
    
    client = genai.Client(api_key=api_key)
    cross_duplicates = []
    to_remove_from_batch2 = set()
    
    total_comparisons = len(unique_cases_batch1) * len(unique_cases_batch2)
    logger.info(f"📊 Total cross-batch comparisons: {total_comparisons}")
    
    completed = 0
    
    # Compare each case from batch1 with each case from batch2
    for i, case1 in enumerate(unique_cases_batch1):
        for j, case2 in enumerate(unique_cases_batch2):
            if j in to_remove_from_batch2:
                continue
            
            # Build prompt
            prompt = build_comparison_prompt(
                case1.model_dump(),
                case2.model_dump(),
                custom_prompt
            )
            
            # Make serial API call
            try:
                response = client.models.generate_content(
                    model=selected_model,
                    contents=prompt
                )
                
                answer = response.text.strip().lower()
                is_same = "yes" in answer
                
                if is_same:
                    logger.info(f"🔗 Found cross-batch duplicate: Batch2[{j}] same as Batch1[{i}]")
                    to_remove_from_batch2.add(j)
                    cross_duplicates.append({
                        "DuplicateCase": case2.model_dump(),
                        "MatchedWith": case1.model_dump(),
                        "OriginalBatch": 2,
                        "MatchedWithBatch": 1,
                        "OriginalIndex": j,
                        "MatchedWithIndex": i
                    })
                
                completed += 1
                if completed % 100 == 0:
                    logger.info(f"⏳ Progress: {completed}/{total_comparisons} ({completed/total_comparisons*100:.1f}%)")
                
                # Rate limiting: ~1 request per second for serial
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"❌ Error in serial comparison: {e}")
                continue
    
    # Filter out duplicates from batch2
    final_batch2_unique = [
        case for idx, case in enumerate(unique_cases_batch2)
        if idx not in to_remove_from_batch2
    ]
    
    final_unique = unique_cases_batch1 + final_batch2_unique
    
    logger.info("="*80)
    logger.info("✅ SERIAL FINAL CHECK COMPLETED")
    logger.info(f"   Batch 1 kept: {len(unique_cases_batch1)}")
    logger.info(f"   Batch 2 kept: {len(final_batch2_unique)}")
    logger.info(f"   Cross-batch duplicates: {len(cross_duplicates)}")
    logger.info(f"   Final unique total: {len(final_unique)}")
    logger.info("="*80)
    
    return final_unique, cross_duplicates


async def parallel_smart_select(
    test_case_list: TestCaseList,
    custom_prompt: str = None,
    selected_model: str = "gemini-2.5-flash",
    api_key: str = None,
    process_id: str = None,
    use_file_mode: bool = True
) -> TestCaseList:
    """
    Parallel Smart Selection using Gemini Batch API
    
    Args:
        test_case_list: Test cases to optimize
        custom_prompt: Custom prompt template
        selected_model: Model name
        api_key: Gemini API key
        process_id: Process ID
        use_file_mode: Use JSONL file (True) or inline (False)
    """
    if not BATCH_API_AVAILABLE:
        raise ImportError("google-genai not installed. Run: pip install google-genai")
    
    total_start = time.time()
    test_cases = test_case_list.test_cases
    n = len(test_cases)
    
    # STEP 1 - Calculate first to determine mode
    total_comparisons = calculate_total_comparisons(n)
    
    # Determine actual mode based on threshold
    will_use_file_mode = use_file_mode and total_comparisons > 20000
    
    logger.info("=" * 80)
    logger.info(f"🚀 GEMINI BATCH API - PARALLEL OPTIMIZATION")
    logger.info(f"   Test cases: {n}")
    logger.info(f"   Total comparisons: {total_comparisons:,}")
    logger.info(f"   Model: {selected_model}")
    logger.info(f"   API Mode: BATCH API (Parallel Processing)")
    logger.info(f"   Strategy: Adaptive batching with auto-split on quota exceeded")
    logger.info(f"   Cost: 50% cheaper than standard API")
    logger.info(f"   Processing Type: ALL comparisons processed in parallel batches")
    logger.info("=" * 80)
    
    # Prepare all comparisons
    logger.info(f"📋 Preparing comparison pairs...")
    all_comparisons = prepare_all_comparisons(test_cases)
    
    # Process with adaptive batching (auto-split on 429 error)
    logger.info(f"🚀 Processing with adaptive batching...")
    unique_cases, duplicates, all_comparison_results = await process_with_auto_split(
        all_comparisons,
        test_cases,
        custom_prompt,
        selected_model,
        api_key,
        process_id
    )
    
    # Validation
    logger.info(f"✅ Validation...")
    validation_passed = validate_unique_not_in_similar(unique_cases, duplicates)
    
    total_elapsed = time.time() - total_start
    
    # Create summary only (don't include all 13k comparison results to avoid MongoDB size limit)
    summary = {
        "Step": "SUMMARY",
        "ProcessType": "GeminiBatchAPI_Parallel",
        "ProcessingMode": "Batch API (Parallel)",
        "APIType": "Gemini Batch API",
        "IsSerialProcessing": False,
        "ProcessID": process_id,
        "Timestamp": datetime.now().isoformat(),
        "TotalTestCases": n,
        "TotalComparisons": total_comparisons,
        "UniqueTestCases": len(unique_cases),
        "TotalDuplicates": len(duplicates),
        "ValidationPassed": validation_passed,
        "TotalTime": f"{total_elapsed:.1f}s",
        "TotalTimeMinutes": f"{total_elapsed/60:.1f} min",
        "Model": selected_model,
        "CostSavings": "50% (Batch API pricing)",
        "Strategy": "Adaptive batching with auto-split on quota exceeded"
    }
    
    # Use summary as comparison_logs (not all 13k results)
    comparison_logs = [summary]
    
    logger.info("=" * 80)
    logger.info(f"🎉 BATCH API PARALLEL OPTIMIZATION COMPLETED")
    logger.info(f"   Processing Mode: Gemini Batch API (Parallel)")
    logger.info(f"   Strategy: Adaptive batching with auto-split")
    logger.info(f"   Total time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
    logger.info(f"   Unique: {len(unique_cases)}, Duplicates: {len(duplicates)}")
    logger.info(f"   Reduction: {len(duplicates)/n*100:.1f}%")
    logger.info(f"   Cost savings: 50% (Batch API pricing)")
    logger.info(f"   This was NOT serial processing - Batch API processed all comparisons in parallel")
    logger.info("=" * 80)
    
    # Convert TestCase objects to dictionaries for compatibility
    return TestCaseList(
        test_cases=[case.model_dump() for case in unique_cases],
        comparison_logs=comparison_logs,
        duplicates=duplicates
    )
    





