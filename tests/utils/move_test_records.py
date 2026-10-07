"""
Move test records from stlc_database to stlc_database
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from pymongo import MongoClient
import json
from datetime import datetime

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')

# Source and destination databases
source_db = client['stlc_database']
dest_db = client['stlc_database']

source_collection = source_db['session_history']
dest_collection = dest_db['session_history']

def move_environment_setup_records():
    """Move environment setup records from stlc_database to stlc_database"""
    print("=== Moving Environment Setup Records ===")
    
    # Get all environment setup records from source
    query = {"step": "environment_setup"}
    source_records = list(source_collection.find(query))
    
    print(f"Found {len(source_records)} environment setup records in stlc_database")
    
    if len(source_records) == 0:
        print("No records to move!")
        return
    
    # Check if records already exist in destination
    existing_session_ids = set()
    for record in dest_collection.find({"step": "environment_setup"}):
        existing_session_ids.add(record.get("session_id"))
    
    print(f"Found {len(existing_session_ids)} existing records in stlc_database")
    
    # Insert records that don't exist in destination
    new_records = []
    for record in source_records:
        session_id = record.get("session_id")
        if session_id not in existing_session_ids:
            # Remove _id to let MongoDB generate new one
            record_copy = record.copy()
            if '_id' in record_copy:
                del record_copy['_id']
            new_records.append(record_copy)
    
    if len(new_records) > 0:
        result = dest_collection.insert_many(new_records)
        print(f"Inserted {len(result.inserted_ids)} new records into stlc_database")
        
        # Show inserted records
        for i, record in enumerate(new_records, 1):
            env_name = record.get('environment_name', 'N/A')
            proc_name = record.get('process_name', 'N/A')
            print(f"  {i}. {env_name} - {proc_name}")
    else:
        print("All records already exist in destination database")

def verify_records():
    """Verify records in destination database"""
    print("\n=== Verification ===")
    
    dest_records = list(dest_collection.find({"step": "environment_setup"}))
    print(f"Total environment setup records in stlc_database: {len(dest_records)}")
    
    for i, record in enumerate(dest_records, 1):
        env_name = record.get('environment_name', 'N/A')
        proc_name = record.get('process_name', 'N/A')
        print(f"  {i}. {env_name} - {proc_name}")

if __name__ == "__main__":
    try:
        move_environment_setup_records()
        verify_records()
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        client.close()