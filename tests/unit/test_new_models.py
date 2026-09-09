#!/usr/bin/env python3
"""
Test script to verify new models mapping in LM Studio
"""

import sys
import os
import asyncio

# Add backend directory to path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.append(backend_dir)

from utils.model_client import LLMClient

async def test_model_mapping():
    """Test that new models are properly mapped"""
    print("🚀 Testing New Model Mappings")
    print("=" * 50)
    
    # Test models to verify
    test_models = [
        "qwen/qwq-32b",
        "mistralai/codestral-22b-v0.1"
    ]
    
    for model_key in test_models:
        print(f"\n📋 Testing model: {model_key}")
        
        try:
            # Create LLMClient instance
            client = LLMClient()
            
            # Test mapping
            mapped_model = client.get_model_identifier(model_key)
            print(f"✅ Mapping result: {model_key} -> {mapped_model}")
            
            # Verify it's not using the default model
            if mapped_model == "llama-3.2-1b-instruct":
                print(f"❌ WARNING: Using default model, mapping may be missing!")
            else:
                print(f"✅ Mapping successful: Custom model identifier found")
                
        except Exception as e:
            print(f"❌ Error testing {model_key}: {e}")
    
    print(f"\n🎯 All Model Mappings:")
    print("-" * 30)
    client = LLMClient()
    
    # Get all mappings from the model_mapping dict
    all_models = [
        "codegeex4:9b",
        "codellama:7b", 
        "deepseek-coder:6.7b",
        "gemma2:2b",
        "gemma3:4b",
        "google/gemma-3-12b",
        "llama3.2:3b",
        "meta/llama-3.3-70b",
        "mistralai/codestral-22b-v0.1",  # New model
        "openai/gpt-oss-20b",
        "qwen/qwq-32b",  # New model
        "qwen2.5:7b",
        "qwen2.5-7b-instruct-1m",
        "qwen2.5-coder:3b",
        "qwen/qwen3-14b",
        "stable-code:3b",
        "starcoder2:7b"
    ]
    
    for model in all_models:
        mapped = client.get_model_identifier(model)
        status = "✅" if mapped != "llama-3.2-1b-instruct" else "❌"
        print(f"{status} {model:<35} -> {mapped}")

if __name__ == "__main__":
    asyncio.run(test_model_mapping())
