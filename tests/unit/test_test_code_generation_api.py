#!/usr/bin/env python3
"""
Test Code Generation API test script
Bu script Test Code Generation API'nin düzgün çalışıp çalışmadığını test eder.
"""

import requests
import json
from datetime import datetime

# Backend URL
BASE_URL = "http://localhost:8000"

def test_get_environment_setups():
    """Environment Setup kayıtlarını çekme testi"""
    print("🔍 Testing GET /api/processes/test-code-generation/environment-setups...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/processes/test-code-generation/environment-setups", timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            print(f"Count: {data.get('count')}")
            
            setups = data.get('data', [])
            print(f"Found {len(setups)} environment setups:")
            
            for i, setup in enumerate(setups[:5]):  # İlk 5'ini göster
                print(f"  {i+1}. Session ID: {setup.get('session_id')}")
                print(f"     Environment Name: {setup.get('environment_name')}")
                print(f"     Timestamp: {setup.get('timestamp')}")
                print()
            
            return True
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Backend bağlantısı kurulamadı. Backend çalışıyor mu?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_test_code_generation():
    """Test Code Generation endpoint testi"""
    print("\n🚀 Testing POST /api/processes/test-code-generation/generate...")
    
    # Test source file content
    source_code = "def login(username, password):\n    if username == 'admin' and password == 'password':\n        return True\n    return False"
    
    # Form data için dosya oluştur
    files = {
        'files': ('login.py', source_code, 'text/plain')
    }
    
    data = {
        'process_title': 'Test Process',
        'environment_session_id': '60c1ff23-b569-4918-8eb8-c12246d0cbde',
        'model': 'llama3.2:3b'
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/processes/test-code-generation/generate",
            files=files,
            data=data,
            timeout=60
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response data: {json.dumps(data, indent=2)}")
            
            if data.get('success'):
                print("✅ Test code generation başarılı!")
                if 'test_code' in data:
                    test_code = data['test_code']
                    print(f"Generated test code ({len(test_code)} characters):")
                    print("=" * 50)
                    print(test_code[:500] + "..." if len(test_code) > 500 else test_code)
                    print("=" * 50)
            else:
                print(f"❌ Test code generation başarısız: {data.get('message', 'No message')}")
            
            return True
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Test Code Generation API Test")
    print("=" * 50)
    
    # Test 1: Environment Setups çekme
    env_test_passed = test_get_environment_setups()
    
    if env_test_passed:
        # Test 2: Test Code Generation
        test_test_code_generation()
    else:
        print("\n❌ Environment Setups test başarısız oldu, Test Code Generation test atlanıyor.")
    
    print("\n✅ Test tamamlandı!")

if __name__ == "__main__":
    main()