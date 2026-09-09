from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from core.database import get_db
from utils.model_client import LLMClient
from datetime import datetime
import json
import uuid
import logging
import asyncio
import random

logger = logging.getLogger(__name__)

# Global dictionary to track running processes
running_processes = {}

# Retry configuration
MAX_RETRIES = 3
BASE_DELAY = 1.0  # seconds
MAX_DELAY = 60.0  # seconds

async def retry_with_exponential_backoff(func, *args, max_retries=MAX_RETRIES, **kwargs):
    """
    Exponential backoff ile retry mekanizması
    """
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_str = str(e)
            
            # Son deneme ise hata fırlat
            if attempt == max_retries:
                logger.error(f"Max retries ({max_retries}) reached for function {func.__name__}")
                raise e
            
            # Retry yapılabilir hata mı kontrol et
            is_retryable = (
                "503" in error_str or 
                "Service Unavailable" in error_str or
                "429" in error_str or 
                "RESOURCE_EXHAUSTED" in error_str or
                "quota" in error_str.lower() or
                "timeout" in error_str.lower() or
                "connection" in error_str.lower() or
                "network" in error_str.lower()
            )
            
            if not is_retryable:
                logger.warning(f"Non-retryable error in {func.__name__}: {error_str}")
                raise e
            
            # Exponential backoff hesapla
            delay = min(BASE_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_DELAY)
            logger.warning(f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {error_str}")
            logger.info(f"Retrying in {delay:.2f} seconds...")
            
            await asyncio.sleep(delay)
    
    # Bu noktaya gelmemeli
    raise Exception(f"Unexpected error in retry mechanism for {func.__name__}")

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
        # LM Studio API'sine LLMClient ile istek gönder
        llm_client = LLMClient(model_name=selected_model, api_key=api_key)
        # Set the original key to support model mapping
        llm_client.original_key = selected_model
        
        # LLMClient'ı kullanarak yanıt al
        response = await llm_client.generate_response(
            prompt=prompt_text.strip(),
            temperature=0.1,  # Consistency için düşük temperature
            max_tokens=1000
        )
        
        if not response:
            logger.error("Empty response from LLM")
            return False
        
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
                logger.error(f"LM Studio response is not valid JSON and doesn't contain expected format: {cleaned_response}")
                return False
            
    except Exception as e:
        logger.error(f"Error calling LM Studio API via LLMClient: {e}")
        return False

async def smart_select(test_case_list: TestCaseList, custom_prompt: str = None, selected_model: str = "llama3.2:3b", api_key: str = None, process_id: str = None) -> TestCaseList:
    """
    Bu fonksiyon, test_cases listesindeki benzer (duplicate) test case'leri 
    LLM tabanlı karşılaştırma ile ayıklar, unique bir liste döndürür.
    """
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
                # Retry mekanizması ile LLM çağrısı
                comparison_result = await retry_with_exponential_backoff(
                    _query_llm_similarity, 
                    case, unique_case, custom_prompt, selected_model, api_key
                )
            except Exception as e:
                logger.warning(f"LLM comparison failed after all retries: {e}")
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
            prompt_text = f"""{custom_prompt}

Below are the test cases to analyze in JSON array format:

{json.dumps(test_cases_data, indent=2, ensure_ascii=False)}

Please analyze all test cases and return a JSON response with unique test cases and duplicates."""
        else:
            prompt_text = f"""
You are an expert test case analyst. Your task is to analyze ALL provided test cases in a single operation and identify duplicate/similar test cases efficiently.

ANALYSIS CRITERIA:
1. Test cases are considered DUPLICATES if they have:
   - Same or substantially similar Title (case-insensitive)
   - AND very similar Description and/or Objective
   - AND serve essentially the same testing purpose
2. Priority order for comparison: Description > Objective > Title
3. Consider contextual similarity, not just exact text matches

OPTIMIZATION APPROACH:
- Analyze the complete set of test cases holistically
- Group similar test cases and select the best representative for each group
- Preserve unique test cases that serve distinct testing purposes
- Ensure comprehensive coverage while eliminating redundancy

Below are the test cases in JSON array format:

{json.dumps(test_cases_data, indent=2, ensure_ascii=False)}

Return your response **only** in valid JSON with the following format:

{{
  "unique_indices": [0, 2, 5, ...],
  "duplicate_groups": [
    {{
      "representative_index": 0,
      "duplicate_indices": [3, 7, 12]
    }},
    {{
      "representative_index": 2,
      "duplicate_indices": [8, 15]
    }}
  ]
}}

Where:
- unique_indices: Array of indices representing unique test cases (including representatives from duplicate groups)
- duplicate_groups: Array of groups where each group has a representative and its duplicates
- representative_index: The index of the test case chosen as the representative for a duplicate group
- duplicate_indices: Array of indices that are duplicates of the representative

IMPORTANT:
- Return ONLY the raw JSON object, no markdown formatting
- Do not use ```json``` or ``` code blocks
- Do not provide any additional text outside the JSON object
- Each test case should appear in either unique_indices or as part of a duplicate group, but not both
- Representatives should also be included in unique_indices
- Ensure all test case indices are accounted for in the response
"""

        # Make single LLM call
        llm_client = LLMClient(model_name=selected_model, api_key=api_key)
        llm_client.original_key = selected_model
        
        response = await llm_client.generate_response(
            prompt=prompt_text.strip(),
            temperature=0.1,
            max_tokens=6000  # Increased for bulk response to handle larger datasets
        )
        
        if not response:
            logger.error("Empty response from LLM in bulk processing")
            # Don't fallback - raise specific error for bulk optimization
            raise ValueError("Bulk optimization failed: LLM returned empty response")
        
        # Clean LLM response from markdown code blocks
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]  # Remove ```json
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]   # Remove ```
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]  # Remove ending ```
        cleaned_response = cleaned_response.strip()
        
        logger.info(f"Original LLM response length: {len(response)}")
        logger.info(f"Cleaned response length: {len(cleaned_response)}")
        logger.info(f"Original response: {response}")
        logger.info(f"Cleaned response: {cleaned_response}")
        
        try:
            # Parse the cleaned bulk response
            parsed_content = json.loads(cleaned_response)
            unique_indices = parsed_content.get("unique_indices", [])
            duplicate_groups = parsed_content.get("duplicate_groups", [])
            
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
                rep_idx = group.get("representative_index")
                dup_indices = group.get("duplicate_indices", [])
                
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

    async def run_bulk_smart_selection(self, selected_test_cases: List[Dict[str, Any]], custom_prompt: str = None, selected_model: str = "llama3.2:3b", api_key: str = None, process_id: str = None) -> Dict[str, Any]:
        """
        Seçilen test case'ler üzerinde bulk smart selection işlemini çalıştır.
        Tüm test case'leri tek bir LLM çağrısında karşılaştırır.
        """
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
