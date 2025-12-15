import requests
import json

url = "http://localhost:8001/jsonrpc"

# Test JSON-RPC request
rpc_request = {
    "jsonrpc": "2.0",
    "method": "executeTest",
    "params": {
        "test_code": "print('Hello from test')",
        "provider": "lm_studio",
        "model_name": "llama3.2:3b"
    },
    "id": "test-123"
}

print("=" * 80)
print("Testing MCP Server JSON-RPC Endpoint")
print("=" * 80)
print(f"URL: {url}")
print(f"Request:")
print(json.dumps(rpc_request, indent=2))
print("-" * 80)

try:
    response = requests.post(url, json=rpc_request, timeout=30)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print("-" * 80)
    print("Response:")
    print(json.dumps(response.json(), indent=2))
except requests.exceptions.RequestException as e:
    print(f"Request Error: {e}")
except Exception as e:
    print(f"Unexpected Error: {e}")
    print(f"Raw Response: {response.text if 'response' in locals() else 'N/A'}")

print("=" * 80)
