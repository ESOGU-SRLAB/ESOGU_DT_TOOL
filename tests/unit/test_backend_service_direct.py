"""
Backend Service Direct Test
Backend service'i directly test eder
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Backend service'i import et
from services.test_code_generation_service import TestCodeGenerationService

def test_backend_service():
    """Backend service'i direkt test et"""
    print("=== Backend Service Direct Test ===")
    
    try:
        service = TestCodeGenerationService()
        print("Service initialized successfully")
        
        # Environment setups'ı al
        setups = service.get_environment_setups()
        print(f"Found {len(setups)} environment setups")
        
        # İlk 3'ü göster
        for i, setup in enumerate(setups[:3], 1):
            env_name = setup.get('environment_name', 'N/A')
            proc_name = setup.get('process_name', 'N/A')
            language = setup.get('environment_info', {}).get('language', 'Unknown')
            print(f"  {i}. {env_name} - {proc_name} ({language})")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_backend_service()