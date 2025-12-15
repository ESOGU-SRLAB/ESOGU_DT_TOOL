"""
test_closure.py
---------------
STLC'nin Test Closure adımına ait işlemleri yönetir.
AI-powered test cycle closure report generation
"""

from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


async def run_step(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute Test Closure step
    
    Args:
        input_data: Dictionary containing:
            - session_ids: List of session IDs to analyze
            - date_from: Optional start date
            - date_to: Optional end date
            - model: LLM model to use
            - api_key: Optional API key for Gemini models
            
    Returns:
        Dictionary with closure report and metrics
    """
    from services.test_closure_service import test_closure_service
    
    try:
        session_ids = input_data.get("session_ids")
        date_from = input_data.get("date_from")
        date_to = input_data.get("date_to")
        
        logger.info(f"[TestClosure] Running test closure step")
        logger.info(f"[TestClosure] Session IDs: {session_ids}")
        
        # Generate closure metrics and prompt
        result = await test_closure_service.generate_closure_report(
            session_ids=session_ids,
            date_from=date_from,
            date_to=date_to
        )
        
        if not result["success"]:
            return {
                "step": "testClosure",
                "status": "error",
                "error": result.get("error", "Failed to generate closure report"),
                "metrics": None
            }
        
        return {
            "step": "testClosure",
            "status": "success",
            "metrics": result["metrics"],
            "prompt": result["prompt"],
            "sessions_analyzed": result["sessions_analyzed"],
            "message": "Test closure analysis completed successfully"
        }
        
    except Exception as e:
        logger.error(f"[TestClosure] Error in run_step: {str(e)}")
        return {
            "step": "testClosure",
            "status": "error",
            "error": str(e),
            "metrics": None
        }
