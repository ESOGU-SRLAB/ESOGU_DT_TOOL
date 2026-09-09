import requests
import json

def test_process_name_functionality():
    """Test the process name functionality for test case optimization"""
    base_url = "http://localhost:8000/api/test-case-optimization"
    
    print("🚀 Testing Test Case Optimization Process Name Functionality")
    print("=" * 60)
    
    # Test 1: Process Names endpoint (should return empty initially)
    print("Testing /process-names endpoint...")
    try:
        response = requests.get(f"{base_url}/process-names")
        print(f"✅ Process names endpoint successful!")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Success: {data.get('success')}")
        print(f"Message: {data.get('message')}")
        print(f"Available process names: {len(data.get('data', []))}")
        for name_data in data.get('data', []):
            print(f"  - {name_data.get('process_name')}: {name_data.get('count')} optimization(s)")
    except Exception as e:
        print(f"❌ Process names endpoint failed: {e}")
    
    # Test 2: Smart selection with process name
    print("\nTesting smart selection with process name...")
    test_data = {
        "selected_test_cases": [
            {
                "ScenarioID": "test_scenario_1",
                "TestCaseID": "TC_001",
                "Title": "Login Test",
                "Description": "Test user login functionality",
                "Objective": "Verify user can login with valid credentials"
            }
        ],
        "process_titles": ["Test Process"],
        "process_name": "Test Case Process 1",
        "selected_model": "llama3.2:3b",
        "custom_prompt": "",
        "session_id": "test_session_process_name"
    }
    
    try:
        response = requests.post(f"{base_url}/smart-selection", json=test_data)
        print(f"✅ Smart selection with process name successful!")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Success: {data.get('success')}")
        print(f"Message: {data.get('message')}")
    except Exception as e:
        print(f"❌ Smart selection with process name failed: {e}")
    
    # Test 3: Process name validation (should fail without process name)
    print("\nTesting process name validation (should fail without process name)...")
    test_data_no_name = {
        "selected_test_cases": [
            {
                "ScenarioID": "test_scenario_1",
                "TestCaseID": "TC_001",
                "Title": "Login Test",
                "Description": "Test user login functionality",
                "Objective": "Verify user can login with valid credentials"
            }
        ],
        "process_titles": ["Test Process"],
        "selected_model": "llama3.2:3b",
        "custom_prompt": "",
        "session_id": "test_session_no_process_name"
    }
    
    try:
        response = requests.post(f"{base_url}/smart-selection", json=test_data_no_name)
        if response.status_code == 400:
            print("✅ Process name validation works correctly - returns 400 when process name missing")
        else:
            print(f"❌ Process name validation failed - expected 400, got {response.status_code}")
            print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"❌ Process name validation test failed: {e}")
    
    # Test 4: Check process names again (should have one now)
    print("\nTesting /process-names endpoint after creating data...")
    try:
        response = requests.get(f"{base_url}/process-names")
        print(f"✅ Process names endpoint successful!")
        data = response.json()
        print(f"Available process names: {len(data.get('data', []))}")
        for name_data in data.get('data', []):
            print(f"  - {name_data.get('process_name')}: {name_data.get('count')} optimization(s)")
    except Exception as e:
        print(f"❌ Process names endpoint failed: {e}")
    
    # Test 5: Get results by process name
    print("\nTesting /results/by-process-name endpoint...")
    try:
        response = requests.get(f"{base_url}/results/by-process-name/Test Case Process 1")
        print(f"✅ Results by process name endpoint successful!")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Success: {data.get('success')}")
        print(f"Message: {data.get('message')}")
        results = data.get('data', [])
        print(f"Found {len(results)} result(s)")
        for result in results:
            print(f"  - Session: {result.get('session_id')}")
            print(f"    Process Name: {result.get('process_name')}")
            print(f"    Model: {result.get('used_model')}")
            print(f"    Process Count: {result.get('process_count')}")
    except Exception as e:
        print(f"❌ Results by process name failed: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Process name functionality tests completed!")

if __name__ == "__main__":
    test_process_name_functionality()
