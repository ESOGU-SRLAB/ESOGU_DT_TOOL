"""Authenticated REST history and SSE stream for generic STLC telemetry."""

from datetime import datetime
import json
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from core.auth import require_api_key
from models.monitoring import MonitoringEvent, MonitoringEventList
from services.monitoring_event_service import MonitoringEventService, monitoring_event_service


router = APIRouter(
    prefix="/api/v1/monitoring",
    tags=["monitoring"],
    dependencies=[Depends(require_api_key)],
)


def get_monitoring_service() -> MonitoringEventService:
    return monitoring_event_service


def _filters(process_id=None, process_title=None, session_id=None, job_id=None, execution_id=None, module=None, event_type=None, status=None):
    return {
        "process_id": process_id,
        "process_title": process_title,
        "session_id": session_id,
        "job_id": job_id,
        "execution_id": execution_id,
        "module": module,
        "event_type": event_type,
        "status": status,
    }


@router.get("/events/stream", summary="Stream new monitoring events with SSE")
async def stream_events(
    request: Request,
    process_id: Optional[str] = None,
    session_id: Optional[str] = None,
    job_id: Optional[str] = None,
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
    service: MonitoringEventService = Depends(get_monitoring_service),
):
    filters = _filters(process_id=process_id, session_id=session_id, job_id=job_id)

    def encode(event: MonitoringEvent) -> str:
        payload = event.model_dump(mode="json") if hasattr(event, "model_dump") else event.dict()
        return f"id: {event.event_id}\nevent: {event.event_type.value}\ndata: {json.dumps(payload)}\n\n"

    async def generate():
        for event in service.recent_after(last_event_id, filters):
            yield encode(event)
        async for event in service.subscribe(filters):
            if await request.is_disconnected():
                break
            yield encode(event)

    return StreamingResponse(generate(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })


@router.get("/events", response_model=MonitoringEventList, summary="Query persisted monitoring history")
async def list_events(
    process_id: Optional[str] = None,
    process_title: Optional[str] = None,
    session_id: Optional[str] = None,
    job_id: Optional[str] = None,
    execution_id: Optional[str] = None,
    module: Optional[str] = None,
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    since: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=500),
    service: MonitoringEventService = Depends(get_monitoring_service),
):
    events = await service.list_events(
        _filters(process_id, process_title, session_id, job_id, execution_id, module, event_type, status),
        since,
        limit,
    )
    return {"events": events, "count": len(events), "limit": limit}


@router.get("/events/{event_id}", response_model=MonitoringEvent, summary="Get one monitoring event")
async def get_event(event_id: str, service: MonitoringEventService = Depends(get_monitoring_service)):
    event = await service.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail={
            "error_code": "MONITORING_EVENT_NOT_FOUND",
            "message": "Monitoring event was not found.",
            "details": event_id,
        })
    return event
