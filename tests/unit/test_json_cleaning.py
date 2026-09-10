#!/usr/bin/env python3
"""
Test script to verify the JSON cleaning functionality
"""

import json
import re

def clean_llm_response(response):
    """Clean LLM response from markdown code blocks"""
    cleaned_response = response.strip()
    if cleaned_response.startswith("```json"):
        cleaned_response = cleaned_response[7:]  # Remove ```json
    if cleaned_response.startswith("```"):
        cleaned_response = cleaned_response[3:]   # Remove ```
    if cleaned_response.endswith("```"):
        cleaned_response = cleaned_response[:-3]  # Remove ending ```
    cleaned_response = cleaned_response.strip()
    return cleaned_response

def test_json_cleaning():
    """Test the JSON cleaning functionality"""
    print("🧪 Testing JSON Cleaning Functionality")
    print("=" * 50)
    
    # Test case 1: Response with ```json``` blocks
    test_response_1 = '''```json
{
  "unique_indices": [0, 2, 4, 5, 7, 9, 10, 11, 13],
  "duplicate_groups": [
    {
      "representative_index": 0,
      "duplicate_indices": [3, 7]
    },
    {
      "representative_index": 2,
      "duplicate_indices": []
    }
  ]
}
```'''
    
    print("🔍 Test 1: Response with ```json``` blocks")
    print(f"Original length: {len(test_response_1)}")
    
    cleaned = clean_llm_response(test_response_1)
    print(f"Cleaned length: {len(cleaned)}")
    
    try:
        parsed = json.loads(cleaned)
        print("✅ Successfully parsed JSON!")
        print(f"🎯 Found {len(parsed['unique_indices'])} unique indices")
        print(f"🔄 Found {len(parsed['duplicate_groups'])} duplicate groups")
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse: {e}")
        print(f"Cleaned text: {cleaned}")
    
    # Test case 2: Response with simple ``` blocks
    test_response_2 = '''```
{
  "is_same": true
}
```'''
    
    print(f"\n🔍 Test 2: Response with simple ``` blocks")
    print(f"Original: {test_response_2}")
    
    cleaned_2 = clean_llm_response(test_response_2)
    print(f"Cleaned: {cleaned_2}")
    
    try:
        parsed_2 = json.loads(cleaned_2)
        print("✅ Successfully parsed JSON!")
        print(f"🎯 is_same value: {parsed_2['is_same']}")
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse: {e}")
    
    # Test case 3: Clean JSON without markdown
    test_response_3 = '''{"unique_indices": [0, 1, 2], "duplicate_groups": []}'''
    
    print(f"\n🔍 Test 3: Clean JSON without markdown")
    cleaned_3 = clean_llm_response(test_response_3)
    
    try:
        parsed_3 = json.loads(cleaned_3)
        print("✅ Clean JSON parsed successfully!")
        print(f"🎯 Found {len(parsed_3['unique_indices'])} unique indices")
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse: {e}")
    
    print(f"\n✅ JSON cleaning tests completed!")

if __name__ == "__main__":
    test_json_cleaning()
