import requests
import json

url = 'http://localhost:8000/api/processes/test-code-generation/run'
data = {
    'process_title': '15_haziran',
    'environment_session_id': '16f91ead-b607-43e2-96a2-a74d0d4a3543',
    'model': 'llama3.2:3b',
    'environment_name': 'Test_Quick_Check',
    'output_format': 'JSON',
    'session_id': 'test-check-001'
}
files = {'files': ('calc.py', open('test_sample_calculator.py', 'rb'), 'text/x-python')}

print('Testing Test Code Generation...')
try:
    response = requests.post(url, data=data, files=files, timeout=120)
    print(f'Status: {response.status_code}')
    if response.status_code == 200:
        result = response.json()
        print(f'Success: {result.get("success")}')
        if not result.get('success'):
            print(f'Error: {result.get("error")}')
        else:
            print(f'Generated: {result.get("generated_count")}/{result.get("total_test_cases")}')
            if result.get("generated_tests"):
                first = result["generated_tests"][0]
                print(f'\nFirst test: {first.get("title")}')
                print(f'Status: {first.get("status")}')
    else:
        print(f'Error Response: {response.text[:500]}')
except Exception as e:
    print(f'Exception: {type(e).__name__}: {str(e)}')
