import requests
import json

r = requests.get('http://localhost:8000/openapi.json')
data = r.json()
paths = data.get('paths', {})

print("Test Execution Routes:")
print("-" * 80)
for path in paths.keys():
    if 'test-execution' in path or 'test_execution' in path:
        methods = list(paths[path].keys())
        print(f"{path} - Methods: {', '.join(methods)}")

print("\n" + "=" * 80)
print("All Routes:")
print("=" * 80)
for path in sorted(paths.keys()):
    methods = list(paths[path].keys())
    print(f"{path} - Methods: {', '.join(methods)}")
