from pymongo import MongoClient
import json

client = MongoClient('mongodb://localhost:27017')
db = client['stlc_manager']

# Find the latest parallel execution batch
batch_doc = db.session_history.find_one(
    {'processes.parallel_docker_execution': {'$exists': True}},
    sort=[('_id', -1)]
)

if batch_doc:
    print(f"✅ Found parallel execution batch!")
    print(f"Session ID: {batch_doc.get('session_id')}")
    
    pde = batch_doc.get('processes', {}).get('parallel_docker_execution', {})
    print(f"Process Name: {pde.get('process_name')}")
    print(f"Status: {pde.get('status')}")
    
    stats = pde.get('statistics', {})
    print(f"Total Tests: {stats.get('total_tests')}")
    print(f"Completed Tests: {stats.get('completed')}")
    print(f"Failed Tests: {stats.get('failed')}")
    print(f"Success Rate: {stats.get('success_rate')}%")
    
    exec_time = pde.get('execution_time', {})
    print(f"Started At: {exec_time.get('start')}")
    print(f"Completed At: {exec_time.get('end')}")
    if exec_time.get('total_seconds'):
        print(f"Total Time: {exec_time.get('total_seconds'):.2f}s")
    
    results = pde.get('results', [])
    print(f"\n📊 Job Results ({len(results)} tests):")
    
    for idx, job in enumerate(results[:10], 1):  # Show first 10
        print(f"\n{idx}. Test ID: {job.get('test_id')}")
        print(f"   Test Name: {job.get('test_name')}")
        print(f"   Status: {job.get('status')}")
        if job.get('execution_time'):
            print(f"   Execution time: {job.get('execution_time'):.2f}s")
        if job.get('error'):
            print(f"   Error: {job.get('error')[:100]}")
    
    if len(results) > 10:
        print(f"\n... and {len(results) - 10} more tests")
else:
    print("❌ No parallel execution batch found")

client.close()
