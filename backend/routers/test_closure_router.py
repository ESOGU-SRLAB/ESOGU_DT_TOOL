"""
test_closure_router.py
----------------------
Test Closure API Router
Handles test cycle closure report generation with AI-powered analysis
"""

import logging
import aiohttp
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from services.test_closure_service import test_closure_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/test-closure",
    tags=["test-closure"]
)

# LLM Service URLs
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class SessionFilterRequest(BaseModel):
    """Request model for filtering sessions"""
    session_ids: Optional[List[str]] = None
    date_from: Optional[str] = None  # ISO format: "2025-11-01"
    date_to: Optional[str] = None


class ClosureReportRequest(BaseModel):
    """Request model for generating closure report"""
    session_ids: Optional[List[str]] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    model: str  # e.g., "llama3.2:3b", "gemini-2.0-flash-exp"
    api_key: Optional[str] = None  # Required for Gemini


class ClosureMetricsResponse(BaseModel):
    """Response model for closure metrics"""
    success: bool
    metrics: Optional[Dict[str, Any]] = None
    sessions_analyzed: Optional[int] = None
    error: Optional[str] = None


class ClosureReportResponse(BaseModel):
    """Response model for closure report generation"""
    success: bool
    report_content: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    sessions_analyzed: Optional[int] = None
    model_used: Optional[str] = None
    provider: Optional[str] = None
    timestamp: Optional[str] = None
    error: Optional[str] = None


def parse_model_to_provider_info(model_key: str) -> tuple[str, str]:
    """
    Convert model key to provider and model_name
    Returns (provider, model_name)
    """
    if model_key.startswith('gemini'):
        return ("gemini", model_key)
    else:
        return ("lm_studio", model_key)


def convert_to_lm_studio_format(model_key: str) -> str:
    """
    Convert frontend model key to LM Studio model format
    
    Examples:
        llama3.2:3b -> llama-3.2-3b-instruct
        llama3.2:1b -> llama-3.2-1b-instruct
        qwen2.5:7b -> qwen2.5-7b-instruct-1m
        codegeex4:9b -> (keep as is, or map if needed)
    
    Returns the converted model name for LM Studio
    """
    # Known mappings from frontend format to LM Studio format
    model_mappings = {
        "llama3.2:3b": "llama-3.2-3b-instruct",
        "llama3.2:1b": "llama-3.2-1b-instruct",
        "qwen2.5:7b": "qwen2.5-7b-instruct-1m",
        "openai/gpt-oss-20b": "openai/gpt-oss-20b",
    }
    
    # Check if we have an exact mapping
    if model_key in model_mappings:
        return model_mappings[model_key]
    
    # Try to auto-convert common patterns
    # Pattern: modelname:size -> modelname-size-instruct
    if ":" in model_key:
        parts = model_key.split(":")
        if len(parts) == 2:
            base_name = parts[0].replace(".", "-")  # llama3.2 -> llama-3-2
            size = parts[1]  # 3b
            # Try common patterns
            converted = f"{base_name}-{size}-instruct"
            logger.info(f"[convert_to_lm_studio_format] Auto-converted '{model_key}' -> '{converted}'")
            return converted
    
    # If no conversion needed, return as is
    logger.info(f"[convert_to_lm_studio_format] No conversion for '{model_key}', using as is")
    return model_key


async def call_llm(
    prompt: str,
    model: str,
    api_key: Optional[str] = None,
    max_tokens: int = 8000
) -> str:
    """
    Call LLM service (LM Studio or Gemini) for report generation
    
    Args:
        prompt: Prompt to send
        model: Model identifier (frontend format)
        api_key: API key for Gemini
        max_tokens: Max tokens to generate
        
    Returns:
        LLM response text
    """
    provider, model_name = parse_model_to_provider_info(model)
    logger.info(f"[call_llm] Called with model='{model}'")
    logger.info(f"[call_llm] Parsed: provider='{provider}', model_name='{model_name}'")
    
    # Convert to LM Studio format if needed
    if provider == "lm_studio":
        lm_studio_model = convert_to_lm_studio_format(model)
        logger.info(f"[call_llm] Converted to LM Studio format: '{model}' -> '{lm_studio_model}'")
    else:
        lm_studio_model = model

    
    try:
        if provider == "gemini":
            # Gemini API call
            if not api_key:
                raise ValueError("API key required for Gemini models")
            
            url = f"{GEMINI_API_BASE}/{model_name}:generateContent"
            params = {"key": api_key}
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": 0.7
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Gemini API error: {error_text}"
                        )
                    
                    result = await response.json()
                    
                    # Extract text from Gemini response
                    if "candidates" in result and result["candidates"]:
                        candidate = result["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            parts = candidate["content"]["parts"]
                            if parts and "text" in parts[0]:
                                return parts[0]["text"]
                    
                    raise ValueError("Unexpected Gemini response format")
        
        else:
            # LM Studio call
            # Use the converted LM Studio model format
            payload = {
                "model": lm_studio_model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
            logger.info(f"[call_llm] LM Studio payload: model='{payload['model']}'")
            logger.info(f"[call_llm] LM Studio URL: {LM_STUDIO_URL}")
            logger.info(f"[call_llm] Prompt length: {len(prompt)} chars")
            
            async with aiohttp.ClientSession() as session:
                # First, try to load the model in LM Studio
                try:
                    logger.info(f"[call_llm] Attempting to load model in LM Studio: {lm_studio_model}")
                    load_url = "http://localhost:1234/v1/models/load"
                    load_payload = {"model": lm_studio_model}
                    async with session.post(load_url, json=load_payload, timeout=aiohttp.ClientTimeout(total=15)) as load_response:
                        if load_response.status == 200:
                            logger.info(f"[call_llm] Model load request accepted for: {lm_studio_model}")
                            # Wait for model to load - check status periodically
                            import asyncio
                            logger.info(f"[call_llm] Waiting for model to load...")
                            
                            # Wait up to 30 seconds, checking every 3 seconds
                            max_wait_time = 30
                            check_interval = 3
                            total_waited = 0
                            
                            while total_waited < max_wait_time:
                                await asyncio.sleep(check_interval)
                                total_waited += check_interval
                                
                                # Check if model is loaded by querying /v1/models
                                try:
                                    async with session.get("http://localhost:1234/v1/models", timeout=aiohttp.ClientTimeout(total=5)) as models_response:
                                        if models_response.status == 200:
                                            models_data = await models_response.json()
                                            loaded_models = [m.get("id") for m in models_data.get("data", [])]
                                            logger.info(f"[call_llm] Currently loaded models: {loaded_models}")
                                            
                                            if lm_studio_model in loaded_models:
                                                logger.info(f"[call_llm] Model '{lm_studio_model}' is now loaded! (waited {total_waited}s)")
                                                break
                                            else:
                                                logger.info(f"[call_llm] Model not yet loaded, waiting... ({total_waited}s elapsed)")
                                except Exception as check_error:
                                    logger.warning(f"[call_llm] Could not check model status: {str(check_error)}")
                            
                            if total_waited >= max_wait_time:
                                logger.warning(f"[call_llm] Reached max wait time ({max_wait_time}s), proceeding anyway")
                        else:
                            logger.warning(f"[call_llm] Model load request returned status {load_response.status}")
                except Exception as load_error:
                    logger.warning(f"[call_llm] Could not load model (will try anyway): {str(load_error)}")
                
                # Now make the actual chat completion request
                async with session.post(LM_STUDIO_URL, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"LM Studio error for model '{model}': {error_text}")
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"LM Studio error with model '{model}': {error_text}"
                        )
                    
                    result = await response.json()
                    
                    # Extract text from LM Studio response
                    if "choices" in result and result["choices"]:
                        return result["choices"][0]["message"]["content"]
                    
                    raise ValueError("Unexpected LM Studio response format")
    
    except aiohttp.ClientError as e:
        error_msg = f"LLM service unavailable: {str(e)}"
        logger.error(f"LLM API error: {error_msg}")
        raise HTTPException(status_code=503, detail=error_msg)
    except Exception as e:
        error_msg = f"LLM error: {type(e).__name__}: {str(e)}"
        logger.error(f"LLM call error: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/metrics", response_model=ClosureMetricsResponse)
async def get_closure_metrics(request: SessionFilterRequest):
    """
    Calculate test closure metrics without AI report generation
    
    Returns aggregated metrics from specified sessions
    """
    try:
        logger.info(f"[TestClosure] Calculating metrics for sessions: {request.session_ids}")
        
        result = await test_closure_service.generate_closure_report(
            session_ids=request.session_ids,
            date_from=request.date_from,
            date_to=request.date_to
        )
        
        if not result["success"]:
            return ClosureMetricsResponse(
                success=False,
                error=result.get("error", "Failed to calculate metrics")
            )
        
        return ClosureMetricsResponse(
            success=True,
            metrics=result["metrics"],
            sessions_analyzed=result["sessions_analyzed"]
        )
        
    except Exception as e:
        logger.error(f"Error calculating closure metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate metrics: {str(e)}"
        )


@router.post("/generate-report", response_model=ClosureReportResponse)
async def generate_closure_report(request: ClosureReportRequest):
    """
    Generate AI-powered test closure report
    
    Steps:
    1. Aggregate metrics from sessions
    2. Generate AI prompt with metrics
    3. Call LLM to generate comprehensive report
    4. Return report with metadata
    """
    try:
        logger.info(f"[TestClosure] Generating report for sessions: {request.session_ids}")
        logger.info(f"[TestClosure] Using model: {request.model}")
        logger.info(f"[TestClosure] Request object: session_ids={request.session_ids}, model={request.model}, api_key={'***' if request.api_key else None}")
        
        # Step 1: Generate metrics and prompt
        result = await test_closure_service.generate_closure_report(
            session_ids=request.session_ids,
            date_from=request.date_from,
            date_to=request.date_to
        )
        
        if not result["success"]:
            return ClosureReportResponse(
                success=False,
                error=result.get("error", "Failed to generate closure data")
            )
        
        metrics = result["metrics"]
        prompt = result["prompt"]
        
        logger.info(f"[TestClosure] Metrics aggregated. Calling LLM...")
        logger.info(f"[TestClosure] Prompt length: {len(prompt)} characters")
        
        # Step 2: Call LLM to generate report
        provider, model_name = parse_model_to_provider_info(request.model)
        
        report_content = await call_llm(
            prompt=prompt,
            model=request.model,
            api_key=request.api_key,
            max_tokens=8000  # Large token limit for comprehensive report
        )
        
        logger.info(f"[TestClosure] Report generated successfully")
        logger.info(f"[TestClosure] Report length: {len(report_content)} characters")
        
        # Step 3: Return response
        return ClosureReportResponse(
            success=True,
            report_content=report_content,
            metrics=metrics,
            sessions_analyzed=result["sessions_analyzed"],
            model_used=model_name,
            provider=provider,
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating closure report: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(traceback.format_exc())
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate closure report: {str(e)}"
        )


@router.get("/available-sessions")
async def get_available_sessions(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """
    Get list of available sessions for closure analysis
    
    Query params:
        date_from: Start date (ISO format)
        date_to: End date (ISO format)
    """
    try:
        sessions = await test_closure_service.fetch_sessions_for_closure(
            date_from=date_from,
            date_to=date_to
        )
        
        # Format sessions for frontend
        session_list = []
        for session in sessions:
            processes = session.get("processes", {})
            process_names = list(processes.keys())
            
            session_list.append({
                "session_id": session.get("session_id"),
                "created_at": session.get("created_at"),
                "process_count": len(process_names),
                "processes": process_names
            })
        
        return {
            "success": True,
            "sessions": session_list,
            "total_count": len(session_list)
        }
        
    except Exception as e:
        logger.error(f"Error fetching available sessions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch sessions: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "test-closure",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/lm-studio/models")
async def get_lm_studio_models():
    """Get available models from LM Studio"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:1234/v1/models", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    data = await response.json()
                    models = data.get("data", [])
                    return {
                        "success": True,
                        "models": models,
                        "count": len(models)
                    }
                else:
                    return {
                        "success": False,
                        "error": f"LM Studio returned status {response.status}"
                    }
    except Exception as e:
        return {
            "success": False,
            "error": f"Could not connect to LM Studio: {str(e)}"
        }
