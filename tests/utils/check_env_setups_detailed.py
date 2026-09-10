"""
Check database for all environment setup records including new ones
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

def check_environment_setups_detailed():
    """Environment setup kayıtlarını detaylı kontrol eder"""
    print("=== Detailed Environment Setup Records Check ===")
    
    # Environment setup kayıtlarını ara (timestamp'e göre sırala)
    query = {"step": "environment_setup"}
    records = list(collection.find(query).sort("timestamp", -1))
    
    print(f"Total environment setup records: {len(records)}")
    
    for i, record in enumerate(records, 1):
        print(f"\n--- Record {i} ---")
        print(f"ID: {record.get('_id', 'N/A')}")
        print(f"Session ID: {record.get('session_id', 'N/A')}")
        print(f"Timestamp: {record.get('timestamp', 'N/A')}")
        
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
        
        # İlk 5 kaydı göster
        if i >= 5:
            print(f"\n... showing only first 5 of {len(records)} records")
            break

if __name__ == "__main__":
    try:
        check_environment_setups_detailed()
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        client.close()