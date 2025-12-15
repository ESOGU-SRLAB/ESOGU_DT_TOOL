"""
test_reporting_prompt_router.py
--------------------------------
Test Reporting prompt yönetimi için API endpoint'leri
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Dict, Any
from core.database import get_db

router = APIRouter(tags=["test_reporting_prompts"])

class PromptSaveResponse(BaseModel):
    success: bool
    message: str

class TestReportingPromptResponse(BaseModel):
    prompt_text: str
    system_suffix: str
    description: str

@router.get("/api/prompts/test-reporting", response_model=TestReportingPromptResponse)
async def get_test_reporting_prompt():
    """
    Test reporting için prompt ve system_suffix döndürür.
    """
    try:
        db = get_db()
        
        # Fetch from MongoDB
        prompt_doc = db.test_reporting_prompt.find_one({"process_type": "test_reporting"})
        
        if prompt_doc:
            return TestReportingPromptResponse(
                prompt_text=prompt_doc.get("prompt_text", ""),
                system_suffix=prompt_doc.get("system_suffix", ""),
                description=prompt_doc.get("description", "")
            )
        else:
            # Default fallback
            return TestReportingPromptResponse(
                prompt_text="""You are an expert Test Manager analyzing STLC session data.

Generate a comprehensive test report covering:
1. Executive Summary
2. Process Analysis
3. Quality Assessment
4. Metrics & KPIs
5. Recommendations

Session Data:
{session_data}""",
                system_suffix="""Analysis: {analysis_depth}
Sessions: {session_count}
Data:
{session_data}""",
                description="Default test reporting prompt"
            )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/prompts/test-reporting", response_model=PromptSaveResponse)
async def save_test_reporting_prompt(data: Dict[str, Any] = Body(...)):
    """
    Test reporting için yeni prompt ekler/günceller.
    """
    try:
        db = get_db()
        
        new_prompt = data.get("prompt_text", "").strip()
        
        if not new_prompt:
            raise ValueError("Prompt text cannot be empty")
        
        # Update or insert
        from datetime import datetime
        
        result = db.test_reporting_prompt.update_one(
            {"process_type": "test_reporting"},
            {
                "$set": {
                    "prompt_text": new_prompt,
                    "updated_at": datetime.now()
                }
            },
            upsert=True
        )
        
        if result.modified_count > 0 or result.upserted_id:
            return PromptSaveResponse(
                success=True,
                message="Test reporting prompt saved successfully"
            )
        else:
            return PromptSaveResponse(
                success=False,
                message="No changes made to prompt"
            )
            
    except Exception as e:
        return PromptSaveResponse(
            success=False,
            message=f"Error saving prompt: {str(e)}"
        )
