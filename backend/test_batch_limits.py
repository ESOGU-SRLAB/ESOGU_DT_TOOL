"""
Test Gemini Batch API Request Limits
Bu script batch API'nin maksimum request sayısını test eder
"""

import asyncio
from google import genai
from google.genai import types

async def test_batch_limits():
    """Test batch API with different request counts"""
    
    api_key = "AIzaSyCV-4uNhn53rh5Yp5A6IrkrG5iMvko6O4Q"
    client = genai.Client(api_key=api_key)
    
    # Test different request counts
    test_counts = [10, 50, 100, 500, 1000, 5000, 10000, 13041]
    
    print("="*80)
    print("🧪 BATCH API REQUEST LIMIT TESTS")
    print("="*80)
    
    for count in test_counts:
        print(f"\n📊 Testing with {count:,} requests...")
        
        # Create dummy requests
        requests = []
        for i in range(count):
            requests.append(
                types.BatchGenerateContentRequest(
                    model="gemini-2.5-flash",
                    contents=[
                        types.Content(
                            role="user",
                            parts=[types.Part(text=f"Test request {i}")]
                        )
                    ]
                )
            )
        
        try:
            # Try to create batch job
            batch_job = client.batches.create(
                model="gemini-2.5-flash",
                requests=requests
            )
            
            print(f"✅ SUCCESS: Batch job created with {count:,} requests")
            print(f"   Job ID: {batch_job.name}")
            
            # Cancel the job immediately (don't waste quota)
            try:
                client.batches.cancel(name=batch_job.name)
                print(f"   ⚠️ Job cancelled to save quota")
            except Exception as e:
                print(f"   ⚠️ Could not cancel: {e}")
            
            # Wait a bit to avoid rate limiting
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"❌ FAILED: {e}")
            
            # If 429, we found the limit
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print(f"\n🎯 LIMIT FOUND: Maximum ~{count:,} requests")
                print(f"   Your account can't handle {count:,} requests in one batch")
                break
            
            # If different error, continue
            await asyncio.sleep(5)
    
    print("\n" + "="*80)
    print("💡 CONCLUSION:")
    print("="*80)
    print("Check which test passed and which failed above.")
    print("This will tell you the maximum batch size for your account.")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_batch_limits())
