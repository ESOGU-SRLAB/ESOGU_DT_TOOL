import requests
import json

def test_session_save_debug():
    """Debug session saving to see what's happening"""
    base_url = "http://localhost:8000/api/test-case-optimization"
    
    print("🔍 Debug Session Saving")
    print("=" * 40)
    
    # Test with a simple optimization request
    test_data = {
        "selected_test_cases": [
            {
                "ScenarioID": "debug_scenario",
                "TestCaseID": "TC_DEBUG",
                "Title": "Debug Test",
                "Description": "Debug test case",
                "Objective": "Test session saving"
            }
        ],
        "process_titles": ["Debug Process"],
        "process_name": "Debug Process Name",
        "selected_model": "llama3.2:3b",
        "custom_prompt": "",
        "session_id": "debug_session_12345"
    }
    
    try:
        response = requests.post(f"{base_url}/smart-selection", json=test_data)
        print(f"Response Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            print(f"Message: {data.get('message')}")
            print(f"Session ID: {data.get('session_id')}")
            
            # Now check if we can find process names
            print("\nChecking process names...")
            names_response = requests.get(f"{base_url}/process-names")
            print(f"Process names response: {names_response.status_code}")
            names_data = names_response.json()
            print(f"Process names data: {names_data}")
            
    except Exception as e:
        print(f"❌ Debug test failed: {e}")

if __name__ == "__main__":
    test_session_save_debug()
