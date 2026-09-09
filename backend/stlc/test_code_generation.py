"""
test_code_generation.py
-----------------------
STLC'nin Test Code Generation adımına ait işlemleri yönetir.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from services.test_code_generation_service import TestCodeGenerationService
import logging
from typing import Optional, List

router = APIRouter()
logger = logging.getLogger("test_code_generation")


def _service() -> TestCodeGenerationService:
    """Create the DB-backed service per request instead of at application import."""
    return TestCodeGenerationService()

@router.get("/environment-setups")
async def get_environment_setups():
    """
    Mevcut environment setup kayıtlarını getirir
    """
    try:
        setups = _service().get_environment_setups()
        return {
            "success": True,
            "data": setups,
            "count": len(setups)
        }
    except Exception as e:
        logger.error(f"Error getting environment setups: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/process-titles")
async def get_available_process_titles():
    """
    Mevcut process title'ları getirir (test case optimization'dan)
    """
    try:
        process_titles = _service().get_available_process_titles()
        return {
            "success": True,
            "data": process_titles,
            "count": len(process_titles)
        }
    except Exception as e:
        logger.error(f"Error getting process titles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test-case-count/{process_title}")
async def get_test_case_count(process_title: str):
    """
    Belirli bir process title için unique test case sayısını döndürür
    """
    try:
        unique_test_cases = _service().get_unique_test_cases_by_process_title(process_title)
        return {
            "success": True,
            "process_title": process_title,
            "count": len(unique_test_cases)
        }
    except Exception as e:
        logger.error(f"Error getting test case count: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/process-names")
async def get_process_names_with_tests():
    """
    Get list of process names that have generated tests
    Used by Robot Test Execution Panel to populate process dropdown
    """
    try:
        process_names = _service().get_process_names_with_generated_tests()
        return {
            "success": True,
            "process_names": process_names,
            "count": len(process_names)
        }
    except Exception as e:
        logger.error(f"Error getting process names: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tests/{process_name}")
async def get_tests_by_process_name(process_name: str):
    """
    Get generated tests for a specific process name
    Used by Robot Test Execution Panel to populate test selection
    
    Args:
        process_name: The process name (environment_name from test code generation)
        
    Returns:
        List of generated tests with test_id, test_case_name, status, test_code
    """
    try:
        tests = _service().get_generated_tests_by_process_name(process_name)
        return {
            "success": True,
            "process_name": process_name,
            "tests": tests,
            "count": len(tests)
        }
    except Exception as e:
        logger.error(f"Error getting tests for process {process_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/run")
async def process_test_code_generation(
    process_title: str = Form(...),
    environment_session_id: str = Form(...),
    files: List[UploadFile] = File(...),
    model: Optional[str] = Form("llama3.2:3b"),
    custom_prompt: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    environment_name: Optional[str] = Form(None),
    output_format: Optional[str] = Form("JSON"),
    api_key: Optional[str] = Form(None),
    max_test_cases: Optional[int] = Form(None)
):
    """
    Standard process runner for test code generation
    
    Args:
        max_test_cases: Optional limit on number of test cases to process (useful for large batches)
    """
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No source files uploaded")
        
        if not process_title:
            raise HTTPException(status_code=400, detail="Process title is required")
            
        if not environment_session_id:
            raise HTTPException(status_code=400, detail="Environment session ID is required")
        
        if not environment_name or environment_name.strip() == "":
            raise HTTPException(status_code=400, detail="Test Code Generation Process Name is required")
        
        logger.info(f"Running test code generation process")
        logger.info(f"Process title: {process_title}")
        logger.info(f"Environment session: {environment_session_id}")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Environment name: {environment_name}")
        logger.info(f"Files count: {len(files)}")
        logger.info(f"Model: {model}")
        logger.info(f"Output format: {output_format}")
        logger.info(f"Max test cases: {max_test_cases if max_test_cases else 'unlimited'}")
        logger.info(f"API key provided: {'Yes' if api_key else 'No'}")
        if api_key:
            logger.info(f"API key preview: {api_key[:15]}...")
        
        result = await _service().generate_test_codes(
            process_title=process_title,
            environment_session_id=environment_session_id,
            source_files=files,
            model_name=model,
            custom_prompt=custom_prompt,
            session_id=session_id,
            environment_name=environment_name,
            output_format=output_format,
            api_key=api_key,
            max_test_cases=max_test_cases
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test Code Generation Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate")
async def generate_test_code(
    process_title: str = Form(...),
    environment_session_id: str = Form(...),
    files: List[UploadFile] = File(...),
    model: Optional[str] = Form("llama3.2:3b"),
    api_key: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    environment_name: Optional[str] = Form(None),
    output_format: Optional[str] = Form("JSON"),
    custom_prompt: Optional[str] = Form(None)
):
    """
    Legacy endpoint for test code generation (backward compatibility)
    Now supports all parameters from /run endpoint
    """
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No source files uploaded")
        
        if not process_title:
            raise HTTPException(status_code=400, detail="Process title is required")
            
        if not environment_session_id:
            raise HTTPException(status_code=400, detail="Environment session ID is required")
        
        # Validate environment_name is provided
        if not environment_name or environment_name.strip() == "":
            raise HTTPException(status_code=400, detail="Test Code Generation Process Name is required")
        
        logger.info(f"Generating test code for process: {process_title}")
        logger.info(f"Using environment session: {environment_session_id}")
        logger.info(f"Uploaded files count: {len(files)}")
        logger.info(f"Using model: {model}")
        logger.info(f"Environment name: {environment_name}")
        logger.info(f"Output format: {output_format}")
        logger.info(f"API key provided: {'Yes' if api_key else 'No'}")
        if api_key:
            logger.info(f"API key preview: {api_key[:15]}...")
        logger.info(f"Session ID: {session_id}")
        
        result = await _service().generate_test_codes(
            process_title=process_title,
            environment_session_id=environment_session_id,
            source_files=files,
            model_name=model,
            api_key=api_key,
            session_id=session_id,
            environment_name=environment_name,
            output_format=output_format,
            custom_prompt=custom_prompt
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test Code Generation Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def run_step(input_data):
    """Backward compatibility için eski fonksiyon"""
    return {"step": "testCodeGeneration", "result": "Test code generation completed."}
