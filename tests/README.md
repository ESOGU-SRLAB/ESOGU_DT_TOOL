# Tests Directory

Bu klasör STLC Manager projesinin tüm test dosyalarını organize edilmiş şekilde içermektedir.

## Klasör Yapısı

### `/unit`
Birim testleri - Her bir fonksiyon veya sınıfın ayrı ayrı test edildiği dosyalar:
- API testleri (`test_api_*.py`)
- Gemini model testleri (`test_gemini_*.py`)
- Backend service testleri (`test_backend_*.py`)
- Bulk işlem testleri (`test_bulk_*.py`)
- Model optimizasyon testleri (`test_optimization_*.py`)
- JSON işleme testleri (`test_json_*.py`)
- Timeout ve hata düzeltme testleri

### `/integration`
Entegrasyon testleri - Sistemin farklı parçalarının birlikte çalışmasını test eden dosyalar:
- Backend-LLM entegrasyonu (`test_backend_llm_integration.py`)
- Frontend-Backend entegrasyonu (`test_frontend_backend_integration.py`)
- End-to-end demo testleri (`test_end_to_end_demo.py`)
- Final entegrasyon testleri (`test_final_integration.py`)

### `/performance`
Performans testleri - Sistem hızı ve verimlilik testleri:
- Code review hızı testleri (`test_code_review_speed.py`)
- Environment setup hızı testleri (`test_environment_setup_speed.py`)
- Gemini hızı testleri (`test_gemini_speed.py`)
- Requirement analysis hızı testleri (`test_requirement_analysis_speed.py`)
- Test planning hızı testleri (`test_test_planning_speed.py`)

### `/utils`
Yardımcı araçlar ve kontrol scriptleri:
- Database kontrol scriptleri (`check_*.py`)
- Temizlik araçları (`clean*.py`, `cleanup_*.py`)
- Setup ve init scriptleri (`setup_*.py`, `init_*.py`)
- Debug araçları (`debug_*.py`)
- Test data oluşturma araçları (`create_*.py`)
- Doğrulama araçları (`verify_*.py`)

### `/results`
Test sonuçları ve raporları:
- JSON test sonuç dosyaları (`*.json`)
- HTML test raporları (`*.html`)
- Model test sonuçları (`new_models_test_results_*.json`)

## Testleri Çalıştırma

### Tüm testleri çalıştırmak için:
```bash
python -m pytest tests/
```

### Belirli kategori testlerini çalıştırmak için:
```bash
# Unit testleri
python -m pytest tests/unit/

# Integration testleri  
python -m pytest tests/integration/

# Performance testleri
python -m pytest tests/performance/
```

### Belirli bir test dosyasını çalıştırmak için:
```bash
python tests/unit/test_gemini_fix.py
```

## Test Kategorileri

- **Unit Tests**: Tekil fonksiyon/sınıf testleri
- **Integration Tests**: Sistem bileşenleri arası testler  
- **Performance Tests**: Hız ve performans testleri
- **Utils**: Yardımcı araçlar ve kontroller
- **Results**: Test sonuçları ve raporları