"""
Test Environment Setups Database Check
Environment setup kayıtlarını kontrol eder
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

def check_environment_setups():
    """Environment setup kayıtlarını kontrol eder"""
    print("=== Environment Setup Records Check ===")
    
    # Environment setup kayıtlarını ara
    query = {"step": "environment_setup"}
    records = list(collection.find(query))
    
    print(f"Found {len(records)} environment setup records")
    
    for i, record in enumerate(records, 1):
        print(f"\n--- Record {i} ---")
        print(f"Session ID: {record.get('session_id', 'N/A')}")
        print(f"Timestamp: {record.get('timestamp', 'N/A')}")
        print(f"Step: {record.get('step', 'N/A')}")
        
        # Environment name kontrolü
        environment_name = record.get('environment_name', 'NOT SET')
        process_name = record.get('process_name', 'NOT SET')
        
        print(f"Environment Name: {environment_name}")
        print(f"Process Name: {process_name}")
        
        # Setup result kontrolü
        setup_result = record.get('setup_result', {})
        if isinstance(setup_result, dict):
            language = setup_result.get('language', 'Unknown')
            framework = setup_result.get('framework', 'Unknown')
            print(f"Language: {language}")
            print(f"Framework: {framework}")
        
        # Files analyzed kontrolü
        files_analyzed = record.get('files_analyzed', [])
        print(f"Files Analyzed: {len(files_analyzed)} files")

def update_records_with_environment_names():
    """Mevcut kayıtlara environment_name ekler (test amaçlı)"""
    print("\n=== Adding Environment Names to Existing Records ===")
    
    query = {"step": "environment_setup", "environment_name": {"$exists": False}}
    records = list(collection.find(query))
    
    print(f"Found {len(records)} records without environment_name")
    
    for i, record in enumerate(records, 1):
        session_id = record.get('session_id', f'unknown_{i}')
        setup_result = record.get('setup_result', {})
        language = setup_result.get('language', 'Unknown')
        
        # Test environment name oluştur
        environment_name = f"Environment_{language}_{i}"
        process_name = f"Process_{session_id}"
        
        # Update record
        update_result = collection.update_one(
            {"_id": record["_id"]},
            {
                "$set": {
                    "environment_name": environment_name,
                    "process_name": process_name
                }
            }
        )
        
        if update_result.modified_count > 0:
            print(f"Updated record {i}: {environment_name}")
        else:
            print(f"Failed to update record {i}")

if __name__ == "__main__":
    try:
        check_environment_setups()
        
        # Kullanıcı onayı ile kayıtları güncelle
        response = input("\nDo you want to add environment_name to existing records? (y/n): ")
        if response.lower() == 'y':
            update_records_with_environment_names()
            print("\n=== Updated Records Check ===")
            check_environment_setups()
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        client.close()