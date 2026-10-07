from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017')
db = client['stlc_manager']

# Find latest test case generation document
doc = db.session_history.find_one(
    {'processes.test_case_generation': {'$exists': True}},
    sort=[('_id', -1)]
)

if doc:
    print(f"Process Title: {doc.get('process_title')}")
    test_cases = doc.get('processes', {}).get('test_case_generation', {}).get('output', {}).get('test_cases', [])
    print(f"Number of test cases: {len(test_cases)}")
else:
    print("No test case generation found")

client.close()
