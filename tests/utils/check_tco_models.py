import requests
import json

response = requests.get('http://localhost:8000/api/test-case-optimization/models')
data = response.json()

print("Test Case Optimization Models Endpoint Response:")
print(f"Status Code: {response.status_code}")
print(f"Success: {data.get('success')}")
print(f"Total models: {len(data.get('data', []))}")

gemini_models = [m for m in data['data'] if 'gemini' in m['key']]
print(f"\nGemini models found: {len(gemini_models)}")

for model in gemini_models:
    print(f"  - {model['key']}")
    print(f"    Name: {model.get('name', 'NOT SET')}")
    print(f"    Type: {model.get('type', 'NOT SET')}")
    print(f"    Provider: {model.get('provider', 'NOT SET')}")
    print()