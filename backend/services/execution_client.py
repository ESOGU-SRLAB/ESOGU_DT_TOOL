"""Configurable adapters for external test execution systems."""

from abc import ABC, abstractmethod
import asyncio
from datetime import datetime, timezone
import hashlib
import logging
from pathlib import Path
import re
import shlex
import tempfile
from typing import Any, Dict, List, Optional
import uuid

import aiohttp
from pydantic import BaseModel, Field

from core.settings import Settings, get_settings
from utils.standalone_test_validation import (
    require_standalone_python,
    supports_legacy_sim_robot_goal,
)


logger = logging.getLogger(__name__)


class ExecutionRequest(BaseModel):
    test_code: str = Field(..., min_length=1)
    language: Optional[str] = None
    framework: Optional[str] = None
    test_case_id: Optional[str] = None
    session_id: Optional[str] = None
    process_id: Optional[str] = None
    process_title: Optional[str] = None
    artifact_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    configuration: Dict[str, Any] = Field(default_factory=dict)


class ExecutionResult(BaseModel):
    execution_id: str
    status: str
    verdict: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    passed: int = 0
    failed: int = 0
    errors: int = 0
    blocked: int = 0
    not_executed: int = 0
    logs: Optional[str] = None
    error: Optional[str] = None
    exit_code: Optional[int] = None
    reset_status: Optional[str] = None
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)


class ExecutionNotConfiguredError(RuntimeError):
    pass


class ExecutionAdapter(ABC):
    @property
    @abstractmethod
    def is_configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def submit(self, request: ExecutionRequest) -> ExecutionResult:
        raise NotImplementedError


class HttpExecutionClient(ExecutionAdapter):
    def __init__(self, base_url: str = None, token: str = None, timeout_seconds: int = None):
        settings = get_settings()
        self.base_url = (base_url or settings.execution_service_url or "").rstrip("/")
        self.token = token if token is not None else settings.execution_service_token
        self.timeout_seconds = timeout_seconds or settings.execution_timeout_seconds

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url)

    async def submit(self, request: ExecutionRequest) -> ExecutionResult:
        if not self.base_url:
            raise ExecutionNotConfiguredError(
                "EXECUTION_SERVICE_URL is not configured; no execution request was sent"
            )
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            payload = request.model_dump(exclude_none=True) if hasattr(request, "model_dump") else request.dict(exclude_none=True)
            async with session.post(
                f"{self.base_url}/executions",
                json=payload,
                headers=headers,
            ) as response:
                if response.status < 200 or response.status >= 300:
                    body = (await response.text())[:500]
                    raise RuntimeError(
                        f"External execution service returned HTTP {response.status}: {body}"
                    )
                response_data = await response.json()
                if hasattr(ExecutionResult, "model_validate"):
                    return ExecutionResult.model_validate(response_data)
                return ExecutionResult.parse_obj(response_data)


class SshDockerExecutionClient(ExecutionAdapter):
    """Upload Python code with SCP and run it in the remote ROS 2 harness."""

    _HOST_PATTERN = re.compile(r"^(?:[A-Za-z0-9_.-]+@)?[A-Za-z0-9_.-]+$")
    _REMOTE_DIR_PATTERN = re.compile(r"^(?:~|/[A-Za-z0-9_.-]+)(?:/[A-Za-z0-9_.-]+)*$")
    _IMAGE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/:@-]*$")
    _RESET_STATUS_PATTERN = re.compile(
        r"^\[harness\]\s+reset:\s+status=([A-Za-z0-9_-]+)",
        re.MULTILINE,
    )
    _EXIT_CODE_ERRORS = {
        1: "Remote pytest reported at least one failed test (exit code 1)",
        2: "Remote pytest collection/import failed (exit code 2)",
        5: "Remote pytest collected no tests (exit code 5)",
        124: "Remote harness stopped the test after its 10-minute limit (exit code 124)",
    }

    def __init__(
        self,
        host: Optional[str] = None,
        remote_dir: Optional[str] = None,
        image: Optional[str] = None,
        identity_file: Optional[Path] = None,
        password: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        connect_timeout_seconds: Optional[int] = None,
    ):
        settings = get_settings()
        self.host = host if host is not None else settings.ssh_execution_host
        self.remote_dir = remote_dir or settings.ssh_execution_remote_dir
        self.image = image or settings.ssh_execution_image
        self.identity_file = (
            Path(identity_file)
            if identity_file is not None
            else settings.ssh_execution_identity_file
        )
        self.password = password if password is not None else settings.ssh_execution_password
        self.timeout_seconds = timeout_seconds or settings.execution_timeout_seconds
        self.connect_timeout_seconds = (
            connect_timeout_seconds or settings.ssh_execution_connect_timeout_seconds
        )
        self._validate_configuration()

    @property
    def is_configured(self) -> bool:
        return bool(self.host)

    def _validate_configuration(self) -> None:
        if self.host and not self._HOST_PATTERN.fullmatch(self.host):
            raise ValueError("SSH_EXECUTION_HOST contains unsupported characters")
        if (
            not self._REMOTE_DIR_PATTERN.fullmatch(self.remote_dir)
            or ".." in self.remote_dir.split("/")
        ):
            raise ValueError("SSH_EXECUTION_REMOTE_DIR contains unsupported characters")
        if not self._IMAGE_PATTERN.fullmatch(self.image):
            raise ValueError("SSH_EXECUTION_IMAGE contains unsupported characters")
        if self.timeout_seconds <= 0 or self.connect_timeout_seconds <= 0:
            raise ValueError("SSH execution timeouts must be positive integers")

    def _connection_options(self) -> List[str]:
        options = [
            "-o", "BatchMode=yes",
            "-o", f"ConnectTimeout={self.connect_timeout_seconds}",
            "-o", "StrictHostKeyChecking=yes",
        ]
        if self.identity_file:
            options.extend(["-i", str(self.identity_file)])
        return options

    def _remote_file(self, filename: str) -> str:
        return f"{self.remote_dir.rstrip('/')}/{filename}"

    @staticmethod
    def _shell_path(path: str) -> str:
        if path == "~":
            return '"$HOME"'
        if path.startswith("~/"):
            return '"$HOME/' + path[2:] + '"'
        return shlex.quote(path)

    @staticmethod
    def _volume_mount(path: str) -> str:
        container_path = "/harness_ws/generated_script.py:ro"
        if path.startswith("~/"):
            return f'"$HOME/{path[2:]}:{container_path}"'
        return shlex.quote(f"{path}:{container_path}")

    @staticmethod
    def _runner_command(request: ExecutionRequest) -> List[str]:
        # Harness 0.3.x must receive the file through its python entrypoint.
        # entrypoint.sh detects test_* definitions and invokes pytest itself;
        # calling pytest directly would bypass the harness timeout and reset.
        return ["python3", "/harness_ws/generated_script.py"]

    async def _run_command(
        self,
        command: List[str],
        timeout: Optional[int],
    ) -> tuple[int, str]:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            if timeout is None:
                stdout, _ = await process.communicate()
            else:
                stdout, _ = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise TimeoutError(f"Command timed out after {timeout} seconds")
        output = stdout.decode("utf-8", errors="replace")
        return process.returncode or 0, output[-200000:]

    @classmethod
    def _result_metadata(cls, return_code: int, logs: str) -> tuple[Optional[str], Optional[str]]:
        matches = cls._RESET_STATUS_PATTERN.findall(logs or "")
        reset_status = matches[-1] if matches else None
        if return_code == 0:
            return None, reset_status
        return (
            cls._EXIT_CODE_ERRORS.get(
                return_code,
                f"Remote container exited with code {return_code}",
            ),
            reset_status,
        )

    @staticmethod
    def _classify_exit_code(return_code: int) -> Dict[str, Any]:
        """Translate harness exit codes into an ISTQB-style test verdict.

        Exit 1 is an executed test whose oracle/assertion did not match. Import,
        collection, missing-test and timeout outcomes did not produce a valid
        functional verdict and must not be counted as product test failures.
        """
        if return_code == 0:
            return {
                "status": "completed", "verdict": "passed", "passed": 1,
                "failed": 0, "errors": 0, "blocked": 0, "not_executed": 0,
            }
        if return_code == 1:
            return {
                "status": "completed", "verdict": "failed", "passed": 0,
                "failed": 1, "errors": 0, "blocked": 0, "not_executed": 0,
            }
        if return_code == 5:
            return {
                "status": "not_executed", "verdict": "not_executed", "passed": 0,
                "failed": 0, "errors": 0, "blocked": 0, "not_executed": 1,
            }
        if return_code == 124:
            return {
                "status": "blocked", "verdict": "blocked", "passed": 0,
                "failed": 0, "errors": 0, "blocked": 1, "not_executed": 0,
            }
        return {
            "status": "error", "verdict": "error", "passed": 0,
            "failed": 0, "errors": 1, "blocked": 0, "not_executed": 0,
        }

    async def submit(self, request: ExecutionRequest) -> ExecutionResult:
        if not self.host:
            raise ExecutionNotConfiguredError(
                "SSH_EXECUTION_HOST is not configured; no execution request was sent"
            )
        language = (request.language or "python").strip().lower()
        if language not in {"python", "py", "python3"}:
            raise ValueError("The SSH Docker harness currently accepts Python test code only")
        require_standalone_python(
            request.test_code,
            allow_legacy_sim_robot_goal=supports_legacy_sim_robot_goal(self.image),
        )

        execution_id = f"exec-{uuid.uuid4().hex}"
        filename = f"{execution_id}.py"
        remote_file = self._remote_file(filename)
        started_at = datetime.now(timezone.utc).isoformat()
        checksum = hashlib.sha256(request.test_code.encode("utf-8")).hexdigest()
        logger.info(
            "Remote harness execution prepared: execution_id=%s test_case_id=%s image=%s. "
            "The harness owns the test timeout and robot reset; output is returned when it exits.",
            execution_id,
            request.test_case_id,
            self.image,
        )

        if self.password:
            return await asyncio.to_thread(
                self._submit_with_password,
                request,
                execution_id,
                filename,
                remote_file,
                started_at,
                checksum,
            )

        ssh_base = ["ssh", *self._connection_options(), self.host]

        preflight = (
            f"test -d {self._shell_path(self.remote_dir)} && "
            f"docker image inspect {shlex.quote(self.image)} >/dev/null"
        )
        preflight_code, preflight_output = await self._run_command(
            [*ssh_base, preflight], self.connect_timeout_seconds + 5
        )
        if preflight_code != 0:
            raise RuntimeError(
                "Remote ROS 2 harness preflight failed: "
                + preflight_output.strip()[:1000]
            )

        with tempfile.TemporaryDirectory(prefix="stlc-exec-") as temp_dir:
            local_file = Path(temp_dir) / filename
            local_file.write_text(request.test_code, encoding="utf-8", newline="\n")
            upload_code, upload_output = await self._run_command(
                [
                    "scp",
                    *self._connection_options(),
                    str(local_file),
                    f"{self.host}:{remote_file}",
                ],
                self.connect_timeout_seconds + 30,
            )
        if upload_code != 0:
            raise RuntimeError("SCP upload failed: " + upload_output.strip()[:1000])

        remote_command = " ".join([
            "docker", "run", "--rm", "--network", "host", "--ipc=host",
            "-e", "FASTDDS_BUILTIN_TRANSPORTS=UDPv4",
            "-v", self._volume_mount(remote_file),
            shlex.quote(self.image),
            *self._runner_command(request),
        ])
        return_code, logs = await self._run_command(
            [*ssh_base, remote_command],
            None,
        )
        finished_at = datetime.now(timezone.utc).isoformat()
        classification = self._classify_exit_code(return_code)
        if upload_output.strip():
            logs = f"{upload_output.strip()}\n{logs}".strip()
        error, reset_status = self._result_metadata(return_code, logs)
        logger.info(
            "Remote harness execution finished: execution_id=%s exit_code=%s reset_status=%s",
            execution_id,
            return_code,
            reset_status or "not_reported",
        )

        return ExecutionResult(
            execution_id=execution_id,
            **classification,
            started_at=started_at,
            finished_at=finished_at,
            logs=logs,
            error=error,
            exit_code=return_code,
            reset_status=reset_status,
            artifacts=[{
                "name": filename,
                "remote_path": remote_file,
                "sha256": checksum,
            }],
        )

    def _submit_with_password(
        self,
        request: ExecutionRequest,
        execution_id: str,
        filename: str,
        remote_file: str,
        started_at: str,
        checksum: str,
    ) -> ExecutionResult:
        """Run one upload/execution using Paramiko for non-interactive passwords."""
        try:
            import paramiko
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Password-based SSH execution requires Paramiko. "
                "Install backend/requirements.txt in the active backend virtual environment."
            ) from exc

        lookup: Dict[str, Any] = {}
        config_path = Path.home() / ".ssh" / "config"
        if config_path.exists():
            with config_path.open("r", encoding="utf-8") as config_file:
                ssh_config = paramiko.SSHConfig()
                ssh_config.parse(config_file)
                lookup = ssh_config.lookup(self.host)

        target = lookup.get("hostname", self.host)
        username = lookup.get("user")
        port = int(lookup.get("port", 22))
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        try:
            client.connect(
                hostname=target,
                port=port,
                username=username,
                password=self.password,
                timeout=self.connect_timeout_seconds,
                banner_timeout=self.connect_timeout_seconds,
                auth_timeout=self.connect_timeout_seconds,
                allow_agent=False,
                look_for_keys=False,
            )
            transport = client.get_transport()
            if transport is not None:
                transport.set_keepalive(30)

            preflight = (
                f"test -d {self._shell_path(self.remote_dir)} && "
                f"docker image inspect {shlex.quote(self.image)} >/dev/null"
            )
            _, preflight_stdout, preflight_stderr = client.exec_command(
                preflight, timeout=self.connect_timeout_seconds + 5
            )
            preflight_code = preflight_stdout.channel.recv_exit_status()
            if preflight_code != 0:
                diagnostic = (preflight_stderr.read() or preflight_stdout.read()).decode(
                    "utf-8", errors="replace"
                )
                raise RuntimeError(
                    "Remote ROS 2 harness preflight failed: " + diagnostic.strip()[:1000]
                )

            sftp = client.open_sftp()
            try:
                home = sftp.normalize(".")
                expanded_remote_file = (
                    f"{home}/{remote_file[2:]}" if remote_file.startswith("~/") else remote_file
                )
                with tempfile.TemporaryDirectory(prefix="stlc-exec-") as temp_dir:
                    local_file = Path(temp_dir) / filename
                    local_file.write_text(request.test_code, encoding="utf-8", newline="\n")
                    sftp.put(str(local_file), expanded_remote_file)
            finally:
                sftp.close()

            remote_command = " ".join([
                "docker", "run", "--rm", "--network", "host", "--ipc=host",
                "-e", "FASTDDS_BUILTIN_TRANSPORTS=UDPv4",
                "-v", shlex.quote(f"{expanded_remote_file}:/harness_ws/generated_script.py:ro"),
                shlex.quote(self.image),
                *self._runner_command(request),
            ])
            _, stdout, stderr = client.exec_command(
                remote_command, timeout=None
            )
            return_code = stdout.channel.recv_exit_status()
            logs = (stdout.read() + stderr.read()).decode("utf-8", errors="replace")[-200000:]
        finally:
            client.close()

        finished_at = datetime.now(timezone.utc).isoformat()
        classification = self._classify_exit_code(return_code)
        error, reset_status = self._result_metadata(return_code, logs)
        logger.info(
            "Remote harness execution finished: execution_id=%s exit_code=%s reset_status=%s",
            execution_id,
            return_code,
            reset_status or "not_reported",
        )
        return ExecutionResult(
            execution_id=execution_id,
            **classification,
            started_at=started_at,
            finished_at=finished_at,
            logs=logs,
            error=error,
            exit_code=return_code,
            reset_status=reset_status,
            artifacts=[{
                "name": filename,
                "remote_path": remote_file,
                "sha256": checksum,
            }],
        )


def create_execution_client(settings: Optional[Settings] = None) -> ExecutionAdapter:
    settings = settings or get_settings()
    if settings.execution_adapter == "http":
        return HttpExecutionClient(
            base_url=settings.execution_service_url,
            token=settings.execution_service_token,
            timeout_seconds=settings.execution_timeout_seconds,
        )
    if settings.execution_adapter in {"ssh", "ssh_docker"}:
        return SshDockerExecutionClient(
            host=settings.ssh_execution_host,
            remote_dir=settings.ssh_execution_remote_dir,
            image=settings.ssh_execution_image,
            identity_file=settings.ssh_execution_identity_file,
            password=settings.ssh_execution_password,
            timeout_seconds=settings.execution_timeout_seconds,
            connect_timeout_seconds=settings.ssh_execution_connect_timeout_seconds,
        )
    raise ValueError("EXECUTION_ADAPTER must be either 'http' or 'ssh_docker'")
