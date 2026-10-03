"""Deterministic quality oracle for generated executable test code."""

import ast
import re
from typing import Any, Dict, List

from utils.standalone_test_validation import validate_standalone_python


ORACLE_PROMPT_REQUIREMENTS = """
## GENERATION ORACLE ACCEPTANCE CRITERIA (MANDATORY):
- Produce syntactically valid, complete code with no TODO, FIXME, `pass`, ellipsis, or NotImplementedError placeholders.
- Include an executable test entry point: a pytest `test_*` function, a test class, a guarded `main`, or explicit top-level test execution.
- Include at least one observable verification that can decide pass/fail, such as `assert`, `pytest.raises`, or a framework assertion method.
- A sequence of robot actions or `print` statements alone is not a test oracle; verify an observable final state, response, pose, collision result, or raised error.
- Every referenced name must be explicitly imported or defined; do not mix a from-import with use of an unbound module name.
- ROS setup must have bounded execution and deterministic cleanup in finally; never use unbounded executor spins, while-rclpy-ok loops, or ROS rate sleeps in a test.
""".strip()


def _check(name: str, passed: bool, details: str) -> Dict[str, Any]:
    return {"name": name, "passed": passed, "details": details}


def _has_main_guard(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id == "__name__"
            and any(isinstance(item, ast.Constant) and item.value == "__main__" for item in test.comparators)
        ):
            return True
    return False


def _has_verification(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            return True
        if isinstance(node, ast.Raise):
            raised = node.exc
            if isinstance(raised, ast.Call):
                raised = raised.func
            if isinstance(raised, ast.Name) and raised.id in {"AssertionError", "pytest.fail"}:
                return True
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
            if name.startswith("assert") or name in {"raises", "fail"}:
                return True
    return False


def _ineffective_assertion_issues(tree: ast.AST) -> List[str]:
    issues: List[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assert)
            and isinstance(node.test, ast.Constant)
            and node.test.value is True
        ):
            issues.append(
                f"Unconditional `assert True` at line {node.lineno} does not verify system behaviour."
            )
    return issues


def _has_entry_point(tree: ast.Module) -> bool:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            return True
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            return True
        if isinstance(node, (ast.Expr, ast.Assign, ast.AnnAssign, ast.For, ast.While, ast.With, ast.Try)):
            return True
    return _has_main_guard(tree)


def _placeholder_issues(code: str, tree: ast.AST) -> List[str]:
    issues: List[str] = []
    if re.search(r"(?im)^\s*#?\s*(TODO|FIXME)\b", code):
        issues.append("TODO/FIXME placeholder remains in generated code.")
    for node in ast.walk(tree):
        if isinstance(node, ast.Pass):
            issues.append(f"`pass` placeholder at line {node.lineno}.")
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and node.value.value is Ellipsis:
            issues.append(f"Ellipsis placeholder at line {node.lineno}.")
        elif isinstance(node, ast.Raise):
            raised = node.exc
            if isinstance(raised, ast.Call) and isinstance(raised.func, ast.Name) and raised.func.id == "NotImplementedError":
                issues.append(f"NotImplementedError placeholder at line {node.lineno}.")
    return issues


def evaluate_test_code(
    code: str,
    language: str = "python",
    *,
    allow_legacy_sim_robot_goal: bool = False,
) -> Dict[str, Any]:
    """Evaluate whether generated code meets deterministic execution-oracle rules."""
    normalized_language = (language or "python").strip().lower()
    checks: List[Dict[str, Any]] = []
    issues: List[str] = []
    warnings: List[str] = []

    if not code or not code.strip():
        checks.append(_check("non_empty", False, "Generated code is empty."))
        return {"passed": False, "verdict": "fail", "score": 0, "checks": checks, "issues": ["Generated code is empty."], "warnings": []}
    checks.append(_check("non_empty", True, "Generated code is not empty."))

    if normalized_language not in {"python", "py", "python3"}:
        placeholder_found = bool(re.search(r"(?im)\b(TODO|FIXME|NotImplementedException)\b", code))
        checks.append(_check("no_placeholders", not placeholder_found, "No obvious placeholders found." if not placeholder_found else "Placeholder text found."))
        if placeholder_found:
            issues.append("Generated code contains placeholder text.")
        warnings.append(f"Deterministic compiler/oracle checks are not implemented for {language}.")
        passed = not issues
        score = round(100 * sum(item["passed"] for item in checks) / len(checks))
        return {"passed": passed, "verdict": "pass_with_warnings" if passed else "fail", "score": score, "checks": checks, "issues": issues, "warnings": warnings}

    try:
        tree = ast.parse(code)
        compile(code, "<generated_test>", "exec")
        checks.append(_check("syntax", True, "Python AST parsing and bytecode compilation succeeded."))
    except SyntaxError as exc:
        message = f"Python syntax error at line {exc.lineno}: {exc.msg}"
        checks.append(_check("syntax", False, message))
        issues.append(message)
        score = round(100 * sum(item["passed"] for item in checks) / len(checks))
        return {"passed": False, "verdict": "fail", "score": score, "checks": checks, "issues": issues, "warnings": warnings}

    standalone_issues = validate_standalone_python(
        code,
        allow_legacy_sim_robot_goal=allow_legacy_sim_robot_goal,
    )
    checks.append(_check("single_file_contract", not standalone_issues, "Single-file imports are valid." if not standalone_issues else " ".join(standalone_issues)))
    issues.extend(standalone_issues)

    has_entry = _has_entry_point(tree)
    checks.append(_check("entry_point", has_entry, "Executable test entry point found." if has_entry else "No test function, test class, guarded main, or top-level execution found."))
    if not has_entry:
        issues.append("Generated code has no executable test entry point.")

    has_verification = _has_verification(tree)
    checks.append(_check("observable_verification", has_verification, "Pass/fail verification found." if has_verification else "No assert, framework assertion, pytest.raises, or explicit failure found."))
    if not has_verification:
        issues.append("Generated code performs actions but has no observable pass/fail verification.")

    placeholder_issues = _placeholder_issues(code, tree)
    checks.append(_check("no_placeholders", not placeholder_issues, "No incomplete placeholders found." if not placeholder_issues else " ".join(placeholder_issues)))
    issues.extend(placeholder_issues)

    ineffective_issues = _ineffective_assertion_issues(tree)
    checks.append(_check(
        "effective_assertions",
        not ineffective_issues,
        "Assertions depend on observable behaviour."
        if not ineffective_issues else " ".join(ineffective_issues),
    ))
    issues.extend(ineffective_issues)

    passed = not issues
    score = round(100 * sum(item["passed"] for item in checks) / len(checks))
    return {"passed": passed, "verdict": "pass" if passed else "fail", "score": score, "checks": checks, "issues": issues, "warnings": warnings}
