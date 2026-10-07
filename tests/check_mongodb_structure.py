from pymongo import MongoClient
import json

client = MongoClient('mongodb://localhost:27017')
db = client['stlc_manager']

# Find test case generation document with E2E Test process
doc = db.session_history.find_one(
    {'processes.test_case_generation.selected_process_title': 'E2E Test - Robot2 UR10e Control'},
    sort=[('_id', -1)]
)

if doc:
    print("✅ Found document!")
    print(f"Session ID: {doc.get('session_id')}")
    print(f"Process Title (root): {doc.get('process_title')}")
    
    tc_gen = doc.get('processes', {}).get('test_case_generation', {})
    print(f"\nTest Case Generation Info:")
    print(f"  selected_process_title: {tc_gen.get('selected_process_title')}")
    print(f"  status: {tc_gen.get('status')}")
    
    output = tc_gen.get('output', {})
    test_cases = output.get('test_cases', [])
    print(f"\n  Number of test cases in output: {len(test_cases)}")
    if test_cases:
        print(f"  First test case ID: {test_cases[0].get('test_case_id')}")
        print(f"  First test case title: {test_cases[0].get('title')}")
else:
    print("❌ No document found with test_case_generation.selected_process_title = 'E2E Test - Robot2 UR10e Control'")
    
    # Try finding any recent test case generation
    any_doc = db.session_history.find_one(
        {'processes.test_case_generation': {'$exists': True}},
        sort=[('_id', -1)]
    )
    
    if any_doc:
        print("\n📝 Found recent test case generation document:")
        tc_gen = any_doc.get('processes', {}).get('test_case_generation', {})
        print(f"  selected_process_title: {tc_gen.get('selected_process_title')}")
        print(f"  All fields: {list(tc_gen.keys())}")

client.close()
