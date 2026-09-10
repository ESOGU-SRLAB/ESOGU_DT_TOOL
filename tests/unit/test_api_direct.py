"""
Direct API test for environment setups
"""

import requests
import json

def test_environment_setups_api():
    """Test environment setups API"""
    print("=== Testing Environment Setups API ===")
    
    url = "http://localhost:8000/api/processes/test-code-generation/environment-setups"
    
    try:
        print(f"Making GET request to: {url}")
        response = requests.get(url)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response Data:")
            print(json.dumps(data, indent=2))
            
            # Check the structure
            if data.get('success'):
                setups = data.get('data', [])
                print(f"\nFound {len(setups)} environment setups:")
                for i, setup in enumerate(setups, 1):
                    print(f"  {i}. {setup.get('environment_name', 'N/A')} - {setup.get('environment_info', {}).get('language', 'Unknown')}")
            else:
                print("API returned success=False")
        else:
            print(f"Error response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - Backend not running!")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_environment_setups_api()