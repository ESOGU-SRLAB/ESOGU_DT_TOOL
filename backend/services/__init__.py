"""Service package with compatibility-preserving lazy exports.

Importing a focused service such as ``services.execution_client`` must not load
the model/generation stack. This keeps the remote execution contract independent
from optional provider packages.
"""

from importlib import import_module

__all__ = [
    'ReviewService',
    'PromptGenerationService', 
    'EnvironmentSetupService',
    'RequirementAnalysisService',
    'TestPlanningService'
]

_EXPORTS = {
    "ReviewService": ("review_service", "ReviewService"),
    "PromptGenerationService": ("prompt_generation_service", "PromptGenerationService"),
    "EnvironmentSetupService": ("environment_setup_service", "EnvironmentSetupService"),
    "RequirementAnalysisService": ("requirement_analysis_service", "RequirementAnalysisService"),
    "TestPlanningService": ("test_planning_service", "TestPlanningService"),
}


def __getattr__(name):
    try:
        module_name, attribute = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    value = getattr(import_module(f"{__name__}.{module_name}"), attribute)
    globals()[name] = value
    return value
