#!/usr/bin/env python3

import requests
import json

# Test Case Optimization endpoint'ini gerçek API key ile test et
url = "http://127.0.0.1:8000/test-case-optimization/optimize"

# Test data
test_data = {
    "testCases": [
        {
            "id": "TC001",
            "title": "Login with valid credentials",
            "description": "Test user login functionality with valid username and password",
            "steps": [
                "Navigate to login page",
                "Enter valid username",
                "Enter valid password", 
                "Click login button"
            ],
            "expectedResults": [
                "Login page loads successfully",
                "Username field accepts input",
                "Password field accepts input",
                "User is redirected to dashboard"
            ]
        }
    ],
    "selectedModel": "gemini-1.5-flash",
    "apiKeys": {
        "google": "YOUR_GEMINI_API_KEY_HERE"  # Gerçek API key'i buraya koyun
    }
}

def test_optimization():
    try:
        print("Testing Test Case Optimization with API key...")
        print(f"URL: {url}")
        print(f"Model: {test_data['selectedModel']}")
        
        response = requests.post(url, json=test_data, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Optimization successful!")
            print(f"Optimized test cases count: {len(result.get('optimizedTestCases', []))}")
            
            if result.get('optimizedTestCases'):
                first_case = result['optimizedTestCases'][0]
                print(f"First optimized case title: {first_case.get('title')}")
                
        else:
            print(f"❌ Error: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"Error details: {error_detail}")
            except:
                print(f"Error text: {response.text}")
                
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    print("=== Test Case Optimization API Test ===")
    print("Note: Replace 'YOUR_GEMINI_API_KEY_HERE' with actual API key to test")
    print()
    test_optimization()