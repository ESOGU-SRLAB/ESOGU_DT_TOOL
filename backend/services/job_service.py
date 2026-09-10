"""Process-local background jobs for long-running generation and execution calls."""

import asyncio
from datetime import datetime, timezone
from enum import Enum
import logging
import re
import time
from typing import Any, Awaitable, Dict, Optional
import uuid


logger = logging.getLogger(__name__)


def _safe_error(exc: Exception) -> str:
    """Redact common credential shapes before logging or returning diagnostics."""
    message = str(exc)
    message = re.sub(
        r"(?i)(api[_-]?key|token|authorization)([=:\s]+)([^\s&,;]+)",
        r"\1\2[REDACTED]",
        message,
    )
    message = re.sub(r"\bAIza[0-9A-Za-z_-]{20,}\b", "[REDACTED]", message)
    message = re.sub(r"\bsk-[0-9A-Za-z_-]{12,}\b", "[REDACTED]", message)
    return message[:1000]


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobNotFoundError(KeyError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobService:
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def submit(
        self,
        job_type: str,
        operation: Awaitable[Any],
        correlation_id: Optional[str] = None,
        monitoring_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        job_id = f"job_{uuid.uuid4().hex}"
        record = {
            "job_id": job_id,
            "job_type": job_type,
            "correlation_id": correlation_id,
            "status": JobStatus.PENDING.value,
            "created_at": _now(),
            "started_at": None,
            "finished_at": None,
            "result": None,
            "error": None,
        }
        self._jobs[job_id] = record
        context = dict(monitoring_context or {})
        if context:
            context.setdefault("session_id", correlation_id)
        asyncio.create_task(self._run(record, operation, context))
        return record.copy()

    async def _emit_monitoring(self, event_type: str, record: Dict[str, Any], context: Dict[str, Any], **extra) -> None:
        if not context:
            return
        try:
            from services.monitoring_event_service import monitoring_event_service

            fields = {
                "job_id": record["job_id"],
                "session_id": context.get("session_id"),
                "process_id": context.get("process_id"),
                "process_title": context.get("process_title"),
                "module": context.get("module"),
                "metadata": context.get("metadata", {}),
                **extra,
            }
            await monitoring_event_service.emit(event_type, **fields)
        except Exception as exc:
            logger.error("Monitoring emission failed for job %s: %s", record["job_id"], type(exc).__name__)

    @staticmethod
    def _metrics(result: Any, module: Optional[str]) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return {}
        metrics: Dict[str, Any] = {}
        if module == "scenario_generation":
            payload = result.get("test_scenarios", result)
            scenarios = payload.get("TestScenarios", []) if isinstance(payload, dict) else []
            metrics["scenario_count"] = len(scenarios)
        elif module == "test_case_generation":
            cases = result.get("test_case_results") or result.get("test_cases") or []
            summary = result.get("summary") or {}
            metrics["scenario_count"] = len(cases) if isinstance(cases, list) else 0
            metrics["test_case_count"] = int(summary.get("total_test_cases", len(cases) if isinstance(cases, list) else 0))
        elif module == "test_code_generation":
            tests = result.get("generated_tests") or result.get("test_cases") or []
            metrics["generated_test_count"] = len(tests) if isinstance(tests, list) else 0
        elif module == "test_execution":
            metrics.update({"passed": int(result.get("passed", 0)), "failed": int(result.get("failed", 0))})
        return metrics

    async def _run(self, record: Dict[str, Any], operation: Awaitable[Any], context: Dict[str, Any]) -> None:
        record["status"] = JobStatus.RUNNING.value
        record["started_at"] = _now()
        started = time.monotonic()
        is_execution = context.get("module") == "test_execution"
        if is_execution:
            await self._emit_monitoring("execution.submitted", record, context, status="queued")
            await self._emit_monitoring("execution.started", record, context, status="running")
        else:
            await self._emit_monitoring("module.started", record, context, status="running")
        try:
            record["result"] = await operation
            record["status"] = JobStatus.COMPLETED.value
            duration_ms = int((time.monotonic() - started) * 1000)
            metrics = self._metrics(record["result"], context.get("module"))
            event_type = "execution.completed" if is_execution else "module.completed"
            await self._emit_monitoring(
                event_type,
                record,
                context,
                execution_id=(record["result"] or {}).get("execution_id") if is_execution else None,
                status="completed",
                progress=100,
                duration_ms=duration_ms,
                metrics=metrics,
            )
        except Exception as exc:
            safe_error = _safe_error(exc)
            logger.error("Background job %s failed: %s", record["job_id"], safe_error)
            record["status"] = JobStatus.FAILED.value
            record["error"] = {
                "error_code": "JOB_FAILED",
                "message": f"{record['job_type']} failed.",
                "details": safe_error,
                "job_id": record["job_id"],
            }
            await self._emit_monitoring(
                "execution.failed" if is_execution else "module.failed",
                record,
                context,
                status="failed",
                duration_ms=int((time.monotonic() - started) * 1000),
                error={"error_code": "JOB_FAILED", "message": f"{record['job_type']} failed."},
            )
        finally:
            record["finished_at"] = _now()

    def get(self, job_id: str) -> Dict[str, Any]:
        try:
            return self._jobs[job_id].copy()
        except KeyError as exc:
            raise JobNotFoundError(job_id) from exc


job_service = JobService()
