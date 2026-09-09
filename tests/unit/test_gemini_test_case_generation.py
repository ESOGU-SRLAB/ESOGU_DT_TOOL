#!/usr/bin/env python3
"""
Test script for Gemini Test Case Generation API integration
"""
import requests
import json
import sys
import os

def test_gemini_test_case_generation():
    """Test Gemini API integration for test case generation"""
    
    # API endpoint
    url = "http://localhost:8000/api/processes/test-scenario-generation/generate-test-cases"
    
    # Read the API key from the environment; never store it in source control.
    api_key = os.getenv("GEMINI_API_KEY", "")
    
    # Test data
    test_data = {
        "selected_scenarios": [
            {
                "scenario_id": "TS_001",
                "scenario": "User Authentication Flow",
                "description": "Test the complete user authentication process including login, logout, and session management",
                "objective": "Ensure secure and reliable user authentication",
                "category": "Security"
            }
        ],
        "process_prompt": "Generate comprehensive test cases for the following scenarios focusing on functionality, security, and user experience.",
        "selected_files": [
            {
                "name": "auth.js",
                "content": "class AuthService {\n  login(username, password) {\n    // Authentication logic\n    return authenticateUser(username, password);\n  }\n  \n  logout() {\n    // Clear session\n    clearUserSession();\n  }\n}"
            }
        ],
        "ai_model": "gemini-2.5-flash",
        "session_id": "test_session_001",
        "selected_process_title": "API Integration Test",
        "api_key": api_key
    }
    
    print("🧪 Testing Gemini Test Case Generation API...")
    print(f"📡 Endpoint: {url}")
    print(f"🤖 Model: {test_data['ai_model']}")
    print(f"🔑 API Key: {'SET' if api_key else 'NOT SET'}")
    print(f"📊 Scenarios: {len(test_data['selected_scenarios'])}")
    
    try:
        # Send request
        response = requests.post(url, json=test_data, timeout=60)
        
        print(f"\n📈 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Success! Response received:")
            print(f"   - Status: {data.get('status')}")
            print(f"   - Test Case Results: {len(data.get('test_case_results', []))}")
            
            if 'test_case_results' in data:
                for result in data['test_case_results']:
                    print(f"   - Scenario: {result.get('scenario_id')} - {result.get('status')}")
                    if result.get('status') == 'success':
                        print(f"     ↳ Test Cases Generated: {result.get('test_cases_count', 0)}")
            
            print(f"\n📄 Full Response:")
            print(json.dumps(data, indent=2))
            
        elif response.status_code == 500:
            print("❌ Internal Server Error (500)")
            try:
                error_data = response.json()
                print(f"   Error Details: {error_data.get('detail', 'No details available')}")
            except:
                print(f"   Raw Error: {response.text}")
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request Exception: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

if __name__ == "__main__":
    print("="*60)
    print("🚀 GEMINI TEST CASE GENERATION API TEST")
    print("="*60)
    print("\nNOTE: Set GEMINI_API_KEY in the environment to test the full integration.")
    print("\nTesting without a key will show the API structure and error handling...")
    print()
    
    test_gemini_test_case_generation()
