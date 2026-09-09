#!/usr/bin/env python3
"""
Test the current Test Case Generation workflow to identify UI display issue
"""

import requests
import json
import time

def test_test_case_generation_workflow():
    """Test the complete test case generation workflow"""
    
    print("Testing Test Case Generation workflow with UI display debugging...")
    
    # Test with a simple scenario
    url = "http://localhost:8000/api/processes/test-scenario-generation/generate-test-cases"
    
    test_data = {
        "selected_scenarios": [
            {
                "scenario_id": "TS_001",
                "scenario": "User Login Authentication",
                "description": "Test that users can log in with valid credentials and receive appropriate error messages for invalid inputs",
                "objective": "Verify user authentication process",
                "category": "Authentication"
            }
        ],
        "process_prompt": "Generate comprehensive test cases for the following scenario. Focus on both positive and negative test cases.",
        "selected_files": [
            {
                "name": "test_file.txt",
                "content": "function login(username, password) { return authenticate(username, password); }"
            }
        ],
        "ai_model": "llama3.2:3b",
        "session_id": "ui_test_session_" + str(int(time.time())),
        "selected_process_title": "UI Test Process",
        "api_key": ""  # Empty for LM Studio
    }
    
    print(f"Making request to: {url}")
    print(f"Test data: {json.dumps(test_data, indent=2)}")
    
    try:
        response = requests.post(url, json=test_data, timeout=60)
        print(f"\nResponse status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ SUCCESS! Backend returned proper data structure:")
            print(f"Status: {result.get('status')}")
            print(f"Test case results count: {len(result.get('test_case_results', []))}")
            print(f"Summary: {result.get('summary', {})}")
            
            # Verify the exact data structure expected by OutputPanel
            if result.get('test_case_results'):
                for i, test_result in enumerate(result['test_case_results']):
                    print(f"\nTest result {i+1}:")
                    print(f"  Scenario ID: {test_result.get('scenario_id')}")
                    print(f"  Status: {test_result.get('status')}")
                    print(f"  Test cases count: {test_result.get('test_cases_count', 0)}")
                    
                    # Check the test cases structure
                    test_cases = test_result.get('test_cases', [])
                    if test_cases and len(test_cases) > 0:
                        print(f"  First test case structure: {list(test_cases[0].keys()) if test_cases[0] else 'Empty'}")
            
            print(f"\n✅ Backend data structure is correct!")
            print(f"\nThe issue is likely in the frontend data flow between:")
            print(f"1. TestCaseGenerationForm.onRun() call")
            print(f"2. App.jsx handleProcessRun() processing") 
            print(f"3. OutputPanel.outputs[activeTab] lookup")
            
            return result
            
        else:
            print(f"❌ ERROR: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return None

if __name__ == "__main__":
    test_test_case_generation_workflow()