import asyncio
import os
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
os.environ["INITIALIZE_PROMPTS_ON_STARTUP"] = "false"

from app import app
from core.settings import reset_settings_cache
from services.job_service import JobService
from services.monitoring_event_service import MonitoringEventService
import services.monitoring_event_service as monitoring_module
import services.job_service as job_module
import routers.pipeline_router as pipeline_router
from pipeline.pipeline_models import PipelineRunRequest, PipelineStepStatus, StepResult


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    monkeypatch.setenv("MONITORING_ENABLED", "true")
    monkeypatch.setenv("API_AUTH_ENABLED", "false")
    reset_settings_cache()
    yield
    reset_settings_cache()


class FakeCollection:
    def __init__(self): self.rows = []
    async def create_index(self, *args, **kwargs): return "idx"
    async def insert_one(self, row): self.rows.append(row)


class FakeDB:
    def __init__(self): self.collection = FakeCollection()
    def __getitem__(self, name): assert name == "monitoring_events"; return self.collection


def test_event_creation_persistence_serialization_and_sanitization(monkeypatch):
    async def exercise():
        database = FakeDB()
        async def fake_db(): return database
        monkeypatch.setattr(monitoring_module, "get_database", fake_db)
        service = MonitoringEventService()
        event = await service.emit(
            "module.completed", module="test_code_generation", session_id="s1",
            metrics={"generated_test_count": 2},
            metadata={"model": "local", "test_code": "SECRET-CODE", "api_key": "SECRET-KEY"},
            status="completed",
        )
        await service.drain()
        assert event.event_id.startswith("evt_")
        assert event.metadata == {"model": "local"}
        assert database.collection.rows[0]["event_type"].value == "module.completed"
        assert "SECRET" not in str(database.collection.rows[0])
    asyncio.run(exercise())


def test_filtering_bounded_history_and_live_publish(monkeypatch):
    async def exercise():
        async def unavailable(): raise RuntimeError("offline")
        monkeypatch.setattr(monitoring_module, "get_database", unavailable)
        service = MonitoringEventService()
        await service.emit("module.started", module="scenario_generation", session_id="one")
        await service.emit("module.completed", module="scenario_generation", session_id="two")
        history = await service.list_events({"session_id": "one"}, None, 1)
        assert len(history) == 1 and history[0].session_id == "one"
        assert len(service.recent_after(None, {"session_id": None, "job_id": None})) == 2

        async def receive():
            async for item in service.subscribe({"job_id": "job-1"}): return item
        receiver = asyncio.create_task(receive())
        await asyncio.sleep(0)
        await service.emit("module.started", module="environment_setup", job_id="job-1")
        assert (await asyncio.wait_for(receiver, 1)).job_id == "job-1"
    asyncio.run(exercise())


def test_module_and_execution_job_events(monkeypatch):
    async def exercise():
        emitted = []
        async def capture(event_type, **fields): emitted.append((event_type, fields))
        monkeypatch.setattr(monitoring_module.monitoring_event_service, "emit", capture)

        service = JobService()
        async def ok(): return {"test_scenarios": {"TestScenarios": [{}, {}]}}
        record = service.submit("scenario", ok(), "s1", {"module": "scenario_generation"})
        await asyncio.sleep(0.02)
        assert service.get(record["job_id"])["status"] == "completed"
        assert [item[0] for item in emitted] == ["module.started", "module.completed"]
        assert emitted[-1][1]["metrics"]["scenario_count"] == 2

        emitted.clear()
        async def executed(): return {"execution_id": "e1", "passed": 3, "failed": 1}
        service.submit("execute", executed(), "s2", {"module": "test_execution"})
        await asyncio.sleep(0.02)
        assert [item[0] for item in emitted] == ["execution.submitted", "execution.started", "execution.completed"]
    asyncio.run(exercise())


def test_monitoring_failure_is_non_authoritative(monkeypatch):
    async def exercise():
        service = MonitoringEventService()
        async def broken(*args, **kwargs): raise RuntimeError("monitoring down")
        monkeypatch.setattr(service, "emit", broken)
        assert await service.emit_safely("module.started", module="environment_setup") is None
    asyncio.run(exercise())


def test_real_pipeline_path_emits_pipeline_and_module_lifecycle(monkeypatch):
    async def exercise():
        emitted = []
        async def capture(event_type, **fields): emitted.append((event_type, fields)); return None
        async def complete(step_id, request, previous):
            return StepResult(
                step_id=step_id, status=PipelineStepStatus.COMPLETED,
                output={"test_scenarios": {"TestScenarios": [{"ScenarioID": "S1"}]}},
                duration_seconds=0.01,
            )
        monkeypatch.setattr(pipeline_router.monitoring_event_service, "emit_safely", capture)
        monkeypatch.setattr(pipeline_router, "execute_step", complete)
        request = PipelineRunRequest(
            session_id="pipeline-session", process_title="ProductDetection",
            selected_steps=["test-scenario-generation"],
        )
        state = pipeline_router._new_state(request.session_id, request.selected_steps)
        await pipeline_router._run_pipeline_background(request, request.selected_steps, state, asyncio.Event())
        assert state["status"] == "completed"
        assert [event[0] for event in emitted] == [
            "pipeline.started", "module.started", "module.completed", "pipeline.completed",
        ]
        assert emitted[2][1]["metrics"]["scenario_count"] == 1
    asyncio.run(exercise())


def test_monitoring_endpoint_authentication(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("APP_API_KEY", "monitoring-test-key")
    reset_settings_cache()
    client = TestClient(app)
    assert client.get("/api/v1/monitoring/events").status_code == 401
    response = client.get(
        "/api/v1/monitoring/events?limit=1",
        headers={"X-API-Key": "monitoring-test-key"},
    )
    assert response.status_code == 200
    assert response.json()["limit"] == 1
