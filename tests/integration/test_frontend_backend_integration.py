#!/usr/bin/env python3
"""
Test the actual test scenario generation endpoint
"""

import requests
import json

def test_scenario_generation_endpoint():
    """Test the /test-scenario-generation/run endpoint"""
    
    url = "http://localhost:8000/api/processes/test-scenario-generation/run"
    
    # Test payload as form data
    form_data = {
        "model": "llama3.2:3b",
        "final_prompt": "Generate comprehensive test scenarios for user login functionality. Include both positive and negative test cases covering username validation, password validation, and authentication flow.",
        "test_type": "functional",
        "test_category": "authentication",
        "process_title": "User Login Test Scenarios",
        "session_id": "frontend-test-session"
    }
    
    print("Testing /test-scenario-generation/run endpoint...")
    print(f"URL: {url}")
    print(f"Form data: {json.dumps(form_data, indent=2)}")
    
    try:
        response = requests.post(url, data=form_data, timeout=60)
        print(f"\nResponse status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            response_json = response.json()
            print(f"\nResponse JSON keys: {list(response_json.keys())}")
            
            if 'test_scenarios' in response_json:
                scenarios = response_json['test_scenarios']
                if 'TestScenarios' in scenarios:
                    print(f"Generated {len(scenarios['TestScenarios'])} test scenarios:")
                    for i, scenario in enumerate(scenarios['TestScenarios'][:2]):  # Show first 2
                        print(f"  {i+1}. {scenario.get('Title', 'No title')}")
                        print(f"     Description: {scenario.get('Description', 'No description')[:100]}...")
            
            print(f"\nMetadata: {response_json.get('metadata', {})}")
        else:
            print(f"Error response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("Request timed out after 60 seconds")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_scenario_generation_endpoint()
