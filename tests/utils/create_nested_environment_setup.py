"""
Create test environment setup with nested processes structure
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from pymongo import MongoClient
from datetime import datetime
import uuid

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['stlc_database']
collection = db['session_history']

def create_nested_environment_setup():
    """Create environment setup record with nested processes structure"""
    print("=== Creating Environment Setup with Nested Structure ===")
    
    session_id = str(uuid.uuid4())
    timestamp = datetime.now()
    
    # Nested processes structure
    record = {
        "session_id": session_id,
        "created_at": timestamp,
        "processes": {
            "environment_setup": {
                "output": {
                    "files": "Files analyzed:\napp.py\nrequirements.txt",
                    "setup": """
{
  "environment_setup": {
    "language": "Python",
    "language_version": "3.10",
    "framework": "FastAPI",
    "operating_system": "Ubuntu 22.04",
    "dependencies": [
      "fastapi>=0.104.1",
      "uvicorn[standard]>=0.24.0",
      "python-multipart>=0.0.6"
    ],
    "database": "MongoDB",
    "required_tools": [
      "pip",
      "virtualenv",
      "docker"
    ],
    "installation_notes": "Create virtual environment, install dependencies with pip, configure MongoDB connection"
  }
}
"""
                },
                "edited_prompt": False,
                "used_prompt": "Environment setup analysis prompt...",
                "used_model": "llama-3.2-3b-instruct",
                "timestamp": timestamp,
                "environment_name": "FastAPI Backend Service"
            }
        }
    }
    
    try:
        result = collection.insert_one(record)
        print(f"✅ Created environment setup record with session_id: {session_id}")
        print(f"   Environment Name: FastAPI Backend Service")
        print(f"   Database ID: {result.inserted_id}")
        return session_id
    except Exception as e:
        print(f"❌ Error creating record: {str(e)}")
        return None

def verify_record(session_id):
    """Verify the created record"""
    print(f"\n=== Verifying Record ===")
    
    record = collection.find_one({"session_id": session_id})
    if record:
        print(f"✅ Record found in database")
        env_setup = record.get("processes", {}).get("environment_setup", {})
        print(f"   Environment Name: {env_setup.get('environment_name', 'N/A')}")
        print(f"   Timestamp: {env_setup.get('timestamp', 'N/A')}")
        print(f"   Used Model: {env_setup.get('used_model', 'N/A')}")
    else:
        print(f"❌ Record not found!")

if __name__ == "__main__":
    try:
        session_id = create_nested_environment_setup()
        if session_id:
            verify_record(session_id)
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        client.close()