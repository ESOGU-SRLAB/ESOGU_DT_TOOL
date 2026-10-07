#!/usr/bin/env python3

import requests
import time
import json

def wait_for_backend():
    """Backend'in hazır olmasını bekle"""
    print("Backend'in başlamasını bekliyorum...")
    for i in range(30):  # 30 saniye bekle
        try:
            response = requests.get("http://127.0.0.1:8000/health", timeout=2)
            if response.status_code == 200:
                print("✅ Backend hazır!")
                return True
        except:
            pass
        
        try:
            # Health endpoint yoksa models endpoint'i dene
            response = requests.get("http://127.0.0.1:8000/api/models?legacy_format=true", timeout=2)
            if response.status_code == 200:
                print("✅ Backend hazır!")
                return True
        except:
            pass
            
        print(f"⏳ Bekliyorum... ({i+1}/30)")
        time.sleep(1)
    
    print("❌ Backend başlamadı!")
    return False

def check_provider_field():
    """Provider field'ının gelip gelmediğini kontrol et"""
    if not wait_for_backend():
        return
        
    try:
        print("\n🔍 Provider field kontrolü yapılıyor...")
        response = requests.get("http://127.0.0.1:8000/api/models?legacy_format=true")
        
        if response.status_code == 200:
            data = response.json()
            models = data.get('data', [])
            
            # Gemini modellerini bul
            gemini_models = [m for m in models if 'gemini' in m.get('key', '').lower()]
            
            print(f"Toplam model sayısı: {len(models)}")
            print(f"Gemini model sayısı: {len(gemini_models)}")
            
            for model in gemini_models:
                provider = model.get('provider')
                print(f"🔎 {model.get('key')}: provider={provider}")
                
                if provider == "Google":
                    print(f"✅ {model.get('key')} - Provider field düzgün!")
                elif provider is None:
                    print(f"❌ {model.get('key')} - Provider field None!")
                else:
                    print(f"⚠️ {model.get('key')} - Provider field beklenmedik: {provider}")
                    
        else:
            print(f"❌ API Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    check_provider_field()