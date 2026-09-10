#!/usr/bin/env python3
"""
Test the test case generation endpoint
"""

import requests
import json

def test_generate_test_cases():
    """Test the /api/processes/test-scenario-generation/generate-test-cases endpoint"""
    
    url = "http://localhost:8000/api/processes/test-scenario-generation/generate-test-cases"
    
    # Test payload similar to what frontend would send
    payload = {
        "selected_scenarios": [
            {
                "scenario_id": "TS_001",
                "scenario": "User Login with Valid Credentials",
                "description": "Test that a user can successfully log in with valid username and password",
                "objective": "Verify successful authentication",
                "category": "Authentication"
            }
        ],
        "process_prompt": "Generate comprehensive test cases for the following test scenario. Focus on both positive and negative test cases.",
        "selected_files": [],
        "ai_model": "llama3.2:3b",
        "session_id": "test-session-123"
    }
    
    print("Testing /api/processes/test-scenario-generation/generate-test-cases endpoint...")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, timeout=120)
        print(f"\nResponse status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            response_json = response.json()
            print(f"\nResponse JSON keys: {list(response_json.keys())}")
            
            if 'test_case_results' in response_json:
                results = response_json['test_case_results']
                print(f"Generated test case results for {len(results)} scenarios:")
                
                for i, result in enumerate(results):
                    print(f"  Scenario {i+1}: {result.get('scenario_id', 'Unknown')}")
                    print(f"    Status: {result.get('status', 'Unknown')}")
                    if result.get('status') == 'success':
                        test_cases = result.get('test_cases', [])
                        print(f"    Generated {len(test_cases)} test cases")
                        if test_cases:
                            print(f"    First test case: {test_cases[0].get('Title', 'No title')}")
                    else:
                        print(f"    Error: {result.get('error', 'Unknown error')}")
            
            if 'summary' in response_json:
                summary = response_json['summary']
                print(f"\nSummary:")
                print(f"  Total scenarios processed: {summary.get('scenarios_processed', 0)}")
                print(f"  Successful scenarios: {summary.get('successful_scenarios', 0)}")
                print(f"  Failed scenarios: {summary.get('failed_scenarios', 0)}")
                print(f"  Total test cases: {summary.get('total_test_cases', 0)}")
        else:
            print(f"Error response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("Request timed out after 120 seconds")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_generate_test_cases()
