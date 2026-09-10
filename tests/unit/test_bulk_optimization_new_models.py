#!/usr/bin/env python3
"""
Test script to verify new models work with Bulk Optimization
"""

import requests
import json

def test_bulk_optimization_new_models():
    """Test Bulk Optimization with new models"""
    print("🚀 Testing Bulk Optimization with New Models")
    print("=" * 60)
    
    # Sample test cases with some potential duplicates
    test_data = {
        "selected_test_cases": [
            {
                "ScenarioID": "TC001",
                "TestCaseID": "TC001",
                "Title": "User Login Test",
                "Description": "Test user login functionality with valid credentials",
                "Objective": "Verify that user can login successfully"
            },
            {
                "ScenarioID": "TC002", 
                "TestCaseID": "TC002",
                "Title": "Login Authentication Test",
                "Description": "Test user authentication with correct login details",
                "Objective": "Verify successful user authentication"
            },
            {
                "ScenarioID": "TC003",
                "TestCaseID": "TC003",
                "Title": "User Logout Test",
                "Description": "Test user logout functionality",
                "Objective": "Verify that user can logout properly"
            },
            {
                "ScenarioID": "TC004",
                "TestCaseID": "TC004",
                "Title": "Valid Login Test",
                "Description": "Test login functionality with valid user credentials",
                "Objective": "Verify that user can login with correct details"
            },
            {
                "ScenarioID": "TC005",
                "TestCaseID": "TC005",
                "Title": "Password Reset Test",
                "Description": "Test password reset functionality",
                "Objective": "Verify that user can reset password"
            }
        ],
        "process_titles": ["Test Process"],
        "process_name": "Bulk New Model Test",
        "optimization_type": "bulk"  # Bulk optimization
    }
    
    # Test new models with bulk optimization
    new_models = [
        "qwen/qwq-32b",
        "mistralai/codestral-22b-v0.1"
    ]
    
    for model in new_models:
        print(f"\n📋 Testing BULK optimization with model: {model}")
        print("-" * 50)
        
        # Add selected model to test data
        test_data["selected_model"] = model
        
        try:
            # Make API request
            response = requests.post(
                'http://localhost:8000/api/test-case-optimization/smart-selection',
                json=test_data,
                timeout=120
            )
            
            print(f"🔄 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Bulk optimization successful!")
                print(f"📊 Success: {result.get('success', 'N/A')}")
                print(f"📋 Message: {result.get('message', 'N/A')}")
                
                if result.get('success') and result.get('data'):
                    data = result['data']
                    unique_cases = data.get('unique_test_cases', [])
                    duplicates = data.get('similar_test_cases', [])
                    
                    print(f"📈 Bulk Results:")
                    print(f"   - Original test cases: 5")
                    print(f"   - Unique test cases: {len(unique_cases)}")
                    print(f"   - Duplicate test cases: {len(duplicates)}")
                    
                    if unique_cases:
                        print(f"📝 Unique test cases:")
                        for i, case in enumerate(unique_cases, 1):
                            title = case.get('Title', 'N/A')
                            print(f"   {i}. {title}")
                    
                    if duplicates:
                        print(f"🔄 Duplicate test cases:")
                        for i, dup in enumerate(duplicates, 1):
                            dup_title = dup.get('DuplicateCase', {}).get('Title', 'N/A')
                            matched_title = dup.get('MatchedWith', {}).get('Title', 'N/A')
                            print(f"   {i}. {dup_title} → matched with → {matched_title}")
                else:
                    print(f"⚠️  No optimization data returned")
                    
            else:
                print(f"❌ Bulk optimization failed!")
                print(f"📄 Response: {response.text[:300]}...")
                
        except requests.Timeout:
            print(f"⏱️  Request timed out after 120 seconds")
        except Exception as e:
            print(f"❌ Error testing {model}: {e}")
    
    print(f"\n🎉 Bulk optimization test completed!")

if __name__ == "__main__":
    test_bulk_optimization_new_models()
