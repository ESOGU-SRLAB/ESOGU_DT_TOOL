"""Robot capability contract loading, prompt shaping, and code validation."""

from __future__ import annotations

import ast
import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple


MAX_CAPABILITY_BYTES = 2 * 1024 * 1024


class RobotCapabilityError(ValueError):
    """Raised when a robot capability document is missing required safety data."""


def parse_robot_capability_json(raw: bytes, filename: str = "robot_capabilities.json") -> Dict[str, Any]:
    if len(raw) > MAX_CAPABILITY_BYTES:
        raise RobotCapabilityError("Robot capability JSON must be 2 MB or smaller.")
    try:
        contract = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RobotCapabilityError(f"{filename} is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(contract, dict):
        raise RobotCapabilityError("Robot capability JSON root must be an object.")

    missing = [key for key in ("schema_version", "meta", "api", "limits") if key not in contract]
    if missing:
        raise RobotCapabilityError(
            "Robot capability JSON is missing required fields: " + ", ".join(missing)
        )
    if not contract.get("api", {}).get("classes"):
        raise RobotCapabilityError("Robot capability JSON must declare api.classes.")
    if not contract.get("api", {}).get("allowed_imports"):
        raise RobotCapabilityError("Robot capability JSON must declare api.allowed_imports.")

    approval = contract.get("meta", {}).get("approval", {})
    if approval.get("approved") is not True:
        raise RobotCapabilityError(
            "Robot capability contract is not manually approved. Set meta.approval.approved=true, "
            "approved_by, and approved_at after engineering review."
        )
    if not approval.get("approved_by") or not approval.get("approved_at"):
        raise RobotCapabilityError(
            "Approved robot capability contracts require approved_by and approved_at."
        )
    return contract


def capability_descriptor(contract: Dict[str, Any], raw: Optional[bytes] = None) -> Dict[str, Any]:
    meta = contract.get("meta", {})
    image = meta.get("pinned_sources", {}).get("image", {})
    encoded = raw if raw is not None else json.dumps(contract, sort_keys=True).encode("utf-8")
    return {
        "schema_version": contract.get("schema_version"),
        "title": meta.get("title"),
        "approved": meta.get("approval", {}).get("approved") is True,
        "approved_by": meta.get("approval", {}).get("approved_by"),
        "approved_at": meta.get("approval", {}).get("approved_at"),
        "image_tag": image.get("tag"),
        "image_id": image.get("id"),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


def capability_prompt_context(contract: Dict[str, Any]) -> str:
    """Return the closed-world portion of the contract used for generation."""
    context = {
        "schema_version": contract.get("schema_version"),
        "execution_environment": contract.get("execution_environment", {}),
        "target_system": contract.get("target_system", {}),
        "api": contract.get("api", {}),
        "limits": contract.get("limits", {}),
        "workspace": contract.get("workspace", {}),
        "test_generation_rules": contract.get("test_generation_rules", {}),
        "open_questions": contract.get("open_questions", []),
    }
    return json.dumps(context, ensure_ascii=False, separators=(",", ":"))


def _method_parameters(signature: str) -> Set[str]:
    match = re.search(r"\((.*)\)", signature or "")
    if not match:
        return set()
    params: Set[str] = set()
    for item in match.group(1).split(","):
        name = item.strip().split("=", 1)[0].strip()
        if name:
            params.add(name.lstrip("*"))
    return params


def _class_catalog(contract: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    classes = contract.get("api", {}).get("classes", {})
    aliases: Dict[str, str] = {}
    for qualified_name in classes:
        aliases[qualified_name.rsplit(".", 1)[-1]] = qualified_name
    return classes, aliases


def _literal_number(node: ast.AST) -> Optional[float]:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        value = _literal_number(node.operand)
        return -value if value is not None else None
    return None


def _literal_number_list(node: ast.AST) -> Optional[List[float]]:
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None
    values = [_literal_number(item) for item in node.elts]
    return None if any(value is None for value in values) else [float(value) for value in values]


def _is_fixture(node: ast.FunctionDef) -> bool:
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Name) and target.id == "fixture":
            return True
        if isinstance(target, ast.Attribute) and target.attr == "fixture":
            return True
    return False


def _expected_boolean_names(function: ast.AST, expected: bool) -> Set[str]:
    names: Set[str] = set()
    for node in ast.walk(function):
        if not isinstance(node, ast.Assert):
            continue
        test = node.test
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not) and not expected:
            if isinstance(test.operand, ast.Name):
                names.add(test.operand.id)
        if not isinstance(test, ast.Compare) or len(test.ops) != 1:
            continue
        pairs = [(test.left, test.comparators[0]), (test.comparators[0], test.left)]
        for candidate, literal in pairs:
            if (
                isinstance(candidate, ast.Name)
                and isinstance(literal, ast.Constant)
                and literal.value is expected
            ):
                names.add(candidate.id)
    return names


def _call_is_directly_expected(call: ast.Call, parent: Dict[ast.AST, ast.AST], expected: Any) -> bool:
    current: ast.AST = call
    while current in parent and not isinstance(parent[current], (ast.FunctionDef, ast.AsyncFunctionDef)):
        current = parent[current]
        if isinstance(current, ast.Assert):
            test = current.test
            if expected is False and isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
                return call in ast.walk(test.operand)
            if isinstance(test, ast.Compare) and len(test.ops) == 1:
                values = [test.left, test.comparators[0]]
                return any(
                    isinstance(value, ast.Constant) and value.value is expected
                    for value in values
                )
            return expected is True and test is call
    return False


def _inside_pytest_raises(node: ast.AST, parent: Dict[ast.AST, ast.AST]) -> bool:
    current = node
    while current in parent:
        current = parent[current]
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return False
        if isinstance(current, ast.With):
            for item in current.items:
                expr = item.context_expr
                if (
                    isinstance(expr, ast.Call)
                    and isinstance(expr.func, ast.Attribute)
                    and expr.func.attr == "raises"
                ):
                    return True
    return False


def validate_generated_code_against_capabilities(
    code: str,
    contract: Dict[str, Any],
) -> List[str]:
    """Reject invented controller APIs and literal values outside the contract."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    issues: List[str] = []
    classes, class_aliases = _class_catalog(contract)
    imported_classes: Dict[str, str] = {}
    global_instances: Dict[str, str] = {}
    fixtures: Dict[str, str] = {}
    parent = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    forbidden = set(
        contract.get("api", {}).get("forbidden", {}).get(
            "nonexistent_names_seen_in_generated_tests", []
        )
    )

    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name in class_aliases:
            issues.append(
                f"Capability controller '{node.name}' must be imported from the approved runtime; "
                "redefining or copying the system under test inside the test file is forbidden."
            )

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                qualified = f"{node.module}.{alias.name}"
                if node.module.startswith("sim_robot_") and qualified not in classes:
                    issues.append(f"Import '{qualified}' is not declared in capability api.classes.")
                if qualified in classes:
                    imported_classes[alias.asname or alias.name] = qualified
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            func = node.value.func
            class_name = func.id if isinstance(func, ast.Name) else ""
            qualified = imported_classes.get(class_name) or class_aliases.get(class_name)
            if qualified:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        global_instances[target.id] = qualified

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not _is_fixture(node):
            continue
        fixture_locals: Dict[str, str] = {}
        for child in ast.walk(node):
            if isinstance(child, ast.Assign) and isinstance(child.value, ast.Call) and isinstance(child.value.func, ast.Name):
                qualified = imported_classes.get(child.value.func.id) or class_aliases.get(child.value.func.id)
                if qualified:
                    for target in child.targets:
                        if isinstance(target, ast.Name):
                            fixture_locals[target.id] = qualified
        for child in ast.walk(node):
            value = child.value if isinstance(child, (ast.Return, ast.Yield)) else None
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
                qualified = imported_classes.get(value.func.id) or class_aliases.get(value.func.id)
                if qualified:
                    fixtures[node.name] = qualified
                    break
            if isinstance(value, ast.Name) and value.id in fixture_locals:
                fixtures[node.name] = fixture_locals[value.id]
                break

    moveit_members = contract.get("api", {}).get("moveit2_interface", {}).get(
        "allowed_members", {}
    )
    allowed_moveit_names = {key.split("(", 1)[0].split(" ", 1)[0] for key in moveit_members}
    joint_limits = contract.get("limits", {}).get("joints", {}).get("items", [])
    recommended_scaling = contract.get("limits", {}).get("scaling", {}).get(
        "recommended_max_for_tests", 1.0
    )

    scopes: List[Tuple[ast.AST, Dict[str, str]]] = [(tree, dict(global_instances))]
    for function in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        scope = dict(global_instances)
        for arg in function.args.args:
            if arg.arg in fixtures:
                scope[arg.arg] = fixtures[arg.arg]
            if isinstance(arg.annotation, ast.Name):
                qualified = imported_classes.get(arg.annotation.id) or class_aliases.get(arg.annotation.id)
                if qualified:
                    scope[arg.arg] = qualified
        for child in ast.walk(function):
            if isinstance(child, ast.Assign) and isinstance(child.value, ast.Call) and isinstance(child.value.func, ast.Name):
                qualified = imported_classes.get(child.value.func.id) or class_aliases.get(child.value.func.id)
                if qualified:
                    for target in child.targets:
                        if isinstance(target, ast.Name):
                            scope[target.id] = qualified
        scopes.append((function, scope))

    for scope_node, instances in scopes:
        false_names = _expected_boolean_names(scope_node, False)
        true_names = _expected_boolean_names(scope_node, True)
        assigned_calls: Dict[int, str] = {}
        literal_lists: Dict[str, List[float]] = {}
        query_state_results: Set[str] = set()
        for candidate in ast.walk(scope_node):
            if isinstance(candidate, ast.Assign) and isinstance(candidate.value, ast.Call):
                targets = [target.id for target in candidate.targets if isinstance(target, ast.Name)]
                if targets:
                    assigned_calls[id(candidate.value)] = targets[0]
                    if (
                        isinstance(candidate.value.func, ast.Attribute)
                        and candidate.value.func.attr == "query_state"
                    ):
                        query_state_results.update(targets)
            if isinstance(candidate, ast.Assign):
                values = _literal_number_list(candidate.value)
                if values is not None:
                    for target in candidate.targets:
                        if isinstance(target, ast.Name):
                            literal_lists[target.id] = values

        for node in ast.walk(scope_node):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                owner = node.func.value
                method = node.func.attr
                class_name: Optional[str] = None
                is_moveit = False
                if isinstance(owner, ast.Name):
                    class_name = instances.get(owner.id)
                elif (
                    isinstance(owner, ast.Attribute)
                    and owner.attr == "moveit2"
                    and isinstance(owner.value, ast.Name)
                ):
                    class_name = instances.get(owner.value.id)
                    is_moveit = class_name is not None

                if class_name and not is_moveit:
                    class_spec = classes[class_name]
                    methods = class_spec.get("methods", {})
                    if method not in methods:
                        issues.append(f"Method '{method}()' is not declared for {class_name}.")
                    else:
                        method_spec = methods[method]
                        allowed_params = _method_parameters(method_spec.get("signature", ""))
                        for keyword in node.keywords:
                            if keyword.arg and keyword.arg not in allowed_params:
                                issues.append(
                                    f"Keyword '{keyword.arg}' is not valid for {class_name}.{method}()."
                                )
                        assigned_name = assigned_calls.get(id(node))
                        expected_true = _call_is_directly_expected(node, parent, True) or (
                            assigned_name in true_names if assigned_name else False
                        )
                        returns = str(method_spec.get("returns", "")).lower()
                        if expected_true and returns.startswith("none"):
                            issues.append(
                                f"{class_name}.{method}() returns None and cannot be asserted as successful."
                            )
                        if _inside_pytest_raises(node, parent) and "never" in str(method_spec.get("raises", "")).lower():
                            issues.append(
                                f"{class_name}.{method}() catches errors and does not raise; pytest.raises is an invalid oracle."
                            )
                        if method == "move_to_position":
                            position_nodes = [node.args[0]] if node.args else []
                            position_nodes.extend(
                                keyword.value for keyword in node.keywords if keyword.arg == "position"
                            )
                            if any(
                                isinstance(value, ast.Constant) and value.value is None
                                for value in position_nodes
                            ):
                                issues.append(
                                    f"{class_name}.move_to_position() requires a real Cartesian position; "
                                    "position=None cannot execute a trajectory previously returned by plan()."
                                )
                elif class_name and is_moveit and method not in allowed_moveit_names:
                    issues.append(f"MoveIt2 member '{method}' is not allowed by the capability contract.")

                if method in {"move_to_joint_angles", "move_to_configuration"} and node.args:
                    values = _literal_number_list(node.args[0])
                    if values is None and isinstance(node.args[0], ast.Name):
                        values = literal_lists.get(node.args[0].id)
                    if values is not None:
                        outside = []
                        if len(values) != len(joint_limits):
                            issues.append(
                                f"Joint target has {len(values)} values; capability contract requires {len(joint_limits)}."
                            )
                        else:
                            outside = [
                                (value, limit) for value, limit in zip(values, joint_limits)
                                if value < limit["position_min"] or value > limit["position_max"]
                            ]
                        if outside:
                            assigned_name = assigned_calls.get(id(node))
                            expects_false = _call_is_directly_expected(node, parent, False) or (
                                assigned_name in false_names if assigned_name else False
                            )
                            if not expects_false:
                                for value, limit in outside:
                                    issues.append(
                                        f"Joint '{limit['name']}' target {value} is outside "
                                        f"[{limit['position_min']}, {limit['position_max']}]; it is allowed only "
                                        "in a negative test that asserts the call returns False."
                                    )

                if method == "plan":
                    has_pose = any(keyword.arg == "position" for keyword in node.keywords)
                    assigned_name = assigned_calls.get(id(node))
                    expects_success = _call_is_directly_expected(node, parent, True) or (
                        assigned_name in true_names if assigned_name else False
                    )
                    # `traj is not None` is not a boolean-True comparison; detect it explicitly.
                    if assigned_name:
                        for assertion in [n for n in ast.walk(scope_node) if isinstance(n, ast.Assert)]:
                            comparison = assertion.test
                            if isinstance(comparison, ast.Compare) and isinstance(comparison.left, ast.Name):
                                if comparison.left.id == assigned_name and any(
                                    isinstance(value, ast.Constant) and value.value is None
                                    for value in comparison.comparators
                                ) and any(isinstance(op, (ast.IsNot, ast.NotEq)) for op in comparison.ops):
                                    expects_success = True
                    verified_poses = contract.get("workspace", {}).get("verified_cartesian_poses", {})
                    if has_pose and expects_success and verified_poses.get("status") == "none yet":
                        issues.append(
                            "The capability contract has no verified Cartesian poses; code must not assert "
                            "that a pose plan succeeds. Use a verified joint configuration or return CAPABILITY_UNSUPPORTED."
                        )

            if isinstance(node, ast.Attribute):
                if (
                    isinstance(node.value, ast.Name)
                    and node.value.id in query_state_results
                    and node.attr == "joint_state"
                ):
                    issues.append(
                        "MoveIt2.query_state() returns a MoveIt2State enum, not an object with joint_state; "
                        "read controller.moveit2.joint_state instead."
                    )
                if isinstance(node.value, ast.Name) and node.value.id in instances:
                    class_spec = classes[instances[node.value.id]]
                    allowed = set(class_spec.get("public_attributes", {})) | set(class_spec.get("methods", {}))
                    if allowed_moveit_names:
                        allowed.add("moveit2")
                    if (
                        isinstance(parent.get(node), ast.Call)
                        and parent[node].func is node
                    ):
                        continue
                    if node.attr not in allowed:
                        issues.append(
                            f"Attribute '{node.attr}' is not declared for {instances[node.value.id]}."
                        )
                elif (
                    isinstance(node.value, ast.Attribute)
                    and node.value.attr == "moveit2"
                    and isinstance(node.value.value, ast.Name)
                    and node.value.value.id in instances
                    and node.attr not in allowed_moveit_names
                ):
                    issues.append(f"MoveIt2 member '{node.attr}' is not allowed by the capability contract.")

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, (ast.Constant, ast.UnaryOp)):
            value = _literal_number(node.value)
            for target in node.targets:
                if (
                    value is not None
                    and isinstance(target, ast.Attribute)
                    and target.attr in {"max_velocity", "max_acceleration"}
                ):
                    if value <= 0 or value > float(recommended_scaling):
                        issues.append(
                            f"{target.attr}={value:g} is outside the approved test scaling range "
                            f"(0, {recommended_scaling}]."
                        )

        if isinstance(node, ast.Attribute) and node.attr in forbidden:
            issues.append(f"Attribute '{node.attr}' is explicitly marked nonexistent/forbidden.")

        if isinstance(node, ast.ImportFrom) and node.module == "unittest.mock":
            issues.append("Mocking robot/controller APIs is forbidden by the capability contract.")

        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "now"
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "Time"
        ):
            issues.append("rclpy.time.Time.now() is not a valid ROS 2 clock API; use a bounded time.time() wait.")
        if (
            isinstance(node, ast.Call)
            and not node.args
            and not node.keywords
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "Time"
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "time"
        ):
            issues.append(
                "rclpy.time.Time() constructs the zero epoch and must not be used as an elapsed-time clock; "
                "use a bounded time.time() wait."
            )
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "spin_once"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id != "rclpy"
        ):
            issues.append("spin_once() belongs to rclpy, not to the controller/node instance.")

    return list(dict.fromkeys(issues))
