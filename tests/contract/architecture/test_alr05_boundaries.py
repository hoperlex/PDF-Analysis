"""Executable enforcement for ALR-05 backend context boundaries."""

from __future__ import annotations

import ast
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
        for node in ast.walk(tree):
            for target in _targets(node, path):
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
