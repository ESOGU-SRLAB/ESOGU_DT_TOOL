import asyncio
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import routers.remote_execution_router as remote_router  # noqa: E402
from services.execution_client import (  # noqa: E402
    ExecutionRequest,
    ExecutionResult,
    SshDockerExecutionClient,
)


def test_password_configuration_uses_noninteractive_password_transport(monkeypatch):
    client = SshDockerExecutionClient(
        host="ifarlab",
        remote_dir="~/stlc_runs",
        image="ros2-exec-harness:0.3.2",
        password="configured-secret",
        timeout_seconds=60,
        connect_timeout_seconds=5,
    )
    captured = {}

    def fake_password_submit(request, execution_id, filename, remote_file, started_at, checksum):
        captured.update({
            "request": request,
            "filename": filename,
            "remote_file": remote_file,
        })
        return ExecutionResult(
            execution_id=execution_id,
            status="completed",
            passed=1,
            artifacts=[{"remote_path": remote_file, "sha256": checksum}],
        )

    monkeypatch.setattr(client, "_submit_with_password", fake_password_submit)
    result = asyncio.run(client.submit(ExecutionRequest(
        test_code="print('remote')",
        language="python",
        configuration={"timeout_seconds": 25},
    )))

    assert result.status == "completed"
    assert captured["request"].test_code == "print('remote')"
    assert captured["filename"].endswith(".py")
    assert captured["remote_file"].startswith("~/stlc_runs/exec-")


def test_remote_execution_endpoint_runs_all_selected_files(monkeypatch):
    submitted = []

    class FakeClient:
        is_configured = True
        host = "ifarlab"
        remote_dir = "~/stlc_runs"
        image = "ros2-exec-harness:0.3.2"
        password = "configured"

        async def submit(self, request):
            submitted.append(request)
            failed = request.test_case_id == "TC-2"
            return ExecutionResult(
                execution_id=f"exec-{request.test_case_id}",
                status="completed",
                verdict="failed" if failed else "passed",
                passed=0 if failed else 1,
                failed=1 if failed else 0,
                logs=f"ran {request.test_case_id}",
                error="assertion failed" if failed else None,
                artifacts=[{"remote_path": f"~/stlc_runs/{request.test_case_id}.py"}],
            )

    monkeypatch.setattr(remote_router, "SshDockerExecutionClient", FakeClient)
    request = remote_router.ExecuteRemoteTestsRequest(
        session_id="session-remote",
        process_name="Remote process",
        timeout_seconds=45,
        test_files=[
            {"test_id": "TC-1", "filename": "tc_1.py", "content": "print('one')"},
            {"test_id": "TC-2", "filename": "tc_2.py", "content": "raise AssertionError"},
        ],
    )

    response = asyncio.run(remote_router.execute_remote_tests(request))

    assert response["success"] is False
    assert response["summary"] == {
        "total": 2,
        "passed": 1,
        "failed": 1,
        "error": 0,
        "blocked": 0,
        "not_executed": 0,
        "invalid": 0,
    }
    assert [item.test_case_id for item in submitted] == ["TC-1", "TC-2"]
    assert all(item.framework == "pytest" for item in submitted)
    assert all(item.configuration == {"timeout_seconds": 45} for item in submitted)
    assert response["results"][0]["artifacts"][0]["remote_path"].endswith("TC-1.py")


def test_pytest_framework_uses_harness_python_entrypoint():
    request = ExecutionRequest(test_code="def test_ok(): assert True", framework="pytest")

    assert SshDockerExecutionClient._runner_command(request) == [
        "python3", "/harness_ws/generated_script.py"
    ]


def test_harness_exit_codes_have_distinct_test_verdicts():
    expected = {
        0: ("completed", "passed", 1, 0, 0, 0, 0),
        1: ("completed", "failed", 0, 1, 0, 0, 0),
        2: ("error", "error", 0, 0, 1, 0, 0),
        5: ("not_executed", "not_executed", 0, 0, 0, 0, 1),
        124: ("blocked", "blocked", 0, 0, 0, 1, 0),
    }

    for exit_code, values in expected.items():
        result = SshDockerExecutionClient._classify_exit_code(exit_code)
        assert (
            result["status"],
            result["verdict"],
            result["passed"],
            result["failed"],
            result["errors"],
            result["blocked"],
            result["not_executed"],
        ) == values


def test_remote_execution_does_not_submit_generation_oracle_rejections(monkeypatch):
    submitted = []

    class FakeClient:
        is_configured = True

        async def submit(self, request):
            submitted.append(request)
            raise AssertionError("invalid test must not reach the remote runner")

    monkeypatch.setattr(remote_router, "SshDockerExecutionClient", FakeClient)
    request = remote_router.ExecuteRemoteTestsRequest(
        test_files=[{
            "test_id": "TC-INVALID",
            "filename": "invalid.py",
            "content": "def test_invalid(): assert True",
            "execution_eligibility": "invalid",
            "eligibility_reason": "Unknown controller method validate_input().",
            "oracle": {"passed": False},
        }],
    )

    response = asyncio.run(remote_router.execute_remote_tests(request))

    assert submitted == []
    assert response["success"] is False
    assert response["summary"]["invalid"] == 1
    assert response["summary"]["failed"] == 0
    assert response["results"][0]["verdict"] == "invalid"
