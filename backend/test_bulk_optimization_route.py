import asyncio
import json
from services.test_case_optimization_service import TestCaseOptimizationService

# Test data
test_cases = [
    {
        "ScenarioID": "SC001",
        "TestCaseID": "TC001",
        "Title": "Login with valid credentials",
        "Description": "Test user login with correct username and password",
        "Objective": "Verify successful login"
    },
    {
        "ScenarioID": "SC001",
        "TestCaseID": "TC002",
        "Title": "Login with valid user",
        "Description": "Test user login with valid username and password",
        "Objective": "Verify login works correctly"
    },
    {
        "ScenarioID": "SC002",
        "TestCaseID": "TC003",
        "Title": "Logout functionality",
        "Description": "Test user logout",
        "Objective": "Verify logout works"
    }
]

async def test_bulk_vs_serial():
    """
    Test to compare bulk vs serial optimization behavior
    """
    service = TestCaseOptimizationService()
    
    print("\n" + "="*80)
    print("TESTING BULK OPTIMIZATION")
    print("="*80)
    
    # Test bulk optimization
    print("\n[1] Testing run_bulk_smart_selection...")
    print(f"   Input: {len(test_cases)} test cases")
    
    result_bulk = await service.run_bulk_smart_selection(
        selected_test_cases=test_cases,
        custom_prompt=None,
        selected_model="gemini-2.5-flash",
        api_key=None,  # Will use env var if needed
        process_id="test_bulk_001"
    )
    
    print(f"   Result: {result_bulk['success']}")
    if result_bulk['success']:
        print(f"   Unique test cases: {len(result_bulk['data']['unique_test_cases'])}")
        print(f"   Similar test cases: {len(result_bulk['data']['similar_test_cases'])}")
        print(f"   Comparison logs count: {len(result_bulk['data']['comparison_logs'])}")
        if result_bulk['data']['comparison_logs']:
            log = result_bulk['data']['comparison_logs'][0]
            print(f"   Processing type: {log.get('ProcessingType')}")
            print(f"   Optimization method: {log.get('OptimizationMethod')}")
    else:
        print(f"   Error: {result_bulk['message']}")
    
    print("\n" + "="*80)
    print("TESTING SERIAL OPTIMIZATION")
    print("="*80)
    
    # Test serial optimization
    print("\n[2] Testing run_smart_selection (serial)...")
    print(f"   Input: {len(test_cases)} test cases")
    
    result_serial = await service.run_smart_selection(
        selected_test_cases=test_cases,
        custom_prompt=None,
        selected_model="gemini-2.5-flash",
        api_key=None,
        process_id="test_serial_001"
    )
    
    print(f"   Result: {result_serial['success']}")
    if result_serial['success']:
        print(f"   Unique test cases: {len(result_serial['data']['unique_test_cases'])}")
        print(f"   Similar test cases: {len(result_serial['data']['similar_test_cases'])}")
        print(f"   Comparison logs count: {len(result_serial['data']['comparison_logs'])}")
        if result_serial['data']['comparison_logs']:
            # Serial should have multiple comparison logs (one per pair)
            print(f"   First log processing type: {result_serial['data']['comparison_logs'][0].get('ProcessingType', 'N/A')}")
    else:
        print(f"   Error: {result_serial['message']}")
    
    print("\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)
    
    if result_bulk['success'] and result_serial['success']:
        bulk_logs = len(result_bulk['data']['comparison_logs'])
        serial_logs = len(result_serial['data']['comparison_logs'])
        
        print(f"\n✓ Bulk optimization logs: {bulk_logs}")
        print(f"✓ Serial optimization logs: {serial_logs}")
        
        if bulk_logs == 1:
            print("\n✅ BULK optimization is working correctly (1 LLM call)")
        else:
            print(f"\n❌ BULK optimization issue: Expected 1 log, got {bulk_logs}")
            
        if serial_logs > 1:
            print("✅ SERIAL optimization is working correctly (multiple LLM calls)")
        else:
            print(f"❌ SERIAL optimization issue: Expected multiple logs, got {serial_logs}")

if __name__ == "__main__":
    asyncio.run(test_bulk_vs_serial())
