import pymongo
import json
from datetime import datetime

def check_optimization_results():
    """Check if optimization results are saved with model information"""
    print("🔍 Checking MongoDB for optimization results with model info...")
    
    try:
        # Connect to MongoDB
        client = pymongo.MongoClient("mongodb://localhost:27017")
        db = client["stlc_management"]  # Default database name
        
        # Check test_case_optimizations collection
        optimization_collection = db["test_case_optimizations"]
        
        print(f"📊 Total optimization documents: {optimization_collection.count_documents({})}")
        
        # Get recent optimization results
        recent_results = list(optimization_collection.find().sort("created_at", -1).limit(5))
        
        if recent_results:
            print(f"\n📋 Recent optimization results:")
            for i, result in enumerate(recent_results, 1):
                print(f"\n{i}. Process: {result.get('process_title', 'Unknown')}")
                print(f"   Model: {result.get('selected_model', 'Not specified')}")
                print(f"   Created: {result.get('created_at', 'Unknown')}")
                
                # Check if optimization results contain data
                opt_results = result.get('optimization_results', {})
                unique_cases = opt_results.get('unique_test_cases', [])
                similar_cases = opt_results.get('similar_test_cases', [])
                
                print(f"   Unique test cases: {len(unique_cases)}")
                print(f"   Similar test cases: {len(similar_cases)}")
        
        # Check session_history collection for model info
        session_collection = db["session_history"]
        
        # Find test case optimization sessions
        optimization_sessions = list(session_collection.find(
            {"processes.test_case_optimization": {"$exists": True}}
        ).sort("timestamp", -1).limit(3))
        
        print(f"\n📝 Test case optimization sessions: {len(optimization_sessions)}")
        
        for i, session in enumerate(optimization_sessions, 1):
            session_data = session.get("processes", {}).get("test_case_optimization", {})
            print(f"\n{i}. Session ID: {session.get('session_id', 'Unknown')}")
            print(f"   Model: {session_data.get('used_model', 'Not specified')}")
            print(f"   Process titles: {session_data.get('process_titles', [])}")
            print(f"   Process count: {session_data.get('process_count', 0)}")
            print(f"   Timestamp: {session.get('timestamp', 'Unknown')}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error checking optimization results: {e}")
        return False
    
    finally:
        try:
            client.close()
        except:
            pass

if __name__ == "__main__":
    print("🔍 MongoDB Optimization Results Check")
    print("=" * 50)
    
    success = check_optimization_results()
    
    if success:
        print("\n✅ Database check completed successfully!")
    else:
        print("\n❌ Database check failed!")
