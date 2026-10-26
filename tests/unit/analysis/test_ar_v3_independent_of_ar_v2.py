"""ar_v3 and analysis.recognised do not depend on the recorded АР v2 package (PROD-10).

``ADR-0024`` section 2 removes АР v1 and v2 in ``PROD-11``. What v3 needed from ``ar_v2`` moved to
``ar_shared`` first (``PROD-10``), so the removal cannot break v3. This test reads the source of
``src/auditmanager`` with :mod:`ast` (it executes nothing) and holds that:

* no module under ``ar_v3/`` or ``analysis/recognised/`` imports ``ar_v2`` directly;
* none reaches it through a chain of runtime imports inside the analysis context (``ar_shared``,
  ``analysis.text`` and the rest of ``auditmanager.analysis``, plus ``auditmanager.shared``). A module
  of another bounded context that the closure imports is visited but not followed, and must itself
  neither import ``ar_v2`` nor take a v2 export of ``analysis.public``;
* ``auditmanager.analysis.public`` is a sink, not followed. It re-exports the v2 surface for the
  executor, and other contexts import it (``norms.references.text_pages`` for one), so merely
  reaching it is not a dependency on v2. What is forbidden is a module in the closure importing
  a *v2 export* of that module, by name or by ``*``;
* ``analysis.public`` is the only module outside ``ar_v2`` that imports ``ar_v2`` at all, so the sink
  list is complete and a new importer is caught here.

Limits, stated because they bound what is proved. Imports under ``if TYPE_CHECKING:`` never run and
are skipped; imports inside functions do run and are kept; the implicit execution of a parent
package's ``__init__`` is not an edge; ``importlib`` calls are not followed. **The whole-repository
closure is not clean and cannot be before ``PROD-11``**: ``ar_v3.citation_grounding`` imports
``norms.public``, which reaches ``jobs.public``, ``runs.public``, ``runs.executor``, the
``runs.recorded_v2_*`` modules and so ``analysis.public``; and importing any module below
``auditmanager.analysis`` runs ``auditmanager/analysis/__init__.py``, which imports
``analysis.public``, so ``ar_v2`` is loaded at run time. Both dissolve when ``PROD-11`` removes the v2
exports of ``analysis.public`` and the recorded-v2 modules; it deletes ``ar_v2`` and ``_SINKS`` here.

Each guard has a test that feeds it a mutated copy of the real sources and expects a violation.
"""

from __future__ import annotations

import ast
from collections import deque
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
V2_PACKAGE = "auditmanager.analysis.profiles.ar_v2"
ROOT_PACKAGES = (
    "auditmanager.analysis.profiles.ar_v3",
    "auditmanager.analysis.recognised",
)
_SINKS = frozenset({"auditmanager.analysis.public"})
_PUBLIC_SURFACES = frozenset({"auditmanager.analysis.public", "auditmanager.analysis"})
_FOLLOWED = ("auditmanager.analysis", "auditmanager.shared")


def _under(module: str, package: str) -> bool:
    return module == package or module.startswith(package + ".")


@dataclass(frozen=True, slots=True)
class _Source:
    text: str
    is_package: bool


@dataclass(slots=True)
class _Graph:
    sources: dict[str, _Source]
    modules: frozenset[str]
    edges: dict[str, set[str]] = field(default_factory=dict)
    raw_targets: dict[str, set[str]] = field(default_factory=dict)
    from_imports: dict[str, list[tuple[str, tuple[str, ...]]]] = field(default_factory=dict)


@lru_cache(maxsize=1)
def _real_sources() -> dict[str, _Source]:
    found: dict[str, _Source] = {}
    for path in (SOURCE_ROOT / "auditmanager").rglob("*.py"):
        parts = list(path.relative_to(SOURCE_ROOT).with_suffix("").parts)
        is_package = parts[-1] == "__init__"
        if is_package:
            parts = parts[:-1]
        found[".".join(parts)] = _Source(path.read_text(encoding="utf-8"), is_package)
    return found


@lru_cache(maxsize=None)
def _runtime_imports(text: str) -> tuple[ast.Import | ast.ImportFrom, ...]:
    tree = ast.parse(text)
    guarded: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test = node.test
            name = test.id if isinstance(test, ast.Name) else getattr(test, "attr", "")
            if name == "TYPE_CHECKING":
                for statement in node.body:
                    guarded.update(id(inner) for inner in ast.walk(statement))
    return tuple(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom)) and id(node) not in guarded
    )


def _resolve(node: ast.ImportFrom, module: str, is_package: bool) -> str:
    if not node.level:
        return node.module or ""
    package = module.split(".")
    if not is_package:
        package = package[:-1]
    package = package[: len(package) - (node.level - 1)]
    return ".".join(package + ([node.module] if node.module else []))


def _nearest_module(name: str, modules: frozenset[str]) -> str | None:
    parts = name.split(".")
    while parts:
        candidate = ".".join(parts)
        if candidate in modules:
            return candidate
        parts.pop()
    return None


def _build(sources: dict[str, _Source]) -> _Graph:
    graph = _Graph(sources=sources, modules=frozenset(sources))
    for module, source in sources.items():
        edges: set[str] = set()
        raw: set[str] = set()
        from_imports: list[tuple[str, tuple[str, ...]]] = []
        for node in _runtime_imports(source.text):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    raw.add(alias.name)
                    target = _nearest_module(alias.name, graph.modules)
                    if target:
                        edges.add(target)
                continue
            base = _resolve(node, module, source.is_package)
            names = tuple(alias.name for alias in node.names)
            from_imports.append((base, names))
            raw.add(base)
            target = _nearest_module(base, graph.modules)
            if target:
                edges.add(target)
            for name in names:
                raw.add(f"{base}.{name}")
                if f"{base}.{name}" in graph.modules:
                    edges.add(f"{base}.{name}")
        graph.edges[module] = edges
        graph.raw_targets[module] = raw
        graph.from_imports[module] = from_imports
    return graph


def _roots(graph: _Graph) -> list[str]:
    return sorted(m for m in graph.modules if any(_under(m, p) for p in ROOT_PACKAGES))


def _direct_violations(graph: _Graph) -> list[str]:
    return [
        f"{module} imports {target}"
        for module in _roots(graph)
        for target in sorted(graph.raw_targets[module])
        if _under(target, V2_PACKAGE)
    ]


def _followed(module: str) -> bool:
    return module not in _SINKS and any(_under(module, p) for p in _FOLLOWED)


def _closure(graph: _Graph) -> dict[str, str | None]:
    """Modules reachable from the roots over runtime imports, mapped to their predecessor.

    Modules outside the analysis context and the sinks are visited, not followed.
    """
    seen: dict[str, str | None] = {root: None for root in _roots(graph)}
    queue = deque(seen)
    while queue:
        module = queue.popleft()
        if not _followed(module):
            continue
        for target in sorted(graph.edges.get(module, ())):
            if target not in seen:
                seen[target] = module
                queue.append(target)
    return seen


def _chain(seen: dict[str, str | None], end: str) -> str:
    chain: list[str] = []
    cursor: str | None = end
    while cursor is not None:
        chain.append(cursor)
        cursor = seen[cursor]
    return " <- ".join(chain)


def _transitive_violations(graph: _Graph) -> list[str]:
    seen = _closure(graph)
    found = [f"reaches v2: {_chain(seen, m)}" for m in sorted(seen) if _under(m, V2_PACKAGE)]
    found += [
        f"{m} (outside the analysis context) imports {t}: {_chain(seen, m)}"
        for m in sorted(seen)
        if not _followed(m) and m not in _SINKS and not _under(m, V2_PACKAGE)
        for t in sorted(graph.raw_targets[m])
        if _under(t, V2_PACKAGE)
    ]
    return found


def _v2_exports_of_public(graph: _Graph) -> frozenset[str]:
    """Names ``analysis.public`` binds from an ``ar_v2`` module."""
    names: set[str] = set()
    for node in _runtime_imports(graph.sources["auditmanager.analysis.public"].text):
        if isinstance(node, ast.ImportFrom) and _under(node.module or "", V2_PACKAGE):
            names.update(alias.asname or alias.name for alias in node.names)
    return frozenset(names)


def _export_violations(graph: _Graph) -> list[str]:
    exports = _v2_exports_of_public(graph)
    seen = _closure(graph)
    found: list[str] = []
    for module in sorted(seen):
        for base, names in graph.from_imports.get(module, ()):
            if base in _PUBLIC_SURFACES:
                used = sorted(n for n in names if n in exports or n == "*")
                if used:
                    found.append(f"{module} takes {used} from {base} ({_chain(seen, module)})")
    return found


def _outside_importers(graph: _Graph) -> list[str]:
    return sorted(
        module
        for module in graph.modules
        if not _under(module, V2_PACKAGE)
        and any(_under(target, V2_PACKAGE) for target in graph.raw_targets[module])
    )


@lru_cache(maxsize=1)
def _real_graph() -> _Graph:
    return _build(_real_sources())


def _mutated(module: str, appended: str) -> dict[str, _Source]:
    sources = dict(_real_sources())
    sources[module] = _Source(sources[module].text + "\n" + appended + "\n", sources[module].is_package)
    return sources


# --- the guards on the real tree -------------------------------------------------------------


def test_the_graph_covers_the_modules_the_guards_are_about() -> None:
    graph = _real_graph()
    roots = _roots(graph)
    assert "auditmanager.analysis.profiles.ar_v3.v3_profile" in roots
    assert "auditmanager.analysis.recognised.region_candidate" in roots
    assert len(roots) >= 15
    assert V2_PACKAGE + ".registered" in graph.modules
    assert "auditmanager.analysis.profiles.ar_shared.content" in graph.modules


def test_no_ar_v3_or_recognised_module_imports_ar_v2_directly() -> None:
    assert _direct_violations(_real_graph()) == []


def test_no_runtime_import_chain_from_ar_v3_or_recognised_reaches_ar_v2_except_through_the_sink() -> None:
    assert _transitive_violations(_real_graph()) == []


def test_nothing_in_the_closure_takes_a_v2_export_of_analysis_public() -> None:
    graph = _real_graph()
    assert _v2_exports_of_public(graph) >= {"resolve_recorded_profile", "RecordedProfileError"}
    assert _export_violations(graph) == []


def test_only_the_named_sink_imports_ar_v2_from_outside_it() -> None:
    assert set(_outside_importers(_real_graph())) <= _SINKS


def test_the_moved_names_left_no_shim_in_ar_v2() -> None:
    package = SOURCE_ROOT / "auditmanager" / "analysis" / "profiles" / "ar_v2"
    assert sorted(p.name for p in package.glob("*.md")) == []
    for name in ("content", "recognised_context", "grounding"):
        assert not (package / f"{name}.py").exists(), name
    from auditmanager.analysis.profiles.ar_v2 import registered

    assert not hasattr(registered, "PROFILE_ID")
    assert not hasattr(registered, "PROMPT_BUNDLE_ID")


# --- every guard can fail: the same checks on a mutated copy of the real sources -------------


def test_a_direct_import_added_to_ar_v3_is_found() -> None:
    graph = _build(
        _mutated(
            "auditmanager.analysis.profiles.ar_v3.prompt_material",
            "from auditmanager.analysis.profiles.ar_v2.registered import PROFILE_ID",
        )
    )
    assert _direct_violations(graph) == [
        "auditmanager.analysis.profiles.ar_v3.prompt_material imports "
        "auditmanager.analysis.profiles.ar_v2.registered",
        "auditmanager.analysis.profiles.ar_v3.prompt_material imports "
        "auditmanager.analysis.profiles.ar_v2.registered.PROFILE_ID",
    ]
    assert _transitive_violations(graph) != []


def test_a_relative_import_of_ar_v2_in_recognised_is_found() -> None:
    graph = _build(
        _mutated(
            "auditmanager.analysis.recognised.flags", "from ..profiles.ar_v2 import response_schema"
        )
    )
    assert _direct_violations(graph) != []


def test_a_chain_through_a_module_outside_both_packages_is_found() -> None:
    sources = _mutated(
        "auditmanager.analysis.profiles.ar_shared.content",
        "from auditmanager.analysis.profiles.ar_v2.response_schema import CATEGORIES",
    )
    graph = _build(sources)
    assert _direct_violations(graph) == []
    found = _transitive_violations(graph)
    assert any("ar_v2.response_schema <- ar_shared.content" in line.replace("auditmanager.analysis.profiles.", "") for line in found)
    assert "auditmanager.analysis.profiles.ar_shared.content" in _outside_importers(graph)


def test_a_v2_export_taken_from_analysis_public_by_a_recognised_module_is_found() -> None:
    graph = _build(
        _mutated(
            "auditmanager.analysis.recognised.flags",
            "from auditmanager.analysis.public import resolve_recorded_profile",
        )
    )
    assert _direct_violations(graph) == []
    assert _transitive_violations(graph) == []
    violations = _export_violations(graph)
    assert len(violations) == 1 and "resolve_recorded_profile" in violations[0]


def test_a_v2_export_taken_through_the_analysis_package_is_found() -> None:
    graph = _build(
        _mutated(
            "auditmanager.analysis.profiles.ar_v3.scope_partition",
            "from auditmanager.analysis import RecordedProfileError",
        )
    )
    assert any("RecordedProfileError" in line for line in _export_violations(graph))


def test_a_new_importer_of_ar_v2_outside_the_sink_is_found() -> None:
    graph = _build(
        _mutated(
            "auditmanager.norms.public",
            "from auditmanager.analysis.profiles.ar_v2.response_schema import CATEGORIES",
        )
    )
    assert not set(_outside_importers(graph)) <= _SINKS
    # norms.public is imported by ar_v3.set_input, so the chain is also a transitive finding.
    assert _transitive_violations(graph) != []


def test_a_guarded_type_checking_import_is_not_an_edge() -> None:
    graph = _build(
        _mutated(
            "auditmanager.analysis.profiles.ar_v3.scope_partition",
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n"
            "    from auditmanager.analysis.profiles.ar_v2.registered import PROFILE_ID",
        )
    )
    assert _direct_violations(graph) == []
