"""MongoDB-backed monitoring history with process-local SSE fan-out."""

import asyncio
from collections import deque
from datetime import datetime, timezone
import logging
from typing import Any, AsyncGenerator, Dict, Optional
import uuid

from pymongo import ASCENDING, DESCENDING

from core.database import get_database
from core.settings import get_settings
from models.monitoring import MonitoringError, MonitoringEvent, MonitoringEventType


logger = logging.getLogger(__name__)
_SENSITIVE_PARTS = ("api_key", "apikey", "token", "authorization", "secret", "password")
_LARGE_PAYLOAD_KEYS = ("test_code", "generated_code", "content", "prompt", "artifacts", "files")


def _dump(model, *, json_mode: bool = False):
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json" if json_mode else "python")
    return model.dict()


def _safe_mapping(value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Drop secrets and artifact/code payloads from telemetry recursively."""
    result: Dict[str, Any] = {}
    for key, item in (value or {}).items():
        lowered = str(key).lower()
        if any(part in lowered for part in _SENSITIVE_PARTS + _LARGE_PAYLOAD_KEYS):
            continue
        if isinstance(item, dict):
            result[str(key)] = _safe_mapping(item)
        elif isinstance(item, (str, int, float, bool)) or item is None:
            result[str(key)] = item if not isinstance(item, str) else item[:500]
        elif isinstance(item, (list, tuple)):
            result[str(key)] = [
                entry if isinstance(entry, (int, float, bool)) or entry is None else str(entry)[:200]
                for entry in item[:50]
            ]
    return result


class MonitoringEventService:
    def __init__(self, memory_limit: int = 1000):
        self._recent = deque(maxlen=memory_limit)
        self._subscribers: set[asyncio.Queue] = set()
        self._persistence_tasks: set[asyncio.Task] = set()
        self._indexes_ready = False

    async def emit(self, event_type: str, **fields) -> Optional[MonitoringEvent]:
        if not get_settings().monitoring_enabled:
            return None
        fields["metrics"] = _safe_mapping(fields.get("metrics"))
        fields["metadata"] = _safe_mapping(fields.get("metadata"))
        error = fields.get("error")
        if isinstance(error, dict):
            fields["error"] = MonitoringError(
                error_code=str(error.get("error_code", "OPERATION_FAILED")),
                message=str(error.get("message", "Operation failed."))[:500],
            )
        event = MonitoringEvent(
            event_id=f"evt_{uuid.uuid4().hex}",
            event_type=MonitoringEventType(event_type),
            **fields,
        )
        self._recent.append(event)
        for queue in tuple(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                self._subscribers.discard(queue)

        task = asyncio.create_task(self._persist(event))
        self._persistence_tasks.add(task)
        task.add_done_callback(self._persistence_tasks.discard)
        return event

    async def emit_safely(self, event_type: str, **fields) -> Optional[MonitoringEvent]:
        """Best-effort boundary used by authoritative generation paths."""
        try:
            return await self.emit(event_type, **fields)
        except Exception as exc:
            logger.error("Monitoring event emission failed: %s", type(exc).__name__)
            return None

    async def _persist(self, event: MonitoringEvent) -> None:
        try:
            db = await get_database()
            collection = db["monitoring_events"]
            if not self._indexes_ready:
                await collection.create_index([("event_id", ASCENDING)], unique=True)
                for field in ("process_id", "process_title", "session_id", "job_id", "execution_id", "module", "event_type", "status"):
                    await collection.create_index([(field, ASCENDING), ("timestamp", DESCENDING)])
                retention = get_settings().monitoring_event_retention_days
                if retention > 0:
                    await collection.create_index(
                        [("timestamp", ASCENDING)],
                        expireAfterSeconds=retention * 86400,
                        name="monitoring_event_ttl",
                    )
                self._indexes_ready = True
            await collection.insert_one(_dump(event))
        except Exception as exc:
            logger.error("Monitoring event persistence failed: %s", type(exc).__name__)

    async def drain(self) -> None:
        tasks = tuple(self._persistence_tasks)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def list_events(self, filters: Dict[str, Any], since: Optional[datetime], limit: int) -> list[MonitoringEvent]:
        query = {key: value for key, value in filters.items() if value is not None}
        if since is not None:
            if since.tzinfo is None:
                since = since.replace(tzinfo=timezone.utc)
            query["timestamp"] = {"$gte": since}
        try:
            db = await get_database()
            cursor = db["monitoring_events"].find(query, {"_id": 0}).sort("timestamp", DESCENDING).limit(limit)
            rows = await cursor.to_list(length=limit)
            return [MonitoringEvent(**row) for row in rows]
        except Exception as exc:
            logger.warning("Monitoring history database query failed; using process-local history: %s", type(exc).__name__)
            events = [event for event in reversed(self._recent) if self._matches(event, query)]
            return events[:limit]

    async def get_event(self, event_id: str) -> Optional[MonitoringEvent]:
        try:
            db = await get_database()
            row = await db["monitoring_events"].find_one({"event_id": event_id}, {"_id": 0})
            if row:
                return MonitoringEvent(**row)
        except Exception as exc:
            logger.warning("Monitoring event database lookup failed: %s", type(exc).__name__)
        return next((item for item in self._recent if item.event_id == event_id), None)

    @staticmethod
    def _matches(event: MonitoringEvent, filters: Dict[str, Any]) -> bool:
        for key, expected in filters.items():
            if expected is None:
                continue
            if key == "timestamp":
                if event.timestamp < expected["$gte"]:
                    return False
                continue
            actual = getattr(event, key, None)
            if hasattr(actual, "value"):
                actual = actual.value
            if actual != expected:
                return False
        return True

    async def subscribe(self, filters: Dict[str, Any]) -> AsyncGenerator[MonitoringEvent, None]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._subscribers.add(queue)
        try:
            while True:
                event = await queue.get()
                if self._matches(event, filters):
                    yield event
        finally:
            self._subscribers.discard(queue)

    def recent_after(self, event_id: Optional[str], filters: Dict[str, Any]) -> list[MonitoringEvent]:
        events = list(self._recent)
        start = 0
        if event_id:
            for index, event in enumerate(events):
                if event.event_id == event_id:
                    start = index + 1
                    break
        return [event for event in events[start:] if self._matches(event, filters)]


monitoring_event_service = MonitoringEventService()
