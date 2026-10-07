import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import Thread

import pytest
from pydantic import ValidationError


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import services.execution_client as execution_module  # noqa: E402
import core.database as database_module  # noqa: E402
from pipeline.pipeline_models import PipelineRunRequest, StepConfig  # noqa: E402
from pipeline.step_adapters import run_test_execution  # noqa: E402
from services.execution_client import (  # noqa: E402
    ExecutionNotConfiguredError,
    ExecutionRequest,
    HttpExecutionClient,
    SshDockerExecutionClient,
)
from services.job_service import JobNotFoundError, JobService  # noqa: E402


def test_job_lifecycle_failure_and_concurrency():
    async def exercise():
        service = JobService()
        gate = asyncio.Event()

        async def blocked(value):
            await gate.wait()
            return {"value": value}

        first = service.submit("generation", blocked(1), correlation_id="session-1")
        second = service.submit("generation", blocked(2), correlation_id="session-2")
        assert first["status"] == "pending"
        assert second["status"] == "pending"

        await asyncio.sleep(0)
        assert service.get(first["job_id"])["status"] == "running"
        assert service.get(second["job_id"])["status"] == "running"

        gate.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert service.get(first["job_id"])["result"] == {"value": 1}
        assert service.get(second["job_id"])["result"] == {"value": 2}
        assert service.get(first["job_id"])["status"] == "completed"

        async def failing():
            raise RuntimeError("provider token=must-not-leak")

        failed = service.submit("generation", failing())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        failed_record = service.get(failed["job_id"])
        assert failed_record["status"] == "failed"
        assert failed_record["error"]["error_code"] == "JOB_FAILED"
        assert "must-not-leak" not in failed_record["error"]["details"]
        assert failed_record["finished_at"]

        with pytest.raises(JobNotFoundError):
            service.get("job_unknown")

    asyncio.run(exercise())


def test_missing_execution_service_url_fails_cleanly():
    client = HttpExecutionClient(base_url="")
    with pytest.raises(ExecutionNotConfiguredError, match="EXECUTION_SERVICE_URL"):
        asyncio.run(client.submit(ExecutionRequest(test_code="assert True")))


class _FakeResponse:
    def __init__(self, status=200, body=None, text="", enter_error=None):
        self.status = status
        self._body = body
        self._text = text
        self._enter_error = enter_error

    async def __aenter__(self):
        if self._enter_error:
            raise self._enter_error
        return self

    async def __aexit__(self, *args):
        return False

    async def json(self):
        return self._body

    async def text(self):
        return self._text


class _FakeSession:
    response = None
    captured = None

    def __init__(self, timeout):
        type(self).captured = {"timeout": timeout}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def post(self, url, json, headers):
        type(self).captured.update({"url": url, "json": json, "headers": headers})
        return type(self).response


def test_execution_adapter_request_and_result_contract(monkeypatch):
    _FakeSession.response = _FakeResponse(body={
        "execution_id": "exec-1",
        "status": "completed",
        "started_at": "2026-09-03T10:00:00Z",
        "finished_at": "2026-09-03T10:00:01Z",
        "passed": 1,
        "failed": 0,
        "logs": "ok",
        "error": None,
        "artifacts": [{"name": "report.xml"}],
    })
    monkeypatch.setattr(execution_module.aiohttp, "ClientSession", _FakeSession)
    client = HttpExecutionClient(base_url="https://executor.example", token="secret", timeout_seconds=7)
    request = ExecutionRequest(
        test_code="assert True",
        language="python",
        framework="pytest",
        test_case_id="TC-1",
        session_id="session-1",
        artifact_ids=["art-1"],
        metadata={"source": "audit"},
        configuration={"timeout": 5},
    )
    result = asyncio.run(client.submit(request))
    assert result.execution_id == "exec-1"
    assert result.passed == 1
    assert _FakeSession.captured["url"] == "https://executor.example/executions"
    assert _FakeSession.captured["json"]["test_case_id"] == "TC-1"
    assert _FakeSession.captured["headers"]["Authorization"] == "Bearer secret"


def test_execution_adapter_against_independent_http_stub():
    captured = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            captured["path"] = self.path
            captured["authorization"] = self.headers.get("Authorization")
            captured["body"] = json.loads(self.rfile.read(length))
            response = json.dumps({
                "execution_id": "remote-exec-1",
                "status": "completed",
                "started_at": "2026-09-04T10:00:00Z",
                "finished_at": "2026-09-04T10:00:01Z",
                "passed": 2,
                "failed": 0,
                "logs": "remote stub completed",
                "error": None,
                "artifacts": [{"name": "report.xml", "url": "/artifacts/report.xml"}],
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def log_message(self, _format, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = ExecutionRequest(
            test_code="def test_robot(): assert True",
            language="python",
            framework="pytest",
            test_case_id="TC-42",
            session_id="session-42",
            artifact_ids=["artifact-42"],
            metadata={"correlation_id": "cloud-42"},
            configuration={"timeout_seconds": 30},
        )
        client = HttpExecutionClient(
            base_url=f"http://127.0.0.1:{server.server_port}",
            token="stub-token",
            timeout_seconds=5,
        )
        result = asyncio.run(client.submit(request))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert result.execution_id == "remote-exec-1"
    assert (result.passed, result.failed) == (2, 0)
    assert captured["path"] == "/executions"
    assert captured["authorization"] == "Bearer stub-token"
    assert captured["body"] == {
        "test_code": "def test_robot(): assert True",
        "language": "python",
        "framework": "pytest",
        "test_case_id": "TC-42",
        "session_id": "session-42",
        "artifact_ids": ["artifact-42"],
        "metadata": {"correlation_id": "cloud-42"},
        "configuration": {"timeout_seconds": 30},
    }


@pytest.mark.parametrize(
    "response,expected_exception",
    [
        (_FakeResponse(status=503, text="unavailable"), RuntimeError),
        (_FakeResponse(status=200, body={"unexpected": "shape"}), ValidationError),
        (_FakeResponse(enter_error=TimeoutError("timed out")), TimeoutError),
        (_FakeResponse(enter_error=ConnectionError("refused")), ConnectionError),
    ],
)
def test_execution_adapter_failures(monkeypatch, response, expected_exception):
    _FakeSession.response = response
    monkeypatch.setattr(execution_module.aiohttp, "ClientSession", _FakeSession)
    client = HttpExecutionClient(base_url="https://executor.example", timeout_seconds=1)
    with pytest.raises(expected_exception):
        asyncio.run(client.submit(ExecutionRequest(test_code="assert True")))


def test_ssh_docker_adapter_uploads_and_runs_verified_ros2_command(tmp_path):
    client = SshDockerExecutionClient(
        host="ifarlab",
        remote_dir="~/stlc_runs",
        image="ros2-exec-harness:0.3.2",
        identity_file=tmp_path / "id_ed25519_ifarlab",
        password="",
        timeout_seconds=60,
        connect_timeout_seconds=5,
    )
    calls = []

    async def fake_run(command, timeout):
        calls.append((command, timeout))
        if command[0] == "scp":
            local_path = Path(command[-2])
            assert local_path.read_text(encoding="utf-8") == "print('robot test')"
        return 0, "remote ok"

    client._run_command = fake_run
    result = asyncio.run(client.submit(ExecutionRequest(
        test_code="print('robot test')",
        language="python",
        test_case_id="TC-ROS2-1",
        configuration={"timeout_seconds": 30},
    )))

    assert result.status == "completed"
    assert (result.passed, result.failed) == (1, 0)
    assert len(calls) == 3
    assert calls[0][0][0] == "ssh"
    assert "docker image inspect ros2-exec-harness:0.3.2" in calls[0][0][-1]
    assert calls[1][0][0] == "scp"
    assert calls[1][0][-1].startswith("ifarlab:~/stlc_runs/exec-")
    remote_command = calls[2][0][-1]
    assert "--network host" in remote_command
    assert "--ipc=host" in remote_command
    assert "FASTDDS_BUILTIN_TRANSPORTS=UDPv4" in remote_command
    assert not remote_command.startswith("timeout ")
    assert "python3 -m pytest" not in remote_command
    assert remote_command.endswith("python3 /harness_ws/generated_script.py")
    assert calls[2][1] is None
    assert "/harness_ws/generated_script.py:ro" in remote_command
    assert result.artifacts[0]["sha256"]


def test_ssh_docker_adapter_reports_remote_container_failure():
    client = SshDockerExecutionClient(
        host="ifarlab",
        remote_dir="~/stlc_runs",
        image="ros2-exec-harness:0.3.2",
        password="",
        timeout_seconds=20,
        connect_timeout_seconds=5,
    )
    responses = iter([
        (0, "preflight ok"),
        (0, "uploaded"),
        (124, "timed out\n[harness] reset: status=homed"),
    ])

    async def fake_run(_command, _timeout):
        return next(responses)

    client._run_command = fake_run
    result = asyncio.run(client.submit(ExecutionRequest(test_code="while True: pass")))
    assert result.status == "blocked"
    assert result.verdict == "blocked"
    assert result.failed == 0
    assert result.blocked == 1
    assert result.error == "Remote harness stopped the test after its 10-minute limit (exit code 124)"
    assert result.exit_code == 124
    assert result.reset_status == "homed"
    assert "timed out" in result.logs


def test_pipeline_ssh_docker_sends_generated_test_codes(monkeypatch):
    generated = [
        {"test_case_id": "TC-1", "code": "print('one')"},
        {"test_case_id": "TC-2", "test_code": "print('two')"},
    ]

    class FakeCollection:
        async def find_one(self, query):
            assert query == {"session_id": "session-ssh"}
            return {
                "processes": {
                    "test_code_generation": {
                        "output": {"generated_tests": generated}
                    }
                }
            }

    class FakeDatabase:
        def __getitem__(self, name):
            assert name == "session_history"
            return FakeCollection()

    async def fake_get_database():
        return FakeDatabase()

    submitted = []

    class FakeSshClient:
        is_configured = True

        async def submit(self, request):
            submitted.append(request)
            return execution_module.ExecutionResult(
                execution_id=f"exec-{request.test_case_id}",
                status="completed",
                passed=1,
                logs=f"ran {request.test_case_id}",
                artifacts=[{"remote_path": f"~/stlc_runs/{request.test_case_id}.py"}],
            )

    monkeypatch.setattr(database_module, "get_database", fake_get_database)
    monkeypatch.setattr(execution_module, "SshDockerExecutionClient", FakeSshClient)

    request = PipelineRunRequest(
        session_id="session-ssh",
        selected_steps=["test-execution"],
        process_title="Remote ROS2 pipeline",
        step_configs={
            "test-execution": StepConfig(
                execution_method="ssh_docker",
                remote_timeout=45,
            )
        },
    )
    result = asyncio.run(run_test_execution(request, {}))

    assert result.status.value == "completed"
    assert result.output["summary"] == {"total": 2, "successful": 2, "failed": 0}
    assert [item.test_code for item in submitted] == ["print('one')", "print('two')"]
    assert all(item.configuration == {"timeout_seconds": 45} for item in submitted)
    assert all(item.metadata == {"source": "stlc_pipeline"} for item in submitted)
