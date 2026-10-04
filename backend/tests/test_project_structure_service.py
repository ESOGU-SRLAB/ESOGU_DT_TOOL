import json

from services.project_structure_service import (
    PROJECT_AST_SCHEMA,
    build_project_structure,
    parse_project_structure,
    project_structure_prompt_context,
    validate_code_against_project_structure,
)


SOURCE = """
from dataclasses import dataclass

@dataclass
class RobotController:
    speed: float = 0.2

    def move_home(self) -> bool:
        return True

    def query_state(self) -> dict:
        return {"home": True}

def create_controller(speed: float = 0.2) -> RobotController:
    return RobotController(speed)
"""


def test_build_project_structure_extracts_importable_symbols_and_signatures():
    manifest = build_project_structure([{"name": "controller.py", "content": SOURCE}])

    assert manifest["schema_version"] == PROJECT_AST_SCHEMA
    assert manifest["summary"] == {
        "source_files": 1,
        "modules": 1,
        "classes": 1,
        "functions": 1,
        "methods": 2,
    }
    assert "controller.RobotController.move_home" in manifest["symbol_index"]
    assert "controller.create_controller" in manifest["symbol_index"]
    assert manifest["files"][0]["functions"][0]["signature"].startswith("(speed: float")


def test_uploaded_manifest_is_parsed_and_bounded_for_prompt_use():
    original = build_project_structure([{"name": "controller.py", "content": SOURCE}])
    parsed = parse_project_structure(json.dumps(original), "project_ast.json")

    assert parsed["source"] == "uploaded"
    assert "RobotController" in project_structure_prompt_context(parsed)


def test_validator_rejects_undeclared_project_symbol_and_method():
    manifest = build_project_structure([{"name": "robot/controller.py", "content": SOURCE}])
    invalid = """
from robot.controller import RobotController, MissingController

def test_robot():
    robot = RobotController()
    assert robot.teleport_home()
"""

    issues = validate_code_against_project_structure(invalid, manifest)

    assert any("MissingController" in issue for issue in issues)
    assert any("RobotController.teleport_home" in issue for issue in issues)


def test_validator_accepts_declared_project_method():
    manifest = build_project_structure([{"name": "robot/controller.py", "content": SOURCE}])
    valid = """
from robot.controller import RobotController

def test_robot():
    robot = RobotController()
    assert robot.move_home() is True
"""

    assert validate_code_against_project_structure(valid, manifest) == []


def test_folder_import_paths_preserve_packages_but_strip_selected_root():
    manifest = build_project_structure([
        {"name": "robot_project/robot/__init__.py", "content": ""},
        {"name": "robot_project/robot/controller.py", "content": SOURCE},
        {"name": "robot_project/robot/types.pyi", "content": "def speed_limit() -> float: ..."},
    ])

    assert manifest["project_root"] == "robot_project"
    modules = {item["module"] for item in manifest["files"]}
    assert modules == {"robot", "robot.controller", "robot.types"}
    controller = next(item for item in manifest["files"] if item["module"] == "robot.controller")
    assert controller["path"] == "robot_project/robot/controller.py"
    assert controller["relative_path"] == "robot/controller.py"
