#!/usr/bin/env python3
"""
Test script to verify the newly added models work in Test Case Optimization
Tests the 7 new models added to the model mapping
"""

import requests
import json
import time
import sys
import asyncio

def test_model_mapping_validation():
    """Test that all new models are properly mapped"""
    print("🔍 Testing Model Mapping Validation")
    print("=" * 60)
    
    # Import the LLMClient to test model mapping
    sys.path.append('./backend/utils')
    try:
        from model_client import LLMClient
        
        # Test new model keys
        new_model_keys = [
            "codellama:70b-instruct",
            "kimi-dev:72b", 
            "openai/gpt-oss-120b",
            "deepseek-r1-distill:32b",
            "google/gemma-3-27b",
            "qwen/qwen3-coder-30b",
            "deepseek/deepseek-r1-qwen3-8b"
        ]
        
        expected_values = [
            "CodeLlama-70B-Instruct-GGUF/codellama-70b-instruct.Q4_K_S.gguf",
            "Kimi-Dev-72B-GGUF/Kimi-Dev-72B-Q3_K_S.gguf",
            "openai/gpt-oss-120b",
            "DeepSeek-R1-Distill-Qwen-32B-GGUF/DeepSeek-R1-Distill-Qwen-32B-Q3_K_L.gguf",
            "google/gemma-3-27b", 
            "qwen/qwen3-coder-30b",
            "deepseek/deepseek-r1-0528-qwen3-8b"
        ]
        
        client = LLMClient()
        
        print("📋 Testing model key mappings:")
        for i, model_key in enumerate(new_model_keys):
            mapped_value = client.get_model_identifier(model_key)
            expected_value = expected_values[i]
            
            if mapped_value == expected_value:
                print(f"✅ {model_key} -> {mapped_value}")
            else:
                print(f"❌ {model_key} -> {mapped_value} (Expected: {expected_value})")
                
        print(f"\n✅ Model mapping validation completed!")
        
    except Exception as e:
        print(f"❌ Error in model mapping validation: {e}")

def test_optimization_with_new_models():
    """Test Test Case Optimization with all new models"""
    print("\n🚀 Testing Test Case Optimization with New Models")
    print("=" * 60)
    
    # Sample test cases for optimization
    test_data = {
        "selected_test_cases": [
            {
                "ScenarioID": "TC001",
                "TestCaseID": "TC001",
                "Title": "User Login Test",
                "Description": "Test user login functionality with valid credentials",
                "Objective": "Verify that user can login successfully with correct username and password"
            },
            {
                "ScenarioID": "TC002", 
                "TestCaseID": "TC002",
                "Title": "User Authentication Test",
                "Description": "Test user authentication with correct login details",
                "Objective": "Verify successful user authentication process"
            },
            {
                "ScenarioID": "TC003",
                "TestCaseID": "TC003", 
                "Title": "Login Validation Test",
                "Description": "Test login validation with proper credentials",
                "Objective": "Ensure proper login validation mechanism"
            },
            {
                "ScenarioID": "TC004",
                "TestCaseID": "TC004",
                "Title": "User Logout Test", 
                "Description": "Test user logout functionality",
                "Objective": "Verify that user can logout properly and session is terminated"
            }
        ],
        "process_titles": ["Authentication Process", "Session Management"],
        "process_name": "New Models Test - Authentication Flow",
        "optimization_type": "individual"
    }
    
    # New models to test (using the key values for frontend)
    new_models_to_test = [
        ("codellama:70b-instruct", "CodeLlama 70B Instruct"),
        ("kimi-dev:72b", "Kimi Dev 72B"), 
        ("openai/gpt-oss-120b", "GPT OSS 120B"),
        ("deepseek-r1-distill:32b", "DeepSeek R1 Distill 32B"),
        ("google/gemma-3-27b", "Google Gemma 3 27B"),
        ("qwen/qwen3-coder-30b", "Qwen 3 Coder 30B"),
        ("deepseek/deepseek-r1-qwen3-8b", "DeepSeek R1 Qwen3 8B")
    ]
    
    results_summary = []
    
    for model_key, model_name in new_models_to_test:
        print(f"\n📋 Testing optimization with model: {model_name} ({model_key})")
        print("-" * 60)
        
        # Add selected model to test data
        test_data["selected_model"] = model_key
        
        start_time = time.time()
        
        try:
            # Make API request with extended timeout for large models
            print(f"🔄 Making API request to optimization endpoint...")
            response = requests.post(
                'http://localhost:8000/api/test-case-optimization/smart-selection',
                json=test_data,
                timeout=300  # 5 minutes timeout for large models
            )
            
            elapsed_time = time.time() - start_time
            print(f"⏱️  Request completed in {elapsed_time:.2f} seconds")
            print(f"🔄 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                success = result.get('success', False)
                message = result.get('message', 'No message')
                
                print(f"✅ Optimization successful!")
                print(f"📊 Success: {success}")
                print(f"📋 Message: {message}")
                
                if success and result.get('data'):
                    data = result['data']
                    unique_cases = data.get('unique_test_cases', [])
                    duplicates = data.get('similar_test_cases', [])
                    
                    print(f"📈 Optimization Results:")
                    print(f"   - Original test cases: {len(test_data['selected_test_cases'])}")
                    print(f"   - Unique test cases: {len(unique_cases)}")
                    print(f"   - Duplicate/similar test cases: {len(duplicates)}")
                    
                    if unique_cases:
                        print(f"📝 Unique test cases found:")
                        for i, case in enumerate(unique_cases, 1):
                            title = case.get('Title', 'N/A')
                            print(f"   {i}. {title}")
                    
                    if duplicates:
                        print(f"🔄 Similar test cases identified:")
                        for i, case in enumerate(duplicates, 1):
                            title = case.get('Title', 'N/A') 
                            print(f"   {i}. {title}")
                    
                    results_summary.append({
                        'model': model_name,
                        'model_key': model_key,
                        'status': 'SUCCESS',
                        'unique_cases': len(unique_cases),
                        'duplicates': len(duplicates),
                        'elapsed_time': elapsed_time
                    })
                else:
                    print(f"⚠️  No optimization data returned")
                    results_summary.append({
                        'model': model_name,
                        'model_key': model_key,
                        'status': 'NO_DATA',
                        'unique_cases': 0,
                        'duplicates': 0,
                        'elapsed_time': elapsed_time
                    })
                    
            else:
                error_text = response.text[:500] if response.text else "No error text"
                print(f"❌ Optimization failed!")
                print(f"📄 Response: {error_text}...")
                
                results_summary.append({
                    'model': model_name,
                    'model_key': model_key,
                    'status': f'FAILED ({response.status_code})',
                    'unique_cases': 0,
                    'duplicates': 0,
                    'elapsed_time': elapsed_time,
                    'error': error_text
                })
                
        except requests.Timeout:
            print(f"⏱️  Request timed out after 300 seconds")
            results_summary.append({
                'model': model_name,
                'model_key': model_key,
                'status': 'TIMEOUT',
                'unique_cases': 0,
                'duplicates': 0,
                'elapsed_time': 300
            })
        except Exception as e:
            print(f"❌ Error testing {model_name}: {e}")
            results_summary.append({
                'model': model_name,
                'model_key': model_key,
                'status': f'ERROR: {str(e)}',
                'unique_cases': 0,
                'duplicates': 0,
                'elapsed_time': time.time() - start_time
            })
        
        # Add delay between requests to avoid overwhelming the server
        if model_key != new_models_to_test[-1][0]:  # Don't delay after last model
            print(f"⏳ Waiting 3 seconds before next model test...")
            time.sleep(3)
    
    # Print summary
    print(f"\n📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"{'Model':<25} {'Status':<15} {'Unique':<8} {'Dupes':<8} {'Time(s)':<10}")
    print("-" * 60)
    
    successful_models = 0
    for result in results_summary:
        model_display = result['model'][:24]
        status = result['status']
        unique = result['unique_cases']
        dupes = result['duplicates'] 
        elapsed = f"{result['elapsed_time']:.1f}"
        
        print(f"{model_display:<25} {status:<15} {unique:<8} {dupes:<8} {elapsed:<10}")
        
        if result['status'] == 'SUCCESS':
            successful_models += 1
    
    print("-" * 60)
    print(f"✅ Successful models: {successful_models}/{len(new_models_to_test)}")
    print(f"🎉 Test completed!")
    
    return results_summary

def main():
    """Main test function"""
    print("🧪 NEW MODELS TEST CASE OPTIMIZATION VALIDATION")
    print("=" * 80)
    print("Testing 7 newly added models for Test Case Optimization functionality")
    print("=" * 80)
    
    # Step 1: Test model mapping
    test_model_mapping_validation()
    
    # Step 2: Test optimization with new models
    results = test_optimization_with_new_models()
    
    # Step 3: Save results to file
    timestamp = int(time.time())
    results_file = f"new_models_test_results_{timestamp}.json"
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Test results saved to: {results_file}")
    print(f"🔚 All tests completed!")

if __name__ == "__main__":
    main()
