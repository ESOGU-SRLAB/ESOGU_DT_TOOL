import requests
import json

# Test Code Generation test
url = 'http://localhost:8000/api/processes/test-code-generation/run'

# Prepare form data
data = {
    'process_title': '15_haziran',
    'environment_session_id': '16f91ead-b607-43e2-96a2-a74d0d4a3543',
    'model': 'llama3.2:3b',
    'environment_name': 'Test_Calculator_llama3.2_3b',
    'output_format': 'JSON',
    'session_id': 'test-llama-session-001'
}

# Prepare file
files = {
    'files': ('calculator.py', open('test_sample_calculator.py', 'rb'), 'text/x-python')
}

print('Testing Test Code Generation with llama3.2:3b...')
print(f'Request data: {json.dumps(data, indent=2)}')

try:
    response = requests.post(url, data=data, files=files, timeout=300)
    print(f'Status Code: {response.status_code}')
    
    if response.status_code == 200:
        result = response.json()
        print(f'Success: {result.get("success", False)}')
        print(f'Process Title: {result.get("process_title", "N/A")}')
        print(f'Total Test Cases: {result.get("total_test_cases", 0)}')
        print(f'Generated Count: {result.get("generated_count", 0)}')
        print(f'Failed Count: {result.get("failed_count", 0)}')
        print(f'Model: {result.get("model_name", "N/A")}')
        
        # Show first generated test
        if result.get("generated_tests"):
            first_test = result["generated_tests"][0]
            print(f'\nFirst Test:')
            print(f'  Title: {first_test.get("title", "N/A")}')
            print(f'  Status: {first_test.get("status", "N/A")}')
            if first_test.get("code"):
                print(f'  Code Length: {len(first_test["code"])} chars')
    else:
        print(f'Error: {response.text}')
except Exception as e:
    print(f'Exception: {str(e)}')
