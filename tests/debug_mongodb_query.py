#!/usr/bin/env python3
"""Debug MongoDB query for parallel execution"""

from pymongo import MongoClient
import json

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "stlc_manager"
PROCESS_NAME = "E2E Test - Remote Execution"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db["session_history"]

# Find sessions with test code generation for this process
query = {"processes.test_code_generation.process_name": PROCESS_NAME}
print(f"🔍 Query: {json.dumps(query, indent=2)}")
print()

cursor = collection.find(query).limit(5)
docs = list(cursor)

print(f"📊 Found {len(docs)} documents")
print()

for i, doc in enumerate(docs, 1):
    session_id = doc.get("session_id")
    tcg = doc.get("processes", {}).get("test_code_generation", {})
    output = tcg.get("output", {})
    generated_tests = output.get("generated_tests", [])
    
    print(f"📄 Document {i}:")
    print(f"   session_id: {session_id}")
    print(f"   test_count: {len(generated_tests)}")
    
    if generated_tests:
        print(f"   Test IDs:")
        for test in generated_tests[:3]:  # Show first 3
            test_id = test.get("test_id")
            test_name = test.get("test_name")
            print(f"     - {test_id}: {test_name}")
    print()

client.close()
