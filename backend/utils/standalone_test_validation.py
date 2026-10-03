"""Validation rules for single-file remote Python test execution."""

import ast
import builtins
import re
import symtable
from typing import List


STANDALONE_REMOTE_REQUIREMENTS = """
## SINGLE-FILE REMOTE HARNESS CONTRACT (MANDATORY):
- The generated Python file must be completely self-contained and runnable as the only mounted source file.
- Import only Python standard-library modules and public APIs of installed packages.
- Never import modules from an installed package's `examples/`, `scripts/`, demo, or executable directories.
- Never use `from sim_robot_goal import ...` or import `sim_robot_goal` in any form. It is an example executable, not an importable package API.
- For ROS 2 / MoveIt tests, public imports such as `from pymoveit2_sim import MoveIt2` are allowed when required by the environment.
- If the test needs a helper/controller class that exists only in an example script (for example `SimCollisionAwareRobotController`), define the required helper class inside the generated test file instead of importing the example script.
- Do not rely on sibling project files, relative imports, PYTHONPATH modifications, or files that are not explicitly part of an installed package API.
- Every referenced symbol must be explicitly imported, defined, assigned, or provided as a function argument. Importing 'init' from rclpy does not define the name 'rclpy'.
- ROS initialization must be paired with deterministic cleanup in a 'finally' block, including rclpy.shutdown() (or its imported alias).
- Do not start unbounded executors or waits in tests: no executor.spin, while rclpy.ok(), or ROS rate sleep calls. Use bounded operations and explicit cleanup.
""".strip()


_IMPLICIT_GLOBALS = {
    "__builtins__", "__file__", "__loader__", "__name__", "__package__", "__spec__",
}


def _undefined_global_names(code: str) -> List[str]:
    """Find names that Python will resolve globally but the file never binds."""
    table = symtable.symtable(code, "<generated_test>", "exec")
    module_bound = {
        symbol.get_name()
        for symbol in table.get_symbols()
        if symbol.is_imported() or symbol.is_assigned() or symbol.is_namespace()
    }
    allowed = module_bound | set(dir(builtins)) | _IMPLICIT_GLOBALS
    missing = set()

    def inspect(current):
        for symbol in current.get_symbols():
            if symbol.is_referenced() and symbol.is_global() and symbol.get_name() not in allowed:
                missing.add(symbol.get_name())
        for child in current.get_children():
            inspect(child)

    inspect(table)
    return sorted(missing)


def _call_matches(node: ast.AST, module_names: set, function_names: set, attribute: str) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if isinstance(node.func, ast.Name):
        return node.func.id in function_names
    return (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == attribute
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id in module_names
    )


def _ros_lifecycle_issues(tree: ast.AST) -> List[str]:
    """Reject ROS patterns that commonly leave pytest or its container hanging."""
    issues: List[str] = []
    rclpy_modules = {"rclpy"}
    init_names = set()
    shutdown_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "rclpy":
                    rclpy_modules.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module == "rclpy":
            for alias in node.names:
                if alias.name == "init":
                    init_names.add(alias.asname or alias.name)
                elif alias.name == "shutdown":
                    shutdown_names.add(alias.asname or alias.name)

    has_init = any(
        _call_matches(node, rclpy_modules, init_names, "init")
        for node in ast.walk(tree)
    )
    shutdown_in_finally = any(
        _call_matches(child, rclpy_modules, shutdown_names, "shutdown")
        for node in ast.walk(tree)
        if isinstance(node, ast.Try)
        for final_node in node.finalbody
        for child in ast.walk(final_node)
    )
    if has_init and not shutdown_in_finally:
        issues.append(
            "ROS initialization must be paired with rclpy.shutdown() (or its imported alias) "
            "inside a finally block so remote pytest cannot hang during cleanup."
        )

    if any(isinstance(node, ast.Attribute) and node.attr == "spin" for node in ast.walk(tree)):
        issues.append("Unbounded executor.spin usage is not allowed in a remote single-test file.")

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "sleep"
            and isinstance(node.func.value, ast.Call)
            and isinstance(node.func.value.func, ast.Attribute)
            and node.func.value.func.attr == "create_rate"
        ):
            issues.append("ROS rate sleep can wait forever without simulation time; use a bounded wait.")
            break
        if (
            isinstance(node, ast.While)
            and isinstance(node.test, ast.Call)
            and isinstance(node.test.func, ast.Attribute)
            and node.test.func.attr == "ok"
            and isinstance(node.test.func.value, ast.Name)
            and node.test.func.value.id in rclpy_modules
        ):
            issues.append("while rclpy.ok() is unbounded and is not allowed in a single test.")
            break
    return issues


def supports_legacy_sim_robot_goal(image: str) -> bool:
    """Return whether the selected harness exposes the legacy example module."""
    image_name = (image or "").rsplit("/", 1)[-1]
    match = re.fullmatch(r"ros2-exec-harness:(\d+)\.(\d+)\.(\d+)", image_name)
    if not match:
        return False
    return tuple(int(part) for part in match.groups()) >= (0, 2, 0)


def validate_standalone_python(
    code: str,
    *,
    allow_legacy_sim_robot_goal: bool = False,
) -> List[str]:
    """Return actionable violations of the single-file remote harness contract."""
    issues: List[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"Python syntax error at line {exc.lineno}: {exc.msg}"]

    try:
        undefined_names = _undefined_global_names(code)
    except SyntaxError as exc:
        return [f"Python syntax error at line {exc.lineno}: {exc.msg}"]
    if undefined_names:
        issues.append(
            "Undefined global name(s): " + ", ".join(undefined_names) + ". "
            "Import or define every referenced symbol in the generated file."
        )

    issues.extend(_ros_lifecycle_issues(tree))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                issues.append(
                    f"Relative import at line {node.lineno} is unavailable in the single-file harness."
                )
            modules = [node.module] if node.module else []
        else:
            continue

        for module in modules:
            parts = module.split(".")
            if parts[0] == "sim_robot_goal" and not allow_legacy_sim_robot_goal:
                issues.append(
                    f"Import '{module}' at line {node.lineno} targets a ROS example executable, "
                    "not an importable package API. Embed the required controller/helper in the test file."
                )
            elif "examples" in parts or "scripts" in parts:
                issues.append(
                    f"Import '{module}' at line {node.lineno} targets an examples/scripts directory "
                    "that is not part of the supported package API."
                )

    return issues


def require_standalone_python(
    code: str,
    *,
    allow_legacy_sim_robot_goal: bool = False,
) -> None:
    issues = validate_standalone_python(
        code,
        allow_legacy_sim_robot_goal=allow_legacy_sim_robot_goal,
    )
    if issues:
        raise ValueError("Remote single-file validation failed: " + " ".join(issues))
