"""
test_code_generation.py
-----------------------
STLC'nin Test Code Generation adımına ait işlemleri yönetir.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from services.test_code_generation_service import TestCodeGenerationService
from services.robot_capability_service import (
    RobotCapabilityError,
    parse_robot_capability_json,
)
import logging
import json
import math
from typing import Optional, List
from utils.text_splitter import count_tokens
from services.robot_capability_service import capability_prompt_context
from core.settings import get_settings
from services.project_structure_service import (
    ProjectStructureError,
    build_project_structure,
    parse_project_structure,
    project_structure_prompt_context,
)

router = APIRouter()
logger = logging.getLogger("test_code_generation")


def _service() -> TestCodeGenerationService:
    """Create the DB-backed service per request instead of at application import."""
    return TestCodeGenerationService()


async def _load_capability_contract(
    capability_file: Optional[UploadFile],
):
    if capability_file is None:
        return None
    try:
        raw = await capability_file.read()
        contract = parse_robot_capability_json(
            raw,
            capability_file.filename or "robot_capabilities.json",
        )
        expected_image = get_settings().ssh_execution_image
        pinned_image = (
            contract.get("meta", {})
            .get("pinned_sources", {})
            .get("image", {})
            .get("tag")
        )
        if pinned_image and expected_image and pinned_image != expected_image:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Robot capability contract is pinned to {pinned_image}, but the "
                    f"configured remote harness is {expected_image}. Upload the matching, "
                    "manually approved robot_capabilities.json."
                ),
            )
        return contract
    except RobotCapabilityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def _load_project_structure(
    project_ast_file: Optional[UploadFile],
    source_files: List[UploadFile],
):
    try:
        if project_ast_file is not None:
            return parse_project_structure(
                await project_ast_file.read(),
                project_ast_file.filename or "project_ast.json",
            )
        source_items = []
        for upload in source_files:
            raw = await upload.read()
            await upload.seek(0)
            source_items.append({
                "name": upload.filename or "unknown",
                "content": raw.decode("utf-8", errors="replace"),
            })
        return build_project_structure(source_items)
    except ProjectStructureError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/token-estimate")
async def estimate_test_code_generation_tokens(
    process_title: str = Form(...),
    environment_session_id: str = Form(...),
    files: List[UploadFile] = File(...),
    custom_prompt: Optional[str] = Form(None),
    capability_file: Optional[UploadFile] = File(None),
    project_ast_file: Optional[UploadFile] = File(None),
    max_input_tokens: int = Form(64000),
):
    """Estimate the exact per-test prompt size before starting generation."""
    if not 4096 <= max_input_tokens <= 64000:
        raise HTTPException(status_code=400, detail="max_input_tokens must be between 4096 and 64000")
    service = _service()
    capability_contract = await _load_capability_contract(capability_file)
    project_structure = await _load_project_structure(project_ast_file, files)
    test_cases = service.get_unique_test_cases_by_process_title(process_title)
    if not test_cases:
        raise HTTPException(status_code=404, detail="No test cases found for the selected process")

    selected_env = next(
        (
            item for item in service.get_environment_setups()
            if item["session_id"] == environment_session_id
        ),
        None,
    )
    if not selected_env:
        raise HTTPException(status_code=404, detail="Selected environment setup not found")
    environment_info = selected_env["environment_info"]
    framework = environment_info.get("framework", "pytest")
    template = {
        "pytest": {"imports": "import pytest\nimport unittest.mock as mock"},
        "unittest": {"imports": "import unittest\nfrom unittest import mock"},
    }.get(framework, {"imports": ""})

    code_files = []
    raw_source = []
    for upload in files:
        raw = await upload.read()
        content = raw.decode("utf-8", errors="replace")
        raw_source.append(content)
        code_files.append({
            "name": upload.filename or "unknown",
            "content": content[:12000],
            "size": len(content),
        })
    code_analysis = {
        "files": code_files,
        "structure_analysis": "Token estimate preview; final analysis may add a small summary.",
        "imports_dependencies": [],
    }

    per_case = []
    for index, test_case in enumerate(test_cases, 1):
        test_case_info = {
            "id": test_case.get("TestCaseID", f"TC_{index}"),
            "title": test_case.get("Title", ""),
            "description": test_case.get("Description", ""),
            "objective": test_case.get("Objective", ""),
            "steps": test_case.get("TestSteps", []) or [],
        }
        prompt = service._create_test_generation_prompt(
            test_case_info,
            code_analysis,
            environment_info,
            template,
            custom_prompt,
            capability_contract,
            project_structure,
        )
        per_case.append({
            "test_case_id": test_case_info["id"],
            "tokens": count_tokens(prompt),
        })

    totals = [item["tokens"] for item in per_case]
    maximum = max(totals)
    components = {
        "source_code_raw": count_tokens("\n".join(raw_source)),
        "source_code_included": count_tokens("\n".join(item["content"] for item in code_files)),
        "custom_prompt": count_tokens(custom_prompt or ""),
        "largest_test_case": max(
            count_tokens(json.dumps(item, ensure_ascii=False)) for item in test_cases
        ),
        "robot_capabilities": count_tokens(
            capability_prompt_context(capability_contract) if capability_contract else ""
        ),
        "project_ast": count_tokens(project_structure_prompt_context(project_structure)),
    }
    return {
        "success": True,
        "max_input_tokens": max_input_tokens,
        "test_case_count": len(per_case),
        "min_tokens_per_test": min(totals),
        "max_tokens_per_test": maximum,
        "average_tokens_per_test": round(sum(totals) / len(totals)),
        "fits_budget": maximum <= max_input_tokens,
        "legacy_chunk_count": math.ceil(maximum / max_input_tokens),
        "components": components,
        "per_test_case": per_case,
        "note": "Each test case is generated in one atomic LLM request; executable code responses are never concatenated from chunks.",
    }

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
    max_test_cases: Optional[int] = Form(None),
    capability_file: Optional[UploadFile] = File(None),
    project_ast_file: Optional[UploadFile] = File(None),
    max_input_tokens: int = Form(64000),
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
        
        capability_contract = await _load_capability_contract(capability_file)
        project_structure = await _load_project_structure(project_ast_file, files)
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
            max_test_cases=max_test_cases,
            capability_contract=capability_contract,
            project_structure=project_structure,
            max_input_tokens=max_input_tokens,
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
    custom_prompt: Optional[str] = Form(None),
    max_test_cases: Optional[int] = Form(None),
    capability_file: Optional[UploadFile] = File(None),
    project_ast_file: Optional[UploadFile] = File(None),
    max_input_tokens: int = Form(64000),
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
        
        capability_contract = await _load_capability_contract(capability_file)
        project_structure = await _load_project_structure(project_ast_file, files)
        result = await _service().generate_test_codes(
            process_title=process_title,
            environment_session_id=environment_session_id,
            source_files=files,
            model_name=model,
            api_key=api_key,
            session_id=session_id,
            environment_name=environment_name,
            output_format=output_format,
            custom_prompt=custom_prompt,
            max_test_cases=max_test_cases,
            capability_contract=capability_contract,
            project_structure=project_structure,
            max_input_tokens=max_input_tokens,
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
