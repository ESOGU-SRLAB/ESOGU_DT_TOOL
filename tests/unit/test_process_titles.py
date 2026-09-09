#!/usr/bin/env python3
"""
Test available process titles
"""

import requests

BASE_URL = "http://localhost:8000"

def test_process_titles():
    """Available process titles'ları test et"""
    try:
        response = requests.get(f"{BASE_URL}/api/processes/test-code-generation/process-titles", timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            print(f"Count: {data.get('count')}")
            
            titles = data.get('data', [])
            print(f"Available process titles ({len(titles)}):")
            
            for i, title in enumerate(titles):
                print(f"  {i+1}. {title}")
            
            return titles
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return []
            
    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    print("🔍 Testing available process titles...")
    titles = test_process_titles()
    
    if titles:
        print(f"\n✅ Found {len(titles)} process titles.")
        print("Use one of these in your test code generation request.")
    else:
        print("\n❌ No process titles found.")