"""
Test MongoDB Aggregation Pipeline for Test Code Generation Service
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from pymongo import MongoClient
import json
from datetime import datetime

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['stlc_database']
collection = db['session_history']

def test_aggregation_pipeline():
    """Test the exact aggregation pipeline used in test_code_generation_service"""
    print("=== Testing Aggregation Pipeline ===")
    
    # Exact pipeline from the service
    pipeline = [
        {"$match": {"step": "environment_setup"}},
        {
            "$project": {
                "session_id": 1,
                "timestamp": 1,
                "setup_result": 1,
                "files_analyzed": 1,
                "environment_name": 1,
                "process_name": 1
            }
        },
        {"$sort": {"timestamp": -1}}
    ]
    
    print("Pipeline:")
    print(json.dumps(pipeline, indent=2))
    print()
    
    results = list(collection.aggregate(pipeline))
    
    print(f"Found {len(results)} results from aggregation:")
    
    for i, result in enumerate(results[:5], 1):
        print(f"\n--- Result {i} ---")
        print(f"Session ID: {result.get('session_id', 'N/A')}")
        print(f"Timestamp: {result.get('timestamp', 'N/A')}")
        print(f"Environment Name: {result.get('environment_name', 'NOT IN PROJECTION')}")
        print(f"Process Name: {result.get('process_name', 'NOT IN PROJECTION')}")
        
        setup_result = result.get('setup_result', {})
        if isinstance(setup_result, dict) and 'language' in setup_result:
            print(f"Setup Language: {setup_result.get('language', 'N/A')}")
        elif isinstance(setup_result, dict) and 'setup' in setup_result:
            print("Setup result is in string format, needs parsing")
        else:
            print("Setup result structure unknown")
    
    print(f"\n... showing only first 5 of {len(results)} results")

def test_simple_find():
    """Test simple find with environment_name"""
    print("\n=== Testing Simple Find with Environment Name ===")
    
    query = {"step": "environment_setup", "environment_name": {"$exists": True}}
    records = list(collection.find(query).sort("timestamp", -1))
    
    print(f"Records with environment_name: {len(records)}")
    
    for i, record in enumerate(records[:3], 1):
        print(f"\n--- Record {i} ---")
        print(f"Environment Name: {record.get('environment_name', 'N/A')}")
        print(f"Process Name: {record.get('process_name', 'N/A')}")
        print(f"Timestamp: {record.get('timestamp', 'N/A')}")

if __name__ == "__main__":
    try:
        test_aggregation_pipeline()
        test_simple_find()
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        client.close()