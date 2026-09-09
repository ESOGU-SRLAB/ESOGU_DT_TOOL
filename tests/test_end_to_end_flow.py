#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-End Test Flow
====================
Tests the complete STLC-Manager workflow:
1. Test Scenario Generation (LLaMa 3.2:3B)
2. Test Case Optimization
3. Test Code Generation
4. Parallel Docker Execution (NEW!)

Usage:
    python test_end_to_end_flow.py
"""

import sys
import io

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
import time
import json
import os
from pathlib import Path
from typing import Dict, Optional
from pymongo import MongoClient
from datetime import datetime
import uuid

# Configuration
BASE_URL = "http://localhost:8000"
PROCESS_TITLE = "E2E Test - Sample Source"
MODEL = "llama3.2:3b"
MAX_PARALLEL = 5

# Repository-owned fixture; override without introducing a local repository dependency.
SOURCE_FILE_PATH = os.getenv(
    "STLC_E2E_SOURCE_FILE",
    str(Path(__file__).parent.parent / "test_inputs" / "ProductDetection.cpp"),
)

# MongoDB Configuration
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "stlc_manager"

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text: str):
    """Print section header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def check_services():
    """Check if all required services are running"""
    print_header("STEP 0: Service Health Check")
    
    services = {
        "Backend API": f"{BASE_URL}/docs",
        "MongoDB": None,  # Checked via backend
        "Docker": None,   # Checked via backend
        "LM Studio": "http://localhost:1234/v1/models"
    }
    
    all_ok = True
    
    # Check Backend
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print_success("Backend API is running")
        else:
            print_error("Backend API returned non-200 status")
            all_ok = False
    except Exception as e:
        print_error(f"Backend API is not accessible: {e}")
        all_ok = False
    
    # Check LM Studio
    try:
        response = requests.get("http://localhost:1234/v1/models", timeout=5)
        if response.status_code == 200:
            models = response.json().get("data", [])
            print_success(f"LM Studio is running ({len(models)} models loaded)")
            for model in models:
                print_info(f"  - {model.get('id', 'unknown')}")
        else:
            print_error("LM Studio is not responding correctly")
            all_ok = False
    except Exception as e:
        print_error(f"LM Studio is not accessible: {e}")
        print_warning("Please start LM Studio and load llama-3.2-3b-instruct model")
        all_ok = False
    
    # Check Docker
    try:
        response = requests.get(f"{BASE_URL}/api/docker-execution/health", timeout=5)
        if response.status_code == 200:
            print_success("Docker is running")
        else:
            print_warning("Docker health check returned non-200 status")
    except Exception as e:
        print_warning(f"Docker health check failed: {e}")
    
    return all_ok

def create_dummy_environment_setup() -> str:
    """Create a dummy environment setup in MongoDB and return session_id"""
    print_header("Setup: Creating Environment Setup")
    
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db["session_history"]
        
        # Check if already exists
        existing = collection.find_one({"session_id": "e2e-test-env"})
        if existing:
            print_success("Environment setup already exists")
            client.close()
            return "e2e-test-env"
        
        # Create environment setup document in session_history collection
        # Following the structure expected by backend: processes.environment_setup
        env_setup = {
            "session_id": "e2e-test-env",
            "process_title": "E2E Test Environment Setup",
            "created_at": datetime.now(),
            "processes": {
                "environment_setup": {
                    "environment_name": "E2E Test Environment",
                    "timestamp": datetime.now().isoformat(),
                    "status": "success",
                    "output": {
                        "language": "python",
                        "version": "3.11",
                        "framework": "pytest",
                        "dependencies": ["pytest", "pytest-asyncio"],
                        "summary": "E2E test environment for robot2_ur.py testing"
                    }
                }
            }
        }
        
        collection.insert_one(env_setup)
        client.close()
        
        print_success("Environment setup created successfully")
        return "e2e-test-env"
        
    except Exception as e:
        print_error(f"Error creating environment setup: {e}")
        return None

def get_test_file_content() -> str:
    """Get test file content from robot2_ur.py"""
    test_file = Path(SOURCE_FILE_PATH)
    
    if not test_file.exists():
        print_error(f"Source file not found: {test_file}")
        return None
    
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print_success(f"Loaded source file: {test_file.name} ({len(content)} characters)")
    return content

def step1_test_scenario_generation(file_content: str) -> Optional[str]:
    """Step 1: Generate test scenarios using LLaMa 3.2:3B"""
    print_header("STEP 1: Test Scenario Generation (LLaMa 3.2:3B)")
    
    # Prepare request data
    data = {
        "fileContents": [
            {
                "name": "robot2_ur.py",
                "content": file_content
            }
        ],
        "model": MODEL,
        "test_category": "unit",
        "test_type": "functional",
        "process_title": PROCESS_TITLE
    }
    
    print_info(f"Generating custom prompt for process: {PROCESS_TITLE}")
    print_info(f"Using model: {MODEL}")
    
    # Generate custom prompt
    try:
        response = requests.post(
            f"{BASE_URL}/api/processes/test-scenario-generation/generate-prompt",
            json=data,
            timeout=120
        )
        
        if response.status_code != 200:
            print_error(f"Failed to generate prompt: {response.text}")
            return None
        
        result = response.json()
        custom_prompt = result.get("generated_custom_prompt", "")
        session_id = result.get("session_id", "")
        
        print_success("Custom prompt generated")
        print_info(f"Session ID: {session_id}")
        print_info(f"Prompt length: {len(custom_prompt)} characters")
        
    except Exception as e:
        print_error(f"Error generating prompt: {e}")
        return None
    
    # Run test scenario generation
    print_info("Running test scenario generation...")
    
    try:
        # Prepare form data
        files = {
            'files': ('ex_joint_goal.py', file_content, 'text/x-python')
        }
        
        form_data = {
            'model': MODEL,
            'final_prompt': custom_prompt,
            'test_category': 'functional',
            'test_type': 'integration',
            'session_id': session_id,
            'process_title': PROCESS_TITLE
        }
        
        response = requests.post(
            f"{BASE_URL}/api/processes/test-scenario-generation/run",
            files=files,
            data=form_data,
            timeout=300  # 5 minutes timeout
        )
        
        if response.status_code != 200:
            print_error(f"Failed to run test scenario generation: {response.text}")
            return None
        
        result = response.json()
        
        if result.get("status") == "success":
            print_success("Test scenarios generated successfully!")
            
            # Display summary - API response has test_scenarios directly
            test_scenarios_obj = result.get("test_scenarios", {})
            scenarios = test_scenarios_obj.get("TestScenarios", [])
            print_info(f"Generated {len(scenarios)} test scenarios")
            
            # Show first few scenarios
            for i, scenario in enumerate(scenarios[:3], 1):
                print_info(f"  {i}. {scenario.get('Title', 'Untitled')}")
            
            return session_id
        else:
            print_error(f"Test scenario generation failed: {result.get('message', 'Unknown error')}")
            return None
            
    except Exception as e:
        print_error(f"Error running test scenario generation: {e}")
        return None

def step2_test_case_generation(session_id: str) -> bool:
    """Step 2: Generate test cases from test scenarios"""
    print_header("STEP 2: Test Case Generation")
    
    print_info(f"Generating test cases for process: {PROCESS_TITLE}")
    
    try:
        # First, fetch test scenarios from the session
        # We need to get them from MongoDB via session ID
        # For now, we'll use predefined test scenarios from the response
        # In production, this would query the session data
        
        # For E2E test, we'll generate test cases for all scenarios
        # We need to send selected_scenarios to the endpoint
        data = {
            "selected_scenarios": [
                {"scenario_id": "TS_001", "title": "Test Scenario 1"},
                {"scenario_id": "TS_002", "title": "Test Scenario 2"},
                {"scenario_id": "TS_003", "title": "Test Scenario 3"}
            ],
            "process_prompt": "Generate comprehensive test cases for the supplied source",
            "selected_files": [],
            "ai_model": MODEL,
            "session_id": session_id,
            "selected_process_title": PROCESS_TITLE
        }
        
        response = requests.post(
            f"{BASE_URL}/api/processes/test-scenario-generation/generate-test-cases",
            json=data,
            timeout=300
        )
        
        if response.status_code != 200:
            print_error(f"Failed to generate test cases: {response.text}")
            return False
        
        result = response.json()
        
        if result.get("status") == "success":
            print_success("Test cases generated successfully!")
            
            # Display summary - API returns summary object
            summary = result.get("summary", {})
            total_test_cases = summary.get("total_test_cases", 0)
            scenarios_processed = summary.get("scenarios_processed", 0)
            successful_scenarios = summary.get("successful_scenarios", 0)
            
            print_info(f"Total test cases generated: {total_test_cases}")
            print_info(f"Scenarios processed: {scenarios_processed}")
            print_info(f"Successful scenarios: {successful_scenarios}")
            
            return True
        else:
            print_error(f"Test case generation failed: {result.get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print_error(f"Error generating test cases: {e}")
        return False

def step3_test_code_generation(process_title: str, source_file_path: str) -> Optional[list]:
    """Step 3: Generate REAL test codes using source file"""
    print_header("STEP 3: Test Code Generation (REAL)")
    
    print_info(f"Generating test codes from source file: {source_file_path}")
    print_info(f"Process: {process_title}")
    
    # Read source file
    if not os.path.exists(source_file_path):
        print_error(f"Source file not found: {source_file_path}")
        return None
    
    try:
        # Prepare multipart form data
        with open(source_file_path, 'rb') as f:
            files = {
                'files': (os.path.basename(source_file_path), f, 'text/x-python')
            }
            
            # Prepare form data with all required fields
            data = {
                'process_title': process_title,
                'environment_session_id': 'e2e-test-env',  # Dummy environment ID for E2E test
                'environment_name': 'E2E Test Environment',  # Required field
                'model': MODEL,  # llama3.2:3b
                'output_format': 'JSON',
                'session_id': f"e2e-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            }
            
            print_info(f"Using model: {MODEL}")
            print_info("Calling test code generation API...")
            response = requests.post(
                f"{BASE_URL}/api/processes/test-code-generation/generate",
                files=files,
                data=data,
                timeout=180  # 3 minutes timeout for code generation
            )
        
        if response.status_code != 200:
            print_error(f"Test code generation failed: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None
        
        result = response.json()
        
        print_info(f"API Response: {result}")  # Debug: Show full response
        
        if result.get("success"):
            print_success("Test codes generated successfully!")
            
            # Get test IDs from the response
            generated_tests = result.get("generated_tests", [])
            
            if not generated_tests:
                print_error("No tests were generated")
                return None
            
            test_ids = [test["test_case_id"] for test in generated_tests if test.get("status") == "success"]
            
            print_info(f"Total test codes generated: {len(test_ids)}")
            for i, test in enumerate(generated_tests[:5], 1):  # Show first 5
                print_info(f"  {i}. {test.get('title', 'N/A')} (ID: {test['test_case_id']})")
            
            if len(generated_tests) > 5:
                print_info(f"  ... and {len(generated_tests) - 5} more tests")
            
            print_success(f"Test IDs ready for Docker execution")
            return test_ids
        else:
            print_error(f"Test code generation failed!")
            print_error(f"Error message: {result.get('message', 'No message')}")
            print_error(f"Error detail: {result.get('detail', 'No detail')}")
            print_error(f"Full response: {result}")
            return None
            
    except Exception as e:
        print_error(f"Error generating test codes: {e}")
        import traceback
        traceback.print_exc()
        return None
    
def save_test_codes_to_mongodb(test_codes: list) -> list:
    """Save test codes to MongoDB and return test IDs"""
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db["session_history"]
        
        # Create session document
        session_id = f"e2e-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Prepare generated_tests in the format expected by parallel_docker_executor
        generated_tests = []
        test_ids = []
        
        for i, test_code in enumerate(test_codes, 1):
            test_id = f"test-{uuid.uuid4().hex[:8]}"
            test_ids.append(test_id)
            
            generated_tests.append({
                "test_id": test_id,
                "test_case_id": test_code.get("test_case_id", f"TC_{i}"),
                "test_name": test_code.get("test_name", f"test_{i}.py"),
                "test_code": test_code.get("code", ""),
                "source_code": "",
                "status": "success"
            })
        
        # Create document structure matching parallel_docker_executor expectations
        document = {
            "session_id": session_id,
            "process_title": PROCESS_TITLE,
            "created_at": datetime.now(),
            "processes": {
                "test_code_generation": {
                    "process_name": PROCESS_TITLE,
                    "status": "success",
                    "output": {
                        "generated_tests": generated_tests,
                        "total_test_cases": len(test_codes),
                        "generated_count": len(test_codes),
                        "failed_count": 0
                    },
                    "timestamp": datetime.now().isoformat()
                }
            }
        }
        
        # Insert document
        collection.insert_one(document)
        client.close()
        
        return test_ids
        
    except Exception as e:
        print_error(f"Failed to save test codes to MongoDB: {e}")
        return []

def step4_parallel_docker_execution(test_ids: list) -> bool:
    """Step 4: Execute tests in parallel Docker containers"""
    try:
        print_header("STEP 4: ⚡ Parallel Docker Execution (NEW!)")
        
        print("DEBUG: Step 4 started!", flush=True)
        print(f"DEBUG: Received test_ids = {test_ids}", flush=True)
        print(f"DEBUG: type = {type(test_ids)}, len = {len(test_ids)}", flush=True)
        
        print_info(f"📊 Received {len(test_ids)} test IDs")
        print_info(f"Test IDs: {test_ids[:5] if len(test_ids) > 5 else test_ids}")  # Debug
        
        if not test_ids:
            print_error("No test IDs provided to Step 4")
            return False
        
        print("DEBUG: About to print execution info", flush=True)
        print_info(f"Executing {len(test_ids)} tests in parallel Docker containers")
        print_info(f"Max parallel containers: {MAX_PARALLEL}")
        
        # Prepare execution request
        data = {
            "process_name": "E2E Test Environment",  # MUST match environment_name from Step 3
            "test_ids": test_ids,
            "language": "python",
            "max_parallel": MAX_PARALLEL,
            "timeout": 300,
            "additional_packages": ["pytest", "pytest-asyncio"]  # Added pytest for test execution
        }
        
        print_info(f"Request data: {json.dumps(data, indent=2)}")
        
        response = requests.post(
            f"{BASE_URL}/api/docker-execution/parallel/execute",
            json=data,
            timeout=30
        )
        
        print_info(f"Response status: {response.status_code}")
        print_info(f"Response body: {response.text}")
        
        if response.status_code != 200:
            print_error(f"Failed to start parallel execution: {response.text}")
            return False
        
        result = response.json()
        batch_session_id = result.get("batch_session_id")
        
        print_success(f"Parallel execution started! Batch ID: {batch_session_id}")
        print_info("Monitoring progress (real-time)...")
        
    except Exception as e:
        print_error(f"Error starting parallel execution: {e}")
        return False
    
    # Monitor progress
    try:
        completed = False
        last_status = None
        
        while not completed:
            time.sleep(2)  # Poll every 2 seconds
            
            response = requests.get(
                f"{BASE_URL}/api/docker-execution/parallel/progress/{batch_session_id}",
                timeout=10
            )
            
            if response.status_code != 200:
                print_error("Failed to fetch progress")
                break
            
            progress = response.json()
            
            # Display progress
            status = progress.get("status")
            stats = progress.get("statistics", {})
            
            if status != last_status:
                print_info(f"Status: {status}")
                last_status = status
            
            total = stats.get("total", 0)
            completed_count = stats.get("completed", 0)
            passed = stats.get("passed", 0)
            failed = stats.get("failed", 0)
            running = stats.get("running", 0)
            
            # Progress bar
            if total > 0:
                progress_pct = (completed_count / total) * 100
                bar_length = 40
                filled = int(bar_length * completed_count / total)
                bar = '█' * filled + '░' * (bar_length - filled)
                
                print(f"\r  Progress: [{bar}] {progress_pct:.1f}% | "
                      f"Running: {running} | Passed: {passed} | Failed: {failed} | "
                      f"Total: {completed_count}/{total}", end='', flush=True)
            
            if status in ["completed", "cancelled", "failed"]:
                completed = True
                print()  # New line after progress bar
        
        # Get final results
        response = requests.get(
            f"{BASE_URL}/api/docker-execution/parallel/results/{batch_session_id}",
            timeout=10
        )
        
        if response.status_code != 200:
            print_error("Failed to fetch final results")
            return False
        
        results = response.json()
        
        # Display summary
        print_success("Parallel execution completed!")
        
        stats = results.get("statistics", {})
        print_info(f"Total tests: {stats.get('total', 0)}")
        print_info(f"Passed: {stats.get('passed', 0)} ✅")
        print_info(f"Failed: {stats.get('failed', 0)} ❌")
        print_info(f"Success rate: {stats.get('success_rate', 0):.1f}%")
        print_info(f"Total execution time: {stats.get('total_execution_time', 0):.2f}s")
        
        if stats.get('average_execution_time', 0) > 0:
            speedup = stats.get('total', 0) * stats.get('average_execution_time', 0) / stats.get('total_execution_time', 1)
            print_info(f"Speedup (vs sequential): {speedup:.2f}x 🚀")
        
        # Show individual results
        test_results = results.get("results", [])
        print("\n" + "─" * 80)
        print("Individual Test Results:")
        print("─" * 80)
        
        for i, test in enumerate(test_results, 1):
            status_icon = "✅" if test.get("status") == "COMPLETED" else "❌"
            execution_time = test.get("execution_time", 0)
            print(f"{i}. {status_icon} {test.get('test_name', 'unknown')} - {execution_time:.2f}s")
            
            if test.get("error"):
                print(f"   Error: {test.get('error')}")
        
        return stats.get('failed', 0) == 0
        
    except Exception as e:
        print_error(f"Error monitoring execution: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    except Exception as outer_e:
        print_error(f"🚨 CRITICAL ERROR in step4: {outer_e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test flow"""
    print_header("🧪 End-to-End Test Flow")
    print_info("Testing complete STLC-Manager workflow:")
    print_info("  1. Test Scenario Generation (LLaMa 3.2:3B)")
    print_info("  2. Test Case Optimization")
    print_info("  3. Test Code Generation")
    print_info("  4. ⚡ Parallel Docker Execution")
    
    start_time = time.time()
    
    # Step 0: Check services
    if not check_services():
        print_error("Service check failed. Please ensure all services are running.")
        print_warning("Required services:")
        print_warning("  - Backend API (http://localhost:8000)")
        print_warning("  - LM Studio (http://localhost:1234) with llama-3.2-3b-instruct")
        print_warning("  - Docker Desktop")
        return False
    
    # Step 0.5: Create environment setup
    if not create_dummy_environment_setup():
        print_error("Failed to create environment setup")
        return False
    
    # Get test file
    file_content = get_test_file_content()
    if not file_content:
        return False
    
    # Step 1: Test Scenario Generation
    session_id = step1_test_scenario_generation(file_content)
    if not session_id:
        print_error("Test scenario generation failed")
        return False
    
    # Step 2: Test Case Generation
    if not step2_test_case_generation(session_id):
        print_error("Test case generation failed")
        return False
    
    # Step 3: Test Code Generation (REAL - using API)
    test_ids = step3_test_code_generation(PROCESS_TITLE, SOURCE_FILE_PATH)
    print_info(f"🔍 DEBUG: step3 returned test_ids = {test_ids}")  # Debug
    print_info(f"🔍 DEBUG: test_ids type = {type(test_ids)}, len = {len(test_ids) if test_ids else 'None'}")  # Debug
    
    if not test_ids:
        print_error("Test code generation failed")
        return False
    
    # Step 4: Parallel Docker Execution
    if not step4_parallel_docker_execution(test_ids):
        print_warning("Some tests failed, but parallel execution completed")
    
    # Final summary
    total_time = time.time() - start_time
    
    print_header("🎉 End-to-End Test Complete!")
    print_success(f"Total execution time: {total_time:.2f}s")
    print_info("All workflow steps completed successfully!")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print_warning("\n\nTest interrupted by user")
        exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
