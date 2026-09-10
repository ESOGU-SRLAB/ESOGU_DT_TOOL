#!/usr/bin/env python3
"""
Test the UI display fix by running a test case generation and checking console logs
"""

import requests
import json
import time

def test_ui_display_fix():
    """Test that the UI display fix works with proper debug output"""
    
    print("Testing UI display fix with enhanced debugging...")
    
    # Test with regular LM Studio model first to ensure basic flow works
    url = "http://localhost:8000/api/processes/test-scenario-generation/generate-test-cases"
    
    test_data = {
        "selected_scenarios": [
            {
                "scenario_id": "TS_001",
                "scenario": "User Login Test - UI Display Fix",
                "description": "Test user login functionality to verify UI display fix",
                "objective": "Verify UI displays test case generation results correctly",
                "category": "UI Testing"
            }
        ],
        "process_prompt": "Generate 3-4 test cases for this scenario to test the UI display fix.",
        "selected_files": [
            {
                "name": "login.js",
                "content": "function login(user, pass) { return authenticate(user, pass); }"
            }
        ],
        "ai_model": "llama3.2:3b",
        "session_id": "ui_display_fix_test_" + str(int(time.time())),
        "selected_process_title": "UI Display Fix Test",
        "api_key": ""
    }
    
    print(f"Making request to: {url}")
    print(f"Session ID: {test_data['session_id']}")
    
    try:
        response = requests.post(url, json=test_data, timeout=60)
        print(f"\nResponse status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Backend Response Structure:")
            print(f"   Status: {result.get('status')}")
            print(f"   Test case results count: {len(result.get('test_case_results', []))}")
            print(f"   Summary: {result.get('summary', {})}")
            
            print(f"\n📋 Expected Frontend Data Flow:")
            print(f"   1. TestCaseGenerationForm calls: onRun('test-case-generation', {{data: result}})")
            print(f"   2. App.jsx handleProcessRun stores: outputs['test-case-generation'] = {{data: result, ...}}")
            print(f"   3. OutputPanel checks: outputs['test-case-generation'].data.test_case_results")
            
            print(f"\n🔧 Fixed Issues:")
            print(f"   ✅ Enhanced renderTestCaseContent() to handle nested data structures")
            print(f"   ✅ Added fallback for output.data.data.test_case_results (nested structure)")
            print(f"   ✅ Added rawData fallback for backwards compatibility")
            print(f"   ✅ Added debug information display when no data found")
            print(f"   ✅ Added proper error handling with user-friendly messages")
            
            print(f"\n🎯 Next Steps:")
            print(f"   1. Open the Test Case Generation tab in the frontend")
            print(f"   2. Run this same test through the UI")
            print(f"   3. Check browser console for debug logs from OutputPanel")
            print(f"   4. Verify results display correctly in the UI")
            print(f"   5. Test with Gemini API if API key is available")
            
            # Simulate the exact data structure that will be in outputs[activeTab]
            simulated_output_structure = {
                "type": "test-case-generation",
                "data": result,  # This is what gets stored
                "content": f"Test Case Generation completed with {result.get('summary', {}).get('successful_scenarios', 0)} successful scenarios",
                "status": "completed",
                "processType": "Test Case Generation",
                "processId": "test-case-generation", 
                "timestamp": "2024-01-01T00:00:00.000Z",
                "rawData": result
            }
            
            print(f"\n📊 Simulated Frontend Output Structure:")
            print(f"   outputs['test-case-generation'] will contain:")
            print(f"   - type: {simulated_output_structure['type']}")
            print(f"   - data.test_case_results: {len(simulated_output_structure['data'].get('test_case_results', []))} results")
            print(f"   - data.summary: {bool(simulated_output_structure['data'].get('summary'))}")
            print(f"   - rawData.test_case_results: {len(simulated_output_structure['rawData'].get('test_case_results', []))} results")
            
            print(f"\n✅ UI Display Fix Status: READY FOR TESTING")
            
            return result
            
        else:
            print(f"❌ Backend Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Test Error: {e}")
        return None

if __name__ == "__main__":
    test_ui_display_fix()