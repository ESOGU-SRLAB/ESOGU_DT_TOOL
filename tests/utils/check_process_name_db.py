import pymongo
import json
from datetime import datetime

def check_process_name_in_mongodb():
    """Check if process name is saved correctly in MongoDB"""
    print("🔍 Checking MongoDB for process name data...")
    
    try:
        # Connect to MongoDB
        client = pymongo.MongoClient("mongodb://localhost:27017")
        db = client["stlc_management"]  # Default database name
        
        # Check session_history collection for test_case_optimization with process_name
        session_collection = db["session_history"]
        
        print(f"📊 Total session documents: {session_collection.count_documents({})}")
        
        # Get test case optimization sessions with process_name
        optimization_sessions = list(session_collection.find(
            {"processes.test_case_optimization": {"$exists": True}}
        ).sort("timestamp", -1))
        
        print(f"\n📋 Test case optimization sessions: {len(optimization_sessions)}")
        
        for i, session in enumerate(optimization_sessions, 1):
            session_data = session.get("processes", {}).get("test_case_optimization", {})
            print(f"\n{i}. Session ID: {session.get('session_id', 'Unknown')}")
            print(f"   Process Name: {session_data.get('process_name', 'Not specified')}")
            print(f"   Model: {session_data.get('used_model', 'Not specified')}")
            print(f"   Process titles: {session_data.get('process_titles', [])}")
            print(f"   Process count: {session_data.get('process_count', 0)}")
            print(f"   Has output: {'Yes' if session_data.get('output') else 'No'}")
            
            # Check if process_name is saved correctly
            if session_data.get('process_name'):
                print(f"   ✅ Process name is saved correctly!")
            else:
                print(f"   ❌ Process name is missing!")
        
        # Test aggregation for process names
        print(f"\n🔍 Testing aggregation for process names...")
        pipeline = [
            {"$match": {"processes.test_case_optimization": {"$exists": True}}},
            {"$project": {"process_name": "$processes.test_case_optimization.process_name"}},
            {"$match": {"process_name": {"$exists": True, "$ne": ""}}},
            {"$group": {"_id": "$process_name", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        
        results = list(session_collection.aggregate(pipeline))
        print(f"Found {len(results)} unique process names:")
        for result in results:
            print(f"  - {result['_id']}: {result['count']} optimization(s)")
            
        return True
        
    except Exception as e:
        print(f"❌ Error checking MongoDB: {e}")
        return False
    
    finally:
        try:
            client.close()
        except:
            pass

if __name__ == "__main__":
    print("🔍 MongoDB Process Name Check")
    print("=" * 40)
    
    success = check_process_name_in_mongodb()
    
    if success:
        print("\n✅ Database check completed successfully!")
    else:
        print("\n❌ Database check failed!")
