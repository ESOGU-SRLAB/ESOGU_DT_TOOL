import requests
import json

def test_models_endpoint():
    """Test the new models endpoint"""
    print("Testing /api/test-case-optimization/models endpoint...")
    
    try:
        response = requests.get('http://localhost:8000/api/test-case-optimization/models')
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Models endpoint successful!")
            print(f"Success: {data['success']}")
            print(f"Message: {data['message']}")
            print(f"Number of models: {len(data['data'])}")
            
            print("\nAvailable models:")
            for model in data['data']:
                print(f"  - {model['key']}: {model['name']} - {model['description']}")
                
            return True
        else:
            print(f"❌ Models endpoint failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing models endpoint: {e}")
        return False

def test_smart_selection_with_model():
    """Test smart selection with model parameter"""
    print("\nTesting smart selection with model parameter...")
    
    # Sample test data
    test_data = {
        "selected_test_cases": [
            {
                "ScenarioID": "test_scenario_1",
                "TestCaseID": "TC_001",
                "Title": "Login Test",
                "Description": "Test user login functionality",
                "Objective": "Verify user can login with valid credentials"
            },
            {
                "ScenarioID": "test_scenario_1", 
                "TestCaseID": "TC_002",
                "Title": "Login Verification",
                "Description": "Test user login feature",
                "Objective": "Verify user authentication works correctly"
            }
        ],
        "process_titles": ["Test Process"],
        "custom_prompt": "",
        "selected_model": "llama3.2:3b",
        "session_id": "test_session_123"
    }
    
    try:
        response = requests.post(
            'http://localhost:8000/api/test-case-optimization/smart-selection',
            json=test_data
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Smart selection with model successful!")
            print(f"Success: {data['success']}")
            print(f"Message: {data['message']}")
            return True
        else:
            print(f"❌ Smart selection failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing smart selection: {e}")
        return False

def test_missing_model_validation():
    """Test that model selection is required"""
    print("\nTesting model validation (should fail without model)...")
    
    # Sample test data without model
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
        "custom_prompt": "",
        "session_id": "test_session_123"
        # No selected_model parameter
    }
    
    try:
        response = requests.post(
            'http://localhost:8000/api/test-case-optimization/smart-selection',
            json=test_data
        )
        
        if response.status_code == 400:
            print("✅ Model validation works correctly - returns 400 when model missing")
            return True
        else:
            print(f"❌ Model validation failed - expected 400, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing model validation: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Test Case Optimization with Model Selection")
    print("=" * 60)
    
    results = []
    
    # Test 1: Models endpoint
    results.append(test_models_endpoint())
    
    # Test 2: Smart selection with model
    results.append(test_smart_selection_with_model())
    
    # Test 3: Model validation
    results.append(test_missing_model_validation())
    
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"✅ Passed: {sum(results)}/{len(results)}")
    print(f"❌ Failed: {len(results) - sum(results)}/{len(results)}")
    
    if all(results):
        print("\n🎉 All tests passed! Model selection feature is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Please check the implementation.")
