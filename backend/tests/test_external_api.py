import os
from pathlib import Path
import sys
import time

import pytest
from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ["INITIALIZE_PROMPTS_ON_STARTUP"] = "false"

from core.settings import Settings, reset_settings_cache  # noqa: E402
from pipeline.pipeline_models import PipelineStepStatus, StepResult  # noqa: E402
from services.execution_client import ExecutionResult  # noqa: E402
from app import app  # noqa: E402
import routers.external_api_router as external_router  # noqa: E402
import routers.operations_router as operations_router  # noqa: E402
from services.test_case_generation_service import TestCaseGenerationService  # noqa: E402


client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("INITIALIZE_PROMPTS_ON_STARTUP", "false")
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("API_AUTH_ENABLED", "false")
    monkeypatch.delenv("APP_API_KEY", raising=False)
    reset_settings_cache()
    yield
    reset_settings_cache()


def _wait_for_job(job_id):
    for _ in range(50):
        response = client.get(f"/api/v1/jobs/{job_id}")
        if response.json()["status"] in {"completed", "failed"}:
            return response.json()
        time.sleep(0.01)
    raise AssertionError("job did not finish")


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_reports_database_failure(monkeypatch):
    def unavailable():
        raise RuntimeError("database down")

    monkeypatch.setattr(operations_router, "check_database_ready", unavailable)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["error_code"] == "DATABASE_UNAVAILABLE"
    assert response.json()["dependencies"] == {"database": "unavailable"}


def test_external_authentication(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("APP_API_KEY", "test-machine-secret")
    reset_settings_cache()

    # Liveness/readiness stay public for container orchestrators.
    assert client.get("/health").status_code == 200

    denied = client.get("/api/v1/jobs/missing")
    assert denied.status_code == 401
    assert denied.json()["error_code"] == "UNAUTHORIZED"

    allowed = client.get(
        "/api/v1/jobs/missing",
        headers={"Authorization": "Bearer test-machine-secret"},
    )
    assert allowed.status_code == 404
    assert allowed.json()["error_code"] == "JOB_NOT_FOUND"

    allowed_with_header = client.get(
        "/api/v1/jobs/missing",
        headers={"X-API-Key": "test-machine-secret"},
    )
    assert allowed_with_header.status_code == 404

    invalid_header = client.get(
        "/api/v1/jobs/missing",
        headers={"X-API-Key": "wrong-secret"},
    )
    assert invalid_header.status_code == 401


def test_request_validation_is_structured():
    response = client.post("/api/v1/artifacts", json={"name": "empty.txt", "content": ""})
    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"


def test_unknown_artifact_uses_structured_error():
    response = client.post("/api/v1/generations/scenarios", json={
        "process_title": "Missing artifact",
        "artifact_ids": ["art_doesnotexist"],
    })
    assert response.status_code == 404
    assert response.json()["error_code"] == "ARTIFACT_NOT_FOUND"


def test_headless_scenario_generation_uses_existing_adapter(monkeypatch):
    async def fake_generation(request, previous):
        assert request.files["test-scenario-generation"][0].content == "REQ-1"
        return StepResult(
            step_id="test-scenario-generation",
            status=PipelineStepStatus.COMPLETED,
            output={"test_scenarios": {"TestScenarios": [{"ScenarioID": "TS-001"}]}},
        )

    monkeypatch.setattr(external_router, "run_test_scenario_generation", fake_generation)
    artifact = client.post(
        "/api/v1/artifacts",
        json={"name": "requirements.txt", "content": "REQ-1", "type": "requirement"},
    )
    assert artifact.status_code == 201
    assert "content" not in artifact.json()

    response = client.post(
        "/api/v1/generations/scenarios",
        json={
            "process_title": "External flow",
            "artifact_ids": [artifact.json()["artifact_id"]],
        },
    )
    assert response.status_code == 202
    job = _wait_for_job(response.json()["job_id"])
    assert job["status"] == "completed"
    result = client.get(response.json()["result_url"])
    assert result.json()["result"]["test_scenarios"]["TestScenarios"][0]["ScenarioID"] == "TS-001"


def test_generation_failure_is_retained_in_job_state(monkeypatch):
    async def failed_generation(request, previous):
        return StepResult(
            step_id="test-scenario-generation",
            status=PipelineStepStatus.ERROR,
            error="model unavailable",
        )

    monkeypatch.setattr(external_router, "run_test_scenario_generation", failed_generation)
    response = client.post(
        "/api/v1/generations/scenarios",
        json={"process_title": "Failure audit"},
    )
    assert response.status_code == 202
    job = _wait_for_job(response.json()["job_id"])
    assert job["status"] == "failed"
    assert job["error"]["error_code"] == "JOB_FAILED"
    result = client.get(response.json()["result_url"])
    assert result.status_code == 422
    assert result.json()["job_id"] == response.json()["job_id"]


def test_execution_adapter_is_mockable(monkeypatch):
    class FakeExecutionClient:
        is_configured = True

        async def submit(self, request):
            assert request.test_code == "assert True"
            return ExecutionResult(
                execution_id="exec-1",
                status="completed",
                passed=1,
                failed=0,
            )

    monkeypatch.setattr(external_router, "_execution_client", lambda: FakeExecutionClient())
    response = client.post("/api/v1/executions", json={"test_code": "assert True"})
    assert response.status_code == 202
    job = _wait_for_job(response.json()["job_id"])
    assert job["status"] == "completed"
    result = client.get(response.json()["result_url"]).json()["result"]
    assert result["execution_id"] == "exec-1"
    assert result["passed"] == 1


def test_execution_endpoint_reports_missing_optional_executor(monkeypatch):
    class UnconfiguredExecutionClient:
        is_configured = False

    monkeypatch.setattr(external_router, "_execution_client", lambda: UnconfiguredExecutionClient())
    response = client.post("/api/v1/executions", json={"test_code": "assert True"})
    assert response.status_code == 503
    assert response.json() == {
        "error_code": "EXECUTION_SERVICE_NOT_CONFIGURED",
        "message": "The optional external execution service is not configured.",
        "details": (
            "Set EXECUTION_SERVICE_URL for HTTP execution, or set "
            "EXECUTION_ADAPTER=ssh_docker and SSH_EXECUTION_HOST for the ROS 2 harness."
        ),
        "job_id": None,
    }


def test_legacy_ui_case_route_uses_shared_service(monkeypatch):
    captured = {}

    async def fake_generate(self, payload):
        captured.update(payload)
        return {"status": "success", "test_case_results": [], "summary": {}}

    monkeypatch.setattr(TestCaseGenerationService, "generate", fake_generate)
    response = client.post(
        "/api/processes/test-scenario-generation/generate-test-cases",
        json={"selected_scenarios": [{"scenario_id": "TS-1"}]},
    )
    assert response.status_code == 200
    assert captured["selected_scenarios"][0]["scenario_id"] == "TS-1"


def test_configuration_loading(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_PORT", "9123")
    monkeypatch.setenv("DATABASE_NAME", "external_test_db")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://one.example,https://two.example")
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))
    settings = Settings.from_env()
    assert settings.app_port == 9123
    assert settings.database_name == "external_test_db"
    assert settings.cors_origins == ["https://one.example", "https://two.example"]


def test_authenticated_configuration_rejects_wildcard_cors(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("APP_API_KEY", "secret")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    with pytest.raises(ValueError, match="Wildcard CORS"):
        Settings.from_env()


def test_cors_allows_configured_origin_and_rejects_other_origin():
    allowed = client.options(
        "/api/v1/artifacts",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"

    rejected = client.options(
        "/api/v1/artifacts",
        headers={
            "Origin": "https://unconfigured.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers
