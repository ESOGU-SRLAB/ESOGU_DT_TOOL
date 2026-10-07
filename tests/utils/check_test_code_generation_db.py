#!/usr/bin/env python3
"""
Check Test Code Generation Database Structure
"""

import pymongo
import json
from datetime import datetime
from pprint import pprint

def check_test_code_generation_db():
    """Check the current structure of test_code_generation processes in MongoDB"""
    print("🔍 Checking Test Code Generation Database Structure...")
    print("=" * 60)
    
    try:
        # Connect to MongoDB
        client = pymongo.MongoClient("mongodb://localhost:27017")
        db = client["stlc_database"]
        
        # Check session_history collection for test_code_generation processes
        session_collection = db["session_history"]
        
        print(f"📊 Total session documents: {session_collection.count_documents({})}")
        
        # Find documents with test_code_generation processes
        test_code_gen_sessions = list(session_collection.find(
            {"processes.test_code_generation": {"$exists": True}}
        ).sort("timestamp", -1))
        
        print(f"\n📋 Test code generation sessions found: {len(test_code_gen_sessions)}")
        
        if test_code_gen_sessions:
            print("\n🔍 Analyzing test_code_generation structure:")
            
            for i, session in enumerate(test_code_gen_sessions[:3], 1):  # Show first 3
                print(f"\n--- Session {i} ---")
                session_id = session.get("session_id", "Unknown")
                timestamp = session.get("timestamp", "Unknown")
                print(f"Session ID: {session_id}")
                print(f"Timestamp: {timestamp}")
                
                # Get test_code_generation data
                processes = session.get("processes", {})
                tcg_data = processes.get("test_code_generation", {})
                
                print(f"Test Code Generation fields: {list(tcg_data.keys())}")
                
                # Check for redundant/duplicate fields
                redundant_fields = []
                
                # Look for common duplicated fields
                if "environment_info" in tcg_data and "input" in tcg_data and "environment_info" in tcg_data.get("input", {}):
                    redundant_fields.append("environment_info (duplicated in input and root)")
                
                if "model" in tcg_data and "model_name" in tcg_data:
                    redundant_fields.append("model vs model_name (inconsistent naming)")
                
                if "timestamp" in tcg_data and "created_at" in tcg_data:
                    redundant_fields.append("timestamp vs created_at (duplicate timestamps)")
                
                if redundant_fields:
                    print(f"⚠️ Redundant fields detected:")
                    for field in redundant_fields:
                        print(f"   - {field}")
                
                # Show full structure for first document
                if i == 1:
                    print(f"\n📋 Full test_code_generation structure:")
                    print(json.dumps(tcg_data, indent=2, default=str))
        
        # Check separate test_code_generation_results collection
        tcg_results_collection = db["test_code_generation_results"]
        tcg_results_count = tcg_results_collection.count_documents({})
        print(f"\n📊 test_code_generation_results collection: {tcg_results_count} documents")
        
        if tcg_results_count > 0:
            sample_result = tcg_results_collection.find_one()
            print(f"\n📋 Sample test_code_generation_results structure:")
            print(f"Fields: {list(sample_result.keys())}")
        
        # Analyze field inconsistencies across all documents
        print(f"\n🔍 Field Analysis Across All Documents:")
        
        all_fields = set()
        field_variations = {}
        
        for session in test_code_gen_sessions:
            tcg_data = session.get("processes", {}).get("test_code_generation", {})
            session_fields = set(tcg_data.keys())
            all_fields.update(session_fields)
            
            # Check for field naming variations
            for field in session_fields:
                if field not in field_variations:
                    field_variations[field] = 0
                field_variations[field] += 1
        
        print(f"All unique fields found: {sorted(all_fields)}")
        print(f"\nField usage frequency:")
        for field, count in sorted(field_variations.items()):
            percentage = (count / len(test_code_gen_sessions)) * 100 if test_code_gen_sessions else 0
            print(f"  {field}: {count} times ({percentage:.1f}%)")
        
        # Identify potential issues
        print(f"\n⚠️ Potential Issues:")
        
        # Check for inconsistent model field naming
        model_fields = [f for f in all_fields if 'model' in f.lower()]
        if len(model_fields) > 1:
            print(f"   - Multiple model field variants: {model_fields}")
        
        # Check for timestamp fields
        timestamp_fields = [f for f in all_fields if 'time' in f.lower() or f in ['created_at', 'updated_at']]
        if len(timestamp_fields) > 1:
            print(f"   - Multiple timestamp fields: {timestamp_fields}")
        
        # Check for environment fields  
        env_fields = [f for f in all_fields if 'environment' in f.lower()]
        if len(env_fields) > 1:
            print(f"   - Multiple environment fields: {env_fields}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return False
    
    finally:
        try:
            client.close()
        except:
            pass

if __name__ == "__main__":
    print("🔍 Test Code Generation Database Structure Check")
    print("=" * 60)
    
    success = check_test_code_generation_db()
    
    if success:
        print("\n✅ Database check completed!")
    else:
        print("\n❌ Database check failed!")