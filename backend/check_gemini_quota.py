"""
Gemini API Quota Checker
Checks current quota usage and limits
"""

import os
import sys
import requests
from datetime import datetime

def check_quota(api_key: str):
    """Check Gemini API quota and limits"""
    
    print("="*80)
    print("🔍 GEMINI API QUOTA CHECKER")
    print("="*80)
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔑 API Key: {api_key[:10]}...{api_key[-5:]}")
    print("="*80)
    
    # Test 1: Simple API call
    print("\n📊 Test 1: Simple Model List Request")
    try:
        response = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"key": api_key}
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API key is valid and working")
            models = response.json().get("models", [])
            print(f"📦 Available models: {len(models)}")
            
            # Check for batch-capable models
            batch_models = [m for m in models if "generateContent" in m.get("supportedGenerationMethods", [])]
            print(f"🚀 Batch-capable models: {len(batch_models)}")
            
        elif response.status_code == 429:
            print("❌ QUOTA EXCEEDED!")
            error_data = response.json()
            print(f"Error: {error_data}")
        else:
            print(f"⚠️ Unexpected status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Check Batch API availability
    print("\n📊 Test 2: Batch API Availability Check")
    try:
        # Try to list batch jobs
        response = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/batches",
            params={"key": api_key}
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Batch API is accessible")
            batches = response.json()
            print(f"Response: {batches}")
        elif response.status_code == 429:
            print("❌ QUOTA EXCEEDED on Batch API!")
            error_data = response.json()
            print(f"Error: {error_data}")
        elif response.status_code == 403:
            print("⚠️ Batch API not available (might need paid plan)")
            print(f"Response: {response.text}")
        else:
            print(f"⚠️ Unexpected status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Get quota details
    print("\n📊 Test 3: Quota Information")
    print("Visit these links to check your quota:")
    print("1. Usage Dashboard: https://ai.dev/usage?tab=rate-limit")
    print("2. API Console: https://aistudio.google.com/apikey")
    print("3. Billing: https://console.cloud.google.com/billing")
    
    print("\n" + "="*80)
    print("💡 RECOMMENDATIONS:")
    print("="*80)
    print("1. If free tier: Daily quota resets at midnight PST")
    print("2. For production: Upgrade to paid plan")
    print("3. Batch API might require paid plan")
    print("4. Alternative: Use LM Studio for testing")
    print("="*80)

if __name__ == "__main__":
    # Get API key from user
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
    else:
        api_key = input("Enter your Gemini API key: ").strip()
    
    if not api_key:
        print("❌ No API key provided!")
        sys.exit(1)
    
    check_quota(api_key)
