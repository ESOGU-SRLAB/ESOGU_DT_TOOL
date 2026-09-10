#!/usr/bin/env python3
"""
Comprehensive test for test case generation with multiple scenarios
"""

import requests
import json

def test_comprehensive_test_case_generation():
    """Test the test case generation with multiple scenarios like the frontend would send"""
    
    url = "http://localhost:8000/api/processes/test-scenario-generation/generate-test-cases"
    
    # Test payload with multiple scenarios (similar to the console log structure)
    payload = {
        "selected_scenarios": [
            {
                "scenario_id": "TS_001",
                "scenario": "Create New Task with Valid Data",
                "description": "Test creating a new task with all required fields properly filled",
                "objective": "Verify task creation functionality with valid inputs",
                "category": "Functional"
            },
            {
                "scenario_id": "TS_002", 
                "scenario": "Mark Task as Completed",
                "description": "Test marking an existing task as completed",
                "objective": "Verify task status update functionality",
                "category": "Functional"
            },
            {
                "scenario_id": "TS_003",
                "scenario": "Invalid Task Title",
                "description": "Test creating a task with invalid or empty title",
                "objective": "Verify input validation for task title field",
                "category": "Negative Testing"
            }
        ],
        "process_prompt": "Acting as a senior ISTQB-certified test analyst, generate a comprehensive set of functional test cases for the following test scenario. Focus on creating practical, executable test cases that cover both positive and negative scenarios.",
        "selected_files": [
            {
                "name": "task_manager.js",
                "content": "// Sample task manager code\nclass TaskManager {\n  createTask(title, description) {\n    if (!title || title.trim() === '') {\n      throw new Error('Task title is required');\n    }\n    return { id: Date.now(), title, description, status: 'pending' };\n  }\n  \n  markCompleted(taskId) {\n    // Mark task as completed\n    return { ...task, status: 'completed' };\n  }\n}"
            }
        ],
        "ai_model": "llama3.2:3b",
        "session_id": "comprehensive-test-session"
    }
    
    print("Testing comprehensive test case generation...")
    print(f"URL: {url}")
    print(f"Processing {len(payload['selected_scenarios'])} scenarios")
    
    try:
        response = requests.post(url, json=payload, timeout=180)  # 3 minutes timeout
        print(f"\nResponse status: {response.status_code}")
        
        if response.status_code == 200:
            response_json = response.json()
            print(f"Response keys: {list(response_json.keys())}")
            
            # Check test case results
            if 'test_case_results' in response_json:
                results = response_json['test_case_results']
                print(f"\n=== TEST CASE RESULTS ({len(results)} scenarios) ===")
                
                for i, result in enumerate(results):
                    scenario_id = result.get('scenario_id', 'Unknown')
                    status = result.get('status', 'Unknown')
                    title = result.get('scenario_title', 'Unknown')
                    
                    print(f"\nScenario {i+1}: {scenario_id}")
                    print(f"  Title: {title}")
                    print(f"  Status: {status}")
                    
                    if status == 'success':
                        test_cases = result.get('test_cases', [])
                        print(f"  Generated: {len(test_cases)} test cases")
                        
                        # Show first few test cases
                        for j, tc in enumerate(test_cases[:3]):  # First 3 test cases
                            tc_title = tc.get('Title', tc.get('TestCaseID', f'Test Case {j+1}'))
                            print(f"    {j+1}. {tc_title}")
                    else:
                        error = result.get('error', 'Unknown error')
                        print(f"  Error: {error}")
            
            # Check summary
            if 'summary' in response_json:
                summary = response_json['summary']
                print(f"\n=== SUMMARY ===")
                print(f"Total scenarios processed: {summary.get('scenarios_processed', 0)}")
                print(f"Successful scenarios: {summary.get('successful_scenarios', 0)}")
                print(f"Failed scenarios: {summary.get('failed_scenarios', 0)}")
                print(f"Total test cases generated: {summary.get('total_test_cases', 0)}")
                print(f"Model used: {summary.get('model_used', 'Unknown')}")
                
        else:
            print(f"Error response ({response.status_code}): {response.text}")
            
    except requests.exceptions.Timeout:
        print("Request timed out after 180 seconds")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_comprehensive_test_case_generation()
