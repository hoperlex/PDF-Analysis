"""Executable enforcement for ALR-05 backend context boundaries."""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPOSITORY_ROOT / "src" / "auditmanager"

_EXEMPT_IMPORTERS = frozenset({"bootstrap", "shared"})
_EXEMPT_TARGETS = frozenset({"shared"})


@dataclass(frozen=True, slots=True)
class Violation:
    kind: str
    path: str
    line: int
    target: str

    def render(self) -> str:
        return f"{self.kind} {self.path}:{self.line} {self.target}"


def _importer_module(path: Path) -> str:
    relative = path.relative_to(SOURCE_ROOT)
    if relative.name == "__init__.py":
        parts = relative.parent.parts
    else:
        parts = relative.with_suffix("").parts
    return ".".join(("auditmanager", *parts))


def _resolved_from_module(node: ast.ImportFrom, path: Path) -> str:
    if node.level == 0:
        return node.module or ""

    importer = _importer_module(path)
    package = importer if path.name == "__init__.py" else importer.rpartition(".")[0]
    package_parts = package.split(".")
    retained = len(package_parts) - node.level + 1
    if retained < 1:
        return ""
    suffix = node.module.split(".") if node.module else []
    return ".".join((*package_parts[:retained], *suffix))


def _targets(node: ast.AST, path: Path) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    if not isinstance(node, ast.ImportFrom):
        return ()

    module = _resolved_from_module(node, path)
    if module == "auditmanager":
        return tuple(f"{module}.{alias.name}" for alias in node.names if alias.name != "*")
    return (module,) if module else ()


def _dynamic_target(
    node: ast.AST, module_aliases: set[str], function_aliases: set[str]
) -> str | None:
    if not isinstance(node, ast.Call) or not node.args:
        return None
    function = node.func
    is_import = (
        isinstance(function, ast.Attribute)
        and isinstance(function.value, ast.Name)
        and function.value.id in module_aliases
        and function.attr == "import_module"
    ) or (isinstance(function, ast.Name) and function.id in function_aliases)
    if is_import and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
        return node.args[0].value
    return None


def _violations() -> list[Violation]:
    violations: list[Violation] = []
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        relative = path.relative_to(SOURCE_ROOT)
        if len(relative.parts) < 2:
            continue
        importer = relative.parts[0]
        if importer in _EXEMPT_IMPORTERS:
            continue

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        module_aliases = {
            alias.asname or alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
            if alias.name == "importlib"
        }
        function_aliases = {
            alias.asname or alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module == "importlib"
            for alias in node.names
            if alias.name == "import_module"
        }
        for node in ast.walk(tree):
            targets = _targets(node, path)
            dynamic = _dynamic_target(node, module_aliases, function_aliases)
            if dynamic is not None:
                targets = (*targets, dynamic)
            for target in targets:
                parts = target.split(".")
                if len(parts) < 2 or parts[0] != "auditmanager":
                    continue
                target_context = parts[1]
                if target_context in _EXEMPT_TARGETS or target_context == importer:
                    continue
                if len(parts) == 3 and parts[2] == "public":
                    continue
                kind = "package-root" if len(parts) == 2 else "deep"
                violations.append(
                    Violation(
                        kind=kind,
                        path=path.relative_to(REPOSITORY_ROOT).as_posix(),
                        line=node.lineno,
                        target=target,
                    )
                )
    return violations


def test_backend_cross_context_imports_use_public_modules() -> None:
    assert SOURCE_ROOT.is_dir(), f"ALR-05 source root is absent: {SOURCE_ROOT}"
    violations = _violations()
    assert violations == [], "ALR-05 violations:\n" + "\n".join(
        violation.render() for violation in violations
    )


def test_literal_dynamic_cross_context_import_is_visible(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    source = root / "src" / "auditmanager"
    importer = source / "jobs" / "repository.py"
    importer.parent.mkdir(parents=True)
    importer.write_text(
        "import importlib as loader\n"
        "from importlib import import_module as load\n"
        "loader.import_module('auditmanager.storage.models')\n"
        "load('auditmanager.storage')\n"
        "load('auditmanager.storage.public')\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys.modules[__name__], "REPOSITORY_ROOT", root)
    monkeypatch.setattr(sys.modules[__name__], "SOURCE_ROOT", source)
    assert [(item.kind, item.target) for item in _violations()] == [
        ("deep", "auditmanager.storage.models"),
        ("package-root", "auditmanager.storage"),
    ]
