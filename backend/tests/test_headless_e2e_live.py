"""Opt-in real STLC headless workflow against local MongoDB and model service."""

import os
from pathlib import Path
import sys
import time
import uuid

import pytest
from fastapi.testclient import TestClient


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_HEADLESS_E2E") != "1",
    reason="Set RUN_HEADLESS_E2E=1 to use local MongoDB and model services",
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import app  # noqa: E402
from core.database import get_db  # noqa: E402


def _await_job(client: TestClient, job_id: str, timeout_seconds: int = 240):
    deadline = time.monotonic() + timeout_seconds
    seen = []
    while time.monotonic() < deadline:
        status_response = client.get(f"/api/v1/jobs/{job_id}")
        assert status_response.status_code == 200, status_response.text
        body = status_response.json()
        if not seen or seen[-1] != body["status"]:
            seen.append(body["status"])
        if body["status"] == "completed":
            result_response = client.get(f"/api/v1/jobs/{job_id}/result")
            assert result_response.status_code == 200, result_response.text
            return body, result_response.json()["result"], seen
        if body["status"] == "failed":
            pytest.fail(f"Job failed: {body['error']}")
        time.sleep(0.25)
    pytest.fail(f"Job {job_id} timed out after {timeout_seconds}s; states={seen}")


def test_real_headless_generation_chain():
    process_title = f"headless-audit-{uuid.uuid4().hex[:10]}"
    model = os.getenv("HEADLESS_E2E_MODEL", "llama-3.2-3b-instruct")
    source_path = REPO_DIR / "test_inputs" / "Functional_and_NonFunctional_Requirements.txt"
    source_content = source_path.read_text(encoding="utf-8")

    with TestClient(app) as client:
        artifact_response = client.post("/api/v1/artifacts", json={
            "name": source_path.name,
            "type": "requirement",
            "content": source_content,
            "metadata": {"purpose": "headless-e2e-audit"},
        })
        assert artifact_response.status_code == 201, artifact_response.text
        artifact_id = artifact_response.json()["artifact_id"]

        environment_response = client.post("/api/v1/generations/environment", json={
            "process_title": process_title,
            "environment_name": f"{process_title}-environment",
            "artifact_ids": [artifact_id],
            "model": model,
        })
        assert environment_response.status_code == 202, environment_response.text
        environment_submission = environment_response.json()
        environment_status, environment_result, environment_states = _await_job(
            client, environment_submission["job_id"]
        )
        assert environment_result["session_id"] == environment_submission["session_id"]
        assert environment_result["setups"]

        scenario_response = client.post("/api/v1/generations/scenarios", json={
            "process_title": process_title,
            "artifact_ids": [artifact_id],
            "model": model,
            "test_type": "Functional",
            "test_category": "Positive",
        })
        assert scenario_response.status_code == 202, scenario_response.text
        scenario_submission = scenario_response.json()
        scenario_status, scenario_result, scenario_states = _await_job(
            client, scenario_submission["job_id"]
        )
        scenarios = scenario_result["test_scenarios"]["TestScenarios"]
        assert scenarios

        cases_response = client.post("/api/v1/generations/test-cases", json={
            "process_title": process_title,
            "scenario_job_id": scenario_submission["job_id"],
            "artifact_ids": [artifact_id],
            "model": model,
        })
        assert cases_response.status_code == 202, cases_response.text
        cases_submission = cases_response.json()
        cases_status, cases_result, cases_states = _await_job(
            client, cases_submission["job_id"]
        )
        assert cases_result["summary"]["total_test_cases"] > 0

        code_response = client.post("/api/v1/generations/test-code", json={
            "process_title": process_title,
            "environment_session_id": environment_submission["session_id"],
            "environment_name": f"{process_title}-code",
            "artifact_ids": [artifact_id],
            "model": model,
            "max_test_cases": 1,
        })
        assert code_response.status_code == 202, code_response.text
        code_submission = code_response.json()
        code_status, code_result, code_states = _await_job(
            client, code_submission["job_id"]
        )
        assert code_result["success"] is True
        assert code_result["generated_count"] > 0

        db = get_db()
        environment_doc = db["session_history"].find_one({
            "session_id": environment_submission["session_id"],
            "processes.environment_setup": {"$exists": True},
        })
        scenario_doc = db["session_history"].find_one({
            "session_id": scenario_submission["session_id"],
            "processes.test_scenario_generation": {"$exists": True},
        })
        cases_doc = db["session_history"].find_one({
            "session_id": cases_submission["session_id"],
            "processes.test_case_generation": {"$exists": True},
        })
        code_doc = db["session_history"].find_one({
            "session_id": code_submission["session_id"],
            "processes.test_code_generation": {"$exists": True},
        })
        assert environment_doc and scenario_doc and cases_doc and code_doc

        print({
            "artifact_id": artifact_id,
            "process_title": process_title,
            "environment": {
                "http_status": environment_response.status_code,
                "job_id": environment_submission["job_id"],
                "session_id": environment_submission["session_id"],
                "states": environment_states,
                "result_keys": sorted(environment_result),
            },
            "scenarios": {
                "http_status": scenario_response.status_code,
                "job_id": scenario_submission["job_id"],
                "session_id": scenario_submission["session_id"],
                "states": scenario_states,
                "scenario_count": len(scenarios),
            },
            "test_cases": {
                "http_status": cases_response.status_code,
                "job_id": cases_submission["job_id"],
                "session_id": cases_submission["session_id"],
                "states": cases_states,
                "case_count": cases_result["summary"]["total_test_cases"],
            },
            "test_code": {
                "http_status": code_response.status_code,
                "job_id": code_submission["job_id"],
                "session_id": code_submission["session_id"],
                "states": code_states,
                "generated_count": code_result["generated_count"],
            },
            "persisted": {
                "environment_setup": True,
                "test_scenario_generation": True,
                "test_case_generation": True,
                "test_code_generation": True,
            },
        })
