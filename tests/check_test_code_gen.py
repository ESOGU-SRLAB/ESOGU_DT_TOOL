from pymongo import MongoClient
import json

client = MongoClient('mongodb://localhost:27017')
db = client['stlc_manager']

# Find test code generation document with E2E Test Environment
doc = db.session_history.find_one(
    {'processes.test_code_generation.process_name': 'E2E Test Environment'},
    sort=[('_id', -1)]
)

if doc:
    print("✅ Found document!")
    print(f"Session ID: {doc.get('session_id')}")
    
    tcg = doc.get('processes', {}).get('test_code_generation', {})
    print(f"\nTest Code Generation Info:")
    print(f"  process_name: {tcg.get('process_name')}")
    print(f"  status: {tcg.get('status')}")
    
    output = tcg.get('output', {})
    generated_tests = output.get('generated_tests', [])
    print(f"\n  Number of generated_tests: {len(generated_tests)}")
    
    if generated_tests:
        first_test = generated_tests[0]
        print(f"\n  First test fields: {list(first_test.keys())}")
        print(f"  First test sample:")
        for key, value in list(first_test.items())[:10]:  # Show first 10 fields
            if key == 'code':
                print(f"    {key}: <code truncated, length={len(str(value))}>")
            else:
                print(f"    {key}: {str(value)[:100]}")
else:
    print("❌ No document found with process_name = 'E2E Test Environment'")

client.close()
