#!/usr/bin/env python3
"""
setup_prompts.py
----------------
STLC Manager için base prompt'ları manuel olarak kurulum scriptı.
Bu script, projeyi GitHub'dan indirdikten sonra tek seferde çalıştırılabilir.

Kullanım:
    python setup_prompts.py

Not: Bu script sadece gerektiğinde manual kurulum için kullanılır.
Normal kullanımda app.py başlatıldığında otomatik olarak prompt'lar yüklenir.
"""

import sys
import os
import logging

# Backend dizinini Python path'ine ekle
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

# Logging konfigürasyonu
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """
    STLC Manager için tüm base prompt'ları database'e yükler.
    """
    print("=" * 60)
    print("🚀 STLC Manager - Base Prompt Setup")
    print("=" * 60)
    print()
    
    try:
        # MongoDB bağlantısını test et
        logger.info("📡 MongoDB bağlantısı test ediliyor...")
        from core.database import get_db
        db = get_db()
        
        # Ping test
        db.admin.command('ping')
        logger.info("✅ MongoDB bağlantısı başarılı!")
        
        # Prompt manager'ı import et
        from core.prompt_manager import (
            initialize_code_review_prompt,
            initialize_requirement_analysis_prompt,
            initialize_test_planning_prompt,
            initialize_environment_setup_prompt,
            initialize_test_scenario_generation_prompt,
            initialize_base_prompts
        )
        
        print()
        logger.info("📝 Base prompt'lar yükleniyor...")
        print("-" * 50)
        
        # Her modül için prompt'ları yükle
        modules = [
            ("Code Review", initialize_code_review_prompt),
            ("Requirement Analysis", initialize_requirement_analysis_prompt),
            ("Test Planning", initialize_test_planning_prompt),
            ("Environment Setup", initialize_environment_setup_prompt),
            ("Test Scenario Generation", initialize_test_scenario_generation_prompt),
        ]
        
        success_count = 0
        for module_name, init_func in modules:
            try:
                logger.info(f"  ├── {module_name} prompt'ları işleniyor...")
                init_func()
                success_count += 1
                logger.info(f"  │   ✅ {module_name} - Tamamlandı")
            except Exception as e:
                logger.error(f"  │   ❌ {module_name} - Hata: {str(e)}")
        
        # Genel initialization
        try:
            logger.info("  ├── Genel prompt kontrolü yapılıyor...")
            initialize_base_prompts()
            logger.info("  └── ✅ Genel kontrol tamamlandı")
        except Exception as e:
            logger.error(f"  └── ❌ Genel kontrol hatası: {str(e)}")
        
        print("-" * 50)
        print()
        
        if success_count == len(modules):
            logger.info("🎉 Tüm base prompt'lar başarıyla yüklendi!")
            print("✅ STLC Manager kullanıma hazır!")
        else:
            logger.warning(f"⚠️  {success_count}/{len(modules)} modül başarılı.")
            print("⚠️  Bazı prompt'lar yüklenemedi, lütjen log'ları kontrol edin.")
        
        print()
        print("📋 Yüklenen Modüller:")
        print("  • Code Review")
        print("  • Requirement Analysis") 
        print("  • Test Planning")
        print("  • Environment Setup")
        print("  • Test Scenario Generation")
        print()
        print("🚀 Backend'i başlatmak için:")
        print("   cd backend && python app.py")
        print()
        
    except ImportError as e:
        logger.error(f"❌ Import hatası: {str(e)}")
        print("💡 Çözüm: Backend dizininde gerekli kütüphaneleri yükleyin:")
        print("   cd backend && pip install -r requirements.txt")
        
    except Exception as e:
        logger.error(f"❌ Beklenmeyen hata: {str(e)}")
        print("💡 MongoDB'nin çalıştığından emin olun ve tekrar deneyin.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
