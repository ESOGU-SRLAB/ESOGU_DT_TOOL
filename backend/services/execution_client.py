"""Configurable adapter for a future external test execution system."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import aiohttp
from pydantic import BaseModel, Field

from core.settings import get_settings


class ExecutionRequest(BaseModel):
    test_code: str = Field(..., min_length=1)
    language: Optional[str] = None
    framework: Optional[str] = None
    test_case_id: Optional[str] = None
    session_id: Optional[str] = None
    process_id: Optional[str] = None
    process_title: Optional[str] = None
    artifact_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    configuration: Dict[str, Any] = Field(default_factory=dict)


class ExecutionResult(BaseModel):
    execution_id: str
    status: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    passed: int = 0
    failed: int = 0
    logs: Optional[str] = None
    error: Optional[str] = None
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)


class ExecutionNotConfiguredError(RuntimeError):
    pass


class ExecutionAdapter(ABC):
    @abstractmethod
    async def submit(self, request: ExecutionRequest) -> ExecutionResult:
        raise NotImplementedError


class HttpExecutionClient(ExecutionAdapter):
    def __init__(self, base_url: str = None, token: str = None, timeout_seconds: int = None):
        settings = get_settings()
        self.base_url = (base_url or settings.execution_service_url or "").rstrip("/")
        self.token = token if token is not None else settings.execution_service_token
        self.timeout_seconds = timeout_seconds or settings.execution_timeout_seconds

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url)

    async def submit(self, request: ExecutionRequest) -> ExecutionResult:
        if not self.base_url:
            raise ExecutionNotConfiguredError(
                "EXECUTION_SERVICE_URL is not configured; no execution request was sent"
            )
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            payload = request.model_dump(exclude_none=True) if hasattr(request, "model_dump") else request.dict(exclude_none=True)
            async with session.post(
                f"{self.base_url}/executions",
                json=payload,
                headers=headers,
            ) as response:
                if response.status < 200 or response.status >= 300:
                    body = (await response.text())[:500]
                    raise RuntimeError(
                        f"External execution service returned HTTP {response.status}: {body}"
                    )
                response_data = await response.json()
                if hasattr(ExecutionResult, "model_validate"):
                    return ExecutionResult.model_validate(response_data)
                return ExecutionResult.parse_obj(response_data)
