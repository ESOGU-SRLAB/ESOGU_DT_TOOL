"""Generic, consumer-neutral monitoring event contract."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class MonitoringEventType(str, Enum):
    PIPELINE_STARTED = "pipeline.started"
    PIPELINE_COMPLETED = "pipeline.completed"
    PIPELINE_FAILED = "pipeline.failed"
    MODULE_STARTED = "module.started"
    MODULE_PROGRESS = "module.progress"
    MODULE_COMPLETED = "module.completed"
    MODULE_FAILED = "module.failed"
    EXECUTION_SUBMITTED = "execution.submitted"
    EXECUTION_STARTED = "execution.started"
    EXECUTION_COMPLETED = "execution.completed"
    EXECUTION_FAILED = "execution.failed"


class MonitoringModule(str, Enum):
    ARTIFACT_INGESTION = "artifact_ingestion"
    ENVIRONMENT_SETUP = "environment_setup"
    SCENARIO_GENERATION = "scenario_generation"
    TEST_CASE_GENERATION = "test_case_generation"
    TEST_CODE_GENERATION = "test_code_generation"
    TEST_EXECUTION = "test_execution"


class MonitoringError(BaseModel):
    error_code: str
    message: str


class MonitoringEvent(BaseModel):
    event_id: str
    event_type: MonitoringEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    process_id: Optional[str] = None
    process_title: Optional[str] = None
    session_id: Optional[str] = None
    job_id: Optional[str] = None
    execution_id: Optional[str] = None
    module: Optional[MonitoringModule] = None
    status: Optional[str] = None
    progress: Optional[float] = Field(None, ge=0, le=100)
    duration_ms: Optional[int] = Field(None, ge=0)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[MonitoringError] = None


class MonitoringEventList(BaseModel):
    events: list[MonitoringEvent]
    count: int
    limit: int

