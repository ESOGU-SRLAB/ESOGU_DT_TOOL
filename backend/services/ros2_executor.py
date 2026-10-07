"""
ros2_executor.py
----------------
ROS2 Docker execution service for STLC Manager.

Deprecated optional local execution path. Connects to an operator-configured
ROS 2 container via Docker exec
(no new containers are spawned). Test code is copied into the container as a
Python script and executed with `python3`.  Supports two execution flavors:

  • headless  – DISPLAY env var is NOT forwarded → Gazebo/RViz windows stay closed
  • visual    – DISPLAY env var IS forwarded  → GUI windows open on the host X server

Batch execution lets the user choose how many tests run visually; the rest are
headless.
"""

import io
import os
import tarfile
import logging
import asyncio
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Image name that identifies the ROS2 container
ROS2_IMAGE_NAME = os.getenv("LEGACY_ROS2_IMAGE", "stlc-robot-ros2:latest")
ROS2_SETUP_SCRIPT = os.getenv(
    "LEGACY_ROS2_SETUP_SCRIPT", "/opt/stlc_ros/install/setup.bash"
)


class ROS2Executor:
    """Service that executes Python test scripts inside a running ROS2 container."""

    def __init__(self):
        self._docker_client = None

    # ------------------------------------------------------------------
    # Docker client (lazy init so import errors surface at runtime)
    # ------------------------------------------------------------------

    def _get_client(self):
        if self._docker_client is not None:
            return self._docker_client
        try:
            import docker
            self._docker_client = docker.from_env()
            self._docker_client.ping()
            logger.info("✅ ROS2Executor: Docker client initialised")
        except Exception as exc:
            logger.error(f"❌ ROS2Executor: Docker client error – {exc}")
            self._docker_client = None
        return self._docker_client

    # ------------------------------------------------------------------
    # Container discovery
    # ------------------------------------------------------------------

    def find_ros2_container(self):
        """Return the first running container built from ROS2_IMAGE_NAME, or None."""
        client = self._get_client()
        if client is None:
            return None
        try:
            containers = client.containers.list()
            for c in containers:
                # RepoTags may look like ['ros2_colcon_workspace:humble']
                tags = c.image.tags or []
                if any(ROS2_IMAGE_NAME in t for t in tags):
                    logger.info(f"🦿 Found ROS2 container: {c.name} ({c.short_id})")
                    return c
            logger.warning(f"⚠️ No running container found with image {ROS2_IMAGE_NAME}")
            return None
        except Exception as exc:
            logger.error(f"Container discovery error: {exc}")
            return None

    def is_ros2_available(self) -> bool:
        """True when Docker is reachable AND a ROS2 container is running."""
        return self.find_ros2_container() is not None

    def get_status(self) -> Dict[str, Any]:
        """Return a status dict for the /status endpoint."""
        client = self._get_client()
        if client is None:
            return {
                "available": False,
                "reason": "Docker is not running or docker-py is not installed",
            }
        container = self.find_ros2_container()
        if container is None:
            return {
                "available": False,
                "reason": (
                    f"No running container with image '{ROS2_IMAGE_NAME}'. "
                    "Start the container first (see README_Docker.md Step 4)."
                ),
            }
        return {
            "available": True,
            "container_name": container.name,
            "container_id": container.short_id,
            "image": ROS2_IMAGE_NAME,
            "status": container.status,
        }

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    def _write_script_to_container(self, container, script_content: str, remote_path: str):
        """Write *script_content* to *remote_path* inside *container* via put_archive."""
        filename = os.path.basename(remote_path)
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
            encoded = script_content.encode("utf-8")
            info = tarfile.TarInfo(name=filename)
            info.size = len(encoded)
            tar.addfile(info, io.BytesIO(encoded))
        tar_buffer.seek(0)
        remote_dir = os.path.dirname(remote_path)
        container.put_archive(remote_dir, tar_buffer)

    def _exec_in_container(
        self,
        container,
        remote_path: str,
        visual: bool,
        timeout: int,
    ) -> Dict[str, Any]:
        """
        Run `python3 <remote_path>` inside the container.

        *visual=True*  → inherit the container's DISPLAY env var (set via -e DISPLAY=…
                          when docker run was called per README_Docker.md Step 4)
        *visual=False* → explicitly unset DISPLAY so GUI windows don't pop up
        """
        env_overrides: Dict[str, str] = {}
        if not visual:
            env_overrides["DISPLAY"] = ""  # suppress GUI

        cmd = [
            "bash", "-c",
            (
                "source /opt/ros/humble/setup.bash 2>/dev/null || true && "
                f"source {ROS2_SETUP_SCRIPT} 2>/dev/null || true && "
                f"python3 {remote_path}"
            )
        ]
        try:
            exit_code, output_raw = container.exec_run(
                cmd=cmd,
                environment=env_overrides if env_overrides else None,
                demux=False,
                stdout=True,
                stderr=True,
            )
            output = output_raw.decode("utf-8", errors="replace") if output_raw else ""
            return {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "output": output,
                "error": None if exit_code == 0 else f"Process exited with code {exit_code}",
                "visual": visual,
            }
        except Exception as exc:
            return {
                "success": False,
                "exit_code": -1,
                "output": "",
                "error": str(exc),
                "visual": visual,
            }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute_single(
        self,
        test_code: str,
        test_id: str = "test",
        visual: bool = False,
        timeout: int = 120,
    ) -> Dict[str, Any]:
        """Execute a single Python test script in the ROS2 container (synchronous)."""
        container = self.find_ros2_container()
        if container is None:
            return {
                "success": False,
                "exit_code": -1,
                "output": "",
                "error": "ROS2 container is not running. Start it first (README_Docker.md Step 4).",
                "visual": visual,
                "test_id": test_id,
            }

        remote_path = f"/tmp/stlc_{test_id}.py"
        try:
            self._write_script_to_container(container, test_code, remote_path)
        except Exception as exc:
            return {
                "success": False,
                "exit_code": -1,
                "output": "",
                "error": f"Failed to copy script to container: {exc}",
                "visual": visual,
                "test_id": test_id,
            }

        result = self._exec_in_container(container, remote_path, visual=visual, timeout=timeout)
        result["test_id"] = test_id

        # Cleanup the temp file (best-effort)
        try:
            container.exec_run(f"rm -f {remote_path}", stdout=False, stderr=False)
        except Exception:
            pass

        return result

    async def execute_batch(
        self,
        test_items: List[Dict[str, Any]],
        visual_count: int = 0,
        timeout: int = 120,
    ) -> List[Dict[str, Any]]:
        """
        Execute *test_items* sequentially.

        The first *visual_count* items run with DISPLAY forwarded (GUI visible).
        The remaining items run headless.

        Each test_item dict must have:
          • 'test_id'  (str)
          • 'code'     (str) — the Python test script
        """
        results: List[Dict[str, Any]] = []
        for idx, item in enumerate(test_items):
            test_id = item.get("test_id", str(idx))
            code = item.get("code", "")
            visual = idx < visual_count

            logger.info(
                f"🦿 ROS2 batch [{idx + 1}/{len(test_items)}] "
                f"test_id={test_id} visual={visual}"
            )

            # Run synchronous Docker call in a thread so we don't block the event loop
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda _id=test_id, _code=code, _v=visual: self.execute_single(
                    test_code=_code,
                    test_id=_id,
                    visual=_v,
                    timeout=timeout,
                ),
            )
            results.append(result)

        return results


# Global singleton
ros2_executor = ROS2Executor()
