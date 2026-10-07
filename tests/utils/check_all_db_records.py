"""
Check all database records
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from pymongo import MongoClient
import json

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['stlc_database']
collection = db['session_history']

def check_all_records():
    """Tüm kayıtları kontrol eder"""
    print("=== All Database Records Check ===")
    
    # Tüm kayıtları getir
    records = list(collection.find({}))
    
    print(f"Total records found: {len(records)}")
    
    # Step'lere göre grupla
    steps = {}
    for record in records:
        step = record.get('step', 'unknown')
        if step not in steps:
            steps[step] = []
        steps[step].append(record)
    
    print(f"\nRecords by step:")
    for step, step_records in steps.items():
        print(f"  {step}: {len(step_records)} records")
    
    # İlk birkaç kaydı detaylı göster
    print(f"\n=== First 3 Records Details ===")
    for i, record in enumerate(records[:3], 1):
        print(f"\n--- Record {i} ---")
        print(f"ID: {record.get('_id', 'N/A')}")
        print(f"Session ID: {record.get('session_id', 'N/A')}")
        print(f"Step: {record.get('step', 'N/A')}")
        print(f"Timestamp: {record.get('timestamp', 'N/A')}")
        
        # Environment name kontrolü
        if 'environment_name' in record:
            print(f"Environment Name: {record['environment_name']}")
        if 'process_name' in record:
            print(f"Process Name: {record['process_name']}")

if __name__ == "__main__":
    try:
        check_all_records()
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        client.close()