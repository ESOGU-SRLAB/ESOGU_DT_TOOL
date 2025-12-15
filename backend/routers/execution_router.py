"""                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    
execution_router.py
-----------------------
Test Execution API Router
Handles test code execution requests by fetching test code from MongoDB 
and communicating with the MCP server
"""

import logging
import aiohttp
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from core.database import get_database
import json
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/test-execution",
    tags=["test-execution"]
)

def parse_model_to_provider_info(model_key: str) -> tuple[str, str]:
    """
    Convert model key to provider and model_name
    Returns (provider, model_name)
    """
    # API models (Gemini)
    if model_key.startswith('gemini'):
        return ("gemini", model_key)
    
    # Local models (LM Studio compatible)
    else:
        return ("lm_studio", model_key)

# MCP Server configuration
MCP_SERVER_URL = "http://localhost:8001"

class TestExecutionRequest(BaseModel):
    process_name: str  # Required - Test Code Generation process name
    model: str  # Model key (e.g., "llama3.2:1b", "gemini-2.5-flash")
    api_key: Optional[str] = None  # Required for API models

class SelectedRecordsExecutionRequest(BaseModel):
    record_ids: List[str]  # Selected record IDs to execute
    model: str  # Model key (e.g., "llama3.2:1b", "gemini-2.5-flash")
    api_key: Optional[str] = None  # Required for API models

class SelectedTestsExecutionRequest(BaseModel):
    test_ids: List[str]  # Selected individual test IDs to execute
    model: str  # Model key (e.g., "llama3.2:1b", "gemini-2.5-flash")
    api_key: Optional[str] = None  # Required for API models

class TestExecutionResponse(BaseModel):
    model_config = {"protected_namespaces": ()}  # Allow model_* field names
    
    success: bool
    terminal_output: Optional[str] = None
    error: Optional[str] = None
    provider: Optional[str] = None
    model_used: Optional[str] = None
    timestamp: Optional[str] = None

class IndividualTest(BaseModel):
    test_id: str  # Unique identifier for the test
    session_id: str
    test_index: int  # Index in the generated_tests array
    code_snippet: str  # First 200 characters
    full_code: str
    test_name: Optional[str] = None  # Test name if available
    source_code: Optional[str] = None  # Source code context for the test

class TestCodeRecord(BaseModel):
    id: str
    session_id: str
    timestamp: str
    code_snippet: str  # First 200 characters
    full_code: str
    status: str = "available"

class IndividualTestsResponse(BaseModel):
    success: bool
    process_name: str
    tests: List[IndividualTest]
    total_count: int

class ProcessRecordsResponse(BaseModel):
    success: bool
    process_name: str
    records: List[TestCodeRecord]
    total_count: int

async def fetch_test_code_from_db(session_id: str) -> str:
    """
    Fetch test code from MongoDB session_history collection
    Path: processes.test_code_generation.output
    """
    try:
        db = await get_database()
        collection = db["session_history"]
        
        # Find the document with the specific session_id
        document = await collection.find_one({"session_id": session_id})
        
        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"No session found with session_id: {session_id}"
            )
        
        # Navigate to test code generation output
        processes = document.get("processes", {})
        test_code_gen = processes.get("test_code_generation", {})
        output = test_code_gen.get("output", {})
        
        # Try different possible paths where test code might be stored
        test_code = None
        
        # Path 1: Direct test_code field
        if "test_code" in output:
            test_code = output["test_code"]
        
        # Path 2: In test_cases array
        elif "test_cases" in output:
            test_cases = output["test_cases"]
            if isinstance(test_cases, list) and test_cases:
                # Combine all test cases
                test_code = "\n\n".join([
                    case.get("code", "") if isinstance(case, dict) else str(case)
                    for case in test_cases
                ])
        
        # Path 3: In generated_code field
        elif "generated_code" in output:
            test_code = output["generated_code"]
        
        # Path 4: In content field (markdown format)
        elif "content" in output:
            content = output["content"]
            if isinstance(content, str):
                # Extract code blocks from markdown
                import re
                code_blocks = re.findall(r'```(?:python|java|javascript|js)?\n(.*?)\n```', content, re.DOTALL)
                if code_blocks:
                    test_code = "\n\n".join(code_blocks)
                else:
                    test_code = content
        
        if not test_code:
            raise HTTPException(
                status_code=404,
                detail=f"No test code found in session {session_id}. Available fields: {list(output.keys())}"
            )
        
        logger.info(f"Successfully fetched test code for session {session_id}")
        return test_code.strip()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching test code from database: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

async def fetch_process_records(process_name: str) -> List[TestCodeRecord]:
    """
    Fetch all test code records for a specific process name
    """
    try:
        db = await get_database()
        collection = db["session_history"]
        
        # Find all documents with matching code_generation_process_name
        query = {
            "processes.test_code_generation.code_generation_process_name": process_name
        }
        
        documents = await collection.find(query).sort("timestamp", -1).to_list(None)
        
        records = []
        
        for document in documents:
            try:
                # Navigate to test code generation output
                processes = document.get("processes", {})
                test_code_gen = processes.get("test_code_generation", {})
                output = test_code_gen.get("output", {})
                
                # Extract test code using the same logic as fetch_test_code_by_process_name
                full_code = None
                
                # Path 1: Direct code field
                if "code" in output:
                    full_code = output["code"]
                
                # Path 2: Generated tests array
                elif "generated_tests" in output:
                    generated_tests = output["generated_tests"]
                    if isinstance(generated_tests, list) and generated_tests:
                        full_code = "\n\n".join([
                            test.get("code", "") if isinstance(test, dict) else str(test)
                            for test in generated_tests
                        ])
                
                # Path 3: In data.generated_tests
                elif "data" in output and "generated_tests" in output["data"]:
                    generated_tests = output["data"]["generated_tests"]
                    if isinstance(generated_tests, list) and generated_tests:
                        full_code = "\n\n".join([
                            test.get("code", "") if isinstance(test, dict) else str(test)
                            for test in generated_tests
                        ])
                
                # Path 4: Content field with code extraction
                elif "content" in output:
                    content = output["content"]
                    if isinstance(content, str) and "```" in content:
                        # Extract code blocks
                        import re
                        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', content, re.DOTALL)
                        if code_blocks:
                            full_code = "\n\n".join(code_blocks)
                
                if full_code:
                    # Create record
                    record_id = str(document.get("_id"))
                    session_id = document.get("session_id", "")
                    timestamp = document.get("timestamp", "")
                    
                    # Create snippet (first 200 chars)
                    code_snippet = (full_code[:200] + "...") if len(full_code) > 200 else full_code
                    
                    record = TestCodeRecord(
                        id=record_id,
                        session_id=session_id,
                        timestamp=timestamp,
                        code_snippet=code_snippet,
                        full_code=full_code,
                        status="available"
                    )
                    
                    records.append(record)
                    
            except Exception as e:
                logger.warning(f"Error processing document {document.get('_id', 'unknown')}: {str(e)}")
                continue
        
        return records
        
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

async def fetch_selected_records_code(record_ids: List[str]) -> str:
    """
    Fetch and combine test code from selected records
    """
    try:
        db = await get_database()
        collection = db["session_history"]
        
        combined_code = []
        
        for record_id in record_ids:
            try:
                # Convert string ID to ObjectId
                from bson import ObjectId
                object_id = ObjectId(record_id)
                
                document = await collection.find_one({"_id": object_id})
                
                if not document:
                    logger.warning(f"Record not found: {record_id}")
                    continue
                
                # Navigate to test code generation output
                processes = document.get("processes", {})
                test_code_gen = processes.get("test_code_generation", {})
                output = test_code_gen.get("output", {})
                
                # Extract test code using the same logic
                full_code = None
                
                # Path 1: Direct code field
                if "code" in output:
                    full_code = output["code"]
                
                # Path 2: Generated tests array
                elif "generated_tests" in output:
                    generated_tests = output["generated_tests"]
                    if isinstance(generated_tests, list) and generated_tests:
                        full_code = "\n\n".join([
                            test.get("code", "") if isinstance(test, dict) else str(test)
                            for test in generated_tests
                        ])
                
                # Path 3: In data.generated_tests
                elif "data" in output and "generated_tests" in output["data"]:
                    generated_tests = output["data"]["generated_tests"]
                    if isinstance(generated_tests, list) and generated_tests:
                        full_code = "\n\n".join([
                            test.get("code", "") if isinstance(test, dict) else str(test)
                            for test in generated_tests
                        ])
                
                # Path 4: Content field with code extraction
                elif "content" in output:
                    content = output["content"]
                    if isinstance(content, str) and "```" in content:
                        # Extract code blocks
                        import re
                        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', content, re.DOTALL)
                        if code_blocks:
                            full_code = "\n\n".join(code_blocks)
                
                if full_code:
                    timestamp = document.get("timestamp", "")
                    session_id = document.get("session_id", record_id[:8])
                    combined_code.append(f"# Record ID: {record_id}\n# Session: {session_id}\n# Timestamp: {timestamp}\n\n{full_code}")
                    
            except Exception as e:
                logger.warning(f"Error processing record {record_id}: {str(e)}")
                continue
        
        if not combined_code:
            raise HTTPException(
                status_code=404,
                detail="No valid test code found in selected records"
            )
        
        return "\n\n" + "="*80 + "\n\n".join(combined_code)
        
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

async def fetch_test_code_by_process_name(process_name: str) -> str:
    """
    Fetch test code from MongoDB by code_generation_process_name
    """
    try:
        db = await get_database()
        collection = db["session_history"]
        
        # Find documents with matching code_generation_process_name
        query = {
            "processes.test_code_generation.code_generation_process_name": process_name
        }
        
        documents = await collection.find(query).sort("timestamp", -1).limit(1).to_list(1)
        
        if not documents:
            raise HTTPException(
                status_code=404,
                detail=f"No test code found for process name: {process_name}"
            )
        
        document = documents[0]
        
        # Navigate to test code generation output
        processes = document.get("processes", {})
        test_code_gen = processes.get("test_code_generation", {})
        output = test_code_gen.get("output", {})
        
        # Try to find code in various fields
        test_code = None
        
        # Path 1: Direct code field
        if "code" in output:
            test_code = output["code"]
        
        # Path 2: Generated tests array
        elif "generated_tests" in output:
            generated_tests = output["generated_tests"]
            if isinstance(generated_tests, list) and generated_tests:
                # Combine all generated test codes
                test_code = "\n\n".join([
                    test.get("code", "") if isinstance(test, dict) else str(test)
                    for test in generated_tests
                ])
        
        # Path 3: In data.generated_tests
        elif "data" in output:
            data = output["data"]
            if isinstance(data, dict) and "generated_tests" in data:
                generated_tests = data["generated_tests"]
                if isinstance(generated_tests, list) and generated_tests:
                    test_code = "\n\n".join([
                        test.get("code", "") if isinstance(test, dict) else str(test)
                        for test in generated_tests
                    ])
        
        if not test_code:
            # Fallback: try to get any string value that might contain code
            for key, value in output.items():
                if isinstance(value, str) and len(value) > 50:  # Assume code is longer than 50 chars
                    test_code = value
                    break
        
        if not test_code:
            raise HTTPException(
                status_code=404,
                detail=f"No executable test code found for process: {process_name}. Available fields: {list(output.keys())}"
            )
        
        logger.info(f"Successfully fetched test code for process name: {process_name}")
        return test_code.strip()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching test code by process name: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

async def call_mcp_server(test_code: str, model_key: str, api_key: Optional[str] = None, source_code: Optional[str] = None, timeout: int = 90) -> Dict[str, Any]:
    """
    Call the MCP server with JSON-RPC 2.0 protocol
    Optionally includes source code for context-aware execution
    """
    try:
        # Parse model key to get provider and model name
        provider, model_name = parse_model_to_provider_info(model_key)
        
        # Prepare JSON-RPC 2.0 request
        rpc_request = {
            "jsonrpc": "2.0",
            "method": "executeTest",
            "params": {
                "test_code": test_code,
                "provider": provider,
                "model_name": model_name
            },
            "id": "test-execution-" + str(hash(test_code))[:8]
        }
        
        # Add source code if provided (for context-aware execution)
        if source_code:
            rpc_request["params"]["source_code"] = source_code
            logger.info(f"[call_mcp_server] Including source code context ({len(source_code)} chars)")
        
        # Add API key if provided
        if api_key:
            rpc_request["params"]["api_key"] = api_key
        
        logger.info(f"[call_mcp_server] Sending JSON-RPC request to {MCP_SERVER_URL}/jsonrpc")
        logger.info(f"[call_mcp_server] Method: {rpc_request['method']}")
        logger.info(f"[call_mcp_server] Provider: {provider}, Model: {model_name}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{MCP_SERVER_URL}/jsonrpc",
                json=rpc_request,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"[call_mcp_server] HTTP error {response.status}: {error_text}")
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"MCP Server error: {error_text}"
                    )
                
                result = await response.json()
                logger.info(f"[call_mcp_server] Raw response: {result}")
                
                # Check for JSON-RPC error (error field must exist AND not be None)
                if result.get("error") is not None:
                    error_info = result["error"]
                    logger.error(f"[call_mcp_server] JSON-RPC error: {error_info}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"MCP execution error: {error_info.get('message', 'Unknown error')}"
                    )
                
                # Get the result field from JSON-RPC response
                rpc_result = result.get("result")
                if rpc_result is None:
                    logger.error(f"[call_mcp_server] No 'result' field in response: {result}")
                    raise HTTPException(
                        status_code=500,
                        detail="Invalid MCP server response: missing 'result' field"
                    )
                
                logger.info(f"[call_mcp_server] Success: {rpc_result.get('success', False)}")
                return rpc_result
                
    except aiohttp.ClientError as e:
        logger.error(f"MCP server connection error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to MCP server: {str(e)}"
        )
    except Exception as e:
        logger.error(f"MCP server call error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"MCP server error: {str(e)}"
        )

@router.post("/execute", response_model=TestExecutionResponse)
async def execute_tests(request: TestExecutionRequest):
    """
    Main endpoint for test execution
    Fetches test code from MongoDB and executes it via MCP server
    """
    try:
        provider, _ = parse_model_to_provider_info(request.model)
        logger.info(f"Test execution request: process_name={request.process_name}, model={request.model}, provider={provider}")
        
        # Step 1: Fetch test code from MongoDB by process name
        test_code = await fetch_test_code_by_process_name(request.process_name)
        
        # Step 2: Call MCP server to execute the test code
        mcp_result = await call_mcp_server(
            test_code=test_code,
            model_key=request.model,
            api_key=request.api_key
        )
        
        # Get provider info for response
        provider, _ = parse_model_to_provider_info(request.model)
        
        # Step 3: Return formatted response
        return TestExecutionResponse(
            success=mcp_result.get("success", False),
            terminal_output=mcp_result.get("terminal_output", ""),
            provider=mcp_result.get("provider", provider),
            model_used=mcp_result.get("model_used", request.model),
            timestamp=mcp_result.get("timestamp", ""),
            error=mcp_result.get("error", None)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test execution failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Test execution failed: {str(e)}"
        )

@router.get("/session/{session_id}/test-code")
async def get_test_code(session_id: str):
    """
    [DEPRECATED] Get test code for a specific session - Use process name instead
    """
    logger.warning("DEPRECATED: session-based test code loading is deprecated. Use process name instead.")
    try:
        test_code = await fetch_test_code_from_db(session_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "session_id": session_id,
                "test_code": test_code,
                "length": len(test_code),
                "deprecated": True,
                "message": "This endpoint is deprecated. Use /process/{process_name}/test-code instead."
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching test code: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching test code: {str(e)}"
        )

@router.get("/mcp/status")
async def check_mcp_status():
    """
    Check MCP server status and available providers
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{MCP_SERVER_URL}/providers/status",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                if response.status == 200:
                    return await response.json()
                else:
                    return {
                        "status": "error",
                        "message": f"MCP server returned status {response.status}"
                    }
                    
    except Exception as e:
        logger.error(f"MCP status check failed: {str(e)}")
        return {
            "status": "error",
            "message": f"Cannot connect to MCP server: {str(e)}"
        }

@router.get("/providers")
async def get_available_providers():
    """
    Get list of available AI providers for test execution
    """
    return {
        "providers": [
            {
                "id": "lm_studio",
                "name": "LM Studio",
                "type": "local",
                "description": "Local AI models via LM Studio",
                "requires_api_key": False
            },
            {
                "id": "gemini",
                "name": "Google Gemini",
                "type": "api",
                "description": "Google Gemini AI via API",
                "requires_api_key": True
            }
        ]
    }

@router.get("/process-names")
async def get_available_process_names():
    """
    Get list of available test code generation process names
    """
    try:
        db = await get_database()
        collection = db["session_history"]
        
        # Find all documents with test_code_generation process and get unique process names
        pipeline = [
            {"$match": {"processes.test_code_generation.code_generation_process_name": {"$exists": True, "$ne": ""}}},
            {"$project": {"process_name": "$processes.test_code_generation.code_generation_process_name"}},
            {"$group": {"_id": "$process_name", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        
        results = list(await collection.aggregate(pipeline).to_list(None))
        
        process_names = [
            {
                "name": result["_id"],
                "count": result["count"]
            }
            for result in results
        ]
        
        return {
            "success": True,
            "process_names": process_names,
            "total": len(process_names)
        }
        
    except Exception as e:
        logger.error(f"Error fetching process names: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

@router.get("/process/{process_name}/test-code")
async def get_test_code_by_process_name(process_name: str):
    """
    Get test code by process name
    """
    try:
        test_code = await fetch_test_code_by_process_name(process_name)
        return {
            "success": True,
            "test_code": test_code,
            "process_name": process_name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting test code by process name: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )

@router.get("/process/{process_name}/records")
async def get_process_records(process_name: str) -> ProcessRecordsResponse:
    """
    Get all test code records for a specific process name
    """
    try:
        records = await fetch_process_records(process_name)
        return ProcessRecordsResponse(
            success=True,
            process_name=process_name,
            records=records,
            total_count=len(records)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting process records: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )

@router.post("/execute-selected")
async def execute_selected_records(request: SelectedRecordsExecutionRequest) -> TestExecutionResponse:
    """
    Execute test code from selected records
    """
    try:
        provider, _ = parse_model_to_provider_info(request.model)
        logger.info(f"Selected records execution: record_ids={len(request.record_ids)}, model={request.model}, provider={provider}")
        
        if not request.record_ids:
            raise HTTPException(
                status_code=400,
                detail="No records selected for execution"
            )
        
        # Step 1: Fetch and combine test code from selected records
        combined_test_code = await fetch_selected_records_code(request.record_ids)
        
        # Step 2: Call MCP server to execute the combined test code
        mcp_result = await call_mcp_server(
            test_code=combined_test_code,
            model_key=request.model,
            api_key=request.api_key
        )
        
        # Get provider info for response
        provider, _ = parse_model_to_provider_info(request.model)
        
        # Step 3: Return formatted response
        return TestExecutionResponse(
            success=mcp_result.get("success", False),
            terminal_output=mcp_result.get("terminal_output", ""),
            provider=mcp_result.get("provider", provider),
            model_used=mcp_result.get("model_used", request.model),
            timestamp=mcp_result.get("timestamp", ""),
            error=mcp_result.get("error", None)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing selected records: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )

async def fetch_individual_tests(process_name: str) -> List[IndividualTest]:
    """
    Fetch individual tests from generated_tests array for a specific process name
    """
    try:
        db = await get_database()
        collection = db["session_history"]
        
        # Find all documents with matching code_generation_process_name
        query = {
            "processes.test_code_generation.code_generation_process_name": process_name
        }
        
        documents = await collection.find(query).sort("timestamp", -1).to_list(None)
        
        individual_tests = []
        
        for document in documents:
            try:
                # Navigate to test code generation output
                processes = document.get("processes", {})
                test_code_gen = processes.get("test_code_generation", {})
                output = test_code_gen.get("output", {})
                input_data = test_code_gen.get("input", {})
                session_id = document.get("session_id", str(document.get("_id", "")))
                
                # Extract source code from input
                source_files = input_data.get("source_files", [])
                source_code = ""
                
                if source_files and isinstance(source_files, list):
                    # Combine all source files
                    source_code_parts = []
                    for file_info in source_files:
                        if isinstance(file_info, dict):
                            filename = file_info.get("filename", "Unknown")
                            content = file_info.get("content", "")
                            source_code_parts.append(f"// File: {filename}\n{content}")
                        elif isinstance(file_info, str):
                            source_code_parts.append(file_info)
                    
                    if source_code_parts:
                        source_code = "\n\n" + "="*80 + "\n\n".join(source_code_parts)
                
                # Extract individual tests from generated_tests array
                generated_tests = None
                
                # Path 1: Direct generated_tests
                if "generated_tests" in output:
                    generated_tests = output["generated_tests"]
                
                # Path 2: In data.generated_tests
                elif "data" in output and "generated_tests" in output["data"]:
                    generated_tests = output["data"]["generated_tests"]
                
                if generated_tests and isinstance(generated_tests, list):
                    for idx, test in enumerate(generated_tests):
                        if isinstance(test, dict):
                            test_code = test.get("code", "")
                            test_name = test.get("name", f"Test {idx + 1}")
                        else:
                            test_code = str(test)
                            test_name = f"Test {idx + 1}"
                        
                        if test_code.strip():
                            test_id = f"{session_id}_{idx}"
                            code_snippet = test_code[:200] + "..." if len(test_code) > 200 else test_code
                            
                            individual_tests.append(IndividualTest(
                                test_id=test_id,
                                session_id=session_id,
                                test_index=idx,
                                code_snippet=code_snippet,
                                full_code=test_code,
                                test_name=test_name,
                                source_code=source_code  # Add source code context
                            ))
                            
            except Exception as e:
                logger.error(f"Error processing document {document.get('_id')}: {str(e)}")
                continue
        
        return individual_tests
        
    except Exception as e:
        logger.error(f"Error fetching individual tests: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

@router.get("/process/{process_name}/individual-tests")
async def get_individual_tests(process_name: str) -> IndividualTestsResponse:
    """
    Get all individual tests for a specific process name
    """
    try:
        tests = await fetch_individual_tests(process_name)
        return IndividualTestsResponse(
            success=True,
            process_name=process_name,
            tests=tests,
            total_count=len(tests)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting individual tests: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )

async def fetch_selected_tests_code(test_ids: List[str]) -> str:
    """
    Fetch and combine test code from selected individual test IDs
    """
    try:
        logger.info(f"[fetch_selected_tests_code] Fetching {len(test_ids)} test(s)")
        logger.info(f"[fetch_selected_tests_code] Test IDs: {test_ids}")
        
        db = await get_database()
        collection = db["session_history"]
        
        combined_code = []
        test_metadata = []  # Store metadata for summary
        
        for idx, test_id in enumerate(test_ids, 1):
            try:
                # Parse test_id format: session_id_test_index
                parts = test_id.rsplit('_', 1)
                if len(parts) != 2:
                    logger.warning(f"Invalid test_id format: {test_id}")
                    continue
                    
                session_id, test_index_str = parts
                test_index = int(test_index_str)
                
                logger.info(f"[fetch_selected_tests_code] Processing test_id: {test_id}")
                logger.info(f"  - session_id: {session_id}")
                logger.info(f"  - test_index: {test_index}")
                
                # Find document by session_id
                document = await collection.find_one({"session_id": session_id})
                
                if not document:
                    logger.warning(f"Document not found for session_id: {session_id}")
                    continue
                
                # Navigate to test code generation output
                processes = document.get("processes", {})
                test_code_gen = processes.get("test_code_generation", {})
                output = test_code_gen.get("output", {})
                
                # Extract individual test code
                generated_tests = None
                test_name = None
                
                # Path 1: Direct generated_tests
                if "generated_tests" in output:
                    generated_tests = output["generated_tests"]
                
                # Path 2: In data.generated_tests
                elif "data" in output and "generated_tests" in output["data"]:
                    generated_tests = output["data"]["generated_tests"]
                
                if generated_tests and isinstance(generated_tests, list) and test_index < len(generated_tests):
                    test = generated_tests[test_index]
                    
                    if isinstance(test, dict):
                        test_code = test.get("code", "")
                        test_name = test.get("name", f"Test {test_index + 1}")
                    else:
                        test_code = str(test)
                        test_name = f"Test {test_index + 1}"
                    
                    if test_code.strip():
                        # Add formatted separator and metadata
                        separator = "=" * 80
                        header = f"TEST #{idx}: {test_name}"
                        metadata = f"Session: {session_id} | Index: {test_index}"
                        
                        formatted_test = f"""
{separator}
{header}
{metadata}
{separator}

{test_code}
"""
                        combined_code.append(formatted_test)
                        test_metadata.append({
                            "index": idx,
                            "name": test_name,
                            "session_id": session_id,
                            "test_index": test_index
                        })
                
            except (ValueError, IndexError) as e:
                logger.warning(f"Error processing test_id {test_id}: {str(e)}")
                continue
            except Exception as e:
                logger.error(f"Error fetching test {test_id}: {str(e)}")
                continue
        
        if not combined_code:
            raise HTTPException(
                status_code=404,
                detail="No valid test code found for the selected test IDs"
            )
        
        # Create summary header
        summary_header = f"""
{'=' * 80}
TEST EXECUTION BATCH
Total Tests: {len(combined_code)}
{'=' * 80}

SELECTED TESTS:
"""
        for meta in test_metadata:
            summary_header += f"  [{meta['index']}] {meta['name']} (Session: {meta['session_id']}, Index: {meta['test_index']})\n"
        
        summary_header += f"\n{'=' * 80}\n"
        
        # Combine summary with all tests
        return summary_header + "\n".join(combined_code)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching selected tests code: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

async def fetch_single_test_code(test_id: str) -> Dict[str, Any]:
    """
    Fetch a single test's code and metadata along with source code
    Returns dict with test_id, test_name, code, source_code, session_id, test_index
    """
    try:
        # Parse test_id format: session_id_test_index
        parts = test_id.rsplit('_', 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid test_id format: {test_id}")
            
        session_id, test_index_str = parts
        test_index = int(test_index_str)
        
        db = await get_database()
        collection = db["session_history"]
        
        # Find document by session_id
        document = await collection.find_one({"session_id": session_id})
        
        if not document:
            raise ValueError(f"Document not found for session_id: {session_id}")
        
        # Navigate to test code generation
        processes = document.get("processes", {})
        test_code_gen = processes.get("test_code_generation", {})
        output = test_code_gen.get("output", {})
        input_data = test_code_gen.get("input", {})
        
        # Extract source code from input
        source_files = input_data.get("source_files", [])
        source_code = ""
        
        if source_files and isinstance(source_files, list):
            # Combine all source files
            source_code_parts = []
            for file_info in source_files:
                if isinstance(file_info, dict):
                    filename = file_info.get("filename", "Unknown")
                    content = file_info.get("content", "")
                    source_code_parts.append(f"// File: {filename}\n{content}")
                elif isinstance(file_info, str):
                    source_code_parts.append(file_info)
            
            source_code = "\n\n" + "="*80 + "\n\n".join(source_code_parts)
        
        # Extract individual test code
        generated_tests = None
        
        # Path 1: Direct generated_tests
        if "generated_tests" in output:
            generated_tests = output["generated_tests"]
        
        # Path 2: In data.generated_tests
        elif "data" in output and "generated_tests" in output["data"]:
            generated_tests = output["data"]["generated_tests"]
        
        if not generated_tests or not isinstance(generated_tests, list) or test_index >= len(generated_tests):
            raise ValueError(f"Test not found at index {test_index}")
        
        test = generated_tests[test_index]
        
        if isinstance(test, dict):
            test_code = test.get("code", "")
            test_name = test.get("name", f"Test {test_index + 1}")
        else:
            test_code = str(test)
            test_name = f"Test {test_index + 1}"
        
        if not test_code.strip():
            raise ValueError("Test code is empty")
        
        return {
            "test_id": test_id,
            "test_name": test_name,
            "code": test_code,
            "source_code": source_code,  # ADDED: Source code for context
            "session_id": session_id,
            "test_index": test_index
        }
        
    except Exception as e:
        logger.error(f"Error fetching test {test_id}: {str(e)}")
        raise

@router.post("/execute-selected-tests")
async def execute_selected_tests(request: SelectedTestsExecutionRequest) -> TestExecutionResponse:
    """
    Execute selected individual tests one by one and return combined results
    """
    try:
        provider, _ = parse_model_to_provider_info(request.model)
        logger.info(f"[execute_selected_tests] Request received:")
        logger.info(f"  - test_ids count: {len(request.test_ids)}")
        logger.info(f"  - model: {request.model}")
        logger.info(f"  - provider: {provider}")
        
        if not request.test_ids:
            logger.error("[execute_selected_tests] No test_ids provided")
            raise HTTPException(
                status_code=400,
                detail="No test IDs provided for execution"
            )
        
        # Execute tests one by one
        logger.info("[execute_selected_tests] Executing tests individually...")
        
        test_results = []
        successful_tests = 0
        failed_tests = 0
        source_code_sample = None  # Store source code from first test for display
        
        for idx, test_id in enumerate(request.test_ids, 1):
            try:
                logger.info(f"[execute_selected_tests] Executing test {idx}/{len(request.test_ids)}: {test_id}")
                
                # Fetch single test code and metadata
                test_data = await fetch_single_test_code(test_id)
                
                # Store source code from first test for display in output
                if idx == 1 and test_data.get("source_code"):
                    source_code_sample = test_data.get("source_code")
                
                logger.info(f"[execute_selected_tests] Test data fetched: {test_data['test_name']}")
                logger.info(f"[execute_selected_tests] Source code available: {bool(test_data.get('source_code'))}")
                
                # Execute single test with source code context
                mcp_result = await call_mcp_server(
                    test_code=test_data["code"],
                    model_key=request.model,
                    api_key=request.api_key,
                    source_code=test_data.get("source_code")  # Include source code for context
                )
                
                # Store result
                test_result = {
                    "test_number": idx,
                    "test_id": test_id,
                    "test_name": test_data["test_name"],
                    "session_id": test_data["session_id"],
                    "test_index": test_data["test_index"],
                    "success": mcp_result.get("success", False),
                    "output": mcp_result.get("terminal_output", ""),
                    "error": mcp_result.get("error", None)
                }
                
                test_results.append(test_result)
                
                if test_result["success"]:
                    successful_tests += 1
                    logger.info(f"[execute_selected_tests] Test {idx} SUCCESS: {test_data['test_name']}")
                else:
                    failed_tests += 1
                    logger.warning(f"[execute_selected_tests] Test {idx} FAILED: {test_data['test_name']}")
                    
            except Exception as e:
                logger.error(f"[execute_selected_tests] Error executing test {test_id}: {str(e)}")
                test_results.append({
                    "test_number": idx,
                    "test_id": test_id,
                    "test_name": f"Test {idx}",
                    "session_id": "unknown",
                    "test_index": -1,
                    "success": False,
                    "output": "",
                    "error": f"Failed to execute: {str(e)}"
                })
                failed_tests += 1
        
        # Format combined output with source code context
        combined_output = format_batch_execution_output(
            test_results, 
            successful_tests, 
            failed_tests,
            source_code_sample  # Pass source code for display
        )
        
        logger.info(f"[execute_selected_tests] Batch execution complete: {successful_tests} success, {failed_tests} failed")
        
        # Get provider info for response
        provider, _ = parse_model_to_provider_info(request.model)
        
        return TestExecutionResponse(
            success=failed_tests == 0,  # Success only if all tests passed
            terminal_output=combined_output,
            provider=provider,
            model_used=request.model,
            timestamp=datetime.now().isoformat(),
            error=f"{failed_tests} test(s) failed" if failed_tests > 0 else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing selected tests: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )

def format_batch_execution_output(
    test_results: List[Dict], 
    successful: int, 
    failed: int,
    source_code: Optional[str] = None
) -> str:
    """
    Format batch test execution results into readable output with source code context
    """
    total = len(test_results)
    
    # Header
    output = f"""
{'=' * 80}
BATCH TEST EXECUTION RESULTS
{'=' * 80}

CONTEXT-AWARE EXECUTION:
  ✅ Source code context extracted from database
  ✅ AI received both test code and source code
  ✅ Each test executed with full understanding of context

SUMMARY:
  Total Tests: {total}
  ✅ Successful: {successful}
  ❌ Failed: {failed}
  Success Rate: {(successful/total*100) if total > 0 else 0:.1f}%

{'=' * 80}

"""
    
    # Add source code context if available
    if source_code:
        # Truncate if too long for display
        display_code = source_code[:1000] + "..." if len(source_code) > 1000 else source_code
        output += f"""
Source Code Context:
{display_code}

{'=' * 80}

"""
    
    # Individual test results
    for result in test_results:
        status_icon = "✅" if result["success"] else "❌"
        status_text = "PASSED" if result["success"] else "FAILED"
        
        output += f"""
{'=' * 80}
TEST #{result['test_number']}: {result['test_name']} {status_icon}
Status: {status_text}
Test ID: {result['test_id']}
Session: {result['session_id']} | Index: {result['test_index']}
{'=' * 80}

"""
        
        if result["success"]:
            output += f"""OUTPUT:
{result['output']}

"""
        else:
            output += f"""ERROR:
{result['error'] or 'Unknown error'}

"""
            if result["output"]:
                output += f"""OUTPUT:
{result['output']}

"""
    
    # Footer
    output += f"""
{'=' * 80}
BATCH EXECUTION COMPLETE
{'=' * 80}
"""
    
    return output