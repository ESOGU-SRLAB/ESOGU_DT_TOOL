import requests
import json

url = 'http://localhost:8000/api/processes/test-code-generation/run'
data = {
    'process_title': '15_haziran',
    'environment_session_id': '16f91ead-b607-43e2-96a2-a74d0d4a3543',
    'model': 'llama3.2:3b',
    'environment_name': 'Test_LLM_Request_Check',
    'output_format': 'JSON',
    'session_id': 'test-llm-check-001'
}
files = {'files': ('test.py', open('test_sample_calculator.py', 'rb'), 'text/x-python')}

print('Sending Test Code Generation request...')
print(f'Model: {data["model"]}')
print('This should generate test codes for available test cases.')
print('Watch the backend terminal for LLM request logs...')
print()

try:
    response = requests.post(url, data=data, files=files, timeout=180)
    print(f'Status: {response.status_code}')
    
    if response.status_code == 200:
        result = response.json()
        print(f'Success: {result.get("success")}')
        if result.get('success'):
            print(f'Generated: {result.get("generated_count")}/{result.get("total_test_cases")}')
            print(f'Failed: {result.get("failed_count")}')
        else:
            print(f'Error: {result.get("error")}')
    else:
        print(f'Error Response: {response.text[:500]}')
except requests.Timeout:
    print('Request timed out after 180 seconds')
    print('Check backend logs to see if LLM requests were sent')
except Exception as e:
    print(f'Exception: {type(e).__name__}: {str(e)}')
