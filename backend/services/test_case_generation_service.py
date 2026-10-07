"""Shared entry point for the existing test-case generation implementation.

The legacy implementation remains in its original router module to minimize a
high-risk move, but both the UI route and pipeline adapter call it through this
service. This removes the previously duplicated pipeline algorithm.
"""

from typing import Any, Dict

from core.database import get_database


class _JsonRequest:
    def __init__(self, payload: Dict[str, Any]):
        self._payload = payload

    async def json(self) -> Dict[str, Any]:
        return self._payload


class TestCaseGenerationService:
    async def generate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(payload)
        if not data.get("process_prompt"):
            db = await get_database()
            test_type = data.get("test_type") or "Functional"
            prompt_doc = await db["test_scenario_generation_prompt"].find_one(
                {"test_name": test_type}
            )
            if prompt_doc:
                data["process_prompt"] = (
                    prompt_doc.get("test_case_main_prompt")
                    or prompt_doc.get("test_prompt")
                    or ""
                )
        if not data.get("process_prompt"):
            data["process_prompt"] = (
                "Generate comprehensive test cases for each test scenario. "
                "Follow ISTQB standards and cover positive, negative and boundary cases."
            )

        # Lazy import avoids a router/service import cycle during application startup.
        from routers.test_scenario_generation_router import (
            _generate_test_cases_for_scenarios_impl,
        )

        return await _generate_test_cases_for_scenarios_impl(_JsonRequest(data))
