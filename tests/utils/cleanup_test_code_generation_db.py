#!/usr/bin/env python3
"""
Test Code Generation Database Cleanup Script
-------------------------------------------
This script will:
1. Remove redundant fields
2. Unify field names 
3. Fix timestamp conflicts
4. Add missing UI fields
5. Ensure clean JSON output
"""

import pymongo
import json
from datetime import datetime
from pprint import pprint

def cleanup_test_code_generation_db():
    """Clean up test_code_generation documents according to specifications"""
    print("🔧 Starting Test Code Generation Database Cleanup...")
    print("=" * 60)
    
    try:
        # Connect to MongoDB
        client = pymongo.MongoClient("mongodb://localhost:27017")
        db = client["stlc_database"]
        session_collection = db["session_history"]
        
        # Find all documents with test_code_generation processes
        test_code_sessions = list(session_collection.find(
            {"processes.test_code_generation": {"$exists": True}}
        ))
        
        print(f"📋 Found {len(test_code_sessions)} test code generation sessions to clean")
        
        if not test_code_sessions:
            print("ℹ️ No test code generation sessions found to clean")
            return True
        
        cleaned_count = 0
        
        for session in test_code_sessions:
            session_id = session.get("session_id", "Unknown")
            print(f"\n🔍 Processing session: {session_id}")
            
            tcg_data = session.get("processes", {}).get("test_code_generation", {})
            
            if not tcg_data:
                print(f"   ⚠️ No test_code_generation data found, skipping")
                continue
            
            # Create clean structure
            cleaned_data = create_clean_structure(tcg_data, session_id)
            
            if cleaned_data:
                # Update the document
                update_result = session_collection.update_one(
                    {"session_id": session_id},
                    {"$set": {"processes.test_code_generation": cleaned_data}}
                )
                
                if update_result.modified_count > 0:
                    cleaned_count += 1
                    print(f"   ✅ Cleaned session {session_id}")
                else:
                    print(f"   ℹ️ No changes needed for session {session_id}")
            else:
                print(f"   ❌ Failed to clean session {session_id}")
        
        print(f"\n📊 Summary:")
        print(f"   Total sessions processed: {len(test_code_sessions)}")
        print(f"   Sessions cleaned: {cleaned_count}")
        
        # Verify cleanup by checking a sample
        if cleaned_count > 0:
            verify_cleanup(session_collection)
        
        return True
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False
    
    finally:
        try:
            client.close()
        except:
            pass

def create_clean_structure(tcg_data, session_id):
    """Create a clean, unified structure for test_code_generation process"""
    try:
        # Extract all relevant data first
        status = tcg_data.get("status", "completed")
        environment_name = tcg_data.get("environment_name", "Test Code Generation")
        
        # Handle timestamp - use the most recent one
        timestamp = get_unified_timestamp(tcg_data)
        
        # Extract input data with unified field names
        input_data = extract_unified_input(tcg_data)
        
        # Extract output data
        output_data = extract_unified_output(tcg_data)
        
        # Create the clean structure
        clean_structure = {
            "status": status,
            "timestamp": timestamp,
            "process_name": environment_name,  # Unified field name for UI display
            "model_name": input_data.get("model_name", "llama3.2:3b"),  # Unified field name
            "input": input_data,
            "output": output_data
        }
        
        print(f"   📝 Created clean structure with keys: {list(clean_structure.keys())}")
        return clean_structure
        
    except Exception as e:
        print(f"   ❌ Error creating clean structure: {e}")
        return None

def get_unified_timestamp(tcg_data):
    """Extract and unify timestamp fields"""
    # Priority order for timestamps
    timestamp_fields = ["timestamp", "created_at", "updated_at"]
    
    for field in timestamp_fields:
        if field in tcg_data and tcg_data[field]:
            return tcg_data[field]
    
    # If no timestamp found, use current time
    return datetime.now().isoformat()

def extract_unified_input(tcg_data):
    """Extract and unify input fields with consistent naming"""
    input_data = tcg_data.get("input", {})
    
    # Get process_title (from input or root level)
    process_title = input_data.get("process_title") or tcg_data.get("process_title", "")
    
    # Get model name with unified naming (prefer model_name over model)
    model_name = input_data.get("model_name") or input_data.get("model") or tcg_data.get("model_name") or tcg_data.get("model", "llama3.2:3b")
    
    # Get environment info
    environment_session_id = input_data.get("environment_session_id", "")
    
    # Extract other fields
    total_test_cases = input_data.get("total_test_cases", 0)
    custom_prompt = input_data.get("custom_prompt")
    output_format = input_data.get("output_format", "JSON")  # Add missing UI field
    
    unified_input = {
        "process_title": process_title,
        "model_name": model_name,  # Unified field name
        "environment_session_id": environment_session_id,
        "total_test_cases": total_test_cases,
        "output_format": output_format  # Ensure this UI field is present
    }
    
    # Add custom_prompt only if it exists
    if custom_prompt:
        unified_input["custom_prompt"] = custom_prompt
    
    return unified_input

def extract_unified_output(tcg_data):
    """Extract and unify output fields"""
    output_data = tcg_data.get("output", {})
    
    # Core output fields
    success = output_data.get("success", True)
    generated_tests = output_data.get("generated_tests", [])
    generated_count = output_data.get("generated_count", len(generated_tests))
    failed_count = output_data.get("failed_count", 0)
    
    # Environment info (keep only one copy)
    environment_info = output_data.get("environment_info", {})
    
    # Full data object (keep for backward compatibility)
    data = output_data.get("data", {})
    
    unified_output = {
        "success": success,
        "generated_tests": generated_tests,
        "generated_count": generated_count,
        "failed_count": failed_count,
        "environment_info": environment_info,
        "data": data
    }
    
    return unified_output

def verify_cleanup(session_collection):
    """Verify that the cleanup was successful"""
    print(f"\n🔍 Verifying cleanup results...")
    
    # Get a sample cleaned document
    sample = session_collection.find_one({"processes.test_code_generation": {"$exists": True}})
    
    if sample:
        tcg_data = sample.get("processes", {}).get("test_code_generation", {})
        
        print(f"✅ Sample cleaned document structure:")
        print(f"   Session ID: {sample.get('session_id', 'Unknown')}")
        print(f"   Top-level fields: {list(tcg_data.keys())}")
        
        input_data = tcg_data.get("input", {})
        print(f"   Input fields: {list(input_data.keys())}")
        
        output_data = tcg_data.get("output", {})
        print(f"   Output fields: {list(output_data.keys())}")
        
        # Check for UI field requirements
        ui_requirements = [
            ("process_title", input_data.get("process_title")),
            ("model_name", input_data.get("model_name")),
            ("environment_session_id", input_data.get("environment_session_id")),
            ("output_format", input_data.get("output_format"))
        ]
        
        print(f"\n🎯 UI Requirements Check:")
        for field_name, field_value in ui_requirements:
            status = "✅" if field_value else "❌"
            print(f"   {status} {field_name}: {field_value or 'MISSING'}")
        
        # Check for redundancy elimination
        print(f"\n🧹 Redundancy Check:")
        redundant_checks = [
            ("Multiple environment_info", "environment_info" in tcg_data and "environment_info" in input_data),
            ("Multiple model fields", "model" in input_data and "model_name" in input_data),
            ("Multiple timestamps", len([k for k in tcg_data.keys() if 'time' in k.lower()]) > 1)
        ]
        
        for check_name, is_redundant in redundant_checks:
            status = "❌" if is_redundant else "✅"
            print(f"   {status} {check_name}: {'FOUND' if is_redundant else 'CLEAN'}")
    
    else:
        print(f"❌ Could not find any cleaned documents for verification")

def create_model_schema_update():
    """Create a reference schema for future test_code_generation documents"""
    
    schema = {
        "process_type": "test_code_generation",
        "required_ui_fields": {
            "process_title": {"type": "string", "required": True, "description": "Test Code Generation Process Name from UI"},
            "model_name": {"type": "string", "required": True, "default": "llama3.2:3b", "description": "AI Model selection from UI"},
            "environment_session_id": {"type": "string", "required": True, "description": "Environment Setup selection from UI"},
            "output_format": {"type": "string", "required": True, "default": "JSON", "description": "Output Format selection from UI"}
        },
        "clean_structure": {
            "status": {"type": "string", "enum": ["completed", "failed", "in_progress"]},
            "timestamp": {"type": "string", "format": "ISO8601"},
            "process_name": {"type": "string", "description": "Display name for the process"},
            "model_name": {"type": "string", "description": "Unified field for AI model"},
            "input": {
                "process_title": "string",
                "model_name": "string", 
                "environment_session_id": "string",
                "output_format": "string",
                "total_test_cases": "number",
                "custom_prompt": "string (optional)"
            },
            "output": {
                "success": "boolean",
                "generated_tests": "array",
                "generated_count": "number",
                "failed_count": "number", 
                "environment_info": "object",
                "data": "object (backward compatibility)"
            }
        },
        "removed_redundancies": [
            "Duplicate environment_info fields",
            "Mixed model/model_name fields", 
            "Multiple timestamp fields",
            "Nested redundant process_title references"
        ]
    }
    
    print(f"\n📋 Reference Schema for Future Documents:")
    print(json.dumps(schema, indent=2))
    
    return schema

if __name__ == "__main__":
    print("🔧 Test Code Generation Database Cleanup")
    print("=" * 60)
    
    success = cleanup_test_code_generation_db()
    
    if success:
        print("\n✅ Cleanup completed successfully!")
        
        # Create reference schema
        create_model_schema_update()
        
        print(f"\n🎯 Next Steps:")
        print(f"   1. Update TestCodeGenerationService._save_test_generation_results() method")
        print(f"   2. Update frontend TestCodeGenerationForm to use unified field names")
        print(f"   3. Test the new structure with a sample generation")
        
    else:
        print("\n❌ Cleanup failed!")