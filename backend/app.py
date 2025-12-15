import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from stlc.code_review import router as code_review_router
from routers.test_scenario_generation_router import router as test_scenario_router
from routers.test_scenario_prompt_router import router as test_scenario_prompt_router
from stlc.test_scenario_generation import generate_prompt
import logging
from routers.code_review_router import router as code_review_prompt_router
from routers.requirement_analysis_router import router as requirement_analysis_prompt_router
from stlc.requirement_analysis import router as requirement_analysis_router
from routers.test_planning_router import router as test_planning_router
from stlc.test_planning import router as test_planning_process_router
from stlc.environment_setup import router as environment_setup_router
from routers.environment_setup_router import router as environment_setup_prompt_router
from routers.test_case_optimization_router import router as test_case_optimization_router
from stlc.test_code_generation import router as test_code_generation_router
from routers.models_router import router as models_router
from routers.api_key_validation_router import router as api_key_validation_router
from routers.execution_router import router as test_execution_router
from routers.execution_prompt_router import router as test_execution_prompt_router
from routers.test_reporting_router import router as test_reporting_router
from routers.test_reporting_prompt_router import router as test_reporting_prompt_router
from routers.test_closure_router import router as test_closure_router
# from routers.test_scenario_analytics_router import router as test_scenario_analytics_router

# Auto-initialization import
from core.prompt_manager import (
    initialize_base_prompts,
    initialize_code_review_prompt,
    initialize_requirement_analysis_prompt,
    initialize_test_planning_prompt,
    initialize_environment_setup_prompt,
    initialize_test_scenario_generation_prompt,
    initialize_test_execution_prompt
)

# Logger configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_application():
    """
    Uygulama başlatıldığında tüm base prompt'ları otomatik olarak database'e ekler.
    GitHub'dan proje indirildikten sonra ilk çalıştırmada tüm modüller için
    default prompt'lar database'e yüklenecek.
    """
    logger.info("🚀 STLC Manager Backend başlatılıyor...")
    logger.info("📝 Base prompt'lar kontrol ediliyor ve gerekirse ekleniyor...")
    
    try:
        # Her modül için individual initialization
        logger.info("  ├── Code Review prompt'ları kontrol ediliyor...")
        initialize_code_review_prompt()
        
        logger.info("  ├── Requirement Analysis prompt'ları kontrol ediliyor...")
        initialize_requirement_analysis_prompt()
        
        logger.info("  ├── Test Planning prompt'ları kontrol ediliyor...")
        initialize_test_planning_prompt()
        
        logger.info("  ├── Environment Setup prompt'ları kontrol ediliyor...")
        initialize_environment_setup_prompt()
        
        logger.info("  ├── Test Scenario Generation prompt'ları kontrol ediliyor...")
        initialize_test_scenario_generation_prompt()
        
        logger.info("  ├── Test Execution prompt'ları kontrol ediliyor...")
        initialize_test_execution_prompt()
        
        # Unified initialization (backup)
        logger.info("  └── Tüm prompt'lar için genel kontrol yapılıyor...")
        initialize_base_prompts()
        
        logger.info("✅ Tüm base prompt'lar başarıyla kontrol edildi/eklendi!")
        logger.info("🎯 STLC Manager Backend kullanıma hazır!")
        
    except Exception as e:
        logger.error(f"❌ Base prompt initialization hatası: {str(e)}")
        logger.error("⚠️  Uygulama başlatılacak ancak bazı prompt'lar eksik olabilir.")

app = FastAPI(
    title="STLC Manager Backend",
    description="STLC Manager Backend API",
    version="0.1.0"
)

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React uygulamanızın çalıştığı port
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite default port
        "http://127.0.0.1:5173",
        "http://localhost:5174",  # Vite alternative port
        "http://127.0.0.1:5174",
        "*"  # Geliştirme aşamasında tüm originlere izin vermek için
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router ekleme
app.include_router(code_review_router, prefix="/api/processes/code-review")
app.include_router(test_scenario_router, prefix="/api/processes/test-scenario-generation")
app.include_router(test_scenario_prompt_router)  # test scenario prompt router
app.include_router(code_review_prompt_router)  # code_review prompt router
app.include_router(requirement_analysis_prompt_router)  # requirement_analysis prompt router
app.include_router(requirement_analysis_router, prefix="/api/processes/requirement_analysis")
app.include_router(test_planning_router)  # test planning prompt router
app.include_router(test_planning_process_router, prefix="/api/processes/test-planning")
app.include_router(environment_setup_router, prefix="/api/processes/environment-setup")
app.include_router(environment_setup_prompt_router)  # environment_setup prompt router
app.include_router(test_case_optimization_router)  # test case optimization router
app.include_router(test_code_generation_router, prefix="/api/processes/test-code-generation")  # test code generation router
app.include_router(models_router)  # Merkezi model yönetimi router'ı
app.include_router(api_key_validation_router, prefix="/api")  # API key validation router
app.include_router(test_execution_router)  # Test execution router
app.include_router(test_execution_prompt_router)  # Test execution prompt router
app.include_router(test_reporting_router)  # Test reporting router
app.include_router(test_reporting_prompt_router)  # Test reporting prompt router
app.include_router(test_closure_router)  # Test closure router
# app.include_router(test_scenario_analytics_router, prefix="/api")  # Test scenario analytics

@app.get("/")
def read_root():
    return {"message": "STLC Manager Backend is running!"}

@app.get("/api/health/prompts")
async def check_prompts_status():
    """
    Tüm modüller için base prompt'ların database'de mevcut olup olmadığını kontrol eder.
    GitHub'dan proje indirildikten sonra kurulumun doğru yapıldığını onaylamak için kullanılır.
    """
    from core.prompt_manager import get_base_prompt
    
    modules = [
        "code_review",
        "requirement_analysis", 
        "test_planning",
        "environment_setup",
        "test_scenario_generation",
        "test_execution"
    ]
    
    status = {}
    all_ready = True
    
    for module in modules:
        try:
            prompt = get_base_prompt(module)
            is_available = bool(prompt and len(prompt.strip()) > 0)
            status[module] = {
                "available": is_available,
                "prompt_length": len(prompt) if prompt else 0
            }
            if not is_available:
                all_ready = False
        except Exception as e:
            status[module] = {
                "available": False,
                "error": str(e)
            }
            all_ready = False
    
    return {
        "all_modules_ready": all_ready,
        "modules": status,
        "message": "All prompts loaded successfully!" if all_ready else "Some prompts are missing. Run initialization."
    }

@app.on_event("startup")
async def startup_event():
    """
    FastAPI startup event - uygulama başlatıldığında otomatik çalışır.
    GitHub'dan projeyi indirip ilk kez çalıştırdığınızda tüm prompt'lar
    otomatik olarak database'e eklenecek.
    """
    initialize_application()

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
