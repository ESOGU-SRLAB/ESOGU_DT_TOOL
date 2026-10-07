"""
Create test environment setup records
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from pymongo import MongoClient
import json
from datetime import datetime
import uuid

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['stlc_database']
collection = db['session_history']

def create_test_environment_setups():
    """Test environment setup kayıtları oluşturur"""
    print("=== Creating Test Environment Setup Records ===")
    
    test_records = [
        {
            "session_id": str(uuid.uuid4()),
            "step": "environment_setup",
            "timestamp": datetime.now().isoformat(),
            "environment_name": "Python Django API",
            "process_name": "User Authentication API",
            "setup_result": {
                "language": "Python",
                "framework": "Django",
                "testing_framework": "pytest",
                "database": "PostgreSQL",
                "dependencies": ["django", "djangorestframework", "pytest", "psycopg2"]
            },
            "files_analyzed": [
                {"name": "models.py", "type": "model"},
                {"name": "views.py", "type": "view"},
                {"name": "urls.py", "type": "routing"}
            ]
        },
        {
            "session_id": str(uuid.uuid4()),
            "step": "environment_setup",
            "timestamp": datetime.now().isoformat(),
            "environment_name": "React Frontend App",
            "process_name": "User Interface Components",
            "setup_result": {
                "language": "JavaScript",
                "framework": "React",
                "testing_framework": "Jest",
                "build_tool": "Vite",
                "dependencies": ["react", "react-dom", "axios", "tailwindcss"]
            },
            "files_analyzed": [
                {"name": "App.jsx", "type": "component"},
                {"name": "UserForm.jsx", "type": "component"},
                {"name": "api.js", "type": "service"}
            ]
        },
        {
            "session_id": str(uuid.uuid4()),
            "step": "environment_setup",
            "timestamp": datetime.now().isoformat(),
            "environment_name": "Java Spring Boot",
            "process_name": "REST API Service",
            "setup_result": {
                "language": "Java",
                "framework": "Spring Boot",
                "testing_framework": "JUnit",
                "build_tool": "Maven",
                "dependencies": ["spring-boot-starter-web", "spring-boot-starter-data-jpa", "junit"]
            },
            "files_analyzed": [
                {"name": "Controller.java", "type": "controller"},
                {"name": "Service.java", "type": "service"},
                {"name": "Repository.java", "type": "repository"}
            ]
        }
    ]
    
    # Kayıtları ekle
    for i, record in enumerate(test_records, 1):
        try:
            result = collection.insert_one(record)
            print(f"Created record {i}: {record['environment_name']} (ID: {result.inserted_id})")
        except Exception as e:
            print(f"Failed to create record {i}: {str(e)}")
    
    print(f"\n{len(test_records)} test records created successfully!")
    
    # Kayıtları doğrula
    print("\n=== Verification ===")
    env_setups = list(collection.find({"step": "environment_setup"}))
    print(f"Total environment setup records: {len(env_setups)}")
    
    for setup in env_setups:
        print(f"  - {setup['environment_name']} ({setup['setup_result']['language']})")

if __name__ == "__main__":
    try:
        create_test_environment_setups()
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        client.close()