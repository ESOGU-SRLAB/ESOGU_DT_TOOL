#!/usr/bin/env python3

import requests
import json

# API endpoint'ten gelen raw response'u kontrol et
url = "http://127.0.0.1:8000/api/models?legacy_format=true"

def check_api_response():
    try:
        print("Checking API response from:", url)
        response = requests.get(url)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            print(f"Total models: {len(data.get('data', []))}")
            
            # İlk 3 modeli detaylı incele
            models = data.get('data', [])
            
            print("\nFirst 3 models with all fields:")
            for i, model in enumerate(models[:3]):
                print(f"\nModel {i+1}:")
                for key, value in model.items():
                    print(f"  {key}: {value}")
            
            # Gemini modellerini özellikle kontrol et
            gemini_models = [m for m in models if 'gemini' in m.get('key', '').lower()]
            print(f"\nGemini models found: {len(gemini_models)}")
            
            for model in gemini_models:
                print(f"\nGemini Model: {model.get('key')}")
                print(f"  name: {model.get('name')}")
                print(f"  type: {model.get('type')}")
                print(f"  provider: {model.get('provider')}")
                print(f"  description: {model.get('description')}")
                
        else:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    check_api_response()