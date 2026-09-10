"""
pipeline_router.py
------------------
FastAPI router for the STLC pipeline orchestration.
Provides endpoints to start, stream, query, and stop a pipeline run.

POST   /api/pipeline/run            - Start a new pipeline run
GET    /api/pipeline/status/{sid}   - Get current status snapshot
GET    /api/pipeline/stream/{sid}   - SSE stream of real-time progress
POST   /api/pipeline/stop/{sid}     - Request graceful stop
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from pipeline.pipeline_controller import sort_steps, validate_pipeline
from pipeline.pipeline_models import (
    PipelineRunRequest,
    PipelineStatusResponse,
    PipelineStepStatus,
    PipelineStopResponse,
    StepResult,
)
from pipeline.step_adapters import execute_step
from services.monitoring_event_service import monitoring_event_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pipeline"])

# ---------------------------------------------------------------------------
# In-memory state for running / completed pipelines
# ---------------------------------------------------------------------------

# session_id -> PipelineState dict
_pipeline_states: Dict[str, Dict[str, Any]] = {}

# session_id -> asyncio.Event  (set to request stop)
_stop_events: Dict[str, asyncio.Event] = {}

_MONITORING_MODULES = {
    "environment-setup": "environment_setup",
    "test-scenario-generation": "scenario_generation",
    "test-case-generation": "test_case_generation",
    "test-code-generation": "test_code_generation",
    "test-execution": "test_execution",
}


def _result_metrics(step_id: str, result: StepResult) -> Dict[str, Any]:
    output = result.output or {}
    metrics: Dict[str, Any] = {}
    if step_id == "test-scenario-generation":
        payload = output.get("test_scenarios", output)
        metrics["scenario_count"] = len(payload.get("TestScenarios", [])) if isinstance(payload, dict) else 0
    elif step_id == "test-case-generation":
        cases = output.get("test_case_results") or output.get("test_cases") or []
        summary = output.get("summary") or {}
        metrics["scenario_count"] = len(cases) if isinstance(cases, list) else 0
        metrics["test_case_count"] = int(summary.get("total_test_cases", len(cases) if isinstance(cases, list) else 0))
    elif step_id == "test-code-generation":
        tests = output.get("generated_tests") or output.get("test_cases") or []
        metrics["generated_test_count"] = len(tests) if isinstance(tests, list) else 0
    return metrics


def _get_state(session_id: str) -> Optional[Dict[str, Any]]:
    return _pipeline_states.get(session_id)


def _new_state(session_id: str, ordered_steps: list) -> Dict[str, Any]:
    state: Dict[str, Any] = {
        "session_id": session_id,
        "status": "running",
        "current_step": None,
        "steps_completed": 0,
        "steps_total": len(ordered_steps),
        "ordered_steps": ordered_steps,
        "step_results": {},          # step_id -> StepResult
        "events": [],                # append-only event log for SSE
        "started_at": datetime.utcnow().isoformat(),
        "finished_at": None,
        "error": None,
    }
    _pipeline_states[session_id] = state
    return state


def _push_event(state: Dict[str, Any], event_type: str, payload: Dict[str, Any]) -> None:
    event = {
        "type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        **payload,
    }
    state["events"].append(event)


# ---------------------------------------------------------------------------
# Background pipeline execution coroutine
# ---------------------------------------------------------------------------

async def _run_pipeline_background(
    req: PipelineRunRequest,
    ordered_steps: list,
    state: Dict[str, Any],
    stop_event: asyncio.Event,
) -> None:
    previous_results: Dict[str, StepResult] = {}
    pipeline_started = time.monotonic()

    await monitoring_event_service.emit_safely(
        "pipeline.started", session_id=req.session_id, process_title=req.process_title,
        status="running", progress=0, metadata={"steps_total": len(ordered_steps)},
    )

    _push_event(state, "pipeline_started", {
        "session_id": req.session_id,
        "steps": ordered_steps,
    })

    for step_id in ordered_steps:
        # Check for stop request
        if stop_event.is_set():
            state["status"] = "stopped"
            state["finished_at"] = datetime.utcnow().isoformat()
            _push_event(state, "pipeline_stopped", {
                "session_id": req.session_id,
                "stopped_at_step": step_id,
            })
            logger.info(f"[Pipeline] Stopped at step {step_id}")
            await monitoring_event_service.emit_safely(
                "pipeline.failed", session_id=req.session_id, process_title=req.process_title,
                status="stopped", duration_ms=int((time.monotonic() - pipeline_started) * 1000),
                error={"error_code": "PIPELINE_STOPPED", "message": "Pipeline was stopped."},
            )
            return

        state["current_step"] = step_id
        _push_event(state, "step_started", {
            "step_id": step_id,
            "session_id": req.session_id,
        })
        logger.info(f"[Pipeline] Starting step: {step_id}")
        module = _MONITORING_MODULES.get(step_id)
        step_started = time.monotonic()
        if module:
            await monitoring_event_service.emit_safely(
                "module.started", session_id=req.session_id, process_title=req.process_title,
                module=module, status="running",
                progress=(state["steps_completed"] / max(len(ordered_steps), 1)) * 100,
                metadata={"step_id": step_id, "model": req.global_model},
            )

        try:
            result: StepResult = await execute_step(step_id, req, previous_results)
        except Exception as exc:
            logger.error(f"[Pipeline] Unhandled exception in step {step_id}: {exc}", exc_info=True)
            result = StepResult(
                step_id=step_id,
                status=PipelineStepStatus.ERROR,
                error=str(exc),
                duration_seconds=0,
            )

        state["step_results"][step_id] = result

        if result.status == PipelineStepStatus.COMPLETED:
            state["steps_completed"] += 1
            previous_results[step_id] = result
            _push_event(state, "step_completed", {
                "step_id": step_id,
                "status": result.status.value,
                "duration_seconds": result.duration_seconds,
                "output_keys": list(result.output.keys()) if result.output else [],
            })
            logger.info(f"[Pipeline] Step completed: {step_id} ({result.duration_seconds:.1f}s)")
            if module:
                await monitoring_event_service.emit_safely(
                    "module.completed", session_id=req.session_id, process_title=req.process_title,
                    module=module, status="completed", progress=100,
                    duration_ms=int((time.monotonic() - step_started) * 1000),
                    metrics=_result_metrics(step_id, result), metadata={"step_id": step_id},
                )
        else:
            # Step failed – stop the pipeline
            _push_event(state, "step_failed", {
                "step_id": step_id,
                "status": result.status.value,
                "error": result.error,
            })
            logger.error(f"[Pipeline] Step failed: {step_id} — {result.error}")
            state["status"] = "failed"
            state["current_step"] = step_id
            state["error"] = f"Step '{step_id}' failed: {result.error}"
            state["finished_at"] = datetime.utcnow().isoformat()
            _push_event(state, "pipeline_failed", {
                "session_id": req.session_id,
                "failed_step": step_id,
                "error": result.error,
            })
            if module:
                await monitoring_event_service.emit_safely(
                    "module.failed", session_id=req.session_id, process_title=req.process_title,
                    module=module, status="failed",
                    duration_ms=int((time.monotonic() - step_started) * 1000),
                    error={"error_code": "PIPELINE_STEP_FAILED", "message": f"Pipeline step {step_id} failed."},
                )
            await monitoring_event_service.emit_safely(
                "pipeline.failed", session_id=req.session_id, process_title=req.process_title,
                status="failed", duration_ms=int((time.monotonic() - pipeline_started) * 1000),
                error={"error_code": "PIPELINE_FAILED", "message": f"Pipeline step {step_id} failed."},
            )
            return

    # All steps completed successfully
    state["status"] = "completed"
    state["current_step"] = None
    state["finished_at"] = datetime.utcnow().isoformat()
    _push_event(state, "pipeline_completed", {
        "session_id": req.session_id,
        "total_steps": len(ordered_steps),
        "steps_completed": state["steps_completed"],
    })
    logger.info(f"[Pipeline] All {len(ordered_steps)} steps completed for session {req.session_id}")
    await monitoring_event_service.emit_safely(
        "pipeline.completed", session_id=req.session_id, process_title=req.process_title,
        status="completed", progress=100,
        duration_ms=int((time.monotonic() - pipeline_started) * 1000),
        metrics={"steps_completed": state["steps_completed"]},
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/run")
async def run_pipeline(req: PipelineRunRequest):
    """
    Start a new pipeline run.

    Returns immediately with the session_id; clients should then connect to
    /api/pipeline/stream/{session_id} for real-time progress.
    """
    # Validate dependencies
    is_valid, violations = validate_pipeline(req.selected_steps)
    if not is_valid:
        missing_info = "; ".join(
            f"'{v['step']}' needs {v['missing']}" for v in violations
        )
        raise HTTPException(
            status_code=400,
            detail=f"Pipeline dependency violations: {missing_info}",
        )

    # Determine canonical step order
    ordered_steps = sort_steps(req.selected_steps)

    if not ordered_steps:
        raise HTTPException(status_code=400, detail="No valid steps selected.")

    # Generate session_id if not provided
    if not req.session_id:
        req.session_id = f"pipeline_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    # If a pipeline is already running for this session, reject
    existing = _get_state(req.session_id)
    if existing and existing.get("status") == "running":
        raise HTTPException(
            status_code=409,
            detail=f"Pipeline already running for session {req.session_id}",
        )

    # Create state + stop event
    state = _new_state(req.session_id, ordered_steps)
    stop_event = asyncio.Event()
    _stop_events[req.session_id] = stop_event

    # Launch background coroutine
    asyncio.create_task(
        _run_pipeline_background(req, ordered_steps, state, stop_event)
    )

    return {
        "success": True,
        "session_id": req.session_id,
        "ordered_steps": ordered_steps,
        "message": f"Pipeline started with {len(ordered_steps)} steps.",
    }


@router.get("/status/{session_id}")
async def get_pipeline_status(session_id: str):
    """Return a snapshot of the current pipeline status."""
    state = _get_state(session_id)
    if not state:
        raise HTTPException(
            status_code=404,
            detail=f"No pipeline found for session {session_id}",
        )

    # Serialize step_results
    step_results_serialized = {}
    for sid, r in state["step_results"].items():
        step_results_serialized[sid] = {
            "step_id": r.step_id,
            "status": r.status.value,
            "error": r.error,
            "duration_seconds": r.duration_seconds,
            "output_keys": list(r.output.keys()) if r.output else [],
        }

    return {
        "session_id": session_id,
        "status": state["status"],
        "current_step": state["current_step"],
        "steps_completed": state["steps_completed"],
        "steps_total": state["steps_total"],
        "ordered_steps": state["ordered_steps"],
        "step_results": step_results_serialized,
        "started_at": state["started_at"],
        "finished_at": state["finished_at"],
        "error": state["error"],
    }


@router.get("/step-result/{session_id}/{step_id}")
async def get_step_result(session_id: str, step_id: str):
    """Return the full output data for a completed pipeline step."""
    state = _get_state(session_id)
    if not state:
        raise HTTPException(
            status_code=404,
            detail=f"No pipeline found for session {session_id}",
        )

    result = state["step_results"].get(step_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No result for step '{step_id}' in session {session_id}",
        )

    return {
        "step_id": result.step_id,
        "status": result.status.value,
        "error": result.error,
        "duration_seconds": result.duration_seconds,
        "output": result.output or {},
    }


@router.get("/stream/{session_id}")
async def stream_pipeline(session_id: str):
    """
    Server-Sent Events (SSE) stream for real-time pipeline progress.

    The client should use EventSource to connect to this endpoint.
    Each message is a JSON-encoded event object.
    """
    state = _get_state(session_id)
    if not state:
        raise HTTPException(
            status_code=404,
            detail=f"No pipeline found for session {session_id}",
        )

    async def event_generator():
        last_index = 0
        while True:
            events = state["events"]
            new_events = events[last_index:]
            for event in new_events:
                yield f"data: {json.dumps(event)}\n\n"
            last_index = len(events)

            # Stop streaming once pipeline is in a terminal state and all events sent
            if state["status"] in ("completed", "failed", "stopped") and last_index >= len(events):
                # Send a final "done" signal and close
                yield f"data: {json.dumps({'type': 'stream_end', 'status': state['status']})}\n\n"
                return

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/stop/{session_id}")
async def stop_pipeline(session_id: str):
    """Request graceful stop of a running pipeline."""
    state = _get_state(session_id)
    if not state:
        raise HTTPException(
            status_code=404,
            detail=f"No pipeline found for session {session_id}",
        )

    if state["status"] != "running":
        return PipelineStopResponse(
            success=False,
            session_id=session_id,
            message=f"Pipeline is not running (current status: {state['status']})",
        )

    stop_event = _stop_events.get(session_id)
    if stop_event:
        stop_event.set()

    return PipelineStopResponse(
        success=True,
        session_id=session_id,
        message="Stop signal sent. Pipeline will halt after current step completes.",
    )


@router.delete("/clear/{session_id}")
async def clear_pipeline(session_id: str):
    """Remove a completed/failed pipeline state from memory."""
    state = _get_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"No pipeline for session {session_id}")

    if state["status"] == "running":
        raise HTTPException(status_code=409, detail="Cannot clear a running pipeline. Stop it first.")

    _pipeline_states.pop(session_id, None)
    _stop_events.pop(session_id, None)

    return {"success": True, "message": f"Pipeline state for {session_id} cleared."}
