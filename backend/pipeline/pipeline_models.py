"""
pipeline_models.py
------------------
Pydantic models for the backend pipeline orchestration system.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class PipelineStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    ERROR = "error"


class FileInfo(BaseModel):
    """A file included in the pipeline run."""
    name: str
    content: str
    type: Optional[str] = None  # "requirement", "source", "uml", etc.


class StepConfig(BaseModel):
    """Per-step configuration for a pipeline run."""
    # Common fields
    # None means inherit PipelineRunRequest.global_model. A concrete default here
    # previously overwrote an explicitly selected global model.
    model: Optional[str] = None
    custom_prompt: Optional[str] = None
    api_key: Optional[str] = None

    # Environment Setup specific
    environment_name: Optional[str] = None
    environment_session_id: Optional[str] = None

    # Test Scenario Generation specific
    test_type: Optional[str] = None
    test_category: Optional[str] = None
    process_title: Optional[str] = None
    final_prompt: Optional[str] = None

    # Test Case Optimization specific
    process_name: Optional[str] = None
    optimization_type: Optional[str] = "individual"  # individual / bulk / parallel

    # Test Code Generation specific
    output_format: Optional[str] = "json"
    max_test_cases: Optional[int] = None
    max_input_tokens: Optional[int] = 64000

    # Test Execution specific
    execution_mode: Optional[str] = "standard"          # legacy, kept for compat
    execution_method: Optional[str] = "ai"              # "ai" | "docker" | "robot" | "ros2" | "ssh_docker"
    execution_language: Optional[str] = "python"        # Docker: python/javascript/java/csharp/go/rust
    additional_packages: Optional[List[str]] = None     # Docker: extra pip/npm packages
    docker_timeout: Optional[int] = 300                 # Docker: container timeout seconds
    robot_type: Optional[str] = "generic"              # Robot: generic/industrial/collaborative
    simulation_config: Optional[Dict[str, Any]] = None  # Robot: simulation parameters

    # ROS2 Docker specific
    ros2_visual_count: Optional[int] = 0               # ROS2: number of tests to run with GUI visible
    ros2_timeout: Optional[int] = 120                  # ROS2: per-test timeout in seconds
    remote_timeout: Optional[int] = 300                # SSH/Docker ROS2: per-test timeout in seconds

    # Test Reporting specific
    analysis_depth: Optional[str] = "detailed"


class PipelineRunRequest(BaseModel):
    """Request body for POST /api/pipeline/run"""
    session_id: str
    selected_steps: List[str]  # e.g. ["code-review", "requirement-analysis", ...]
    files: Dict[str, List[FileInfo]] = Field(
        default_factory=dict,
        description="Mapping of step_id -> list of files for that step"
    )
    global_model: Optional[str] = None
    global_api_key: Optional[str] = None
    process_title: str = Field(..., description="The process title used for test scenario / test case naming")
    step_configs: Dict[str, StepConfig] = Field(
        default_factory=dict,
        description="Per-step overrides; keys are step IDs"
    )


class StepResult(BaseModel):
    """Result of a single pipeline step."""
    step_id: str
    status: PipelineStepStatus
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_seconds: Optional[float] = None
    skipped_reason: Optional[str] = None


class PipelineStatusResponse(BaseModel):
    """Response body for GET /api/pipeline/status/{session_id}"""
    session_id: str
    status: str  # "running" | "completed" | "error" | "stopped"
    current_step: Optional[str] = None
    completed_steps: List[str] = Field(default_factory=list)
    step_statuses: Dict[str, PipelineStepStatus] = Field(default_factory=dict)
    step_results: Dict[str, StepResult] = Field(default_factory=dict)
    error: Optional[str] = None


class PipelineStopResponse(BaseModel):
    """Response for POST /api/pipeline/stop/{session_id}"""
    success: bool
    session_id: str
    message: str
