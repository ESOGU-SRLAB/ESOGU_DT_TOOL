import requests
import json

# Test the exact same request frontend is making
url = 'http://localhost:8000/api/test-execution/execute-selected-tests'
payload = {
    'test_ids': ['test_session_1_0'],  # Dummy test ID
    'model': 'llama3.2:3b'
}

print("=" * 80)
print("Testing Test Execution Endpoint")
print("=" * 80)
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print("-" * 80)

try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print("-" * 80)
    print("Response Body:")
    print(json.dumps(response.json(), indent=2))
except requests.exceptions.RequestException as e:
    print(f"Error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
    print(f"Response text: {response.text}")

print("=" * 80)
