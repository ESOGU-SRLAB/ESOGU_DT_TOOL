from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from services.test_case_optimization_service import TestCaseOptimizationService
from core.prompt_manager import save_session_data
from typing import List, Dict, Any
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/test-case-optimization",
    tags=["test-case-optimization"]
)

@router.get("/models")
async def get_available_models():
    """
    Kullanılabilir LLM modellerini getir.
    Merkezi model konfigürasyonundan model listesini döndürür.
    """
    try:
        # Merkezi konfigürasyondan modelleri al
        from config.models_config import get_legacy_model_list
        available_models = get_legacy_model_list()
        
        logger.info(f"Retrieved {len(available_models)} models from central configuration")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Available models retrieved successfully from central configuration",
                "data": available_models
            }
        )
    except ImportError as e:
        logger.warning(f"Could not import central config: {e}, falling back to static list")
        # Fallback: Eski statik liste (geriye uyumluluk için)
        available_models = [
            # Local LM Studio Models
            {"key": "codegeex4:9b", "name": "CodeGeeX4 (9B)", "description": "Code generation optimized model", "type": "local"},
            {"key": "codellama:7b", "name": "Code Llama (7B)", "description": "Meta's code-focused model", "type": "local"},
            {"key": "deepseek-coder:6.7b", "name": "DeepSeek Coder (6.7B)", "description": "DeepSeek's coding model", "type": "local"},
            {"key": "gemma2:2b", "name": "Gemma 2 (2B)", "description": "Google's lightweight model", "type": "local"},
            {"key": "gemma3:4b", "name": "Gemma 3 (4B)", "description": "Google's enhanced model", "type": "local"},
            {"key": "google/gemma-3-12b", "name": "Gemma 3 (12B)", "description": "Google's large Gemma model", "type": "local"},
            {"key": "llama3.2:3b", "name": "Llama 3.2 (3B)", "description": "Meta's latest efficient model", "type": "local"},
            {"key": "meta/llama-3.3-70b", "name": "Llama 3.3 (70B)", "description": "Meta's latest large language model", "type": "local"},
            {"key": "mistralai/codestral-22b-v0.1", "name": "Codestral (22B)", "description": "Mistral AI's code-specialized model", "type": "local"},
            {"key": "openai/gpt-oss-20b", "name": "GPT OSS (20B)", "description": "OpenAI's open source large model", "type": "local"},
            {"key": "qwen/qwq-32b", "name": "QwQ (32B)", "description": "Qwen's reasoning-focused large model", "type": "local"},
            {"key": "qwen2.5:7b", "name": "Qwen 2.5 (7B)", "description": "Alibaba's advanced model", "type": "local"},
            {"key": "qwen2.5:7b-1m", "name": "Qwen 2.5 (7B-1M)", "description": "Large context version", "type": "local"},
            {"key": "qwen2.5-coder:3b", "name": "Qwen 2.5 Coder (3B)", "description": "Coding-focused Qwen model", "type": "local"},
            {"key": "qwen/qwen3-14b", "name": "Qwen 3 (14B)", "description": "Alibaba's latest large model", "type": "local"},
            {"key": "stable-code:3b", "name": "Stable Code (3B)", "description": "Stability AI's code model", "type": "local"},
            {"key": "starcoder2:7b", "name": "StarCoder 2 (7B)", "description": "BigCode's enhanced model", "type": "local"},
            # External API Models
            {"key": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "description": "Google's latest fast model", "type": "api", "provider": "Google"},
            {"key": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "description": "Google's latest pro model", "type": "api", "provider": "Google"},
            {"key": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "description": "Google's pro model", "type": "api", "provider": "Google"},
            {"key": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "description": "Google's fast model", "type": "api", "provider": "Google"}
        ]
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Available models retrieved successfully (fallback mode)",
                "data": available_models
            }
        )
    except Exception as e:
        logger.error(f"Error in get_available_models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/process-titles-with-counts")
async def get_process_titles_with_counts():
    """
    Process title'ları ve test case sayılarını getir.
    """
    try:
        service = TestCaseOptimizationService()
        process_data = service.get_process_titles_with_counts()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Process titles with counts retrieved successfully",
                "data": process_data
            }
        )
    except Exception as e:
        logger.error(f"Error in get_process_titles_with_counts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-cases-multi-process")
async def get_test_cases_by_multiple_processes(request: Request):
    """
    Birden fazla process_title için test case'leri getir.
    """
    try:
        body = await request.json()
        process_titles = body.get("process_titles", [])
        
        if not process_titles:
            raise HTTPException(status_code=400, detail="Process titles list is required")
        
        service = TestCaseOptimizationService()
        test_cases = service.get_test_cases_by_process_titles(process_titles)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Test cases for {len(process_titles)} processes retrieved successfully",
                "data": test_cases
            }
        )
    except Exception as e:
        logger.error(f"Error in get_test_cases_by_multiple_processes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/process-titles")
async def get_process_titles():
    """
    Mevcut process_title değerlerini getir.
    """
    try:
        service = TestCaseOptimizationService()
        process_titles = service.get_available_process_titles()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Process titles retrieved successfully",
                "data": process_titles
            }
        )
    except Exception as e:
        logger.error(f"Error in get_process_titles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test-cases/{process_title}")
async def get_test_cases_by_process_title(process_title: str):
    """
    Belirli bir process_title için test case'leri getir.
    """
    try:
        service = TestCaseOptimizationService()
        test_cases = service.get_test_cases_by_process_title(process_title)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Test cases for {process_title} retrieved successfully",
                "data": test_cases
            }
        )
    except Exception as e:
        logger.error(f"Error in get_test_cases_by_process_title: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/smart-selection")
async def run_smart_selection(request: Request):
    """
    Seçilen test case'ler üzerinde smart selection işlemini çalıştır.
    Optimization type'a göre serial, parallel veya bulk çalıştırır.
    """
    try:
        data = await request.json()
        selected_test_cases = data.get("selected_test_cases", [])
        process_titles = data.get("process_titles", [])  # Accept multiple process titles
        process_title = data.get("process_title", "")  # Backward compatibility
        process_name = data.get("process_name", "")  # Get process name for saving optimization
        custom_prompt = data.get("custom_prompt", "")  # Get custom prompt from request
        selected_model = data.get("selected_model", "")  # Get selected model - don't use default
        api_key = data.get("api_key", "")  # Get API key for external models
        optimization_type = data.get("optimization_type", "individual")  # individual, bulk, or parallel
        session_id = data.get("session_id") or str(uuid.uuid4())  # Generate session_id if not provided
        
        # DEBUG: Log received data
        logger.info(f"🔍 SMART SELECTION REQUEST:")
        logger.info(f"   Received test cases: {len(selected_test_cases)}")
        logger.info(f"   Optimization type: {optimization_type}")
        logger.info(f"   Process titles: {process_titles}")
        
        if not selected_test_cases:
            raise HTTPException(status_code=400, detail="No test cases selected")
        
        # Handle both single and multiple process titles
        if process_titles:
            target_processes = process_titles
        elif process_title:
            target_processes = [process_title]
        else:
            raise HTTPException(status_code=400, detail="Process title(s) required")
        
        # Model seçimi zorunlu
        if not selected_model:
            raise HTTPException(status_code=400, detail="Model selection required")
        
        # Gemini modelleri için API key kontrolü
        is_gemini_model = any(gemini in selected_model.lower() for gemini in ["gemini"])
        if is_gemini_model and not api_key:
            raise HTTPException(status_code=400, detail="API key is required for Gemini models")
        
        # Parallel optimization için Gemini model kontrolü
        if optimization_type == "parallel" and not is_gemini_model:
            raise HTTPException(status_code=400, detail="Parallel optimization only works with Gemini models")
            
        # Process name zorunlu
        if not process_name or process_name.strip() == "":
            raise HTTPException(status_code=400, detail="Process name is required")
        
        service = TestCaseOptimizationService()
        
        # Generate a unique process ID for tracking
        process_id = str(uuid.uuid4())
        
        # Choose optimization method based on type
        logger.info(f"🎯 ROUTER: Optimization type selected = '{optimization_type}'")
        
        if optimization_type == "parallel":
            logger.info("🎯 ROUTER: Calling run_parallel_smart_selection")
            result = await service.run_parallel_smart_selection(
                selected_test_cases, custom_prompt, selected_model, api_key, process_id
            )
        elif optimization_type == "bulk":
            logger.info("🎯 ROUTER: Calling run_bulk_smart_selection")
            result = await service.run_bulk_smart_selection(
                selected_test_cases, custom_prompt, selected_model, api_key, process_id
            )
        else:  # individual (default, serial)
            logger.info(f"🎯 ROUTER: Calling run_smart_selection (serial) - optimization_type was '{optimization_type}'")
            result = await service.run_smart_selection(
                selected_test_cases, custom_prompt, selected_model, api_key, process_id
            )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        # Sonuçları her process için test_case_optimizations koleksiyonuna kaydet
        save_results = []
        for proc_title in target_processes:
            save_success = service.save_optimization_results(proc_title, result["data"], selected_model)
            save_results.append(save_success)
        
        if all(save_results):
            result["message"] += f" and saved successfully for {len(target_processes)} process(es)"
        else:
            result["message"] += f" but failed to save some results"
        
        # Session history'ye kaydet
        try:
            session_data = {
                "session_id": session_id,
                "output": result["data"],
                "edited_prompt": bool(custom_prompt),  # True if custom prompt was used
                "used_prompt": custom_prompt or "Default optimization prompt",
                "used_model": selected_model,  # Use the actual selected model
                "process_name": process_name,  # Save process name for test_case_optimization
                "process_titles": target_processes,  # Save multiple process titles
                "process_count": len(target_processes),
                "optimization_type": optimization_type  # Save optimization type (individual/parallel/bulk)
            }
            
            save_session_result = save_session_data(session_data, "test_case_optimization")
            if save_session_result:
                logger.info(f"Session data saved successfully for session_id: {session_id}")
            else:
                logger.warning(f"Failed to save session data for session_id: {session_id}")
                
        except Exception as session_error:
            logger.error(f"Error saving session data: {session_error}")
            # Don't fail the main request if session saving fails
        
        # Add session_id to response
        result["session_id"] = session_id
        
        return JSONResponse(
            status_code=200,
            content=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in run_smart_selection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results/{process_title}")
async def get_optimization_results(process_title: str):
    """
    Belirli bir process_title için kaydedilmiş optimization sonuçlarını getir.
    """
    try:
        service = TestCaseOptimizationService()
        results = service.get_optimization_results(process_title)
        
        if results is None:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "No optimization results found for this process title",
                    "data": None
                }
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Optimization results retrieved successfully",
                "data": results
            }
        )
        
    except Exception as e:
        logger.error(f"Error in get_optimization_results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/results/{process_title}")
async def delete_optimization_results(process_title: str):
    """
    Belirli bir process_title için optimization sonuçlarını sil.
    """
    try:
        service = TestCaseOptimizationService()
        
        # Sonuçları sil
        optimization_collection = service.db["test_case_optimizations"]
        result = optimization_collection.delete_one({"process_title": process_title})
        
        if result.deleted_count == 0:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "No optimization results found to delete",
                    "data": None
                }
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Optimization results deleted successfully",
                "data": None
            }
        )
        
    except Exception as e:
        logger.error(f"Error in delete_optimization_results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/process-names")
async def get_available_process_names():
    """
    Kaydedilmiş process name'leri getir.
    """
    try:
        from core.database import get_db
        db = get_db()
        session_collection = db["session_history"]
        
        # test_case_optimization süreçlerinden process_name'leri getir
        pipeline = [
            {"$match": {"processes.test_case_optimization": {"$exists": True}}},
            {"$project": {"process_name": "$processes.test_case_optimization.process_name"}},
            {"$match": {"process_name": {"$exists": True, "$ne": ""}}},
            {"$group": {"_id": "$process_name", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        
        results = list(session_collection.aggregate(pipeline))
        process_names = [{"process_name": result["_id"], "count": result["count"]} for result in results]
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Process names retrieved successfully",
                "data": process_names
            }
        )
    except Exception as e:
        logger.error(f"Error in get_available_process_names: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results/by-process-name/{process_name}")
async def get_optimization_results_by_process_name(process_name: str):
    """
    Process name'e göre optimization sonuçlarını getir.
    """
    try:
        from core.database import get_db
        db = get_db()
        session_collection = db["session_history"]
        
        # Process name'e göre optimization sonuçlarını getir
        results = list(session_collection.find(
            {"processes.test_case_optimization.process_name": process_name},
            {"processes.test_case_optimization": 1, "session_id": 1, "timestamp": 1}
        ).sort("timestamp", -1))
        
        if not results:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "No optimization results found for this process name",
                    "data": None
                }
            )
        
        # Format the results
        formatted_results = []
        for result in results:
            session_id = result.get("session_id", "")
            timestamp = result.get("timestamp", "")
            optimization_data = result.get("processes", {}).get("test_case_optimization", {})
            
            formatted_results.append({
                "session_id": session_id,
                "timestamp": timestamp,
                "process_name": optimization_data.get("process_name", ""),
                "used_model": optimization_data.get("used_model", ""),
                "process_titles": optimization_data.get("process_titles", []),
                "process_count": optimization_data.get("process_count", 0),
                "output": optimization_data.get("output", {})
            })
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Optimization results for '{process_name}' retrieved successfully",
                "data": formatted_results
            }
        )
        
    except Exception as e:
        logger.error(f"Error in get_optimization_results_by_process_name: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop-process/{process_id}")
async def stop_process(process_id: str):
    """
    Çalışan bir test case optimization process'ini durdur.
    """
    try:
        service = TestCaseOptimizationService()
        result = service.stop_process(process_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["message"])
        
        return JSONResponse(
            status_code=200,
            content=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in stop_process: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/process-status/{process_id}")
async def get_process_status(process_id: str):
    """
    Bir process'in durumunu getir.
    """
    try:
        service = TestCaseOptimizationService()
        result = service.get_process_status(process_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["message"])
        
        return JSONResponse(
            status_code=200,
            content=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_process_status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/running-processes")
async def list_running_processes():
    """
    Tüm çalışan process'leri listele.
    """
    try:
        service = TestCaseOptimizationService()
        result = service.list_running_processes()
        
        return JSONResponse(
            status_code=200,
            content=result
        )
        
    except Exception as e:
        logger.error(f"Error in list_running_processes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session-report/{session_id}")
async def get_session_report(session_id: str):
    """
    Optimization session raporu getir.
    """
    try:
        from utils.optimization_monitor import optimization_monitor
        
        report = optimization_monitor.export_session_report(session_id)
        
        if "error" in report:
            raise HTTPException(status_code=404, detail=report["error"])
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Session report retrieved successfully",
                "data": report
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_session_report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/error-statistics")
async def get_error_statistics():
    """
    Genel hata istatistiklerini getir.
    """
    try:
        from utils.optimization_monitor import optimization_monitor
        
        stats = optimization_monitor.get_error_statistics()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Error statistics retrieved successfully",
                "data": stats
            }
        )
        
    except Exception as e:
        logger.error(f"Error in get_error_statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configure-retry")
async def configure_retry(request: Request):
    """
    Retry ayarlarını yapılandır.
    """
    try:
        data = await request.json()
        
        # Retry config dosyasını güncelle (runtime'da)
        from config.test_case_optimization_config import RETRY_CONFIG
        
        valid_keys = {"max_retries", "base_delay", "max_delay", "exponential_base"}
        for key, value in data.items():
            if key in valid_keys:
                RETRY_CONFIG[key] = value
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Retry configuration updated successfully",
                "data": RETRY_CONFIG
            }
        )
        
    except Exception as e:
        logger.error(f"Error in configure_retry: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monitoring/stats")
async def get_optimization_stats():
    """
    Optimization istatistiklerini getir.
    """
    try:
        from utils.optimization_monitor import optimization_monitor
        
        stats = optimization_monitor.get_stats_summary()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Optimization statistics retrieved successfully",
                "data": stats
            }
        )
        
    except Exception as e:
        logger.error(f"Error in get_optimization_stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/monitoring/reset")
async def reset_optimization_stats():
    """
    Optimization istatistiklerini sıfırla.
    """
    try:
        from utils.optimization_monitor import optimization_monitor
        
        optimization_monitor.reset_stats()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Optimization statistics reset successfully"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in reset_optimization_stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
