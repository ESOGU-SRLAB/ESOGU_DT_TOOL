"""
remote_execution_router.py
--------------------------
API Router for remote/local test execution folder management.
Enables robot-based test execution scenarios.
"""

import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from services.remote_execution_service import RemoteExecutionService
from services.execution_client import ExecutionRequest, SshDockerExecutionClient
from utils.standalone_test_validation import supports_legacy_sim_robot_goal
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/remote-execution",
    tags=["remote-execution"]
)

# Initialize service
remote_exec_service = RemoteExecutionService()


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateFolderRequest(BaseModel):
    """Request model for creating execution folder"""
    base_path: str = Field(..., description="Base directory path (local or UNC)")
    session_id: str = Field(..., description="Session identifier")
    folder_name: Optional[str] = Field(None, description="Optional custom folder name")


class CreateFolderResponse(BaseModel):
    """Response model for folder creation"""
    success: bool
    folder_path: Optional[str] = None
    folder_name: Optional[str] = None
    created_at: Optional[str] = None
    status: Optional[str] = None
    subfolders: Optional[Dict[str, str]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None


class SourceFileInfo(BaseModel):
    """Model for source file information"""
    filename: str
    content: Optional[str] = None
    source_path: Optional[str] = None


class DeployFilesRequest(BaseModel):
    """Request model for deploying source files"""
    execution_folder: str = Field(..., description="Path to execution folder")
    source_files: List[SourceFileInfo] = Field(..., description="List of files to deploy")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class DeployFilesResponse(BaseModel):
    """Response model for file deployment"""
    success: bool
    deployment_id: Optional[str] = None
    deployed_at: Optional[str] = None
    file_count: Optional[int] = None
    files: Optional[List[Dict[str, Any]]] = None
    metadata_path: Optional[str] = None
    error: Optional[str] = None


class ExecutionStatusResponse(BaseModel):
    """Response model for execution status"""
    success: bool
    session_id: Optional[str] = None
    status: Optional[str] = None
    deployment_status: Optional[str] = None
    execution_status: Optional[str] = None
    robot_accessed: Optional[bool] = None
    created_at: Optional[str] = None
    last_modified: Optional[str] = None
    result_files_count: Optional[int] = None
    log_files_count: Optional[int] = None
    has_results: Optional[bool] = None
    error: Optional[str] = None


class CollectResultsRequest(BaseModel):
    """Request model for collecting results"""
    execution_folder: str = Field(..., description="Path to execution folder")
    result_file_pattern: Optional[str] = Field("*.json", description="File pattern for results")


class CollectResultsResponse(BaseModel):
    """Response model for collected results"""
    success: bool
    results_available: Optional[bool] = None
    collected_at: Optional[str] = None
    result_count: Optional[int] = None
    results: Optional[List[Dict[str, Any]]] = None
    aggregated: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    error: Optional[str] = None


class ListFoldersResponse(BaseModel):
    """Response model for listing folders"""
    success: bool
    base_path: Optional[str] = None
    folder_count: Optional[int] = None
    folders: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class RemoteTestFile(BaseModel):
    test_id: str = Field(..., min_length=1)
    filename: Optional[str] = None
    content: str = Field(..., min_length=1)
    execution_eligibility: str = "eligible"
    eligibility_reason: Optional[str] = None
    oracle: Optional[Dict[str, Any]] = None


class ExecuteRemoteTestsRequest(BaseModel):
    session_id: Optional[str] = None
    process_name: Optional[str] = None
    timeout_seconds: int = Field(300, ge=10, le=1900)
    test_files: List[RemoteTestFile] = Field(..., min_length=1)


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/runner-status")
async def get_remote_runner_status():
    """Return non-sensitive SSH/Docker runner configuration status."""
    try:
        client = SshDockerExecutionClient()
        return {
            "success": True,
            "configured": client.is_configured,
            "host": client.host,
            "remote_dir": client.remote_dir,
            "image": client.image,
            "authentication": "password" if client.password else "ssh_key",
            "legacy_sim_robot_goal_supported": supports_legacy_sim_robot_goal(client.image),
        }
    except Exception as exc:
        return {"success": False, "configured": False, "error": str(exc)}


@router.post("/execute-tests")
async def execute_remote_tests(request: ExecuteRemoteTestsRequest):
    """Upload selected Python tests and execute each in the remote ROS 2 harness."""
    client = SshDockerExecutionClient()
    if not client.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Remote execution is not configured. Set SSH_EXECUTION_HOST.",
        )

    results = []
    for item in request.test_files:
        oracle_failed = item.oracle is not None and item.oracle.get("passed") is False
        if item.execution_eligibility != "eligible" or oracle_failed:
            reason = (
                item.eligibility_reason
                or "Generation oracle rejected this test; remote execution was not started."
            )
            results.append({
                "test_id": item.test_id,
                "filename": item.filename,
                "status": "not_executed",
                "verdict": "invalid",
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "blocked": 0,
                "not_executed": 1,
                "logs": "",
                "error": reason,
                "exit_code": None,
                "reset_status": None,
                "artifacts": [],
            })
            continue
        try:
            result = await client.submit(ExecutionRequest(
                test_code=item.content,
                language="python",
                framework="pytest",
                test_case_id=item.test_id,
                session_id=request.session_id,
                process_title=request.process_name,
                metadata={"filename": item.filename, "source": "test_execution_remote"},
                configuration={"timeout_seconds": request.timeout_seconds},
            ))
            results.append({
                "test_id": item.test_id,
                "filename": item.filename,
                "execution_id": result.execution_id,
                "status": result.status,
                "verdict": result.verdict,
                "passed": result.passed,
                "failed": result.failed,
                "errors": result.errors,
                "blocked": result.blocked,
                "not_executed": result.not_executed,
                "logs": result.logs,
                "error": result.error,
                "exit_code": result.exit_code,
                "reset_status": result.reset_status,
                "artifacts": result.artifacts,
                "started_at": result.started_at,
                "finished_at": result.finished_at,
            })
        except Exception as exc:
            logger.error(
                "Remote test %s failed: %s: %s",
                item.test_id,
                type(exc).__name__,
                str(exc)[:1000],
            )
            results.append({
                "test_id": item.test_id,
                "filename": item.filename,
                "status": "error",
                "verdict": "error",
                "passed": 0,
                "failed": 0,
                "errors": 1,
                "blocked": 0,
                "not_executed": 0,
                "logs": "",
                "error": str(exc)[:1000],
                "exit_code": None,
                "reset_status": None,
                "artifacts": [],
            })

    def result_verdict(item: Dict[str, Any]) -> str:
        if item.get("verdict"):
            return item["verdict"]
        if item.get("failed", 0) > 0:
            return "failed"
        if item.get("status") == "completed":
            return "passed"
        return "error"

    verdicts = [result_verdict(item) for item in results]
    summary = {
        "total": len(results),
        "passed": verdicts.count("passed"),
        "failed": verdicts.count("failed"),
        "error": verdicts.count("error"),
        "blocked": verdicts.count("blocked"),
        "not_executed": verdicts.count("not_executed"),
        "invalid": verdicts.count("invalid"),
    }
    return {
        "success": summary["passed"] == summary["total"],
        "session_id": request.session_id,
        "process_name": request.process_name,
        "summary": summary,
        "results": results,
    }

@router.post("/create-folder", response_model=CreateFolderResponse)
async def create_execution_folder(request: CreateFolderRequest):
    """
    Create an execution folder for robot test scenario.
    
    The folder structure created:
    - execution_folder/
      - source_files/      (Test code files for robot)
      - results/           (Execution results from robot)
      - logs/              (Execution logs)
      - execution_status.json  (Status tracking)
    
    Supports both local paths (C:\\tests) and network paths (\\\\server\\share\\tests)
    """
    try:
        logger.info(f"📁 Creating execution folder at: {request.base_path}")
        
        result = remote_exec_service.create_execution_folder(
            base_path=request.base_path,
            session_id=request.session_id,
            folder_name=request.folder_name
        )
        
        if result.get("success"):
            logger.info(f"✅ Execution folder created: {result['folder_path']}")
        else:
            logger.error(f"❌ Failed to create folder: {result.get('error')}")
        
        return CreateFolderResponse(**result)
        
    except Exception as e:
        logger.error(f"❌ Error in create_execution_folder endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deploy-files", response_model=DeployFilesResponse)
async def deploy_source_files(request: DeployFilesRequest):
    """
    Deploy source files to execution folder with robot instructions.
    
    Creates:
    - Copies/writes files to source_files/ folder
    - Generates deployment_info.json with metadata
    - Updates execution_status.json
    - Includes instructions for robot in metadata
    """
    try:
        logger.info(f"📦 Deploying {len(request.source_files)} files to: {request.execution_folder}")
        
        # Convert Pydantic models to dicts
        source_files_dict = [file.dict(exclude_none=True) for file in request.source_files]
        
        result = remote_exec_service.deploy_source_files(
            execution_folder=request.execution_folder,
            source_files=source_files_dict,
            metadata=request.metadata
        )
        
        if result.get("success"):
            logger.info(f"✅ Deployed {result['file_count']} files")
        else:
            logger.error(f"❌ Deployment failed: {result.get('error')}")
        
        return DeployFilesResponse(**result)
        
    except Exception as e:
        logger.error(f"❌ Error in deploy_source_files endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{execution_folder:path}", response_model=ExecutionStatusResponse)
async def get_execution_status(execution_folder: str):
    """
    Check current status of execution folder.
    
    Returns:
    - Deployment status
    - Execution status
    - Whether robot has accessed files
    - Result availability
    """
    try:
        logger.info(f"📊 Checking status for: {execution_folder}")
        
        result = remote_exec_service.check_execution_status(execution_folder)
        
        return ExecutionStatusResponse(**result)
        
    except Exception as e:
        logger.error(f"❌ Error in get_execution_status endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect-results", response_model=CollectResultsResponse)
async def collect_execution_results(request: CollectResultsRequest):
    """
    Collect and parse results from execution folder.
    
    Searches for result files in results/ folder and aggregates them.
    Returns both individual results and aggregated statistics.
    """
    try:
        logger.info(f"📥 Collecting results from: {request.execution_folder}")
        
        result = remote_exec_service.collect_results(
            execution_folder=request.execution_folder,
            result_file_pattern=request.result_file_pattern
        )
        
        if result.get("success") and result.get("results_available"):
            logger.info(f"✅ Collected {result['result_count']} result files")
        
        return CollectResultsResponse(**result)
        
    except Exception as e:
        logger.error(f"❌ Error in collect_execution_results endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list-folders", response_model=ListFoldersResponse)
async def list_execution_folders(base_path: str):
    """
    List all execution folders in a base directory.
    
    Useful for:
    - Monitoring multiple robot executions
    - Finding previous execution results
    - Cleanup operations
    """
    try:
        logger.info(f"📋 Listing execution folders in: {base_path}")
        
        result = remote_exec_service.list_execution_folders(base_path)
        
        if result.get("success"):
            logger.info(f"✅ Found {result['folder_count']} execution folders")
        
        return ListFoldersResponse(**result)
        
    except Exception as e:
        logger.error(f"❌ Error in list_execution_folders endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cleanup/{execution_folder:path}")
async def cleanup_execution_folder(execution_folder: str, delete_results: bool = False):
    """
    Cleanup execution folder.
    
    Args:
        execution_folder: Path to execution folder
        delete_results: If True, also delete results folder (default: False)
    
    This is useful for cleaning up after successful result collection.
    """
    try:
        import shutil
        from pathlib import Path
        
        logger.info(f"🗑️ Cleaning up: {execution_folder}")
        
        folder_path = Path(execution_folder)
        
        if not folder_path.exists():
            raise HTTPException(status_code=404, detail="Folder not found")
        
        # Clean source files
        source_folder = folder_path / "source_files"
        if source_folder.exists():
            shutil.rmtree(source_folder)
            source_folder.mkdir()
        
        # Optionally clean results
        if delete_results:
            results_folder = folder_path / "results"
            if results_folder.exists():
                shutil.rmtree(results_folder)
                results_folder.mkdir()
        
        # Clean logs
        logs_folder = folder_path / "logs"
        if logs_folder.exists():
            shutil.rmtree(logs_folder)
            logs_folder.mkdir()
        
        logger.info(f"✅ Cleaned up: {execution_folder}")
        
        return {
            "success": True,
            "message": "Cleanup completed",
            "folder": str(execution_folder),
            "deleted_results": delete_results
        }
        
    except Exception as e:
        logger.error(f"❌ Error in cleanup endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint for remote execution service"""
    return {
        "status": "healthy",
        "service": "remote_execution",
        "timestamp": datetime.now().isoformat()
    }
