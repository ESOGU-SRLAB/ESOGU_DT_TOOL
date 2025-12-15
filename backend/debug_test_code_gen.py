import requests
import json
import time

# Test her adımı ayrı ayrı kontrol edelim
print("=== Test Code Generation Debug ===\n")

# 1. Environment setups kontrolü
print("1. Checking environment setups...")
try:
    response = requests.get('http://localhost:8000/api/processes/test-code-generation/environment-setups', timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Found {data['count']} environment setup(s)")
        if data['count'] > 0:
            env = data['data'][0]
            print(f"   Environment ID: {env['session_id']}")
            print(f"   Environment Name: {env['environment_name']}")
    else:
        print(f"   ✗ Error: {response.status_code}")
except Exception as e:
    print(f"   ✗ Exception: {e}")

# 2. Process titles kontrolü
print("\n2. Checking process titles...")
try:
    response = requests.get('http://localhost:8000/api/processes/test-code-generation/process-titles', timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Found {data['count']} process title(s)")
        if data['count'] > 0:
            print(f"   First title: {data['data'][0]}")
    else:
        print(f"   ✗ Error: {response.status_code}")
except Exception as e:
    print(f"   ✗ Exception: {e}")

# 3. LM Studio kontrolü
print("\n3. Checking LM Studio...")
try:
    response = requests.get('http://localhost:1234/v1/models', timeout=5)
    if response.status_code == 200:
        models = response.json()
        print(f"   ✓ LM Studio is running")
        print(f"   Available models: {len(models['data'])}")
        for model in models['data'][:3]:
            print(f"     - {model['id']}")
    else:
        print(f"   ✗ Error: {response.status_code}")
except Exception as e:
    print(f"   ✗ LM Studio not accessible: {e}")

# 4. Test basit bir LLM isteği
print("\n4. Testing LM Studio with simple request...")
try:
    payload = {
        "model": "llama-3.2-3b-instruct",
        "messages": [{"role": "user", "content": "Say 'test ok'"}],
        "max_tokens": 50
    }
    start = time.time()
    response = requests.post('http://localhost:1234/v1/chat/completions', json=payload, timeout=30)
    elapsed = time.time() - start
    if response.status_code == 200:
        result = response.json()
        content = result['choices'][0]['message']['content']
        print(f"   ✓ LM Studio responded in {elapsed:.2f}s")
        print(f"   Response: {content[:100]}")
    else:
        print(f"   ✗ Error: {response.status_code}")
except Exception as e:
    print(f"   ✗ Exception: {e}")

# 5. Test Code Generation endpoint'i test et (kısa timeout)
print("\n5. Testing Test Code Generation endpoint...")
url = 'http://localhost:8000/api/processes/test-code-generation/run'
data = {
    'process_title': '15_haziran',
    'environment_session_id': '16f91ead-b607-43e2-96a2-a74d0d4a3543',
    'model': 'llama3.2:3b',
    'environment_name': 'Debug_Test',
    'output_format': 'JSON',
    'session_id': 'debug-test-001'
}
files = {'files': ('test.py', open('test_sample_calculator.py', 'rb'), 'text/x-python')}

try:
    print("   Sending request (20s timeout)...")
    start = time.time()
    response = requests.post(url, data=data, files=files, timeout=20)
    elapsed = time.time() - start
    print(f"   Response in {elapsed:.2f}s")
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✓ Success: {result.get('success')}")
        if result.get('success'):
            print(f"   Generated: {result.get('generated_count')}/{result.get('total_test_cases')}")
        else:
            print(f"   Error: {result.get('error')}")
    else:
        print(f"   Response: {response.text[:200]}")
except requests.Timeout:
    print(f"   ✗ Timeout after 20s - Backend is processing but taking too long")
    print(f"   This suggests the issue is with test case processing, not LM Studio")
except Exception as e:
    print(f"   ✗ Exception: {type(e).__name__}: {str(e)}")

print("\n=== Debug Complete ===")
