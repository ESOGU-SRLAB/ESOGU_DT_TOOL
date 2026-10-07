import requests
import json

def test_bulk_optimization_with_enhanced_json():
    """Test bulk optimization with the enhanced JSON extraction"""
    
    print("🚀 Testing Bulk Optimization with Enhanced JSON Extraction")
    print("=" * 60)
    
    # Test data - simulate selecting some test cases
    selected_test_cases = [
        {
            "ScenarioID": "TS_001",
            "TestCaseID": "TS_001",
            "Title": "Verify Task Creation and Retrieval",
            "Description": "This scenario tests the functionality of creating a new task and retrieving it from the system.",
            "Objective": "Validate the creation and retrieval of tasks",
            "Category": "Functional",
            "Comments": "",
            "SelectedCategory": "Unknown",
            "SelectedTestType": "Unknown",
            "SessionID": "test-session",
            "ProcessTitle": "Test Process",
            "unique_key": "test_001"
        },
        {
            "ScenarioID": "TS_002",
            "TestCaseID": "TS_002", 
            "Title": "Test Task Update and Completion Status",
            "Description": "This scenario tests the functionality of updating a task's title, description, and completion status.",
            "Objective": "Validate the update and completion status of tasks",
            "Category": "Functional",
            "Comments": "",
            "SelectedCategory": "Unknown",
            "SelectedTestType": "Unknown", 
            "SessionID": "test-session",
            "ProcessTitle": "Test Process",
            "unique_key": "test_002"
        },
        {
            "ScenarioID": "TS_003",
            "TestCaseID": "TS_003",
            "Title": "Task Creation and Retrieval Test", 
            "Description": "This scenario tests creating a task and retrieving it from the system.",
            "Objective": "Validate task creation and retrieval functionality",
            "Category": "Functional",
            "Comments": "",
            "SelectedCategory": "Unknown", 
            "SelectedTestType": "Unknown",
            "SessionID": "test-session",
            "ProcessTitle": "Test Process",
            "unique_key": "test_003"
        }
    ]
    
    # Prepare request
    request_data = {
        "selected_test_cases": selected_test_cases,
        "custom_prompt": None,
        "selected_model": "openai/gpt-oss-20b",  # Use the same model from the terminal output
        "api_key": None,
        "optimization_type": "bulk",
        "process_title": "Test Process Enhanced JSON",
        "process_name": "Test Process Enhanced JSON"
    }
    
    print(f"📊 Test cases to optimize: {len(selected_test_cases)}")
    print(f"🤖 Model: {request_data['selected_model']}")
    print(f"⚙️ Optimization type: {request_data['optimization_type']}")
    
    try:
        print(f"\n🔄 Sending bulk optimization request...")
        response = requests.post(
            "http://localhost:8000/api/test-case-optimization/smart-selection",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        print(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Request successful!")
            print(f"🎯 Success: {result.get('success', False)}")
            print(f"📝 Message: {result.get('message', 'No message')}")
            
            if result.get('success'):
                data = result.get('data', {})
                print(f"\n📊 Optimization Results:")
                print(f"   - Unique test cases: {len(data.get('unique_test_cases', []))}")
                print(f"   - Similar test cases: {len(data.get('similar_test_cases', []))}")
                print(f"   - Optimization type: {data.get('optimization_type', 'Unknown')}")
                
                # Show some details
                unique_cases = data.get('unique_test_cases', [])
                if unique_cases:
                    print(f"\n📋 Unique test cases found:")
                    for i, case in enumerate(unique_cases[:3]):
                        print(f"   {i+1}. {case.get('Title', 'No title')}")
                
                similar_cases = data.get('similar_test_cases', [])
                if similar_cases:
                    print(f"\n🔄 Similar test cases found: {len(similar_cases)}")
                    for i, pair in enumerate(similar_cases[:2]):
                        dup_case = pair.get('DuplicateCase', {})
                        matched_with = pair.get('MatchedWith', {})
                        print(f"   {i+1}. '{dup_case.get('Title', 'No title')}' ≈ '{matched_with.get('Title', 'No title')}'")
                
                return True
            else:
                print(f"❌ Request failed: {result.get('message', 'No message')}")
                return False
        
        else:
            print(f"❌ HTTP Error {response.status_code}")
            try:
                error_data = response.json()
                print(f"📝 Error: {error_data.get('detail', 'No detail')}")
                
                # Check if it's our enhanced JSON extraction working vs failing
                if "JSON" in str(error_data):
                    print(f"\n🔍 This might be a JSON extraction issue:")
                    print(f"   - Check if enhanced extraction worked")
                    print(f"   - Error details: {error_data}")
                
            except:
                print(f"📝 Raw error: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out")
        return False
    except requests.exceptions.ConnectionError:
        print("🔌 Connection error - is backend running?")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_bulk_optimization_with_enhanced_json()
    print(f"\n{'=' * 60}")
    print(f"🏁 Test Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
    if success:
        print("🎉 Enhanced JSON extraction is working!")
    else:
        print("⚠️ Check logs for detailed error analysis")
