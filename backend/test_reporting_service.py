"""
Test script for Test Reporting functionality
"""
import asyncio
import sys
sys.path.append('.')

from services.test_reporting_service import TestReportingService

async def test_reporting_service_func():
    """Test the reporting service functions"""
    print("🧪 Testing Test Reporting Service\n")
    
    # Create service instance
    service = TestReportingService()
    
    # Test 1: Fetch available sessions
    print("1️⃣ Testing fetch_available_sessions...")
    try:
        sessions = await service.fetch_available_sessions()
        print(f"   ✅ Found {len(sessions)} sessions")
        
        if sessions:
            print(f"\n   📋 First session preview:")
            session = sessions[0]
            print(f"      - Session ID: {session.get('session_id', 'N/A')}")
            print(f"      - Timestamp: {session.get('timestamp', 'N/A')}")
            print(f"      - Processes: {list(session.get('processes', {}).keys())}")
        else:
            print(f"   ℹ️  No sessions found in database")
            print(f"   💡 Run some STLC processes first to generate test data")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False
    
    # Test 2: Test chunking
    print(f"\n2️⃣ Testing chunking algorithm...")
    test_data = {
        "output": {
            "test_scenarios": [
                {"id": i, "name": f"Scenario {i}", "description": "Test scenario"}
                for i in range(45)
            ]
        }
    }
    
    try:
        chunks = service.create_chunks("test_scenario_generation", test_data)
        print(f"   ✅ Created {len(chunks)} chunks from 45 scenarios")
        print(f"   📊 Chunk size configuration: {service.CHUNK_SIZES.get('test_scenario_generation', 'default')}")
        
        if chunks:
            print(f"\n   📦 First chunk preview:")
            chunk = chunks[0]
            print(f"      - Chunk index: {chunk.get('chunk_index', 'N/A')}")
            print(f"      - Total chunks: {chunk.get('total_chunks', 'N/A')}")
            print(f"      - Data type: {chunk.get('data_type', 'N/A')}")
            print(f"      - Item count: {chunk.get('item_count', 'N/A')}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False
    
    # Test 3: Test intermediate prompt generation
    print(f"\n3️⃣ Testing intermediate prompt generation...")
    try:
        if chunks:
            prompt = service.create_intermediate_prompt(chunks[0], "detailed")
            prompt_preview = prompt[:200] + "..." if len(prompt) > 200 else prompt
            print(f"   ✅ Generated prompt ({len(prompt)} chars)")
            print(f"\n   📝 Prompt preview:")
            print(f"   {prompt_preview}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False
    
    # Test 4: Test final synthesis prompt
    print(f"\n4️⃣ Testing final synthesis prompt generation...")
    try:
        intermediate_summaries = [
            {
                "process_name": "test_scenario_generation",
                "chunk_index": 0,
                "total_chunks": 2,
                "summary": "Test summary for scenarios"
            },
            {
                "process_name": "test_case_generation",
                "chunk_index": 0,
                "total_chunks": 1,
                "summary": "Test summary for test cases"
            }
        ]
        
        session_metadata = {
            "session_id": "test_session_001",
            "session_timestamp": "2025-11-07T10:00:00",
            "process_name": "test_project"
        }
        
        final_prompt = service.create_final_synthesis_prompt(
            intermediate_summaries,
            session_metadata,
            "detailed"
        )
        
        prompt_preview = final_prompt[:300] + "..." if len(final_prompt) > 300 else final_prompt
        print(f"   ✅ Generated final synthesis prompt ({len(final_prompt)} chars)")
        print(f"\n   📝 Final prompt preview:")
        print(f"   {prompt_preview}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False
    
    print(f"\n✅ All tests passed!")
    return True

if __name__ == "__main__":
    result = asyncio.run(test_reporting_service_func())
    sys.exit(0 if result else 1)
