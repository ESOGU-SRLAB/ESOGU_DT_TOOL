#!/usr/bin/env python3
"""Exercise STLC Manager exactly as an external backend client would."""

import argparse
import json
import os
from pathlib import Path
import sys
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class SmokeFailure(RuntimeError):
    pass


class StlcClient:
    def __init__(self, base_url: str, api_key: str | None, http_timeout: float):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.http_timeout = http_timeout

    def request(self, method: str, path: str, payload=None, api_key=...):
        headers = {"Accept": "application/json"}
        selected_key = self.api_key if api_key is ... else api_key
        if selected_key:
            headers["X-API-Key"] = selected_key
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode("utf-8")
        request = Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.http_timeout) as response:
                body = response.read().decode("utf-8")
                return response.status, json.loads(body) if body else None
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(body)
            except json.JSONDecodeError:
                detail = {"message": body[:500]}
            raise SmokeFailure(f"{method} {path} returned HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise SmokeFailure(f"{method} {path} could not connect: {exc.reason}") from exc

    def expect_status(self, method: str, path: str, expected: int, payload=None, api_key=...):
        try:
            status, body = self.request(method, path, payload, api_key)
        except SmokeFailure as exc:
            expected_text = f"HTTP {expected}:"
            if expected_text in str(exc):
                return expected, None
            raise
        if status != expected:
            raise SmokeFailure(f"{method} {path}: expected HTTP {expected}, got {status}")
        return status, body

    def submit(self, path: str, payload):
        status, body = self.request("POST", path, payload)
        if status not in {201, 202}:
            raise SmokeFailure(f"POST {path}: expected 201/202, got {status}")
        return body

    def wait_for(self, submission, deadline_seconds: float):
        job_id = submission["job_id"]
        deadline = time.monotonic() + deadline_seconds
        states = []
        while time.monotonic() < deadline:
            status, job = self.request("GET", submission["status_url"])
            if status != 200:
                raise SmokeFailure(f"Job {job_id} status returned HTTP {status}")
            if not states or states[-1] != job["status"]:
                states.append(job["status"])
            if job["status"] == "completed":
                result_status, result = self.request("GET", submission["result_url"])
                if result_status != 200:
                    raise SmokeFailure(f"Job {job_id} result returned HTTP {result_status}")
                return result["result"], states
            if job["status"] == "failed":
                raise SmokeFailure(f"Job {job_id} failed: {job.get('error')}")
            time.sleep(1)
        raise SmokeFailure(f"Job {job_id} exceeded {deadline_seconds:g}s; states={states}")


def _count(result, path, default=0):
    value = result
    for key in path:
        if not isinstance(value, dict):
            return default
        value = value.get(key)
    return len(value) if isinstance(value, list) else value if value is not None else default


def run(args):
    client = StlcClient(args.base_url, args.api_key, args.http_timeout)
    health_status, health = client.request("GET", "/health", api_key=None)
    ready_status, ready = client.request("GET", "/ready", api_key=None)
    if health_status != 200 or ready_status != 200:
        raise SmokeFailure(f"Operational checks failed: health={health}, ready={ready}")

    if args.verify_auth:
        if not args.api_key:
            raise SmokeFailure("STLC_API_KEY is required when --verify-auth is enabled")
        client.expect_status("GET", "/api/v1/jobs/smoke-missing", 401, api_key=None)
        client.expect_status("GET", "/api/v1/jobs/smoke-missing", 401, api_key="invalid-smoke-key")
        client.expect_status("GET", "/api/v1/jobs/smoke-missing", 404)

    artifact_path = Path(args.artifact).resolve()
    if not artifact_path.is_file():
        raise SmokeFailure(f"Artifact does not exist: {artifact_path}")
    process_title = args.process_title or f"external-smoke-{uuid.uuid4().hex[:12]}"
    artifact = client.submit("/api/v1/artifacts", {
        "name": artifact_path.name,
        "type": args.artifact_type,
        "content": artifact_path.read_text(encoding="utf-8"),
        "metadata": {"source": "external-integration-smoke"},
    })
    summary = {
        "base_url": args.base_url,
        "process_title": process_title,
        "health": health["status"],
        "readiness": ready["status"],
        "artifact_id": artifact["artifact_id"],
    }
    if args.deployment_only:
        summary["mode"] = "deployment-only"
        return summary

    common = {"process_title": process_title, "artifact_ids": [artifact["artifact_id"]]}
    if args.model:
        common["model"] = args.model

    environment_job = client.submit("/api/v1/generations/environment", {
        **common,
        "environment_name": f"{process_title}-environment",
    })
    environment, environment_states = client.wait_for(environment_job, args.job_timeout)

    scenario_job = client.submit("/api/v1/generations/scenarios", {
        **common,
        "test_type": "Functional",
        "test_category": "Positive",
    })
    scenarios, scenario_states = client.wait_for(scenario_job, args.job_timeout)

    case_job = client.submit("/api/v1/generations/test-cases", {
        **common,
        "scenario_job_id": scenario_job["job_id"],
    })
    cases, case_states = client.wait_for(case_job, args.job_timeout)

    code_job = client.submit("/api/v1/generations/test-code", {
        **common,
        "environment_session_id": environment_job["session_id"],
        "environment_name": f"{process_title}-code",
        "max_test_cases": args.max_test_cases,
    })
    code, code_states = client.wait_for(code_job, args.job_timeout)

    summary.update({
        "mode": "full-pipeline",
        "environment": {"job_id": environment_job["job_id"], "states": environment_states},
        "scenarios": {
            "job_id": scenario_job["job_id"],
            "states": scenario_states,
            "count": _count(scenarios, ["test_scenarios", "TestScenarios"]),
        },
        "test_cases": {
            "job_id": case_job["job_id"],
            "states": case_states,
            "count": _count(cases, ["summary", "total_test_cases"]),
        },
        "test_code": {
            "job_id": code_job["job_id"],
            "states": code_states,
            "count": code.get("generated_count", 0),
        },
    })
    return summary


def parse_args():
    repo_fixture = Path(__file__).resolve().parents[1] / "test_inputs" / "Functional_and_NonFunctional_Requirements.txt"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("STLC_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--api-key", default=os.getenv("STLC_API_KEY"))
    parser.add_argument("--artifact", default=os.getenv("STLC_ARTIFACT_PATH", str(repo_fixture)))
    parser.add_argument("--artifact-type", default=os.getenv("STLC_ARTIFACT_TYPE", "requirement"))
    parser.add_argument("--model", default=os.getenv("STLC_MODEL"))
    parser.add_argument("--process-title", default=os.getenv("STLC_PROCESS_TITLE"))
    parser.add_argument("--http-timeout", type=float, default=float(os.getenv("STLC_HTTP_TIMEOUT", "30")))
    parser.add_argument("--job-timeout", type=float, default=float(os.getenv("STLC_JOB_TIMEOUT", "600")))
    parser.add_argument("--max-test-cases", type=int, default=int(os.getenv("STLC_MAX_TEST_CASES", "1")))
    parser.add_argument("--deployment-only", action="store_true", help="Check health, readiness, auth, and artifact persistence only")
    parser.add_argument("--verify-auth", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def main():
    try:
        summary = run(parse_args())
    except (SmokeFailure, OSError, ValueError, KeyError) as exc:
        print(f"STLC external integration smoke FAILED: {exc}", file=sys.stderr)
        return 1
    print("STLC external integration smoke PASSED")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
