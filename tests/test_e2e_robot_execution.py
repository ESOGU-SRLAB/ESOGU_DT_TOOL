#!/usr/bin/env python3
"""
End-to-End Test: Robot ROS 2 Test Execution Workflow
Tests the legacy robot workflow with a repository-owned source fixture.
Hybrid execution: Headless batch + 1 Gazebo GUI visualization

Steps:
1. Environment Setup (source code upload)
2. Test Scenario Generation
3. Test Case Generation
4. Test Code Generation
5. Robot Test Execution (Headless + GUI)
"""

import requests
import time
import json
import os
from pathlib import Path
from typing import Dict, Any, List

# Configuration
BASE_URL = "http://localhost:8000"
PROCESS_TITLE = "E2E Robot Test - UR10e Joint Control"
MODEL = "llama-3.2-3b-instruct"
SOURCE_FILE_PATH = Path(os.getenv(
    "STLC_E2E_SOURCE_FILE",
    str(Path(__file__).parent.parent / "test_inputs" / "ProductDetection.cpp"),
))

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_step(step_num: int, title: str):
    """Print step header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}STEP {step_num}: {title}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.ENDC}\n")


def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {message}{Colors.ENDC}")


def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {message}{Colors.ENDC}")


def print_info(message: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.ENDC}")


def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.ENDC}")


def step0_health_checks():
    """Step 0: Health checks"""
    print_step(0, "Health Checks")
    
    services = {
        "Backend": f"{BASE_URL}/",
        "Robot Executor": f"{BASE_URL}/api/robot-execution/health"
    }
    
    all_ok = True
    for service_name, url in services.items():
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print_success(f"{service_name} is healthy")
            else:
                print_error(f"{service_name} returned status {response.status_code}")
                all_ok = False
        except Exception as e:
            print_error(f"{service_name} is not accessible: {e}")
            all_ok = False
    
    if not all_ok:
        print_error("Some services are not available. Please start all required services.")
        exit(1)
    
    print_success("All health checks passed!")
    return True


def step1_environment_setup() -> Dict[str, Any]:
    """Step 1: Environment Setup - Upload source code"""
    print_step(1, "Environment Setup (Source Code Upload)")
    
    # Check if source file exists
    if not SOURCE_FILE_PATH.exists():
        print_error(f"Source file not found: {SOURCE_FILE_PATH}")
        exit(1)
    
    print_info(f"Source file: {SOURCE_FILE_PATH}")
    
    # Read source code
    with open(SOURCE_FILE_PATH, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    print_info(f"Source code length: {len(source_code)} characters")
    
    # Upload to environment setup
    url = f"{BASE_URL}/api/processes/environment-setup/generate"
    
    payload = {
        "source_code": source_code,
        "process_title": PROCESS_TITLE,
        "model_identifier": MODEL,
        "programming_language": "python",
        "testing_framework": "pytest",
        "additional_context": "ROS 2 Humble robot arm control with MoveIt2 and Gazebo simulation"
    }
    
    print_info("Uploading source code...")
    response = requests.post(url, json=payload)
    
    if response.status_code != 200:
        print_error(f"Environment setup failed: {response.text}")
        exit(1)
    
    result = response.json()
    print_success("Environment setup completed!")
    print_info(f"Session ID: {result.get('session_id', 'N/A')}")
    
    return result


def step2_test_scenario_generation() -> Dict[str, Any]:
    """Step 2: Test Scenario Generation"""
    print_step(2, "Test Scenario Generation")
    
    url = f"{BASE_URL}/api/processes/test-scenario-generation/generate"
    
    payload = {
        "process_title": PROCESS_TITLE,
        "num_scenarios": 5,
        "model_identifier": MODEL
    }
    
    print_info(f"Generating {payload['num_scenarios']} test scenarios with {MODEL}...")
    response = requests.post(url, json=payload)
    
    if response.status_code != 200:
        print_error(f"Test scenario generation failed: {response.text}")
        exit(1)
    
    result = response.json()
    
    scenarios = result.get("scenarios", [])
    print_success(f"Generated {len(scenarios)} test scenarios!")
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"  {i}. {scenario.get('scenario_name', 'N/A')}")
    
    return result


def step3_test_case_generation() -> Dict[str, Any]:
    """Step 3: Test Case Generation"""
    print_step(3, "Test Case Generation")
    
    url = f"{BASE_URL}/api/processes/test-case-optimization/generate-test-cases"
    
    payload = {
        "process_title": PROCESS_TITLE,
        "model_identifier": MODEL
    }
    
    print_info("Generating test cases from scenarios...")
    response = requests.post(url, json=payload)
    
    if response.status_code != 200:
        print_error(f"Test case generation failed: {response.text}")
        exit(1)
    
    result = response.json()
    
    total_cases = result.get("total_cases_count", 0)
    print_success(f"Generated {total_cases} test cases!")
    
    return result


def step4_test_code_generation() -> Dict[str, Any]:
    """Step 4: Test Code Generation"""
    print_step(4, "Test Code Generation")
    
    # First, get the uploaded source code
    if not SOURCE_FILE_PATH.exists():
        print_error(f"Source file not found: {SOURCE_FILE_PATH}")
        exit(1)
    
    with open(SOURCE_FILE_PATH, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    url = f"{BASE_URL}/api/processes/test-code-generation/generate"
    
    payload = {
        "process_title": PROCESS_TITLE,
        "source_code": source_code,
        "model_identifier": MODEL,
        "language": "python",
        "testing_framework": "pytest"
    }
    
    print_info("Generating test codes from test cases...")
    response = requests.post(url, json=payload)
    
    if response.status_code != 200:
        print_error(f"Test code generation failed: {response.text}")
        exit(1)
    
    result = response.json()
    
    generated_tests = result.get("generated_tests", [])
    generated_count = result.get("generated_count", 0)
    
    print_success(f"Generated {generated_count} test codes!")
    
    # Extract test IDs
    test_ids = []
    for test in generated_tests:
        if test.get("status") == "success":
            test_id = test.get("test_case_id")
            if test_id:
                test_ids.append(test_id)
    
    print_info(f"Valid test IDs: {len(test_ids)}")
    result["test_ids"] = test_ids
    
    return result


def step5_robot_test_execution(test_ids: List[str]) -> Dict[str, Any]:
    """Step 5: Robot Test Execution (Headless + GUI)"""
    print_step(5, "Robot Test Execution (Hybrid: Headless + GUI)")
    
    if not test_ids:
        print_error("No test IDs available for execution")
        exit(1)
    
    print_info(f"Total tests: {len(test_ids)}")
    
    # Select first test for GUI visualization
    visual_test_id = test_ids[0] if test_ids else None
    print_info(f"Visual test (Gazebo): {visual_test_id}")
    print_info(f"Headless tests: {len(test_ids) - (1 if visual_test_id else 0)}")
    
    # Start batch execution
    url = f"{BASE_URL}/api/robot-execution/execute-batch"
    
    payload = {
        "process_name": PROCESS_TITLE,
        "test_ids": test_ids,
        "max_parallel": 5,
        "timeout_per_test": 300,
        "visual_test_id": visual_test_id,
        "enable_gazebo_recording": True,
        "docker_image": "stlc-robot-ros2:latest"
    }
    
    print_info("Starting robot test execution...")
    response = requests.post(url, json=payload)
    
    if response.status_code != 200:
        print_error(f"Robot test execution failed: {response.text}")
        exit(1)
    
    result = response.json()
    session_id = result["session_id"]
    
    print_success(f"Execution initiated! Session: {session_id}")
    print_info(f"Estimated duration: {result.get('estimated_duration', 0):.1f} seconds")
    
    # Poll for progress
    print_info("\nMonitoring execution progress...")
    
    progress_url = f"{BASE_URL}/api/robot-execution/progress/{session_id}"
    
    last_completed = 0
    while True:
        time.sleep(3)  # Poll every 3 seconds
        
        try:
            response = requests.get(progress_url)
            if response.status_code == 200:
                progress = response.json()
                
                status = progress["status"]
                completed = progress["completed_tests"]
                total = progress["total_tests"]
                passed = progress["passed_tests"]
                failed = progress["failed_tests"]
                percentage = progress["progress_percentage"]
                
                # Only print if progress changed
                if completed != last_completed:
                    print(f"  Progress: {completed}/{total} ({percentage:.1f}%) - "
                          f"Passed: {passed}, Failed: {failed}")
                    last_completed = completed
                
                if status in ["completed", "failed"]:
                    break
            else:
                print_warning(f"Could not fetch progress: {response.status_code}")
                
        except Exception as e:
            print_warning(f"Progress check error: {e}")
    
    # Get final results
    print_info("\nFetching final results...")
    
    results_url = f"{BASE_URL}/api/robot-execution/results/{session_id}"
    response = requests.get(results_url)
    
    if response.status_code != 200:
        print_error(f"Could not fetch results: {response.text}")
        exit(1)
    
    final_results = response.json()
    
    # Print summary
    print_step("", "EXECUTION SUMMARY")
    
    summary = final_results["summary"]
    print(f"Total Tests:     {summary['total_tests']}")
    print(f"Completed:       {summary['completed_tests']}")
    print(f"✅ Passed:       {summary['passed_tests']}")
    print(f"❌ Failed:       {summary['failed_tests']}")
    print(f"⚠️  Errors:       {summary['error_tests']}")
    print(f"Success Rate:    {summary['success_rate']}%")
    
    # Print individual test results
    print("\n" + "="*80)
    print("INDIVIDUAL TEST RESULTS")
    print("="*80)
    
    results_list = final_results.get("results", [])
    for i, test_result in enumerate(results_list, 1):
        test_id = test_result.get("test_case_id", "N/A")
        test_name = test_result.get("test_name", "N/A")
        result_status = test_result.get("result", "unknown")
        passed = test_result.get("overall_passed", False)
        duration = test_result.get("execution_duration", 0)
        
        status_icon = "✅" if passed else "❌"
        print(f"\n{status_icon} Test {i}: {test_id}")
        print(f"   Name: {test_name}")
        print(f"   Result: {result_status}")
        print(f"   Duration: {duration:.2f}s")
        
        # Validation results
        validation_results = test_result.get("validation_results", [])
        if validation_results:
            print(f"   Validation Checks:")
            for vr in validation_results:
                check_name = vr.get("check_name", "unknown")
                check_passed = vr.get("passed", False)
                message = vr.get("message", "")
                check_icon = "✓" if check_passed else "✗"
                print(f"     {check_icon} {check_name}: {message}")
    
    return final_results


def main():
    """Main E2E test workflow"""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("="*80)
    print("  🤖 ROBOT ROS 2 TEST EXECUTION - END-TO-END WORKFLOW")
    print("  Hybrid Execution: Headless Batch + Gazebo Visualization")
    print("="*80)
    print(Colors.ENDC)
    
    try:
        # Step 0: Health checks
        step0_health_checks()
        
        # Step 1: Environment setup
        env_result = step1_environment_setup()
        time.sleep(2)
        
        # Step 2: Test scenario generation
        scenario_result = step2_test_scenario_generation()
        time.sleep(2)
        
        # Step 3: Test case generation
        case_result = step3_test_case_generation()
        time.sleep(2)
        
        # Step 4: Test code generation
        code_result = step4_test_code_generation()
        test_ids = code_result.get("test_ids", [])
        time.sleep(2)
        
        # Step 5: Robot test execution
        execution_result = step5_robot_test_execution(test_ids)
        
        # Final summary
        print(f"\n{Colors.BOLD}{Colors.GREEN}")
        print("="*80)
        print("  ✅ END-TO-END TEST COMPLETED SUCCESSFULLY!")
        print("="*80)
        print(Colors.ENDC)
        
    except KeyboardInterrupt:
        print_warning("\n\nTest interrupted by user")
        exit(1)
    except Exception as e:
        print_error(f"\n\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
