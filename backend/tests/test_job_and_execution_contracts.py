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
from services.execution_client import (  # noqa: E402
    ExecutionNotConfiguredError,
    ExecutionRequest,
    HttpExecutionClient,
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
