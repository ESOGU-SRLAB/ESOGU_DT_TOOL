import requests
import json

url = 'http://localhost:8000/api/processes/test-code-generation/run'
data = {
    'process_title': '15_haziran',
    'environment_session_id': '16f91ead-b607-43e2-96a2-a74d0d4a3543',
    'model': 'openai/gpt-oss-20b',
    'environment_name': 'Test_GPT_OSS_20B_Final',
    'output_format': 'JSON',
    'session_id': 'test-gpt-oss-final-001'
}
files = {'files': ('test.py', open('test_sample_calculator.py', 'rb'), 'text/x-python')}

print('Testing GPT OSS 20B with Test Code Generation...')
print(f'Model: {data["model"]}')
print('Note: This will take longer due to model size (~70 seconds per test case)')
print('Expected time: ~15 minutes for 13 test cases')
print()

try:
    response = requests.post(url, data=data, files=files, timeout=1200)  # 20 minutes timeout
    print(f'Status: {response.status_code}')
    
    if response.status_code == 200:
        result = response.json()
        print(f'Success: {result.get("success")}')
        if result.get('success'):
            print(f'Generated: {result.get("generated_count")}/{result.get("total_test_cases")}')
            print(f'Failed: {result.get("failed_count")}')
            print(f'Model Used: {result.get("model_name")}')
        else:
            print(f'Error: {result.get("error")}')
    else:
        print(f'Error Response: {response.text[:500]}')
except requests.Timeout:
    print('Request timed out after 20 minutes')
except Exception as e:
    print(f'Exception: {type(e).__name__}: {str(e)}')
