"""
step_adapters.py
----------------
One async function per STLC pipeline step.
Each adapter:
  - receives the PipelineRunRequest config and the results of all previously completed steps
  - calls the appropriate existing service / router logic
  - returns a StepResult
"""

import logging
import asyncio
import time
import io
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pipeline.pipeline_models import (
    PipelineRunRequest,
    StepResult,
    PipelineStepStatus,
    FileInfo,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_step_config(req: PipelineRunRequest, step_id: str) -> dict:
    """Return merged config: step-specific overrides on top of global defaults."""
    from core.settings import get_settings

    cfg = req.step_configs.get(step_id)
    base = {
        "model": req.global_model or get_settings().model_identifier,
        "api_key": req.global_api_key,
        "process_title": req.process_title,
    }
    if cfg:
        override = (
            cfg.model_dump(exclude_none=True)
            if hasattr(cfg, "model_dump")
            else cfg.dict(exclude_none=True)
        )
        base.update(override)
    return base


def _files_for_step(req: PipelineRunRequest, step_id: str) -> List[FileInfo]:
    """Return the files mapped to this step."""
    return req.files.get(step_id, [])


class _SyncFile:
    """
    File-like wrapper that satisfies both:
    - FastAPI services using `await file.read()` (file_handler.save_files)
    - `file.filename` attribute access

    Making `read()` an async coroutine means `await file.read()` works correctly.
    For the stlc test_scenario_generation.py which calls sync `file.read()`, we
    avoid passing these objects altogether (passing empty files list and embedding
    content directly in the prompt string instead).
    """
    def __init__(self, name: str, content: str):
        self.filename = os.path.basename(name)
        # Existing FileHandler stores uploads by name. Give headless/background
        # jobs a collision-free storage name while preserving the logical name.
        self.storage_name = f"{uuid.uuid4().hex}_{self.filename}"
        self._bytes = content.encode("utf-8") if isinstance(content, str) else content

    async def read(self) -> bytes:
        """Async read — compatible with `await file.read()` in file_handler."""
        return self._bytes


async def _make_upload_files(files: List[FileInfo]):
    """Convert FileInfo list to _SyncFile wrappers for service layer use."""
    return [_SyncFile(name=fi.name, content=fi.content or "") for fi in files]


async def _make_upload_files(files: List[FileInfo]):
    """
    Convert FileInfo objects into sync-readable file-like objects compatible
    with both the legacy stlc layer (sync file.read()) and FastAPI services
    that use await file.read() via _SyncFile.async_read().
    """
    uploads = []
    for fi in files:
        uploads.append(_SyncFile(name=fi.name, content=fi.content or ""))
    return uploads


def _ok(step_id: str, output: dict, t0: float) -> StepResult:
    return StepResult(
        step_id=step_id,
        status=PipelineStepStatus.COMPLETED,
        output=output,
        duration_seconds=round(time.time() - t0, 2),
    )


def _err(step_id: str, error: str, t0: float) -> StepResult:
    return StepResult(
        step_id=step_id,
        status=PipelineStepStatus.ERROR,
        error=error,
        duration_seconds=round(time.time() - t0, 2),
    )


# ---------------------------------------------------------------------------
# Step 1: Code Review
# ---------------------------------------------------------------------------

async def run_code_review(
    req: PipelineRunRequest,
    previous_results: Dict[str, StepResult],
) -> StepResult:
    step_id = "code-review"
    t0 = time.time()
    try:
        from services.review_service import ReviewService

        cfg = _get_step_config(req, step_id)
        files = _files_for_step(req, step_id)
        upload_files = await _make_upload_files(files)

        service = ReviewService()
        result = await service.run_code_review(
            files=upload_files,
            types=[f.type for f in files if f.type],
            model_key=cfg.get("model"),
            custom_prompt=cfg.get("custom_prompt"),
            session_id=req.session_id,
            api_key=cfg.get("api_key"),
        )
        return _ok(step_id, result, t0)
    except Exception as e:
        logger.error(f"[Pipeline][{step_id}] Error: {e}", exc_info=True)
        return _err(step_id, str(e), t0)


# ---------------------------------------------------------------------------
# Step 2: Requirement Analysis
# ---------------------------------------------------------------------------

async def run_requirement_analysis(
    req: PipelineRunRequest,
    previous_results: Dict[str, StepResult],
) -> StepResult:
    step_id = "requirement-analysis"
    t0 = time.time()
    try:
        from services.requirement_analysis_service import RequirementAnalysisService

        cfg = _get_step_config(req, step_id)
        files = _files_for_step(req, step_id)
        upload_files = await _make_upload_files(files)

        service = RequirementAnalysisService()
        result = await service.run_requirement_analysis(
            files=upload_files,
            types=[f.type for f in files if f.type],
            model_key=cfg.get("model"),
            custom_prompt=cfg.get("custom_prompt"),
            session_id=req.session_id,
            api_key=cfg.get("api_key"),
        )
        return _ok(step_id, result, t0)
    except Exception as e:
        logger.error(f"[Pipeline][{step_id}] Error: {e}", exc_info=True)
        return _err(step_id, str(e), t0)


# ---------------------------------------------------------------------------
# Step 3: Test Planning
# ---------------------------------------------------------------------------

async def run_test_planning(
    req: PipelineRunRequest,
    previous_results: Dict[str, StepResult],
) -> StepResult:
    step_id = "test-planning"
    t0 = time.time()
    try:
        from services.test_planning_service import TestPlanningService

        cfg = _get_step_config(req, step_id)
        files = _files_for_step(req, step_id)

        # Enrich files with outputs from code-review and requirement-analysis
        extra_files: List[FileInfo] = []
        for dep_id in ("code-review", "requirement-analysis"):
            dep = previous_results.get(dep_id)
            if dep and dep.status == PipelineStepStatus.COMPLETED and dep.output:
                content_parts = []
                out = dep.output
                # Try multiple known output shapes
                for key in ("reviews", "analysis", "plan"):
                    if key in out:
                        import json as _json
                        content_parts.append(_json.dumps(out[key], ensure_ascii=False))
                if content_parts:
                    extra_files.append(
                        FileInfo(
                            name=f"{dep_id}_output.txt",
                            content="\n\n".join(content_parts),
                            type="context",
                        )
                    )

        all_files = files + extra_files
        upload_files = await _make_upload_files(all_files)

        service = TestPlanningService()
        result = await service.run_test_planning(
            files=upload_files,
            model_key=cfg.get("model"),
            custom_prompt=cfg.get("custom_prompt"),
            session_id=req.session_id,
            api_key=cfg.get("api_key"),
        )
        return _ok(step_id, result, t0)
    except Exception as e:
        logger.error(f"[Pipeline][{step_id}] Error: {e}", exc_info=True)
        return _err(step_id, str(e), t0)


# ---------------------------------------------------------------------------
# Step 4: Environment Setup
# ---------------------------------------------------------------------------

async def run_environment_setup(
    req: PipelineRunRequest,
    previous_results: Dict[str, StepResult],
) -> StepResult:
    step_id = "environment-setup"
    t0 = time.time()
    try:
        from services.environment_setup_service import EnvironmentSetupService

        cfg = _get_step_config(req, step_id)
        files = _files_for_step(req, step_id)
        upload_files = await _make_upload_files(files)
        types = []
        for file_info in files:
            supplied_type = (file_info.type or "source").strip()
            normalized = supplied_type.lower().replace("_", " ").replace("-", " ")
            if normalized in {"requirement", "requirements", "requirement document"}:
                supplied_type = "Requirement Document"
            types.append(supplied_type)

        environment_name = cfg.get("environment_name") or cfg.get("process_title") or "Pipeline Environment"

        service = EnvironmentSetupService()
        result = await service.run_environment_setup(
            files=upload_files,
            types=types,
            model_key=cfg.get("model"),
            custom_prompt=cfg.get("custom_prompt"),
            session_id=req.session_id,
            environment_name=environment_name,
            api_key=cfg.get("api_key"),
        )
        return _ok(step_id, result, t0)
    except Exception as e:
        logger.error(f"[Pipeline][{step_id}] Error: {e}", exc_info=True)
        return _err(step_id, str(e), t0)


# ---------------------------------------------------------------------------
# Step 5: Test Scenario Generation
# ---------------------------------------------------------------------------

async def run_test_scenario_generation(
    req: PipelineRunRequest,
    previous_results: Dict[str, StepResult],
) -> StepResult:
    step_id = "test-scenario-generation"
    t0 = time.time()
    try:
        from stlc.test_scenario_generation import generate_prompt, run_step
        from core.database import get_database
        from utils.text_splitter import count_tokens

        cfg = _get_step_config(req, step_id)
        files = _files_for_step(req, step_id)
        upload_files = await _make_upload_files(files)

        model = cfg.get("model", "qwen2.5-7b-instruct-1m")
        api_key = cfg.get("api_key")
        test_type = cfg.get("test_type") or "Functional"
        test_category = cfg.get("test_category") or "Positive"
        process_title = cfg.get("process_title") or req.process_title or "Pipeline Process"

        # Build file contents list for generate_prompt
        file_contents = [fi.content for fi in files if fi.content]

        # 1. Generate the prompt
        prompt_input = {
            "testType": test_type,
            "testCategory": test_category,
            "model": model,
            "testPrompt": cfg.get("custom_prompt") or "",
            "fileContents": file_contents,
            "process_title": process_title,
            "session_id": req.session_id,
            "api_key": api_key,
        }
        prompt_result = await generate_prompt(prompt_input)
        if prompt_result.get("status") == "error":
            return _err(step_id, prompt_result.get("message", "Prompt generation failed"), t0)

        generated_prompt = prompt_result.get("generated_custom_prompt", "")

        # Build combined file content string to embed in the prompt
        # (avoids async/sync mismatch when run_step calls file.read() sync)
        # Truncate very large files to ~6000 chars to avoid context overflow.
        MAX_FILE_CHARS = 6000
        combined_file_contents = ""
        for fi in files:
            if fi.content:
                content = fi.content
                if len(content) > MAX_FILE_CHARS:
                    content = content[:MAX_FILE_CHARS] + f"\n... [truncated, original {len(fi.content):,} chars]"
                    logger.info(f"[Pipeline][{step_id}] Truncated {fi.name} from {len(fi.content):,} to {MAX_FILE_CHARS} chars")
                combined_file_contents += f"\n\n=== FILE: {fi.name} ===\n{content}\n"

        # If prompt doesn't already contain file contents, append them
        final_prompt = generated_prompt or cfg.get("custom_prompt") or "Generate test scenarios"
        if combined_file_contents and combined_file_contents.strip() not in final_prompt:
            final_prompt = final_prompt + "\n\n## Source Files:\n" + combined_file_contents

        # 2. Run the scenario generation step — pass empty files list since
        # content is already embedded in final_prompt
        run_data = {
            "files": [],  # content is pre-embedded in final_prompt
            "model": model,
            "final_prompt": final_prompt,
            "test_category": test_category,
            "test_type": test_type,
            "session_id": req.session_id,
            "process_title": process_title,
            "api_key": api_key,
        }
        result = await run_step(run_data)
        if result.get("status") == "error":
            return _err(step_id, result.get("message", "Test scenario generation failed"), t0)

        return _ok(step_id, result, t0)
    except Exception as e:
        logger.error(f"[Pipeline][{step_id}] Error: {e}", exc_info=True)
        return _err(step_id, str(e), t0)


# ---------------------------------------------------------------------------
# Step 6: Test Case Generation
# ---------------------------------------------------------------------------

async def run_test_case_generation(
    req: PipelineRunRequest,
    previous_results: Dict[str, StepResult],
) -> StepResult:
    """Adapt pipeline state to the existing UI-backed generation service."""
    step_id = "test-case-generation"
    t0 = time.time()
    try:
        from core.database import get_database
        from services.test_case_generation_service import TestCaseGenerationService

        cfg = _get_step_config(req, step_id)
        scenarios: List[dict] = []
        previous = previous_results.get("test-scenario-generation")
        if previous and previous.status == PipelineStepStatus.COMPLETED and previous.output:
            scenario_data = previous.output.get("test_scenarios", {})
            scenarios = scenario_data.get("TestScenarios", [])

        if not scenarios:
            db = await get_database()
            document = await db["session_history"].find_one({"session_id": req.session_id})
            if document:
                output = (
                    document.get("processes", {})
                    .get("test_scenario_generation", {})
                    .get("output", {})
                )
                scenarios = output.get("test_scenarios", {}).get("TestScenarios", [])

        if not scenarios:
            return _err(step_id, "No test scenarios available from previous step", t0)

        # The UI historically converted stored PascalCase scenario fields into
        # lower-case form fields. Make that implicit frontend transform explicit.
        normalized_scenarios = [
            {
                "scenario_id": item.get("scenario_id") or item.get("ScenarioID"),
                "scenario": item.get("scenario") or item.get("Title"),
                "description": item.get("description") or item.get("Description", ""),
                "objective": item.get("objective") or item.get("Objective", ""),
                "category": item.get("category") or item.get("Category", ""),
            }
            for item in scenarios
        ]
        files = _files_for_step(req, step_id) or _files_for_step(
            req, "test-scenario-generation"
        )
        payload = {
            "selected_scenarios": normalized_scenarios,
            "process_prompt": cfg.get("custom_prompt") or "",
            "selected_files": [
                {"name": file_info.name, "content": file_info.content}
                for file_info in files
            ],
            "ai_model": cfg.get("model"),
            "session_id": req.session_id,
            "selected_process_title": (
                cfg.get("process_title") or req.process_title or "Pipeline Process"
            ),
            "api_key": cfg.get("api_key"),
            "test_type": cfg.get("test_type") or "Functional",
        }
        result = await TestCaseGenerationService().generate(payload)
        total_cases = result.get("summary", {}).get("total_test_cases", 0)
        if result.get("status") != "success" or total_cases <= 0:
            return _err(
                step_id,
                result.get("message") or "Test case generation produced no test cases",
                t0,
            )
        return _ok(step_id, result, t0)
    except Exception as exc:
        logger.error(f"[Pipeline][{step_id}] Error: {exc}", exc_info=True)
        return _err(step_id, str(exc), t0)

# ---------------------------------------------------------------------------
# Step 7: Test Case Optimization
# ---------------------------------------------------------------------------

async def run_test_case_optimization(
    req: PipelineRunRequest,
    previous_results: Dict[str, StepResult],
) -> StepResult:
    step_id = "test-case-optimization"
    t0 = time.time()
    try:
        from services.test_case_optimization_service import TestCaseOptimizationService
        from core.prompt_manager import save_session_data

        cfg = _get_step_config(req, step_id)
        model = cfg.get("model", "qwen2.5-7b-instruct-1m")
        api_key = cfg.get("api_key")
        process_name = cfg.get("process_name") or cfg.get("process_title") or req.process_title or "Pipeline Optimization"
        # Default: bulk (single LLM call). "individual" is O(n²) and impractical for >30 cases.
        optimization_type = cfg.get("optimization_type", "bulk")

        # --- Collect all test cases from test-case-generation ---
        all_tcs: List[dict] = []
        prev_tcg = previous_results.get("test-case-generation")
        if prev_tcg and prev_tcg.status == PipelineStepStatus.COMPLETED and prev_tcg.output:
            for scenario_result in prev_tcg.output.get("test_case_results", []):
                all_tcs.extend(scenario_result.get("test_cases", []))

        if not all_tcs:
            # Fallback: load from DB
            from core.database import get_database
            db = await get_database()
            doc = await db["session_history"].find_one({"session_id": req.session_id})
            if doc:
                tcg_out = doc.get("processes", {}).get("test_case_generation", {}).get("output", {})
                for r in tcg_out.get("test_case_results", []):
                    all_tcs.extend(r.get("test_cases", []))

        if not all_tcs:
            return _err(step_id, "No test cases available for optimization", t0)

        # Cap to a reasonable size — "individual" mode is O(n²) LLM calls.
        MAX_TCS = 60
        if len(all_tcs) > MAX_TCS:
            logger.warning(f"[Pipeline][{step_id}] Capping {len(all_tcs)} test cases to {MAX_TCS} for optimization")
            all_tcs = all_tcs[:MAX_TCS]

        # Gemini parallel requires API key
        is_gemini = "gemini" in model.lower()
        if optimization_type == "parallel" and not is_gemini:
            optimization_type = "bulk"  # Fall back gracefully
        if is_gemini and not api_key:
            optimization_type = "bulk"

        import uuid as _uuid
        process_id = str(_uuid.uuid4())

        service = TestCaseOptimizationService()
        if optimization_type == "parallel":
            result = await service.run_parallel_smart_selection(all_tcs, "", model, api_key, process_id)
        elif optimization_type == "bulk":
            result = await service.run_bulk_smart_selection(all_tcs, "", model, api_key, process_id)
        else:
            result = await service.run_smart_selection(all_tcs, "", model, api_key, process_id)

        if not result.get("success"):
            return _err(step_id, result.get("message", "Optimization failed"), t0)

        # Save to test_case_optimizations collection
        process_title = cfg.get("process_title") or req.process_title or "Pipeline Process"
        service.save_optimization_results(process_title, result["data"], model)

        # Persist to session_history
        session_data = {
            "session_id": req.session_id,
            "output": result["data"],
            "edited_prompt": False,
            "used_prompt": "Default optimization prompt",
            "used_model": model,
            "process_name": process_name,
            "process_titles": [process_title],
            "process_count": 1,
            "optimization_type": optimization_type,
        }
        save_session_data(session_data, "test_case_optimization")

        return _ok(step_id, {"status": "success", **result}, t0)
    except Exception as e:
        logger.error(f"[Pipeline][{step_id}] Error: {e}", exc_info=True)
        return _err(step_id, str(e), t0)


# ---------------------------------------------------------------------------
# Step 8: Test Code Generation
# ---------------------------------------------------------------------------

async def run_test_code_generation(
    req: PipelineRunRequest,
    previous_results: Dict[str, StepResult],
) -> StepResult:
    step_id = "test-code-generation"
    t0 = time.time()
    try:
        from services.test_code_generation_service import TestCodeGenerationService

        cfg = _get_step_config(req, step_id)
        model = cfg.get("model", "qwen2.5-7b-instruct-1m")
        api_key = cfg.get("api_key")
        process_title = cfg.get("process_title") or req.process_title or "Pipeline Process"
        environment_name = cfg.get("environment_name") or process_title
        output_format = cfg.get("output_format", "json")
        max_test_cases = cfg.get("max_test_cases")

        # --- Determine environment session_id ---
        environment_session_id = cfg.get("environment_session_id") or req.session_id
        prev_env = previous_results.get("environment-setup")
        if prev_env and prev_env.status == PipelineStepStatus.COMPLETED and prev_env.output:
            env_sid = prev_env.output.get("session_id")
            if env_sid:
                environment_session_id = env_sid

        # --- Build UploadFile list for source files ---
        files = _files_for_step(req, step_id) or _files_for_step(req, "environment-setup")
        upload_files = await _make_upload_files(files)

        service = TestCodeGenerationService()
        result = await service.generate_test_codes(
            process_title=process_title,
            environment_session_id=environment_session_id,
            source_files=upload_files,
            model_name=model,
            custom_prompt=cfg.get("custom_prompt"),
            session_id=req.session_id,
            environment_name=environment_name,
            output_format=output_format,
            api_key=api_key,
            max_test_cases=max_test_cases,
        )
        if not result.get("success", False):
            return _err(step_id, result.get("error", "Test code generation failed"), t0)
        return _ok(step_id, result, t0)
    except Exception as e:
        logger.error(f"[Pipeline][{step_id}] Error: {e}", exc_info=True)
        return _err(step_id, str(e), t0)


# ---------------------------------------------------------------------------
# Step 9: Test Execution
# ---------------------------------------------------------------------------

async def run_test_execution(
    req: PipelineRunRequest,
    previous_results: Dict[str, StepResult],
) -> StepResult:
    step_id = "test-execution"
    t0 = time.time()
    try:
        import aiohttp
        import os

        cfg = _get_step_config(req, step_id)
        execution_method = cfg.get("execution_method", "ai")  # "ai" | "docker" | "robot"

        logger.info(f"[Pipeline][{step_id}] execution_method={execution_method}")

        # --- Fetch generated test codes from DB (shared by all methods) ---
        from core.database import get_database
        db = await get_database()
        doc = await db["session_history"].find_one({"session_id": req.session_id})
        if not doc:
            return _err(step_id, "Session not found in DB", t0)

        tcg_data = doc.get("processes", {}).get("test_code_generation", {}).get("output", {})
        generated_tests = tcg_data.get("generated_tests", [])

        if not generated_tests:
            return _err(step_id, "No generated test code found for execution", t0)

        # ----------------------------------------------------------------
        # Route to the appropriate execution engine
        # ----------------------------------------------------------------

        if execution_method == "ros2":
            # ---- ROS2 Docker Execution ----
            from services.ros2_executor import ros2_executor
            if not ros2_executor.is_ros2_available():
                return _err(
                    step_id,
                    "ROS2 container is not running. Start stlc-robot-ros2:latest first (README_Docker.md Step 4).",
                    t0,
                )

            visual_count = cfg.get("ros2_visual_count", 0)
            ros2_timeout = cfg.get("ros2_timeout", 120)

            test_items = []
            for test_item in generated_tests:
                code = test_item.get("code") or test_item.get("test_code", "")
                if not code:
                    continue
                test_id = test_item.get("test_case_id", test_item.get("id", "unknown"))
                test_items.append({"test_id": test_id, "code": code})

            logger.info(
                f"[Pipeline][{step_id}] ROS2 execution: "
                f"{len(test_items)} tests, visual_count={visual_count}"
            )

            ros2_results = await ros2_executor.execute_batch(
                test_items=test_items,
                visual_count=visual_count,
                timeout=ros2_timeout,
            )

            execution_results = [
                {
                    "test_id": r.get("test_id"),
                    "status": "success" if r.get("success") else "error",
                    "output": r.get("output", ""),
                    "exit_code": r.get("exit_code"),
                    "error": r.get("error"),
                    "visual": r.get("visual", False),
                }
                for r in ros2_results
            ]

        elif execution_method in ("docker", "robot"):
            # Guard: Docker must be available
            from services.docker_executor import docker_executor
            if not docker_executor.is_available():
                return _err(
                    step_id,
                    "Docker is not available. Please install Docker or select 'AI Execution' method.",
                    t0,
                )

            execution_results = []

            for test_item in generated_tests:
                code = test_item.get("code") or test_item.get("test_code", "")
                if not code:
                    continue
                test_id = test_item.get("test_case_id", test_item.get("id", "unknown"))

                try:
                    if execution_method == "robot":
                        robot_type = cfg.get("robot_type", "generic")
                        simulation_config = cfg.get("simulation_config") or {}
                        logger.info(f"[Pipeline][{step_id}] Robot simulation: type={robot_type}, test={test_id}")
                        result = await docker_executor.execute_robot_arm_simulation(
                            test_code=code,
                            robot_type=robot_type,
                            simulation_config=simulation_config,
                        )
                    else:  # docker
                        language = cfg.get("execution_language", "python")
                        packages = cfg.get("additional_packages") or []
                        timeout = cfg.get("docker_timeout") or 300
                        logger.info(f"[Pipeline][{step_id}] Docker execution: lang={language}, pkgs={packages}, test={test_id}")
                        result = await docker_executor.execute_test_in_container(
                            test_code=code,
                            language=language,
                            additional_packages=packages if packages else None,
                            timeout=timeout,
                        )

                    execution_results.append({
                        "test_id": test_id,
                        "status": "success" if result.get("success") else "error",
                        "output": result.get("output", ""),
                        "exit_code": result.get("exit_code"),
                        "error": result.get("error"),
                    })

                except Exception as exc:
                    execution_results.append({
                        "test_id": test_id,
                        "status": "error",
                        "error": str(exc),
                    })

        else:
            # ---- AI Execution via MCP Server (default) ----
            model = cfg.get("model", "qwen2.5-7b-instruct-1m")
            api_key = cfg.get("api_key")
            MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001")
            is_gemini = "gemini" in model.lower()
            provider = "google" if is_gemini else "lm_studio"

            execution_results = []
            for test_item in generated_tests:
                code = test_item.get("code") or test_item.get("test_code", "")
                if not code:
                    continue
                test_id = test_item.get("test_case_id", test_item.get("id", "unknown"))
                rpc_payload = {
                    "jsonrpc": "2.0",
                    "method": "executeTest",
                    "params": {
                        "test_code": code,
                        "provider": provider,
                        "model_name": model,
                    },
                    "id": 1,
                }
                if api_key:
                    rpc_payload["params"]["api_key"] = api_key

                try:
                    timeout = aiohttp.ClientTimeout(total=120)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.post(
                            f"{MCP_SERVER_URL}/jsonrpc",
                            json=rpc_payload,
                            headers={"Content-Type": "application/json"},
                        ) as resp:
                            resp_data = await resp.json()
                            execution_results.append({
                                "test_id": test_id,
                                "status": "success",
                                "result": resp_data.get("result", {}),
                            })
                except Exception as exc:
                    execution_results.append({
                        "test_id": test_id,
                        "status": "error",
                        "error": str(exc),
                    })

        output = {
            "status": "success",
            "execution_method": execution_method,
            "execution_results": execution_results,
            "summary": {
                "total": len(execution_results),
                "successful": sum(1 for r in execution_results if r.get("status") == "success"),
                "failed": sum(1 for r in execution_results if r.get("status") == "error"),
            },
        }
        return _ok(step_id, output, t0)
    except Exception as e:
        logger.error(f"[Pipeline][{step_id}] Error: {e}", exc_info=True)
        return _err(step_id, str(e), t0)


# ---------------------------------------------------------------------------
# Step 10: Test Reporting
# ---------------------------------------------------------------------------

async def run_test_reporting(
    req: PipelineRunRequest,
    previous_results: Dict[str, StepResult],
) -> StepResult:
    step_id = "test-reporting"
    t0 = time.time()
    try:
        from services.test_reporting_service import TestReportingService
        from utils.model_client import LLMClient

        cfg = _get_step_config(req, step_id)
        model = cfg.get("model", "qwen2.5-7b-instruct-1m")
        api_key = cfg.get("api_key")
        analysis_depth = cfg.get("analysis_depth", "detailed")
        custom_prompt = cfg.get("custom_prompt")

        service = TestReportingService()
        await service.initialize()

        # Fetch session data
        session_data = await service.fetch_session_data(
            session_id=req.session_id,
            selected_processes=None,
        )

        if not session_data.get("processes"):
            return _err(step_id, "No process data found for this session", t0)

        all_session_data = [{"session_id": req.session_id, "data": session_data}]

        # Build prompt
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = service.create_single_session_prompt(
                session_data=session_data,
                analysis_depth=analysis_depth,
            )

        # Call LLM
        llm_client = LLMClient(model_name=model, api_key=api_key, use_case="test_reporting")
        report_content = await llm_client.generate_response(
            prompt=prompt,
            temperature=0.7,
            max_tokens=8000,
        )
        if not report_content:
            return _err(step_id, "LLM returned empty report", t0)

        # Save report
        saved_session_id = await service.save_report(
            session_ids=[req.session_id],
            report_content=report_content,
            metadata={
                "model_used": model,
                "analysis_depth": analysis_depth,
                "pipeline_session_id": req.session_id,
            },
        )

        output = {
            "status": "success",
            "report_content": report_content,
            "report_session_id": saved_session_id,
            "session_id": req.session_id,
        }
        return _ok(step_id, output, t0)
    except Exception as e:
        logger.error(f"[Pipeline][{step_id}] Error: {e}", exc_info=True)
        return _err(step_id, str(e), t0)


# ---------------------------------------------------------------------------
# Step 11: Test Closure
# ---------------------------------------------------------------------------

async def run_test_closure(
    req: PipelineRunRequest,
    previous_results: Dict[str, StepResult],
) -> StepResult:
    step_id = "test-closure"
    t0 = time.time()
    try:
        from services.test_closure_service import TestClosureService
        from utils.model_client import LLMClient

        cfg = _get_step_config(req, step_id)
        model = cfg.get("model", "qwen2.5-7b-instruct-1m")
        api_key = cfg.get("api_key")
        custom_prompt = cfg.get("custom_prompt")

        service = TestClosureService()
        await service.initialize()

        # Determine reporting session IDs to analyze
        reporting_session_id = None
        prev_reporting = previous_results.get("test-reporting")
        if prev_reporting and prev_reporting.output:
            reporting_session_id = prev_reporting.output.get("report_session_id")

        session_ids_to_use = [reporting_session_id] if reporting_session_id else [req.session_id]

        # Generate closure data (metrics + prompt)
        result = await service.generate_closure_report(session_ids=session_ids_to_use)

        if not result.get("success"):
            # Try without filtering — just pass the pipeline session
            result = await service.generate_closure_report(session_ids=[req.session_id])

        if not result.get("success"):
            # Still failing — create minimal prompt
            prompt = custom_prompt or "Generate a test closure report summarizing the testing activities."
            metrics = None
        else:
            prompt = custom_prompt or result.get("prompt", "")
            metrics = result.get("metrics")

        # Call LLM
        llm_client = LLMClient(model_name=model, api_key=api_key, use_case="test_closure")
        report_content = await llm_client.generate_response(
            prompt=prompt,
            temperature=0.7,
            max_tokens=8000,
        )
        if not report_content:
            return _err(step_id, "LLM returned empty closure report", t0)

        # Evaluate quality
        quality_eval = service.evaluate_closure_report_quality(
            report_content=report_content,
            metrics=metrics,
            all_session_data=result.get("all_session_data", []) if isinstance(result, dict) else [],
        )

        # Save
        saved_session_id = await service.save_closure_report_to_database(
            session_ids=session_ids_to_use,
            report_content=report_content,
            quality_evaluation=quality_eval,
            metadata={
                "model_used": model,
                "pipeline_session_id": req.session_id,
                "metrics": metrics,
            },
        )

        output = {
            "status": "success",
            "report_content": report_content,
            "closure_session_id": saved_session_id,
            "quality_evaluation": quality_eval,
            "session_id": req.session_id,
        }
        return _ok(step_id, output, t0)
    except Exception as e:
        logger.error(f"[Pipeline][{step_id}] Error: {e}", exc_info=True)
        return _err(step_id, str(e), t0)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

STEP_ADAPTERS = {
    "code-review":              run_code_review,
    "requirement-analysis":     run_requirement_analysis,
    "test-planning":            run_test_planning,
    "environment-setup":        run_environment_setup,
    "test-scenario-generation": run_test_scenario_generation,
    "test-case-generation":     run_test_case_generation,
    "test-case-optimization":   run_test_case_optimization,
    "test-code-generation":     run_test_code_generation,
    "test-execution":           run_test_execution,
    "test-reporting":           run_test_reporting,
    "test-closure":             run_test_closure,
}


async def execute_step(
    step_id: str,
    req: PipelineRunRequest,
    previous_results: Dict[str, StepResult],
) -> StepResult:
    """Execute a single pipeline step by ID."""
    adapter = STEP_ADAPTERS.get(step_id)
    if not adapter:
        return StepResult(
            step_id=step_id,
            status=PipelineStepStatus.ERROR,
            error=f"Unknown pipeline step: {step_id}",
        )
    return await adapter(req, previous_results)
