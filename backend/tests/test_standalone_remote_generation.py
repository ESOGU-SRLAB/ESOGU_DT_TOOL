import asyncio
import json
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.execution_client import ExecutionRequest, SshDockerExecutionClient  # noqa: E402
from services.test_code_oracle import evaluate_test_code  # noqa: E402
from services.test_code_generation_service import TestCodeGenerationService as CodeGenerationService  # noqa: E402
from services.robot_capability_service import (  # noqa: E402
    RobotCapabilityError,
    parse_robot_capability_json,
    validate_generated_code_against_capabilities,
)
from utils.standalone_test_validation import (  # noqa: E402
    supports_legacy_sim_robot_goal,
    validate_standalone_python,
)


def _service_without_database():
    return object.__new__(CodeGenerationService)


def _approved_capability_contract():
    return {
        "schema_version": "1.0",
        "meta": {
            "title": "Test robot",
            "approval": {
                "approved": True,
                "approved_by": "test-engineer",
                "approved_at": "2026-09-29",
            },
            "pinned_sources": {"image": {"tag": "ros2-exec-harness:0.2.0"}},
        },
        "execution_environment": {"pytest": "6.2.5"},
        "target_system": {"joint_order": ["rail", "j1"]},
        "api": {
            "allowed_imports": [
                "from sim_robot_joint_goal import CollisionAwareRobotController",
                "import pytest",
            ],
            "classes": {
                "sim_robot_joint_goal.CollisionAwareRobotController": {
                    "public_attributes": {"moveit2": "MoveIt2"},
                    "methods": {
                        "move_to_joint_angles": {
                            "signature": "move_to_joint_angles(joint_positions, synchronous=True)",
                            "returns": "bool when synchronous=True",
                            "raises": "Never",
                        },
                        "move_to_position": {
                            "signature": "move_to_position(position, orientation=None, synchronous=True)",
                            "returns": "None ALWAYS",
                            "raises": "Never",
                        }
                    },
                }
            },
            "moveit2_interface": {
                "allowed_members": {
                    "plan(position=None, joint_positions=None) -> JointTrajectory | None": "plan only",
                    "joint_state -> sensor_msgs/JointState | None": "latest state",
                }
            },
            "forbidden": {
                "nonexistent_names_seen_in_generated_tests": ["get_max_speed"]
            },
        },
        "limits": {
            "joints": {"items": [
                {"name": "rail", "position_min": 0.0, "position_max": 2.0},
                {"name": "j1", "position_min": -3.14, "position_max": 3.14},
            ]},
            "scaling": {"recommended_max_for_tests": 0.5},
        },
        "workspace": {"verified_cartesian_poses": {"status": "none yet"}},
    }


def test_validator_rejects_ros_example_and_relative_imports():
    issues = validate_standalone_python(
        "from sim_robot_goal import SimCollisionAwareRobotController\n"
        "from .helper import build_robot\n"
    )

    assert any("example executable" in issue for issue in issues)
    assert any("Relative import" in issue for issue in issues)


def test_validator_rejects_undefined_rclpy_name_and_missing_finally_cleanup():
    issues = validate_standalone_python(
        "from rclpy import init, shutdown\n"
        "def test_robot():\n"
        "    rclpy.init()\n"
        "    assert True\n"
    )

    assert any("Undefined global name(s): rclpy" in issue for issue in issues)
    assert any("inside a finally block" in issue for issue in issues)


def test_validator_accepts_bounded_ros_lifecycle_with_explicit_module_import():
    issues = validate_standalone_python(
        "import rclpy\n"
        "def test_robot():\n"
        "    rclpy.init()\n"
        "    try:\n"
        "        assert True\n"
        "    finally:\n"
        "        rclpy.shutdown()\n"
    )

    assert issues == []


def test_validator_rejects_unbounded_ros_executor_patterns():
    issues = validate_standalone_python(
        "import rclpy\n"
        "def test_robot(executor, node):\n"
        "    rclpy.init()\n"
        "    try:\n"
        "        executor.spin()\n"
        "        node.create_rate(1.0).sleep()\n"
        "    finally:\n"
        "        rclpy.shutdown()\n"
    )

    assert any("executor.spin" in issue for issue in issues)
    assert any("ROS rate sleep" in issue for issue in issues)


def test_validator_allows_legacy_import_only_for_compatible_harness():
    code = "from sim_robot_goal import SimCollisionAwareRobotController\n"

    assert supports_legacy_sim_robot_goal("ros2-exec-harness:0.1.0") is False
    assert supports_legacy_sim_robot_goal("ros2-exec-harness:0.2.0") is True
    assert supports_legacy_sim_robot_goal("registry.local/ros2-exec-harness:0.3.1") is True
    assert validate_standalone_python(
        code,
        allow_legacy_sim_robot_goal=True,
    ) == []


def test_generation_prompt_requires_self_contained_remote_code():
    prompt = _service_without_database()._create_test_generation_prompt(
        {"id": "TC-1", "title": "Robot goal", "description": "", "objective": "", "steps": []},
        {"files": [], "imports_dependencies": []},
        {"language": "python", "framework": "pytest"},
        {"imports": "import pytest"},
    )

    assert "SINGLE-FILE REMOTE HARNESS CONTRACT" in prompt
    assert "Never use `from sim_robot_goal import ...`" in prompt
    assert "define the required helper class inside the generated test file" in prompt
    assert "GENERATION ORACLE ACCEPTANCE CRITERIA" in prompt
    assert "observable verification" in prompt


def test_capability_prompt_is_closed_world_and_allows_declared_legacy_import():
    prompt = _service_without_database()._create_test_generation_prompt(
        {"id": "TC-1", "title": "Robot goal", "description": "", "objective": "", "steps": []},
        {"files": [], "imports_dependencies": []},
        {"language": "python", "framework": "pytest"},
        {"imports": "import pytest"},
        capability_contract=_approved_capability_contract(),
    )

    assert "APPROVED ROBOT CAPABILITY CONTRACT (CLOSED WORLD)" in prompt
    assert "CAPABILITY_UNSUPPORTED" in prompt
    assert "CollisionAwareRobotController" in prompt
    assert "sim_robot_goal` imports are allowed only" in prompt


def test_unapproved_capability_file_is_rejected():
    draft_contract = _approved_capability_contract()
    draft_contract["meta"]["approval"]["approved"] = False
    try:
        parse_robot_capability_json(
            json.dumps(draft_contract).encode("utf-8"),
            "draft_robot_capabilities.json",
        )
        assert False, "draft capability contract must not be accepted"
    except RobotCapabilityError as exc:
        assert "not manually approved" in str(exc)


def test_capability_oracle_rejects_invented_method_and_unsafe_scaling():
    issues = validate_generated_code_against_capabilities(
        "from sim_robot_joint_goal import CollisionAwareRobotController\n"
        "controller = CollisionAwareRobotController()\n"
        "controller.moveit2.max_velocity = 8.0\n"
        "controller.get_max_speed()\n",
        _approved_capability_contract(),
    )

    assert any("get_max_speed" in issue for issue in issues)
    assert any("max_velocity=8" in issue for issue in issues)


def test_capability_oracle_accepts_declared_method_and_joint_limits():
    issues = validate_generated_code_against_capabilities(
        "from sim_robot_joint_goal import CollisionAwareRobotController\n"
        "controller = CollisionAwareRobotController()\n"
        "assert controller.move_to_joint_angles([1.0, 0.5]) is True\n",
        _approved_capability_contract(),
    )

    assert issues == []


def test_capability_oracle_tracks_fixture_controller_and_rejects_unknown_method():
    issues = validate_generated_code_against_capabilities(
        "import pytest\n"
        "from sim_robot_joint_goal import CollisionAwareRobotController\n"
        "@pytest.fixture\n"
        "def controller():\n"
        "    ctrl = CollisionAwareRobotController()\n"
        "    yield ctrl\n"
        "def test_invalid_api(controller):\n"
        "    controller.validate_input([])\n"
        "    assert controller.move_to_joint_angles([1.0, 0.0]) is True\n",
        _approved_capability_contract(),
    )

    assert any("validate_input" in issue for issue in issues)


def test_capability_oracle_rejects_redefined_controller_and_none_success_assertion():
    contract = _approved_capability_contract()
    redefined = validate_generated_code_against_capabilities(
        "class CollisionAwareRobotController:\n"
        "    pass\n"
        "def test_fake():\n"
        "    assert CollisionAwareRobotController()\n",
        contract,
    )
    wrong_return = validate_generated_code_against_capabilities(
        "from sim_robot_joint_goal import CollisionAwareRobotController\n"
        "controller = CollisionAwareRobotController()\n"
        "def test_pose():\n"
        "    assert controller.move_to_position([0.1, 0.2, 0.3]) is True\n",
        contract,
    )

    assert any("redefining" in issue for issue in redefined)
    assert any("returns None" in issue for issue in wrong_return)


def test_capability_oracle_allows_out_of_range_target_only_as_negative_test():
    contract = _approved_capability_contract()
    negative_issues = validate_generated_code_against_capabilities(
        "from sim_robot_joint_goal import CollisionAwareRobotController\n"
        "controller = CollisionAwareRobotController()\n"
        "def test_rejected():\n"
        "    target = [3.0, 0.0]\n"
        "    assert controller.move_to_joint_angles(target) is False\n",
        contract,
    )
    positive_issues = validate_generated_code_against_capabilities(
        "from sim_robot_joint_goal import CollisionAwareRobotController\n"
        "controller = CollisionAwareRobotController()\n"
        "def test_accepted():\n"
        "    assert controller.move_to_joint_angles([3.0, 0.0]) is True\n",
        contract,
    )

    assert negative_issues == []
    assert any("negative test" in issue for issue in positive_issues)


def test_capability_oracle_rejects_positive_unverified_cartesian_pose():
    issues = validate_generated_code_against_capabilities(
        "from sim_robot_joint_goal import CollisionAwareRobotController\n"
        "controller = CollisionAwareRobotController()\n"
        "def test_pose():\n"
        "    trajectory = controller.moveit2.plan(position=[0.1, 0.2, 0.3])\n"
        "    assert trajectory is not None\n",
        _approved_capability_contract(),
    )

    assert any("no verified Cartesian poses" in issue for issue in issues)


def test_capability_oracle_rejects_invalid_execution_and_state_observation_patterns():
    issues = validate_generated_code_against_capabilities(
        "from sim_robot_joint_goal import CollisionAwareRobotController\n"
        "controller = CollisionAwareRobotController()\n"
        "def test_invalid_patterns():\n"
        "    state = controller.moveit2.query_state()\n"
        "    assert state.joint_state is not None\n"
        "    controller.move_to_position(position=None)\n",
        _approved_capability_contract(),
    )

    assert any("query_state() returns" in issue for issue in issues)
    assert any("position=None" in issue for issue in issues)


def test_generation_oracle_rejects_unconditional_true_assertion():
    report = evaluate_test_code("def test_nothing():\n    assert True\n")

    assert report["passed"] is False
    assert any("assert True" in issue for issue in report["issues"])


def test_generation_returns_structured_unsupported_result():
    class FakeLlm:
        model_name = "test-model"
        is_gemini = False

        async def generate_response(self, _prompt, **_kwargs):
            return "CAPABILITY_UNSUPPORTED: No authentication API exists."

    result = asyncio.run(_service_without_database()._generate_single_test_code(
        {"TestCaseID": "TC-AUTH", "Title": "Login"},
        {"files": [], "imports_dependencies": []},
        {"language": "python", "framework": "pytest"},
        FakeLlm(),
        1,
        capability_contract=_approved_capability_contract(),
    ))

    assert result["status"] == "unsupported"
    assert result["execution_eligibility"] == "unsupported"
    assert result["code"] is None
    assert "authentication API" in result["eligibility_reason"]


def test_generation_oracle_accepts_complete_executable_test():
    report = evaluate_test_code(
        "def test_robot_reaches_goal():\n"
        "    actual_pose = (1.0, 2.0, 3.0)\n"
        "    expected_pose = (1.0, 2.0, 3.0)\n"
        "    assert actual_pose == expected_pose\n"
    )

    assert report["passed"] is True
    assert report["verdict"] == "pass"
    assert report["score"] == 100
    assert all(check["passed"] for check in report["checks"])


def test_generation_oracle_rejects_action_only_placeholder_code():
    report = evaluate_test_code(
        "def test_robot_move():\n"
        "    # TODO verify final pose\n"
        "    pass\n"
    )

    assert report["passed"] is False
    assert any("no observable" in issue.lower() for issue in report["issues"])
    assert any("placeholder" in issue.lower() for issue in report["issues"])


def test_invalid_llm_output_gets_one_automatic_repair():
    class FakeLlm:
        model_name = "test-model"
        is_gemini = False

        def __init__(self):
            self.prompts = []
            self.kwargs = []

        async def generate_response(self, prompt, **_kwargs):
            self.prompts.append(prompt)
            self.kwargs.append(_kwargs)
            if len(self.prompts) == 1:
                return "from sim_robot_goal import SimCollisionAwareRobotController\n"
            return (
                "class SimCollisionAwareRobotController:\n"
                "    def reached_goal(self):\n"
                "        return True\n\n"
                "def test_robot():\n"
                "    controller = SimCollisionAwareRobotController()\n"
                "    assert controller.reached_goal() is True\n"
            )

    client = FakeLlm()
    result = asyncio.run(_service_without_database()._generate_single_test_code(
        {"TestCaseID": "TC-1", "Title": "Robot goal"},
        {"files": [], "imports_dependencies": []},
        {"language": "python", "framework": "pytest"},
        client,
        1,
    ))

    assert result["status"] == "success"
    assert "sim_robot_goal import" not in result["code"]
    assert result["oracle"]["passed"] is True
    assert result["oracle"]["score"] == 100
    assert len(client.prompts) == 2
    assert all(call.get("skip_chunking") is True for call in client.kwargs)
    assert "REQUIRED CORRECTION" in client.prompts[1]


def test_generation_rejects_oversized_atomic_input_before_model_call():
    class FakeLlm:
        model_name = "test-model"
        is_gemini = False

        def __init__(self):
            self.prompts = []

        async def generate_response(self, prompt, **_kwargs):
            self.prompts.append(prompt)
            return "def test_unexpected():\n    assert True\n"

    client = FakeLlm()
    result = asyncio.run(_service_without_database()._generate_single_test_code(
        {"TestCaseID": "TC-LARGE", "Title": "Large atomic input"},
        {"files": [], "imports_dependencies": []},
        {"language": "python", "framework": "pytest"},
        client,
        1,
        custom_prompt="robot safety requirement " * 6000,
        max_input_tokens=4096,
    ))

    assert result["status"] == "error"
    assert "exceeding the configured 4096-token budget" in result["error"]
    assert client.prompts == []


def test_remote_adapter_rejects_invalid_import_before_network(monkeypatch):
    client = SshDockerExecutionClient(
        host="ifarlab",
        remote_dir="~/stlc_runs",
        image="ros2-exec-harness:0.1.0",
        password="",
        timeout_seconds=30,
        connect_timeout_seconds=5,
    )

    async def unexpected_network(*_args, **_kwargs):
        raise AssertionError("network must not be used for invalid generated code")

    monkeypatch.setattr(client, "_run_command", unexpected_network)
    try:
        asyncio.run(client.submit(ExecutionRequest(
            test_code="from sim_robot_goal import SimCollisionAwareRobotController",
            language="python",
        )))
        assert False, "validation should fail"
    except ValueError as exc:
        assert "Remote single-file validation failed" in str(exc)
        assert "example executable" in str(exc)
