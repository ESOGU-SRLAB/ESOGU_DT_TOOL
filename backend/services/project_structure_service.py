"""Compact, execution-oriented project structure extraction.

The raw ``ast.dump`` representation is intentionally not exposed to the LLM: it
is large, unstable between Python versions, and contains details that do not
help test generation.  This module produces a small manifest of importable
modules and callable symbols that can be carried through scenario, test-case,
and test-code generation.
"""

from __future__ import annotations

import ast
import json
import os
from typing import Any, Dict, Iterable, List, Optional, Tuple


PROJECT_AST_SCHEMA = "stlc-project-ast/v1"
PROJECT_AST_FILE_TYPES = {"project ast", "project structure", "ast manifest"}


class ProjectStructureError(ValueError):
    """Raised when an uploaded project structure manifest is unusable."""


def is_project_structure_file(name: str, file_type: Optional[str] = None) -> bool:
    normalized_type = (file_type or "").strip().lower().replace("_", "-")
    normalized_name = os.path.basename(name or "").lower()
    return (
        normalized_type in PROJECT_AST_FILE_TYPES
        or normalized_name.endswith(".ast.json")
        or normalized_name in {"project_ast.json", "project-ast.json", "project_structure.json"}
    )


def _module_name(path: str) -> str:
    normalized = (path or "unknown.py").replace("\\", "/")
    if normalized.endswith(".py"):
        normalized = normalized[:-3]
    parts = [part for part in normalized.split("/") if part and part != "__init__"]
    return ".".join(parts) or "__init__"


def _expr_name(node: Optional[ast.AST]) -> str:
    if node is None:
        return ""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _expr_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Subscript):
        return _expr_name(node.value)
    if isinstance(node, ast.Constant):
        return repr(node.value)
    try:
        return ast.unparse(node)
    except Exception:
        return type(node).__name__


def _signature(node: ast.AST) -> str:
    args = node.args  # type: ignore[attr-defined]
    parts: List[str] = []
    positional = [*args.posonlyargs, *args.args]
    default_offset = len(positional) - len(args.defaults)
    for index, arg in enumerate(positional):
        text = arg.arg
        if arg.annotation:
            text += f": {_expr_name(arg.annotation)}"
        if index >= default_offset:
            text += f" = {_expr_name(args.defaults[index - default_offset])}"
        parts.append(text)
        if args.posonlyargs and index + 1 == len(args.posonlyargs):
            parts.append("/")
    if args.vararg:
        parts.append(f"*{args.vararg.arg}")
    elif args.kwonlyargs:
        parts.append("*")
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        text = arg.arg
        if arg.annotation:
            text += f": {_expr_name(arg.annotation)}"
        if default is not None:
            text += f" = {_expr_name(default)}"
        parts.append(text)
    if args.kwarg:
        parts.append(f"**{args.kwarg.arg}")
    result = f"({', '.join(parts)})"
    returns = getattr(node, "returns", None)
    if returns:
        result += f" -> {_expr_name(returns)}"
    return result


def _calls(node: ast.AST, limit: int = 40) -> List[str]:
    found: List[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            name = _expr_name(child.func)
            if name and name not in found:
                found.append(name)
                if len(found) >= limit:
                    break
    return found


def _callable(node: ast.AST) -> Dict[str, Any]:
    return {
        "name": node.name,  # type: ignore[attr-defined]
        "signature": _signature(node),
        "async": isinstance(node, ast.AsyncFunctionDef),
        "decorators": [_expr_name(item) for item in node.decorator_list],  # type: ignore[attr-defined]
        "calls": _calls(node),
        "line": getattr(node, "lineno", None),
    }


def _analyze_python_file(name: str, content: str) -> Dict[str, Any]:
    tree = ast.parse(content, filename=name)
    imports: List[str] = []
    classes: List[Dict[str, Any]] = []
    functions: List[Dict[str, Any]] = []
    constants: List[str] = []

    for node in tree.body:
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            prefix = "." * node.level + (node.module or "")
            imports.extend(f"{prefix}.{alias.name}".strip(".") for alias in node.names)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(_callable(node))
        elif isinstance(node, ast.ClassDef):
            methods = [
                _callable(item)
                for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            classes.append({
                "name": node.name,
                "bases": [_expr_name(base) for base in node.bases],
                "decorators": [_expr_name(item) for item in node.decorator_list],
                "methods": methods,
                "line": node.lineno,
            })
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                name_value = _expr_name(target)
                if name_value and not name_value.startswith("_"):
                    constants.append(name_value)

    return {
        "path": name,
        "module": _module_name(name),
        "imports": sorted(set(imports)),
        "classes": classes,
        "functions": functions,
        "public_constants": sorted(set(constants))[:50],
    }


def build_project_structure(files: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    analyzed: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    symbol_index: List[str] = []

    for item in files:
        name = str(item.get("name") or "unknown")
        content = item.get("content") or ""
        if not isinstance(content, str) or not name.lower().endswith(".py"):
            continue
        try:
            file_data = _analyze_python_file(name, content)
            analyzed.append(file_data)
            module = file_data["module"]
            symbol_index.extend(f"{module}.{fn['name']}" for fn in file_data["functions"])
            for cls in file_data["classes"]:
                symbol_index.append(f"{module}.{cls['name']}")
                symbol_index.extend(
                    f"{module}.{cls['name']}.{method['name']}" for method in cls["methods"]
                )
        except (SyntaxError, ValueError) as exc:
            errors.append({"path": name, "error": str(exc)})

    return {
        "schema_version": PROJECT_AST_SCHEMA,
        "language": "python" if analyzed else "unknown",
        "source": "generated",
        "files": analyzed,
        "symbol_index": sorted(set(symbol_index)),
        "parse_errors": errors,
        "summary": {
            "source_files": len(analyzed),
            "modules": len({item["module"] for item in analyzed}),
            "classes": sum(len(item["classes"]) for item in analyzed),
            "functions": sum(len(item["functions"]) for item in analyzed),
            "methods": sum(
                len(cls["methods"]) for item in analyzed for cls in item["classes"]
            ),
        },
    }


def parse_project_structure(raw: bytes | str, filename: str = "project_ast.json") -> Dict[str, Any]:
    try:
        text = raw.decode("utf-8-sig") if isinstance(raw, bytes) else raw
        data = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProjectStructureError(f"{filename} is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ProjectStructureError(f"{filename} must contain a JSON object")
    files = data.get("files")
    if not isinstance(files, list):
        raise ProjectStructureError(f"{filename} must contain a 'files' array")
    data.setdefault("schema_version", PROJECT_AST_SCHEMA)
    data["source"] = "uploaded"
    data.setdefault("symbol_index", [])
    data.setdefault("parse_errors", [])
    return data


def resolve_project_structure(
    source_files: Iterable[Dict[str, Any]],
    uploaded_manifest: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if uploaded_manifest:
        manifest = dict(uploaded_manifest)
        manifest["source"] = "uploaded"
        return manifest
    return build_project_structure(source_files)


def project_structure_prompt_context(
    manifest: Optional[Dict[str, Any]], max_chars: int = 24000
) -> str:
    if not manifest or not manifest.get("files"):
        return "No Python project AST manifest was available. Do not infer undeclared symbols."
    compact = json.dumps(manifest, ensure_ascii=False, separators=(",", ":"))
    if len(compact) > max_chars:
        compact = compact[:max_chars] + "\n... [project AST manifest truncated]"
    return compact


def validate_code_against_project_structure(
    code: str, manifest: Optional[Dict[str, Any]]
) -> List[str]:
    """Reject project imports/method calls that contradict the AST manifest.

    Validation is intentionally scoped to symbols imported from project modules;
    library calls such as ``pytest.raises`` are outside this contract.
    """
    if not manifest or not manifest.get("files"):
        return []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []  # The general code oracle reports syntax failures.

    module_symbols: Dict[str, set[str]] = {}
    class_methods: Dict[str, set[str]] = {}
    project_modules: set[str] = set()
    for file_data in manifest.get("files", []):
        module = file_data.get("module", "")
        if not module:
            continue
        project_modules.add(module)
        symbols = module_symbols.setdefault(module, set())
        for fn in file_data.get("functions", []):
            symbols.add(fn.get("name", ""))
        for cls in file_data.get("classes", []):
            class_name = cls.get("name", "")
            symbols.add(class_name)
            class_methods[class_name] = {
                method.get("name", "") for method in cls.get("methods", [])
            }

    issues: List[str] = []
    imported_classes: Dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        matching_module = next(
            (
                module for module in project_modules
                if node.module == module or node.module.endswith(f".{module}")
            ),
            None,
        )
        if not matching_module:
            continue
        allowed = module_symbols.get(matching_module, set())
        for alias in node.names:
            if alias.name == "*":
                issues.append(f"Wildcard import from project module '{node.module}' is not allowed.")
            elif alias.name not in allowed:
                issues.append(
                    f"Project symbol '{node.module}.{alias.name}' is absent from the Project AST manifest."
                )
            elif alias.name in class_methods:
                imported_classes[alias.asname or alias.name] = alias.name

    instances: Dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        constructor = _expr_name(node.value.func)
        class_name = imported_classes.get(constructor)
        if not class_name:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                instances[target.id] = class_name

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if isinstance(node.func.value, ast.Name) and node.func.value.id in instances:
            class_name = instances[node.func.value.id]
            if node.func.attr not in class_methods.get(class_name, set()):
                issues.append(
                    f"Method '{class_name}.{node.func.attr}' is absent from the Project AST manifest."
                )
    return sorted(set(issues))


EXECUTION_GROUNDING_RULES = """
## EXECUTION-GROUNDED TEST DESIGN CONTRACT
- Treat the Project AST manifest and supplied source as the authoritative callable surface.
- Reference concrete modules, classes, functions, methods, signatures, setup steps, and observable outputs.
- Never invent a function, method, fixture, topic, service, attribute, or return value.
- A scenario/test case is executable only when setup, action, and oracle can be expressed with declared symbols.
- Mark unsupported intent as ExecutionStatus=unsupported and explain the missing symbol/observable; do not substitute an unrelated action.
- Negative testing passes when the declared rejection/error behavior is observed; expected failure is an oracle, not an execution failure.
- Prefer deterministic state/result/error assertions. Do not use unconditional assertions, sleeps as oracles, or impossible timing/speed values.
""".strip()


def split_project_inputs(files: Iterable[Any]) -> Tuple[List[Any], Optional[Any]]:
    source_files: List[Any] = []
    manifest_file: Optional[Any] = None
    for item in files:
        name = getattr(item, "name", None) or getattr(item, "filename", None) or ""
        file_type = getattr(item, "type", None)
        if is_project_structure_file(name, file_type):
            manifest_file = item
        else:
            source_files.append(item)
    return source_files, manifest_file
