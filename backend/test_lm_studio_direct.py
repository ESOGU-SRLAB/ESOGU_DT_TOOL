import requests
import json
import time

# Test LM Studio directly with GPT OSS 20B
url = 'http://localhost:1234/v1/chat/completions'

payload = {
    "model": "openai/gpt-oss-20b",
    "messages": [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user",
            "content": "Write a simple pytest test function for a calculator add method. Keep it short."
        }
    ],
    "temperature": 0.7,
    "max_tokens": 500
}

print('Testing LM Studio directly with GPT OSS 20B...')
print(f'Model: openai/gpt-oss-20b')
print('Sending request...')

start_time = time.time()

try:
    response = requests.post(url, json=payload, timeout=120)
    elapsed = time.time() - start_time
    
    print(f'Status Code: {response.status_code}')
    print(f'Response Time: {elapsed:.2f} seconds')
    
    if response.status_code == 200:
        result = response.json()
        content = result['choices'][0]['message']['content']
        print(f'\nResponse Length: {len(content)} chars')
        print(f'\nGenerated Content:')
        print(content)
    else:
        print(f'Error: {response.text}')
except requests.Timeout:
    elapsed = time.time() - start_time
    print(f'Timeout after {elapsed:.2f} seconds')
except Exception as e:
    elapsed = time.time() - start_time
    print(f'Exception after {elapsed:.2f} seconds: {str(e)}')
