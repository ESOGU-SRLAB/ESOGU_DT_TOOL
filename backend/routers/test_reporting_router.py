"""
test_reporting_router.py
------------------------
API Router for Test Reporting functionality
Handles comprehensive report generation from STLC processes
"""

import logging
import aiohttp
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from services.test_reporting_service import test_reporting_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/test-reporting",
    tags=["test-reporting"]
)

# LLM Service URL (reuse existing infrastructure)
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class SessionListRequest(BaseModel):
    """Request model for fetching available sessions"""
    process_names: Optional[List[str]] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


class SessionListResponse(BaseModel):
    """Response model for session list"""
    success: bool
    sessions: List[Dict[str, Any]]
    total_count: int


class ReportGenerationRequest(BaseModel):
    """Request model for generating a comprehensive report"""
    session_ids: List[str]  # Changed from session_id to session_ids for multiple sessions
    model: str  # e.g., "llama3.2:1b", "gemini-2.5-pro"
    api_key: Optional[str] = None  # Required for Gemini
    analysis_depth: str = "detailed"  # "summary" | "detailed" | "deep"


class ReportGenerationResponse(BaseModel):
    """Response model for report generation"""
    success: bool
    report_content: Optional[str] = None
    report_id: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ProcessDataRequest(BaseModel):
    """Request model for fetching process data"""
    session_id: str
    process_name: str


class ProcessDataResponse(BaseModel):
    """Response model for process data"""
    success: bool
    process_name: str
    data: Optional[Dict[str, Any]] = None
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


async def call_llm(
    prompt: str,
    model: str,
    api_key: Optional[str] = None,
    max_tokens: int = 4000
) -> str:
    """
    Call LLM service (LM Studio or Gemini)
    
    Args:
        prompt: Prompt to send
        model: Model identifier
        api_key: API key for Gemini
        max_tokens: Max tokens to generate
        
    Returns:
        LLM response text
    """
    provider, model_name = parse_model_to_provider_info(model)
    
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
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(LM_STUDIO_URL, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"LM Studio error: {error_text}"
                        )
                    
                    result = await response.json()
                    
                    # Extract text from LM Studio response
                    if "choices" in result and result["choices"]:
                        return result["choices"][0]["message"]["content"]
                    
                    raise ValueError("Unexpected LM Studio response format")
    
    except aiohttp.ClientError as e:
        error_msg = f"LLM service unavailable: {str(e)}"
        logger.error(f"LLM API error: {error_msg}")
        logger.error(f"Model: {model}, Provider: {provider}, Model name: {model_name}")
        raise HTTPException(status_code=503, detail=error_msg)
    except Exception as e:
        error_msg = f"LLM error: {type(e).__name__}: {str(e)}"
        logger.error(f"LLM call error: {error_msg}")
        logger.error(f"Model: {model}, Provider: {provider}, Model name: {model_name}")
        logger.error(f"Prompt length: {len(prompt)} characters")
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/sessions", response_model=SessionListResponse)
async def get_available_sessions(request: SessionListRequest):
    """
    Fetch available sessions with process data
    
    Returns list of sessions with process counts
    """
    try:
        sessions = await test_reporting_service.fetch_available_sessions(
            process_names=request.process_names,
            date_from=request.date_from,
            date_to=request.date_to
        )
        
        return SessionListResponse(
            success=True,
            sessions=sessions,
            total_count=len(sessions)
        )
    
    except Exception as e:
        logger.error(f"Error fetching sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-report", response_model=ReportGenerationResponse)
async def generate_comprehensive_report(request: ReportGenerationRequest):
    """
    Generate comprehensive test report from selected processes across multiple sessions
    
    This endpoint:
    1. Fetches session data for all selected sessions and processes
    2. Creates smart chunks from each process in each session
    3. Generates intermediate summaries via LLM
    4. Synthesizes final comprehensive comparison report
    5. Saves report to database
    """
    try:
        logger.info(f"Starting report generation for {len(request.session_ids)} sessions")
        logger.info(f"Sessions: {request.session_ids}")
        logger.info(f"Model: {request.model}, Analysis depth: {request.analysis_depth}")
        
        # Step 1: Fetch session data for all sessions (all processes)
        all_session_data = []
        for session_id in request.session_ids:
            session_data = await test_reporting_service.fetch_session_data(
                session_id=session_id,
                selected_processes=None  # Fetch all processes for this session
            )
            
            logger.info(f"Fetched session {session_id}: {len(session_data.get('processes', {}))} processes")
            logger.info(f"Process names: {list(session_data.get('processes', {}).keys())}")
            
            if session_data.get("processes"):
                all_session_data.append({
                    "session_id": session_id,
                    "data": session_data
                })
            else:
                logger.warning(f"No processes found for session {session_id}")
        
        if not all_session_data:
            raise ValueError("No process data found for selected sessions and processes")
        
        logger.info(f"Total sessions with data: {len(all_session_data)}")
        
        # Step 2: Create chunks and generate intermediate summaries
        intermediate_summaries = []
        total_chunks = 0
        processed_chunks = 0
        
        for session_info in all_session_data:
            session_id = session_info["session_id"]
            session_data = session_info["data"]
            
            for process_name, process_data in session_data["processes"].items():
                # Create chunks for this process
                chunks = test_reporting_service.create_chunks(process_name, process_data)
                total_chunks += len(chunks)
                
                logger.info(f"Processing {len(chunks)} chunks for {process_name} in session {session_id}")
                
                # Process each chunk
                for chunk in chunks:
                    # Create intermediate prompt
                    prompt = test_reporting_service.create_intermediate_prompt(
                        chunk=chunk,
                        analysis_depth=request.analysis_depth
                    )
                    
                    # Call LLM for intermediate summary
                    logger.info(f"Analyzing chunk {chunk['chunk_index'] + 1}/{len(chunks)} of {process_name} (Session: {session_id})")
                    
                    summary = await call_llm(
                        prompt=prompt,
                        model=request.model,
                        api_key=request.api_key,
                        max_tokens=2000  # Intermediate summaries can be shorter
                    )
                    
                    intermediate_summaries.append({
                        "session_id": session_id,
                        "process_name": process_name,
                        "chunk_index": chunk["chunk_index"],
                        "total_chunks": chunk["total_chunks"],
                        "summary": summary
                    })
                    
                    processed_chunks += 1
                    logger.info(f"Progress: {processed_chunks}/{total_chunks} chunks processed")
        
        # Step 3: Generate final synthesis for multiple session comparison
        logger.info("Generating final synthesis report for multiple sessions...")
        
        # Prepare session metadata for all sessions
        sessions_metadata = []
        for session_info in all_session_data:
            session_data = session_info["data"]
            sessions_metadata.append({
                "session_id": session_info["session_id"],
                "session_timestamp": session_data.get("session_timestamp", ""),
                "process_name": session_data.get("process_name", "")
            })
        
        final_prompt = test_reporting_service.create_final_synthesis_prompt(
            intermediate_summaries=intermediate_summaries,
            session_metadata={
                "session_ids": request.session_ids,
                "sessions": sessions_metadata,
                "comparison_mode": len(request.session_ids) > 1
            },
            analysis_depth=request.analysis_depth,
            raw_session_data=all_session_data  # Pass raw data for LLM reference
        )
        
        logger.info(f"Final prompt length: {len(final_prompt)} characters")
        logger.info(f"Prompt contains {len(all_session_data)} raw session data entries")
        
        # Call LLM for final report
        logger.info(f"Calling LLM with model: {request.model}")
        final_report = await call_llm(
            prompt=final_prompt,
            model=request.model,
            api_key=request.api_key,
            max_tokens=12000  # Final report can be longer for multiple sessions
        )
        
        # Clean up JSON if it's wrapped in markdown code blocks
        cleaned_report = final_report.strip()
        if cleaned_report.startswith('```json'):
            # Remove ```json from start and ``` from end
            cleaned_report = cleaned_report[7:]  # Remove ```json
            if cleaned_report.endswith('```'):
                cleaned_report = cleaned_report[:-3]  # Remove ```
            cleaned_report = cleaned_report.strip()
        elif cleaned_report.startswith('```'):
            # Remove ``` from start and end
            cleaned_report = cleaned_report[3:]
            if cleaned_report.endswith('```'):
                cleaned_report = cleaned_report[:-3]
            cleaned_report = cleaned_report.strip()
        
        # Try to validate JSON
        try:
            import json
            json.loads(cleaned_report)
            logger.info("✅ LLM response is valid JSON")
            final_report = cleaned_report
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ LLM response is not valid JSON: {str(e)}")
            logger.warning(f"First 500 chars: {cleaned_report[:500]}")
            # Keep original response if JSON parsing fails (might be markdown)
            final_report = final_report
        
        # Step 4: Save report to database
        # Collect all unique process names from intermediate summaries
        processes_included = list(set(
            summary["process_name"] for summary in intermediate_summaries
        ))
        
        report_metadata = {
            "session_ids": request.session_ids,
            "sessions_analyzed": len(request.session_ids),
            "processes_included": processes_included,
            "model_used": request.model,
            "analysis_depth": request.analysis_depth,
            "chunks_processed": total_chunks,
            "timestamp": datetime.now().isoformat()
        }
        
        report_id = await test_reporting_service.save_report(
            session_ids=request.session_ids,  # Changed to session_ids
            report_content=final_report,
            metadata=report_metadata
        )
        
        logger.info(f"Report generation completed: {report_id}")
        
        return ReportGenerationResponse(
            success=True,
            report_content=final_report,
            report_id=report_id,
            metadata=report_metadata
        )
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return ReportGenerationResponse(
            success=False,
            error=str(e)
        )
    
    except HTTPException as e:
        logger.error(f"HTTP error: {str(e.detail)}")
        return ReportGenerationResponse(
            success=False,
            error=str(e.detail)
        )
    
    except Exception as e:
        logger.error(f"Unexpected error during report generation: {str(e)}")
        return ReportGenerationResponse(
            success=False,
            error=f"Report generation failed: {str(e)}"
        )


@router.get("/process/{session_id}/{process_name}", response_model=ProcessDataResponse)
async def get_process_data(session_id: str, process_name: str):
    """
    Fetch specific process data from a session
    
    Useful for previewing process data before report generation
    """
    try:
        session_data = await test_reporting_service.fetch_session_data(
            session_id=session_id,
            selected_processes=[process_name]
        )
        
        process_data = session_data.get("processes", {}).get(process_name)
        
        if not process_data:
            raise ValueError(f"Process {process_name} not found in session {session_id}")
        
        return ProcessDataResponse(
            success=True,
            process_name=process_name,
            data=process_data
        )
    
    except ValueError as e:
        return ProcessDataResponse(
            success=False,
            process_name=process_name,
            error=str(e)
        )
    
    except Exception as e:
        logger.error(f"Error fetching process data: {str(e)}")
        return ProcessDataResponse(
            success=False,
            process_name=process_name,
            error=str(e)
        )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "test-reporting",
        "timestamp": datetime.now().isoformat()
    }
