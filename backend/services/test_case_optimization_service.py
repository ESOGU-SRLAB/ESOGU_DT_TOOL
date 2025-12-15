from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from core.database import get_db
from utils.model_client import LLMClient
from utils.retry_utils import retry_llm_call
from utils.optimization_monitor import optimization_monitor
from datetime import datetime
import json
import uuid
import logging
import asyncio

logger = logging.getLogger(__name__)

# Import parallel optimization service
try:
    from services.parallel_optimization_service import parallel_smart_select
    PARALLEL_OPTIMIZATION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Parallel optimization service not available: {e}")
    PARALLEL_OPTIMIZATION_AVAILABLE = False

# Global dictionary to track running processes
running_processes = {}

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

async def _query_llm_similarity(case1: TestCase, case2: TestCase, custom_prompt: str = None, selected_model: str = "llama3.2:3b", api_key: str = None) -> bool:
    """
    İki TestCase nesnesini LLM'e JSON formatında göndererek benzerlik (is_same) sonucunu döndürür.
    """
    # Create JSON objects
    case1_json = case1.model_dump()
    case2_json = case2.model_dump()

    # Pop the ScenarioID and TestCaseID keys
    case1_json.pop("ScenarioID", None)
    case1_json.pop("TestCaseID", None)
    case2_json.pop("ScenarioID", None)
    case2_json.pop("TestCaseID", None)

    # Use custom prompt if provided, otherwise use default
    if custom_prompt:
        # Replace placeholders in custom prompt with actual test case data
        prompt_text = f"""{custom_prompt}

Below are the two test cases in JSON format:

TestCase1:
{json.dumps(case1_json, indent=2, ensure_ascii=False)}

TestCase2:
{json.dumps(case2_json, indent=2, ensure_ascii=False)}
"""
    else:
        # Default prompt text for Smart Selection using LLM
        prompt_text = f"""
You are given two test cases, each with a certain set of fields:
- Title
- Description
- Objective

You will decide whether these two test cases are "contextually the same" based on the following criteria:

1. If both have the same Title (case-insensitive) OR their Titles are substantially similar in meaning,
2. AND they have either the same or very similar Description and/or Objective,
3. AND they serve essentially the same testing purpose for the same or very closely related scenarios,
4. THEN you should conclude that these two test cases are the same.
5. The order of importance Description > Objective > Title.

Otherwise, they are considered different.

Below are the two test cases in JSON format:

TestCase1:
{json.dumps(case1_json, indent=2, ensure_ascii=False)}

TestCase2:
{json.dumps(case2_json, indent=2, ensure_ascii=False)}

Return your response **only** in valid JSON with the following format:

{{
  "is_same": <true or false>
}}

Where:
- is_same = true if the test cases meet the criteria above
- is_same = false otherwise

Important:
- Return ONLY the raw JSON object, no markdown formatting
- Do not use ```json``` or ``` code blocks  
- Do not provide any additional text outside the JSON object
- Do not explain your reasoning, only provide the final JSON response
"""

    try:
        # LM Studio API'sine LLMClient ile istek gönder (sadece bir kez oluştur)
        logger.debug(f"Creating LLMClient for similarity check: {selected_model}")
        llm_client = LLMClient(model_name=selected_model, api_key=api_key)
        # Set the original key to support model mapping
        llm_client.original_key = selected_model
        
        # LLMClient'ı kullanarak yanıt al
        logger.debug(f"Sending request to LLM: {selected_model}")
        response = await llm_client.generate_response(
            prompt=prompt_text.strip(),
            temperature=0.1,  # Consistency için düşük temperature
            max_tokens=1000
        )
        
        if not response:
            logger.error("Empty response from LLM")
            return False
        
        logger.debug(f"Raw LLM response: {response[:200]}...")  # İlk 200 karakter
        
        # Clean LLM response from markdown code blocks for individual comparison too
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]  # Remove ```json
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]   # Remove ```
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]  # Remove ending ```
        cleaned_response = cleaned_response.strip()
        
        try:
            # JSON parsing ile response'u parse et
            parsed_content = json.loads(cleaned_response)
            return parsed_content.get("is_same", False)
        except json.JSONDecodeError:
            # Eğer JSON değilse, text içinde "true" veya "false" ara
            response_lower = cleaned_response.lower()
            if '"is_same": true' in response_lower or '"is_same":true' in response_lower:
                return True
            elif '"is_same": false' in response_lower or '"is_same":false' in response_lower:
                return False
            else:
                logger.error(f"LLM response is not valid JSON and doesn't contain expected format: {cleaned_response}")
                return False
            
    except Exception as e:
        logger.error(f"Error calling LLM API via LLMClient: {e}")
        # Hata durumunda None döndürmek yerine exception fırlat ki retry mekanizması çalışsın
        raise

async def _query_llm_similarity_with_retry(case1: TestCase, case2: TestCase, custom_prompt: str = None, selected_model: str = "llama3.2:3b", api_key: str = None) -> bool:
    """
    Retry mekanizması ile LLM benzerlik sorgusu - 503 hataları için daha uzun retry
    """
    case1_id = getattr(case1, 'TestCaseID', 'Unknown')
    case2_id = getattr(case2, 'TestCaseID', 'Unknown')
    
    try:
        # Başarılı sonuç alınana kadar denenmeye devam et
        max_retries = float('inf')  # Sonsuz retry
        max_delay = 60.0 if "gemini" in selected_model.lower() else 30.0
        
        logger.info(f"🔄 Starting LLM comparison with unlimited retries until success for model: {selected_model}")
        
        # Retry mekanizması ile LLM çağrısı - başarılı olana kadar devam et  
        result = await retry_llm_call(
            _query_llm_similarity,
            case1, case2, custom_prompt, selected_model, api_key,
            max_retries=999999,  # Çok yüksek sayı (pratikte sonsuz)
            base_delay=2.0,  # Biraz daha uzun base delay
            max_delay=max_delay
        )
        
        # Başarılı karşılaştırmayı kaydet
        optimization_monitor.log_comparison_attempt(
            case1_id, case2_id, 
            success=True, 
            attempt_number=1,  # retry_llm_call içinde attempt number takip etmiyor, bu yüzden 1
            model_used=selected_model
        )
        
        logger.info(f"✅ Successfully compared cases {case1_id} vs {case2_id} with model {selected_model}")
        return result
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Failed to compare cases {case1_id} vs {case2_id} after all retries: {error_msg}")
        
        # Başarısız karşılaştırmayı kaydet (bu duruma artık nadiren gireceğiz)
        optimization_monitor.log_comparison_attempt(
            case1_id, case2_id, 
            success=False, 
            attempt_number=999999,  # Unlimited retry sonrası başarısız (çok nadir)
            error_message=error_msg,
            model_used=selected_model
        )
        
        # 503 hataları için özel mesaj
        if "503" in error_msg or "unavailable" in error_msg.lower():
            logger.error(f"🔴 Google Gemini servers appear to be overloaded. Please try again later.")
        
        return False  # Hata durumunda False döndür (farklı olarak kabul et)

async def smart_select(test_case_list: TestCaseList, custom_prompt: str = None, selected_model: str = "llama3.2:3b", api_key: str = None, process_id: str = None) -> TestCaseList:
    """
    Bu fonksiyon, test_cases listesindeki benzer (duplicate) test case'leri 
    LLM tabanlı karşılaştırma ile ayıklar, unique bir liste döndürür.
    """
    logger.info("🔴 SMART_SELECT (SERIAL) CALLED")
    logger.info(f"🔴 Processing {len(test_case_list.test_cases)} test cases in SERIAL mode (multiple LLM calls)")
    logger.info(f"🔴 Selected model: {selected_model}")
    
    unique_cases = []
    step = 1
    comparison_logs = []
    duplicates = []

    for case in test_case_list.test_cases:
        # Check if process should be stopped
        if process_id and process_id in running_processes and running_processes[process_id]["status"] == "stopped":
            logger.info(f"Smart select process {process_id} was stopped by user (during case processing)")
            break
            
        is_duplicate = False
        for unique_case in unique_cases:
            # Check again before each comparison
            if process_id and process_id in running_processes and running_processes[process_id]["status"] == "stopped":
                logger.info(f"Smart select process {process_id} was stopped during comparison")
                break
                
            try:
                # Retry ve monitoring ile LLM çağrısı
                comparison_result = await _query_llm_similarity_with_retry(case, unique_case, custom_prompt, selected_model, api_key)
            except Exception as e:
                logger.warning(f"LLM comparison failed: {e}")
                comparison_result = False

            comparison_logs.append({
                "Step": step,
                "ProcessName": str(uuid.uuid4()),
                "Timestamp": datetime.now().isoformat(),
                "Case1": case.model_dump(),
                "Case2": unique_case.model_dump(),
                "is_same": comparison_result,
            })
            step += 1

            if comparison_result:
                is_duplicate = True
                # Benzer test durumlarını kaydet
                duplicates.append({
                    "DuplicateCase": case.model_dump(),
                    "MatchedWith": unique_case.model_dump()
                })
                break

        if not is_duplicate:
            unique_cases.append(case)

    # Session summary logla
    optimization_monitor.log_session_summary("individual")

    return TestCaseList(
        test_cases=unique_cases,
        comparison_logs=comparison_logs,
        duplicates=duplicates
    )

async def bulk_smart_select(test_case_list: TestCaseList, custom_prompt: str = None, selected_model: str = "llama3.2:3b", api_key: str = None) -> TestCaseList:
    """
    Tüm test case'leri tek bir LLM çağrısında toplu olarak karşılaştırarak optimization yapar.
    Bu yöntem daha hızlı ve kaynak-verimli olmasına rağmen, büyük test case grupları için
    token limitlerini aşabilir.
    """
    logger.info("🔵 BULK_SMART_SELECT CALLED")
    logger.info(f"🔵 Processing {len(test_case_list.test_cases)} test cases in BULK mode (single LLM call)")
    logger.info(f"🔵 Selected model: {selected_model}")
    
    try:
        # Create test cases array for bulk processing
        test_cases_data = []
        for idx, case in enumerate(test_case_list.test_cases):
            case_json = case.model_dump()
            # Remove IDs for comparison
            case_json.pop("ScenarioID", None)
            case_json.pop("TestCaseID", None)
            case_json["Index"] = idx  # Add index for tracking
            test_cases_data.append(case_json)

        # Create bulk comparison prompt
        if custom_prompt:
            prompt_text = f"""CRITICAL: Return ONLY valid JSON. NO explanations, NO markdown, NO text outside JSON.

{custom_prompt}

TEST CASES TO ANALYZE:
{json.dumps(test_cases_data, indent=2, ensure_ascii=False)}

REQUIRED JSON OUTPUT (exact format):
{{
  "unique_indices": [0, 1, 2],
  "duplicate_groups": [
    {{
      "representative_index": 0,
      "duplicate_indices": [3, 4]
    }}
  ]
}}

Return ONLY the JSON object. Start with {{ and end with }}. NO other text."""
        else:
            prompt_text = f"""
CRITICAL INSTRUCTION: You MUST return ONLY a valid JSON object. NO explanations, NO markdown, NO text before or after the JSON.

Your task: Analyze the test cases and identify duplicates.

ANALYSIS CRITERIA:
1. Test cases are DUPLICATES if they have:
   - Same or very similar Title (case-insensitive)
   - AND very similar Description and/or Objective
   - AND serve the same testing purpose
2. Priority: Description > Objective > Title

TEST CASES TO ANALYZE:
{json.dumps(test_cases_data, indent=2, ensure_ascii=False)}

REQUIRED OUTPUT FORMAT (COPY THIS STRUCTURE EXACTLY):
{{
  "unique_indices": [0, 1, 2],
  "duplicate_groups": [
    {{
      "representative_index": 0,
      "duplicate_indices": [3, 4]
    }}
  ]
}}

RULES:
- unique_indices: Indices of ALL unique test cases (including representatives)
- duplicate_groups: Groups of duplicates with their representative
- representative_index: Best test case from a duplicate group
- duplicate_indices: Other test cases that are duplicates of the representative
- Return ONLY the JSON object
- NO markdown code blocks (```json)
- NO explanations or text
- START your response with {{ and END with }}
"""

        # Make single LLM call with retry
        async def _bulk_llm_call():
            llm_client = LLMClient(model_name=selected_model, api_key=api_key)
            llm_client.original_key = selected_model
            
            return await llm_client.generate_response(
                prompt=prompt_text.strip(),
                temperature=0.1,
                max_tokens=6000  # Increased for bulk response to handle larger datasets
            )
        
        # Retry mekanizması ile bulk LLM çağrısı
        try:
            response = await retry_llm_call(
                _bulk_llm_call,
                max_retries=3,
                base_delay=2.0,  # Bulk için biraz daha uzun bekleme
                max_delay=60.0
            )
            
            # Başarılı bulk çağrıyı logla
            optimization_monitor.log_comparison_attempt(
                "bulk_processing", f"total_{len(test_case_list.test_cases)}_cases",
                success=True,
                attempt_number=1,
                model_used=selected_model
            )
            
        except Exception as e:
            # Başarısız bulk çağrıyı logla
            optimization_monitor.log_comparison_attempt(
                "bulk_processing", f"total_{len(test_case_list.test_cases)}_cases",
                success=False,
                attempt_number=3,
                error_message=str(e),
                model_used=selected_model
            )
            raise ValueError(f"Bulk optimization failed after retries: {str(e)}")
        
        if not response:
            logger.error("Empty response from LLM in bulk processing")
            # Don't fallback - raise specific error for bulk optimization
            raise ValueError("Bulk optimization failed: LLM returned empty response")
        
        # Enhanced JSON extraction algorithm - extract JSON from mixed text response
        def extract_json_from_response(response_text):
            """Extract JSON object from text response that may contain explanatory text"""
            response_text = response_text.strip()
            
            # Method 1: Try to find JSON with regex pattern
            import re
            json_pattern = r'\{[^{}]*"unique_indices"[^{}]*\[[^\]]*\][^{}]*"duplicate_groups"[^{}]*\[[^\]]*\][^{}]*\}'
            json_matches = re.findall(json_pattern, response_text, re.DOTALL)
            
            if json_matches:
                logger.info(f"Found {len(json_matches)} JSON patterns with regex")
                # Try each match until we find valid JSON
                for match in json_matches:
                    try:
                        # Clean the match
                        cleaned_match = match.strip()
                        test_json = json.loads(cleaned_match)
                        if "unique_indices" in test_json and "duplicate_groups" in test_json:
                            logger.info("Successfully validated JSON from regex match")
                            return cleaned_match
                    except json.JSONDecodeError:
                        continue
            
            # Method 2: Look for standalone JSON block patterns
            json_block_patterns = [
                r'```json\s*(\{.*?\})\s*```',
                r'```\s*(\{.*?\})\s*```',
                r'(\{[^{]*"unique_indices"[^}]*\})'
            ]
            
            for pattern in json_block_patterns:
                matches = re.findall(pattern, response_text, re.DOTALL)
                for match in matches:
                    try:
                        cleaned_match = match.strip()
                        test_json = json.loads(cleaned_match)
                        if "unique_indices" in test_json and "duplicate_groups" in test_json:
                            logger.info(f"Successfully validated JSON from pattern: {pattern[:50]}...")
                            return cleaned_match
                    except json.JSONDecodeError:
                        continue
            
            # Method 3: Find JSON object by brace matching
            brace_count = 0
            start_idx = -1
            end_idx = -1
            
            for i, char in enumerate(response_text):
                if char == '{':
                    if start_idx == -1:
                        start_idx = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_idx != -1:
                        end_idx = i
                        potential_json = response_text[start_idx:end_idx + 1]
                        try:
                            test_json = json.loads(potential_json)
                            if "unique_indices" in test_json and "duplicate_groups" in test_json:
                                logger.info("Successfully validated JSON from brace matching")
                                return potential_json
                        except json.JSONDecodeError:
                            pass
                        # Reset for next potential JSON block
                        start_idx = -1
            
            # Method 4: Traditional markdown block cleaning as fallback
            cleaned_response = response_text.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            return cleaned_response
        
        # Use enhanced JSON extraction
        cleaned_response = extract_json_from_response(response)
        
        logger.info(f"Original LLM response length: {len(response)}")
        logger.info(f"Cleaned response length: {len(cleaned_response)}")
        logger.info(f"Original response: {response}")
        logger.info(f"Cleaned response: {cleaned_response}")
        
        try:
            # Parse the cleaned bulk response
            parsed_content = json.loads(cleaned_response)
            
            # Handle different response formats from LLM
            # Format 1: {"unique_indices": [...], "duplicate_groups": [...]}
            # Format 2: {"duplicates": [[0,1], [2,3], ...]}
            # Format 3: [[0,1], [2,3], ...] (plain array)
            # Format 4: {"duplicate_sets": [[0,1], [2,3], ...]}
            
            # Check if parsed_content is a plain list (Format 3)
            if isinstance(parsed_content, list):
                logger.info("🔄 Converting plain array format to standard format")
                
                # Check if it's array of objects with "test_cases" key (detailed format)
                if parsed_content and isinstance(parsed_content[0], dict) and "test_cases" in parsed_content[0]:
                    # Format: [{"duplicate_group": 1, "test_cases": [{"Index": 69}, {"Index": 103}]}]
                    duplicates_array = []
                    for group in parsed_content:
                        indices = [tc.get("Index") for tc in group.get("test_cases", []) if "Index" in tc]
                        if indices:
                            duplicates_array.append(indices)
                else:
                    # Simple array of arrays
                    duplicates_array = parsed_content
                
                # Build unique_indices and duplicate_groups from plain array
                all_duplicate_indices = set()
                duplicate_groups = []
                
                for dup_group in duplicates_array:
                    if len(dup_group) > 1:
                        representative = dup_group[0]
                        duplicates = dup_group[1:]
                        duplicate_groups.append({
                            "representative_index": representative,
                            "duplicate_indices": duplicates
                        })
                        # Add all to duplicate set
                        all_duplicate_indices.update(dup_group)
                
                # Unique indices are all indices NOT in duplicate groups
                total_cases = len(test_case_list.test_cases)
                unique_indices = [i for i in range(total_cases) if i not in all_duplicate_indices]
                
                # Add representatives to unique_indices
                for group in duplicate_groups:
                    rep_idx = group["representative_index"]
                    if rep_idx not in unique_indices:
                        unique_indices.append(rep_idx)
                
                unique_indices.sort()
                
                logger.info(f"✅ Converted {len(duplicates_array)} duplicate groups from plain array")
            elif "duplicate_sets" in parsed_content:
                # Format 4: {"duplicate_sets": [[0,1], [2,3], ...]}
                # or Format 4b: {"duplicate_sets": [{"indices": [0,1], "reason": "..."}, ...]}
                logger.info("🔄 Converting duplicate_sets format to standard format")
                duplicates_raw = parsed_content.get("duplicate_sets", [])
                
                # Check if it's array of objects with "indices" key
                if duplicates_raw and isinstance(duplicates_raw[0], dict) and "indices" in duplicates_raw[0]:
                    # Format 4b: Array of objects with indices and reasons
                    duplicates_array = [item["indices"] for item in duplicates_raw]
                else:
                    # Format 4: Simple array of arrays
                    duplicates_array = duplicates_raw
                
                # Build unique_indices and duplicate_groups from duplicate_sets
                all_duplicate_indices = set()
                duplicate_groups = []
                
                for dup_group in duplicates_array:
                    if len(dup_group) > 1:
                        representative = dup_group[0]
                        duplicates = dup_group[1:]
                        duplicate_groups.append({
                            "representative_index": representative,
                            "duplicate_indices": duplicates
                        })
                        # Add all to duplicate set
                        all_duplicate_indices.update(dup_group)
                
                # Unique indices are all indices NOT in duplicate groups
                total_cases = len(test_case_list.test_cases)
                unique_indices = [i for i in range(total_cases) if i not in all_duplicate_indices]
                
                # Add representatives to unique_indices
                for group in duplicate_groups:
                    rep_idx = group["representative_index"]
                    if rep_idx not in unique_indices:
                        unique_indices.append(rep_idx)
                
                unique_indices.sort()
                
                logger.info(f"✅ Converted {len(duplicates_array)} duplicate groups from duplicate_sets")
            elif "duplicates" in parsed_content and "unique_indices" not in parsed_content:
                # Convert Format 2 to Format 1
                # Can be: {"duplicates": [[0,1], [2,3], ...]} 
                # or {"duplicates": [{"indices": [...], "reason": "..."}]}
                # or {"duplicates": [{"primary_test_case_index": X, "duplicate_test_case_indices": [...], "reason": "..."}]}
                logger.info("🔄 Converting alternative duplicate format to standard format")
                duplicates_raw = parsed_content.get("duplicates", [])
                
                # Check if it's array of objects with "primary_test_case_index" and "duplicate_test_case_indices"
                if duplicates_raw and isinstance(duplicates_raw[0], dict) and "primary_test_case_index" in duplicates_raw[0]:
                    # Format: Array of objects with primary_test_case_index and duplicate_test_case_indices
                    logger.info("🔍 Detected primary_test_case_index format")
                    duplicates_array = []
                    for item in duplicates_raw:
                        primary_idx = item.get("primary_test_case_index")
                        duplicate_indices = item.get("duplicate_test_case_indices", [])
                        # Combine primary with duplicates into single group
                        group = [primary_idx] + duplicate_indices
                        duplicates_array.append(group)
                    logger.info(f"✅ Converted {len(duplicates_array)} groups from primary_test_case_index format")
                # Check if it's array of objects with "indices" key
                elif duplicates_raw and isinstance(duplicates_raw[0], dict) and "indices" in duplicates_raw[0]:
                    # Format: Array of objects with indices and reasons
                    duplicates_array = [item["indices"] for item in duplicates_raw]
                else:
                    # Format: Simple array of arrays
                    duplicates_array = duplicates_raw
                
                # Build unique_indices and duplicate_groups from duplicates array
                all_duplicate_indices = set()
                duplicate_groups = []
                
                for dup_group in duplicates_array:
                    if len(dup_group) > 1:
                        representative = dup_group[0]
                        duplicates = dup_group[1:]
                        duplicate_groups.append({
                            "representative_index": representative,
                            "duplicate_indices": duplicates
                        })
                        # Add all to duplicate set
                        all_duplicate_indices.update(dup_group)
                
                # Unique indices are all indices NOT in duplicate groups
                total_cases = len(test_case_list.test_cases)
                unique_indices = [i for i in range(total_cases) if i not in all_duplicate_indices]
                
                # Add representatives to unique_indices
                for group in duplicate_groups:
                    rep_idx = group["representative_index"]
                    if rep_idx not in unique_indices:
                        unique_indices.append(rep_idx)
                
                unique_indices.sort()
                
                logger.info(f"✅ Converted {len(duplicates_array)} duplicate groups")
            else:
                # Standard format or {"duplicate_groups": [[array], [array]]}
                unique_indices = parsed_content.get("unique_indices", [])
                duplicate_groups_raw = parsed_content.get("duplicate_groups", [])
                
                # Check if duplicate_groups is array of arrays (not array of objects)
                if duplicate_groups_raw and isinstance(duplicate_groups_raw[0], list):
                    # Format: {"duplicate_groups": [[0,1], [2,3], ...]}
                    logger.info("🔄 Converting duplicate_groups array format to standard format")
                    
                    all_duplicate_indices = set()
                    duplicate_groups = []
                    
                    for dup_group in duplicate_groups_raw:
                        if len(dup_group) > 1:
                            representative = dup_group[0]
                            duplicates = dup_group[1:]
                            duplicate_groups.append({
                                "representative_index": representative,
                                "duplicate_indices": duplicates
                            })
                            all_duplicate_indices.update(dup_group)
                    
                    # If unique_indices is empty, calculate it
                    if not unique_indices:
                        total_cases = len(test_case_list.test_cases)
                        unique_indices = [i for i in range(total_cases) if i not in all_duplicate_indices]
                        
                        # Add representatives
                        for group in duplicate_groups:
                            rep_idx = group["representative_index"]
                            if rep_idx not in unique_indices:
                                unique_indices.append(rep_idx)
                        
                        unique_indices.sort()
                    
                    logger.info(f"✅ Converted {len(duplicate_groups_raw)} duplicate groups from array format")
                else:
                    # Standard object format
                    duplicate_groups = duplicate_groups_raw
            
            logger.info(f"JSON parsing successful!")
            logger.info(f"Found unique_indices: {unique_indices}")
            logger.info(f"Found duplicate_groups: {duplicate_groups}")
            logger.info(f"Total unique test cases: {len(unique_indices)}")
            logger.info(f"Total duplicate groups: {len(duplicate_groups)}")
            
            # Build unique cases list
            unique_cases = []
            for idx in unique_indices:
                if 0 <= idx < len(test_case_list.test_cases):
                    unique_cases.append(test_case_list.test_cases[idx])
            
            # Build duplicates list
            duplicates = []
            for group in duplicate_groups:
                # Handle both dict and potential other formats
                if isinstance(group, dict):
                    rep_idx = group.get("representative_index")
                    dup_indices = group.get("duplicate_indices", [])
                else:
                    # Shouldn't happen but just in case
                    continue
                
                if 0 <= rep_idx < len(test_case_list.test_cases):
                    representative = test_case_list.test_cases[rep_idx]
                    for dup_idx in dup_indices:
                        if 0 <= dup_idx < len(test_case_list.test_cases):
                            duplicate_case = test_case_list.test_cases[dup_idx]
                            duplicates.append({
                                "DuplicateCase": duplicate_case.model_dump(),
                                "MatchedWith": representative.model_dump()
                            })
            
            # Create comparison log for bulk processing
            comparison_logs = [{
                "Step": 1,
                "ProcessName": f"Bulk_Optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "Timestamp": datetime.now().isoformat(),
                "ProcessingType": "Bulk",
                "TotalTestCases": len(test_case_list.test_cases),
                "UniqueFound": len(unique_cases),
                "DuplicatesFound": len(duplicates),
                "OptimizationMethod": "Single LLM Call for All Test Cases",
                "Efficiency": f"{len(unique_cases)}/{len(test_case_list.test_cases)} test cases kept ({(len(unique_cases)/len(test_case_list.test_cases)*100):.1f}%)",
                "DuplicateGroups": len(duplicate_groups),
                "LLMResponse": parsed_content,
                "CustomPrompt": bool(custom_prompt),
                "ModelUsed": selected_model
            }]
            
            # Session summary logla
            optimization_monitor.log_session_summary("bulk")
            
            return TestCaseList(
                test_cases=unique_cases,
                comparison_logs=comparison_logs,
                duplicates=duplicates
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse bulk LLM response: {e}")
            logger.error(f"Original response was: {response}")
            logger.error(f"Cleaned response was: {cleaned_response}")
            # Don't fallback - raise specific error for bulk optimization
            raise ValueError(f"Bulk optimization failed: LLM response is not valid JSON after cleaning. Cleaned response: {cleaned_response[:500]}...")
            
    except Exception as e:
        logger.error(f"Error in bulk smart selection: {e}")
        # Don't fallback - raise specific error for bulk optimization
        raise RuntimeError(f"Bulk optimization failed: {str(e)}")

class TestCaseOptimizationService:
    def __init__(self):
        self.db = get_db()  # Use synchronous database connection
        self.collection = self.db["session_history"]  # Updated to use session_history collection

    def stop_process(self, process_id: str) -> Dict[str, Any]:
        """
        Çalışan bir process'i durdur.
        """
        logger.info(f"Stop process request received for process_id: {process_id}")
        logger.info(f"Current running processes: {list(running_processes.keys())}")
        
        if process_id not in running_processes:
            logger.warning(f"Process {process_id} not found in running_processes")
            return {
                "success": False,
                "message": f"Process {process_id} not found or already completed"
            }
        
        # Log current process status before stopping
        current_status = running_processes[process_id]["status"]
        logger.info(f"Process {process_id} current status: {current_status}")
        
        # Mark process as stopped
        running_processes[process_id]["status"] = "stopped"
        running_processes[process_id]["end_time"] = datetime.now()
        
        logger.info(f"Process {process_id} marked as stopped successfully")
        
        return {
            "success": True,
            "message": f"Process {process_id} stopped successfully"
        }

    def get_process_status(self, process_id: str) -> Dict[str, Any]:
        """
        Bir process'in durumunu getir.
        """
        if process_id not in running_processes:
            return {
                "success": False,
                "message": f"Process {process_id} not found"
            }
        
        return {
            "success": True,
            "data": running_processes[process_id]
        }

    def list_running_processes(self) -> Dict[str, Any]:
        """
        Tüm çalışan process'leri listele.
        """
        return {
            "success": True,
            "data": running_processes
        }

    def get_process_titles_with_counts(self) -> List[Dict[str, Any]]:
        """
        Process title'ları, test case sayılarını ve kaynak dosya bilgilerini getir.
        """
        try:
            process_titles = self.get_available_process_titles()
            process_data = []
            
            for title in process_titles:
                test_cases = self.get_test_cases_by_process_title(title)
                file_names = self.get_source_files_for_process_title(title)
                process_data.append({
                    "process_title": title,
                    "test_case_count": len(test_cases),
                    "source_files": file_names,
                    "enabled": True
                })
            
            return process_data
        except Exception as e:
            logger.error(f"Error fetching process titles with counts: {e}")
            return []

    def get_source_files_for_process_title(self, process_title: str) -> List[str]:
        """
        Belirli bir process_title için kaynak dosya isimlerini getir.
        MongoDB'de processes.test_scenario_generation.output.metadata.file_names'den alır.
        """
        try:
            source_files = set()
            
            # test_scenario_generation'dan file_names bilgisini getir
            pipeline = [
                {"$match": {"processes.test_scenario_generation.process_title": process_title}},
                {"$project": {"file_names": "$processes.test_scenario_generation.output.metadata.file_names"}},
                {"$match": {"file_names": {"$exists": True, "$ne": None}}}
            ]
            
            cursor = self.collection.aggregate(pipeline)
            for doc in cursor:
                file_names = doc.get("file_names", [])
                if isinstance(file_names, list):
                    source_files.update(file_names)
                elif isinstance(file_names, str):
                    source_files.add(file_names)
            
            logger.info(f"Found {len(source_files)} source files for process title: {process_title}")
            return sorted(list(source_files))
            
        except Exception as e:
            logger.error(f"Error fetching source files for process title {process_title}: {e}")
            return []

    def get_available_process_titles(self) -> List[str]:
        """
        MongoDB'den mevcut process_title değerlerini getir.
        Önce test_case_generation'dan process title'ları kontrol et, sonra test_scenario_generation'dan al.
        """
        try:
            process_titles = set()
            
            # First, get process titles from test_case_generation results
            pipeline_test_cases = [
                {"$match": {"processes.test_case_generation.output.data.test_case_results": {"$exists": True}}},
                {"$unwind": "$processes.test_case_generation.output.data.test_case_results"},
                {"$match": {"processes.test_case_generation.output.data.test_case_results.metadata.selected_process_title": {"$ne": None, "$exists": True}}},
                {"$group": {"_id": "$processes.test_case_generation.output.data.test_case_results.metadata.selected_process_title"}},
                {"$sort": {"_id": 1}}
            ]
            
            cursor = self.collection.aggregate(pipeline_test_cases)
            for doc in cursor:
                if doc["_id"]:
                    process_titles.add(doc["_id"])
            
            # Then, get process titles from test_scenario_generation
            pipeline_scenarios = [
                {"$match": {"processes.test_scenario_generation.process_title": {"$ne": None, "$exists": True}}},
                {"$group": {"_id": "$processes.test_scenario_generation.process_title"}},
                {"$sort": {"_id": 1}}
            ]
            
            cursor = self.collection.aggregate(pipeline_scenarios)
            for doc in cursor:
                if doc["_id"]:
                    process_titles.add(doc["_id"])
            
            # Convert set to sorted list
            return sorted(list(process_titles))
        except Exception as e:
            logger.error(f"Error fetching process titles: {e}")
            return []

    def get_test_cases_by_process_titles(self, process_titles: List[str]) -> List[Dict[str, Any]]:
        """
        Birden fazla process_title için tüm test case'leri getir.
        Session_history collection'ından test_case_generation sonuçlarını kontrol et.
        """
        try:
            all_test_cases = []
            
            for process_title in process_titles:
                process_test_cases = self.get_test_cases_by_process_title(process_title)
                all_test_cases.extend(process_test_cases)
            
            logger.info(f"Total found {len(all_test_cases)} test cases across {len(process_titles)} processes")
            return all_test_cases
        except Exception as e:
            logger.error(f"Error fetching test cases for multiple processes: {e}")
            return []

    def get_test_cases_by_process_title(self, process_title: str) -> List[Dict[str, Any]]:
        """
        Belirli bir process_title için tüm test case'leri getir.
        Session_history collection'ından test_case_generation sonuçlarını kontrol et.
        """
        try:
            all_test_cases = []
            
            # Search in session_history for test_case_generation results
            # Use the CORRECT path: processes.test_case_generation.output.test_case_results
            documents = list(self.collection.find(
                {"processes.test_case_generation.selected_process_title": process_title},
                {"processes.test_case_generation": 1, "session_id": 1}
            ))
            
            logger.info(f"Found {len(documents)} documents with test_case_generation for {process_title}")
            
            for doc_idx, doc in enumerate(documents):
                session_id = doc.get("session_id", f"unknown_{doc_idx}")
                test_case_gen_data = doc.get("processes", {}).get("test_case_generation", {})
                output_data = test_case_gen_data.get("output", {})
                test_case_results = output_data.get("test_case_results", [])
                
                logger.info(f"Document {doc_idx+1} (Session: {session_id}): Found {len(test_case_results)} test_case_results")
                
                # Iterate through each scenario's test cases
                for result_idx, result in enumerate(test_case_results):
                    # Since we searched by process_title, all results should match
                    if result.get("status") == "success" and "test_cases" in result:
                        scenario_id = result.get("scenario_id", f"Unknown_{doc_idx}_{result_idx}")
                        test_cases = result.get("test_cases", [])
                        metadata = result.get("metadata", {})
                        selected_category = metadata.get("selected_category", "Unknown")
                        selected_test_type = metadata.get("selected_test_type", "Unknown")
                        
                        logger.info(f"  Result {result_idx+1}: {len(test_cases)} test cases for scenario {scenario_id}")
                        
                        # ADD ALL TEST CASES from this scenario, not just one!
                        for tc_idx, test_case in enumerate(test_cases):
                            test_case_id = test_case.get("TestCaseID", f"TC_{scenario_id}_{tc_idx}")
                            title = test_case.get("Title", "No Title")
                            description = test_case.get("Description", "No Description")
                            objective = test_case.get("Objective", "No Objective")
                            category = test_case.get("Category", "No Category")
                            
                            all_test_cases.append({
                                "ScenarioID": scenario_id,
                                "TestCaseID": test_case_id,
                                "Title": title,
                                "Description": description,
                                "Objective": objective,
                                "Category": category,
                                "Comments": test_case.get("Comments", ""),
                                "SelectedCategory": selected_category,
                                "SelectedTestType": selected_test_type,
                                "SessionID": session_id,
                                "ProcessTitle": process_title,  # Add process title for identification
                                "unique_key": f"{test_case_id}_{selected_category}_{selected_test_type}_{doc_idx}_{tc_idx}"
                            })
            
            # If no test cases found from test_case_generation, fallback to test_scenario_generation (scenarios only)
            if not all_test_cases:
                scenario_documents = list(self.collection.find(
                    {"processes.test_scenario_generation.process_title": process_title},
                    {"processes.test_scenario_generation": 1, "session_id": 1}
                ))
                
                logger.info(f"Found {len(scenario_documents)} documents with test_scenario_generation for {process_title}")
                
                for doc_idx, doc in enumerate(scenario_documents):
                    session_id = doc.get("session_id", f"unknown_{doc_idx}")
                    test_generation_data = doc.get("processes", {}).get("test_scenario_generation", {})
                    test_scenarios = test_generation_data.get("output", {}).get("test_scenarios", {})
                    selected_category = test_generation_data.get("selected_category", "Unknown")
                    selected_test_type = test_generation_data.get("selected_test_type", "Unknown")
                    
                    # Test scenarios yapısını kontrol et
                    scenarios_list = []
                    if isinstance(test_scenarios, dict):
                        scenarios_list = test_scenarios.get("TestScenarios", [])
                    elif isinstance(test_scenarios, list):
                        scenarios_list = test_scenarios
                    
                    logger.info(f"Scenario Document {doc_idx+1}: Found {len(scenarios_list)} scenarios")
                    
                    for idx, scenario in enumerate(scenarios_list):
                        scenario_id = scenario.get("ScenarioID", f"Scenario_{doc_idx}_{idx}")
                        title = scenario.get("Title", "No Title")
                        description = scenario.get("Description", "No Description")
                        objective = scenario.get("Objective", "No Objective")
                        category = scenario.get("Category", "No Category")
                        comments = scenario.get("Comments", "No Comments")
                        
                        all_test_cases.append({
                            "ScenarioID": scenario_id,
                            "TestCaseID": scenario_id,  # Use ScenarioID as TestCaseID for scenarios
                            "Title": title,
                            "Description": description,
                            "Objective": objective,
                            "Category": category,
                            "Comments": comments,
                            "SelectedCategory": selected_category,
                            "SelectedTestType": selected_test_type,
                            "SessionID": session_id,
                            "ProcessTitle": process_title,  # Add process title for identification
                            "unique_key": f"{scenario_id}_{selected_category}_{selected_test_type}_{doc_idx}"
                        })
            
            logger.info(f"Total found {len(all_test_cases)} test cases for process_title: {process_title}")
            return all_test_cases
        except Exception as e:
            logger.error(f"Error fetching test cases for process_title {process_title}: {e}")
            return []

    async def run_smart_selection(self, selected_test_cases: List[Dict[str, Any]], custom_prompt: str = None, selected_model: str = "llama3.2:3b", api_key: str = None, process_id: str = None) -> Dict[str, Any]:
        """
        Seçilen test case'ler üzerinde smart selection işlemini çalıştır.
        """
        # Generate process ID if not provided
        if not process_id:
            process_id = str(uuid.uuid4())
            
        # Track this process
        running_processes[process_id] = {
            "status": "running",
            "start_time": datetime.now(),
            "process_type": "smart_selection"
        }
        
        try:
            # Pydantic modeline dönüştür
            valid_data = []
            for item in selected_test_cases:
                # Check if process should be stopped
                if process_id in running_processes and running_processes[process_id]["status"] == "stopped":
                    logger.info(f"Process {process_id} was stopped by user")
                    return {
                        "success": False,
                        "message": "Process stopped by user",
                        "data": {},
                        "process_id": process_id
                    }
                    
                try:
                    test_case = TestCase(
                        ScenarioID=item.get("ScenarioID", ""),
                        TestCaseID=item.get("TestCaseID", ""),
                        Title=item.get("Title", ""),
                        Description=item.get("Description"),
                        Objective=item.get("Objective")
                    )
                    valid_data.append(test_case)
                except Exception as e:
                    logger.warning(f"Skipping invalid test case: {item}. Error: {e}")

            if not valid_data:
                # Remove from tracking
                running_processes.pop(process_id, None)
                return {
                    "success": False,
                    "message": "No valid test cases to process",
                    "data": {},
                    "process_id": process_id
                }

            # Check again before starting the main processing
            if process_id in running_processes and running_processes[process_id]["status"] == "stopped":
                logger.info(f"Process {process_id} was stopped by user")
                return {
                    "success": False,
                    "message": "Process stopped by user",
                    "data": {},
                    "process_id": process_id
                }

            # Smart selection işlemini çalıştır
            test_case_list = TestCaseList(test_cases=valid_data)
            unique_test_cases = await smart_select(test_case_list, custom_prompt, selected_model, api_key, process_id)

            # Check if process was stopped during execution
            if process_id in running_processes and running_processes[process_id]["status"] == "stopped":
                logger.info(f"Process {process_id} was stopped during execution")
                return {
                    "success": False,
                    "message": "Process stopped by user",
                    "data": {},
                    "process_id": process_id
                }

            results = {
                "unique_test_cases": [case.model_dump() for case in unique_test_cases.test_cases],
                "similar_test_cases": unique_test_cases.duplicates,
                "comparison_logs": unique_test_cases.comparison_logs,
            }

            # Mark process as completed
            running_processes[process_id]["status"] = "completed"
            running_processes[process_id]["end_time"] = datetime.now()

            return {
                "success": True,
                "message": f"Successfully processed {len(valid_data)} test cases and found {len(unique_test_cases.test_cases)} unique cases",
                "data": results,
                "process_id": process_id
            }

        except Exception as e:
            # Remove from tracking on error
            running_processes.pop(process_id, None)
            logger.error(f"Error running smart selection: {e}")
            return {
                "success": False,
                "message": f"Error running smart selection: {str(e)}",
                "data": {},
                "process_id": process_id
            }
        finally:
            # Clean up completed or errored processes after some time
            if process_id in running_processes:
                status = running_processes[process_id]["status"]
                if status in ["completed", "stopped", "error"]:
                    # Keep for a short time for status checking, then remove
                    pass

    async def run_parallel_smart_selection(self, selected_test_cases: List[Dict[str, Any]], custom_prompt: str = None, selected_model: str = "gemini-2.5-flash", api_key: str = None, process_id: str = None, grouping_strategy: str = "round_robin") -> Dict[str, Any]:
        """
        Paralel smart selection - sadece Gemini modelleri ile çalışır.
        Gemini Batch API kullanarak GERÇEK paralel işlem yapar.
        """
        # DEBUG: Log input
        logger.info("="*80)
        logger.info(f"🔍 PARALLEL SMART SELECTION INITIATED")
        logger.info(f"   Input test cases: {len(selected_test_cases)}")
        logger.info(f"   Model: {selected_model}")
        logger.info(f"   Mode: BATCH API (Parallel Processing)")
        logger.info(f"   This is NOT serial processing")
        logger.info("="*80)
        
        # Generate process ID if not provided
        if not process_id:
            process_id = str(uuid.uuid4())
        
        # Gemini model kontrolü
        if not any(gemini in selected_model.lower() for gemini in ["gemini"]):
            return {
                "success": False,
                "message": "Parallel optimization only works with Gemini models",
                "data": {},
                "process_id": process_id
            }
        
        # Parallel optimization available kontrolü
        if not PARALLEL_OPTIMIZATION_AVAILABLE:
            return {
                "success": False,
                "message": "Parallel optimization service is not available",
                "data": {},
                "process_id": process_id
            }
        
        # Track this process
        running_processes[process_id] = {
            "status": "running",
            "start_time": datetime.now(),
            "process_type": "parallel_smart_selection"
        }
        
        try:
            # Check if process should be stopped
            if process_id in running_processes and running_processes[process_id]["status"] == "stopped":
                logger.info(f"Parallel process {process_id} was stopped by user")
                return {
                    "success": False,
                    "message": "Process stopped by user",
                    "data": {},
                    "process_id": process_id
                }
            
            # Pydantic modeline dönüştür
            valid_data = []
            for item in selected_test_cases:
                try:
                    test_case = TestCase(
                        ScenarioID=item.get("ScenarioID", ""),
                        TestCaseID=item.get("TestCaseID", ""),
                        Title=item.get("Title", ""),
                        Description=item.get("Description"),
                        Objective=item.get("Objective")
                    )
                    valid_data.append(test_case)
                except Exception as e:
                    logger.warning(f"Skipping invalid test case: {item}. Error: {e}")
            
            logger.info(f"   Valid test cases after Pydantic validation: {len(valid_data)}")
            
            # Store original count BEFORE validation
            original_test_case_count = len(selected_test_cases)
            
            if not valid_data:
                # Remove from tracking
                running_processes.pop(process_id, None)
                return {
                    "success": False,
                    "message": "No valid test cases to process",
                    "data": {},
                    "process_id": process_id
                }
            
            # Minimum test case kontrolü (paralel optimization için)
            if len(valid_data) < 20:
                return {
                    "success": False,
                    "message": f"Parallel optimization requires at least 20 test cases (you have {len(valid_data)}). Use serial optimization instead.",
                    "data": {},
                    "process_id": process_id
                }
            
            # Check again before processing
            if process_id in running_processes and running_processes[process_id]["status"] == "stopped":
                logger.info(f"Parallel process {process_id} was stopped before processing")
                return {
                    "success": False,
                    "message": "Process stopped by user",
                    "data": {},
                    "process_id": process_id
                }
            
            # Parallel smart selection işlemini çalıştır
            logger.info(f"🚀 Starting Gemini Batch API parallel processing...")
            logger.info(f"   Valid test cases: {len(valid_data)}")
            logger.info(f"   Expected comparisons: {len(valid_data) * (len(valid_data) - 1) // 2:,}")
            
            test_case_list = TestCaseList(test_cases=valid_data)
            result_list = await parallel_smart_select(
                test_case_list,
                custom_prompt,
                selected_model,
                api_key,
                process_id,
                use_file_mode=True  # Use Batch API with adaptive batching
            )
            
            logger.info(f"✅ Gemini Batch API parallel processing completed successfully")
            
            # Extract unique test cases from result
            unique_test_cases = result_list
            
            # Check if process was stopped during execution
            if process_id in running_processes and running_processes[process_id]["status"] == "stopped":
                logger.info(f"Parallel process {process_id} was stopped during execution")
                return {
                    "success": False,
                    "message": "Process stopped by user",
                    "data": {},
                    "process_id": process_id
                }
            
            results = {
                "unique_test_cases": [case.model_dump() for case in unique_test_cases.test_cases],
                "similar_test_cases": unique_test_cases.duplicates,
                "comparison_logs": unique_test_cases.comparison_logs,
                "optimization_type": "parallel",
                "total_test_cases": original_test_case_count,  # Use original count from frontend
                "total_comparisons": unique_test_cases.comparison_logs[0].get("TotalComparisons", 0) if unique_test_cases.comparison_logs else 0  # Add comparison count
            }
            
            # Mark process as completed
            running_processes[process_id]["status"] = "completed"
            running_processes[process_id]["end_time"] = datetime.now()
            
            return {
                "success": True,
                "message": "Parallel smart selection completed successfully using Gemini Batch API",
                "data": results,
                "process_id": process_id
            }
        
        except Exception as e:
            # Remove from tracking on error
            running_processes.pop(process_id, None)
            logger.error(f"Error running parallel smart selection: {e}")
            return {
                "success": False,
                "message": f"Unexpected error in parallel optimization: {str(e)}",
                "data": {},
                "process_id": process_id,
                "error_type": "unexpected_error"
            }
        finally:
            # Clean up completed or errored processes after some time
            if process_id in running_processes:
                status = running_processes[process_id]["status"]
                if status in ["completed", "stopped", "error"]:
                    # Keep for a short time for status checking, then remove
                    pass

    async def run_bulk_smart_selection(self, selected_test_cases: List[Dict[str, Any]], custom_prompt: str = None, selected_model: str = "llama3.2:3b", api_key: str = None, process_id: str = None) -> Dict[str, Any]:
        """
        Seçilen test case'ler üzerinde bulk smart selection işlemini çalıştır.
        Tüm test case'leri tek bir LLM çağrısında karşılaştırır.
        """
        logger.info("🟢 RUN_BULK_SMART_SELECTION METHOD CALLED")
        logger.info(f"🟢 Input: {len(selected_test_cases)} test cases")
        logger.info(f"🟢 Model: {selected_model}")
        
        # Generate process ID if not provided
        if not process_id:
            process_id = str(uuid.uuid4())
            
        # Track this process
        running_processes[process_id] = {
            "status": "running",
            "start_time": datetime.now(),
            "process_type": "bulk_smart_selection"
        }
        
        try:
            # Check if process should be stopped
            if process_id in running_processes and running_processes[process_id]["status"] == "stopped":
                logger.info(f"Bulk process {process_id} was stopped by user")
                return {
                    "success": False,
                    "message": "Process stopped by user",
                    "data": {},
                    "process_id": process_id
                }
                
            # Pydantic modeline dönüştür
            valid_data = []
            for item in selected_test_cases:
                try:
                    test_case = TestCase(
                        ScenarioID=item.get("ScenarioID", ""),
                        TestCaseID=item.get("TestCaseID", ""),
                        Title=item.get("Title", ""),
                        Description=item.get("Description"),
                        Objective=item.get("Objective")
                    )
                    valid_data.append(test_case)
                except Exception as e:
                    logger.warning(f"Skipping invalid test case: {item}. Error: {e}")

            if not valid_data:
                # Remove from tracking
                running_processes.pop(process_id, None)
                return {
                    "success": False,
                    "message": "No valid test cases to process",
                    "data": {},
                    "process_id": process_id
                }

            # Check again before processing
            if process_id in running_processes and running_processes[process_id]["status"] == "stopped":
                logger.info(f"Bulk process {process_id} was stopped before processing")
                return {
                    "success": False,
                    "message": "Process stopped by user",
                    "data": {},
                    "process_id": process_id
                }

            # Bulk smart selection işlemini çalıştır
            test_case_list = TestCaseList(test_cases=valid_data)
            unique_test_cases = await bulk_smart_select(test_case_list, custom_prompt, selected_model, api_key)

            # Check if process was stopped during execution
            if process_id in running_processes and running_processes[process_id]["status"] == "stopped":
                logger.info(f"Bulk process {process_id} was stopped during execution")
                return {
                    "success": False,
                    "message": "Process stopped by user",
                    "data": {},
                    "process_id": process_id
                }

            results = {
                "unique_test_cases": [case.model_dump() for case in unique_test_cases.test_cases],
                "similar_test_cases": unique_test_cases.duplicates,
                "comparison_logs": unique_test_cases.comparison_logs,
                "optimization_type": "bulk"
            }

            # Mark process as completed
            running_processes[process_id]["status"] = "completed"
            running_processes[process_id]["end_time"] = datetime.now()

            return {
                "success": True,
                "message": "Bulk smart selection completed successfully",
                "data": results,
                "process_id": process_id
            }

        except ValueError as ve:
            # Handle specific bulk optimization errors (JSON parsing, empty response, etc.)
            running_processes.pop(process_id, None)
            logger.error(f"Bulk optimization validation error: {ve}")
            return {
                "success": False,
                "message": f"Bulk Optimization Error: {str(ve)}",
                "data": {},
                "process_id": process_id,
                "error_type": "bulk_validation_error"
            }
        except RuntimeError as re:
            # Handle bulk optimization runtime errors
            running_processes.pop(process_id, None)
            logger.error(f"Bulk optimization runtime error: {re}")
            return {
                "success": False,
                "message": f"Bulk Optimization Runtime Error: {str(re)}",
                "data": {},
                "process_id": process_id,
                "error_type": "bulk_runtime_error"
            }
        except Exception as e:
            # Remove from tracking on error
            running_processes.pop(process_id, None)
            logger.error(f"Error running bulk smart selection: {e}")
            return {
                "success": False,
                "message": f"Unexpected error in bulk optimization: {str(e)}",
                "data": {},
                "process_id": process_id,
                "error_type": "unexpected_error"
            }
        finally:
            # Clean up completed or errored processes after some time
            if process_id in running_processes:
                status = running_processes[process_id]["status"]
                if status in ["completed", "stopped", "error"]:
                    # Keep for a short time for status checking, then remove
                    pass

    def save_optimization_results(self, process_title: str, results: Dict[str, Any], selected_model: str = None) -> bool:
        """
        Optimization sonuçlarını MongoDB'ye kaydet.
        """
        try:
            # Optimization sonuçlarını ayrı bir koleksiyonda sakla
            optimization_collection = self.db["test_case_optimizations"]
            
            document = {
                "process_title": process_title,
                "optimization_results": results,
                "selected_model": selected_model,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Upsert operation - eğer varsa güncelle, yoksa yeni oluştur
            optimization_collection.update_one(
                {"process_title": process_title},
                {"$set": document},
                upsert=True
            )
            
            return True
        except Exception as e:
            logger.error(f"Error saving optimization results: {e}")
            return False

    def get_optimization_results(self, process_title: str) -> Optional[Dict[str, Any]]:
        """
        Belirli bir process_title için kaydedilmiş optimization sonuçlarını getir.
        """
        try:
            optimization_collection = self.db["test_case_optimizations"]
            result = optimization_collection.find_one({"process_title": process_title})
            
            if result:
                return result.get("optimization_results")
            return None
        except Exception as e:
            logger.error(f"Error fetching optimization results: {e}")
            return None
