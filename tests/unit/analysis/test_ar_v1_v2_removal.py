"""АР v1 and v2 stay removed (`PROD-11-AR-V1-V2-REMOVAL-01`, `ADR-0024` section 2, `AD-12`).

`PROD-10` moved what АР v3 needs out of the recorded v2 package, and its guard
(`test_ar_v3_independent_of_ar_v2.py`, deleted here) proved that nothing in v3 imported it. This task
deleted the package, the recorded v2 path and the АР v1 registration, so the guard that matters now
is the converse: **nothing comes back**. The test reads the repository with :mod:`ast` (it executes
nothing) and holds that

* the removed files are absent;
* no Python file of ``src``, ``tests``, ``tools`` or ``scripts`` imports a removed module, by any
  spelling (absolute, relative, ``from package import submodule``, inside a function, under
  ``TYPE_CHECKING``);
* none of the three public surfaces that used to re-export the v2 path (``analysis.public``,
  ``findings.public``, ``runs.executor``) lists a removed name, and no file takes one from them;
* ``AR_TEXT_PROFILE`` and ``resolve_profile`` appear nowhere in ``src`` (as a name, an attribute, an
  import alias or an ``__all__`` string);
* the two defaults the removal took away stay away: ``run_text_analysis`` has no default ``profile``
  and the executor refuses an unrouted non-v3 run instead of running АР for it.

Each guard has a test that feeds it a mutated copy of the real sources and expects the violation, so
a guard that cannot fail is caught here (the report holds the table of mutations of the real files).
"""

from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
SCANNED = ("src", "tests", "tools", "scripts")

#: Files and directories this task deleted.
REMOVED_PATHS = (
    "src/auditmanager/analysis/profiles/ar_v2",
    "src/auditmanager/runs/recorded_v2_merge.py",
    "src/auditmanager/runs/recorded_v2_publication.py",
    "src/auditmanager/runs/recorded_v2_sources.py",
    "src/auditmanager/runs/recorded_v2_stage.py",
    "src/auditmanager/findings/v2_publication.py",
    "src/auditmanager/findings/v2_recorded.py",
    "src/auditmanager/findings/recorded_saved_plan.py",
    "src/auditmanager/findings/merge_publication_plan.py",
    "src/auditmanager/analysis/stages/finding_merge.py",
    "tools/evaluation/bridge.py",
    "tools/evaluation/run_sources.py",
    "tools/evaluation/local_bundle.py",
)

#: The same files as dotted module names (``tools/evaluation`` is imported as ``evaluation``).
REMOVED_MODULES = (
    "auditmanager.analysis.profiles.ar_v2",
    "auditmanager.runs.recorded_v2_merge",
    "auditmanager.runs.recorded_v2_publication",
    "auditmanager.runs.recorded_v2_sources",
    "auditmanager.runs.recorded_v2_stage",
    "auditmanager.findings.v2_publication",
    "auditmanager.findings.v2_recorded",
    "auditmanager.findings.recorded_saved_plan",
    "auditmanager.findings.merge_publication_plan",
    "auditmanager.analysis.stages.finding_merge",
    "evaluation.bridge",
    "evaluation.run_sources",
    "evaluation.local_bundle",
)

#: The v2 exports of the three public surfaces, and the executor's v2 entry points.
REMOVED_EXPORTS = frozenset({
    "AR_V2_CATEGORIES", "AR_V2_SEVERITIES", "AR_V2_RECORDED_PROFILE_ID", "AR_V2_RECORDED_BUNDLE_ID",
    "BuiltRecordedArtifact", "FinishedV2Response", "MERGE_ARTIFACT_ROLE", "MERGE_ARTIFACT_VERSION",
    "MERGE_RULE_VERSION", "MergePreparation", "ProposalGroundingResult", "RECORDED_OBSERVATION_ARTIFACT_ROLE",
    "RECORDED_OBSERVATION_ARTIFACT_VERSION", "RecordedArtifactError", "RecordedCallFacts",
    "RecordedGenerationSettings", "RecordedMergeInput", "RecordedProfileError", "RecordedReplayResult",
    "RecordedV2Input", "RejectedProposal", "build_recorded_call_facts", "build_recorded_observation_artifact",
    "finish_response", "merge_grounded", "prepare_merge", "prepare_recorded_v2_input",
    "read_recorded_merge_input", "replay_recorded_response", "resolve_recorded_profile",
    "seal_recorded_v2_stage_result", "SavedRecordedPublicationPlan", "V2PublicationContext",
    "V2PublicationResult", "plan_recorded_saved_publication", "publish_v2_merge_plan",
    "RecordedV2ExecutionIntent", "plan_recorded_v2_execution",
})
PUBLIC_SURFACES = (
    "src/auditmanager/analysis/public.py",
    "src/auditmanager/findings/public.py",
    "src/auditmanager/runs/executor.py",
)
SURFACE_MODULES = frozenset({
    "auditmanager.analysis.public", "auditmanager.analysis", "auditmanager.findings.public",
    "auditmanager.findings", "auditmanager.runs.executor", "auditmanager.runs",
})

#: Names that must not appear anywhere in ``src``.
REMOVED_SRC_NAMES = frozenset({"AR_TEXT_PROFILE", "resolve_profile"})


@dataclass(frozen=True, slots=True)
class Source:
    path: str       # repository-relative, posix
    module: str     # dotted name for src files, "" otherwise
    is_package: bool
    text: str


def _module_of(relative: str) -> tuple[str, bool]:
    if not relative.startswith("src/") or not relative.endswith(".py"):
        return "", False
    parts = list(Path(relative[len("src/"):]).with_suffix("").parts)
    is_package = parts[-1] == "__init__"
    if is_package:
        parts = parts[:-1]
    return ".".join(parts), is_package


@lru_cache(maxsize=1)
def _real_sources() -> tuple[Source, ...]:
    found: list[Source] = []
    for area in SCANNED:
        for path in sorted((REPOSITORY_ROOT / area).rglob("*.py")):
            relative = path.relative_to(REPOSITORY_ROOT).as_posix()
            if "/node_modules/" in relative or "/__pycache__/" in relative:
                continue
            module, is_package = _module_of(relative)
            found.append(Source(relative, module, is_package, path.read_text(encoding="utf-8")))
    return tuple(found)


@lru_cache(maxsize=None)
def _parse(text: str) -> ast.Module:
    """One parse per distinct text: the mutated copies share every file but the one they change."""
    return ast.parse(text)


def _resolve(node: ast.ImportFrom, module: str, is_package: bool) -> str:
    if not node.level:
        return node.module or ""
    package = module.split(".") if module else []
    if not is_package:
        package = package[:-1]
    package = package[: len(package) - (node.level - 1)]
    return ".".join(package + ([node.module] if node.module else []))


def _under(name: str, prefix: str) -> bool:
    return name == prefix or name.startswith(prefix + ".")


@lru_cache(maxsize=None)
def _imports(text: str, module: str, is_package: bool) -> tuple[tuple[int, str, str | None], ...]:
    found: list[tuple[int, str, str | None]] = []
    for node in ast.walk(_parse(text)):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name, None) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = _resolve(node, module, is_package)
            found.extend((node.lineno, base, alias.name) for alias in node.names)
    return tuple(found)


def imports_of(source: Source) -> tuple[tuple[int, str, str | None], ...]:
    """``(line, module, imported name or None)`` of every import statement, wherever it is."""
    return _imports(source.text, source.module, source.is_package)


def removed_module_imports(sources: tuple[Source, ...]) -> list[str]:
    """Every import of a removed module, by any spelling, as ``path:line: module``."""
    violations: list[str] = []
    for source in sources:
        for line, base, name in imports_of(source):
            candidates = [base] + ([f"{base}.{name}"] if name else [])
            for candidate in candidates:
                if any(_under(candidate, removed) for removed in REMOVED_MODULES):
                    violations.append(f"{source.path}:{line}: {candidate}")
                    break
    return violations


def removed_names_taken_from_surfaces(sources: tuple[Source, ...]) -> list[str]:
    violations: list[str] = []
    for source in sources:
        for line, base, name in imports_of(source):
            if base in SURFACE_MODULES and name in REMOVED_EXPORTS:
                violations.append(f"{source.path}:{line}: {base}.{name}")
    return violations


def surfaces_listing_a_removed_name(sources: tuple[Source, ...]) -> list[str]:
    violations: list[str] = []
    for source in sources:
        if source.path not in PUBLIC_SURFACES:
            continue
        for node in ast.walk(_parse(source.text)):
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets
            ) and isinstance(node.value, (ast.List, ast.Tuple)):
                for element in node.value.elts:
                    if isinstance(element, ast.Constant) and element.value in REMOVED_EXPORTS:
                        violations.append(f"{source.path}: __all__ lists {element.value}")
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in REMOVED_EXPORTS:
                violations.append(f"{source.path}:{node.lineno}: defines {node.name}")
    return violations


def removed_names_in_src(sources: tuple[Source, ...]) -> list[str]:
    violations: list[str] = []
    for source in sources:
        if not source.path.startswith("src/"):
            continue
        for node in ast.walk(_parse(source.text)):
            hit = None
            if isinstance(node, ast.Name) and node.id in REMOVED_SRC_NAMES:
                hit = node.id
            elif isinstance(node, ast.Attribute) and node.attr in REMOVED_SRC_NAMES:
                hit = node.attr
            elif isinstance(node, ast.alias) and node.name in REMOVED_SRC_NAMES:
                hit = node.name
            elif isinstance(node, ast.Constant) and node.value in REMOVED_SRC_NAMES:
                hit = str(node.value)
            elif isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in REMOVED_SRC_NAMES:
                hit = node.name
            if hit is not None:
                violations.append(f"{source.path}:{getattr(node, 'lineno', 0)}: {hit}")
    return violations


# --- the real tree --------------------------------------------------------------------------


def test_the_removed_files_are_absent() -> None:
    assert [path for path in REMOVED_PATHS if (REPOSITORY_ROOT / path).exists()] == []


def test_no_python_file_imports_a_removed_module() -> None:
    assert removed_module_imports(_real_sources()) == []


def test_no_file_takes_a_removed_name_from_a_public_surface_and_none_lists_one() -> None:
    assert removed_names_taken_from_surfaces(_real_sources()) == []
    assert surfaces_listing_a_removed_name(_real_sources()) == []


def test_the_ar_v1_profile_constant_and_its_resolver_are_gone_from_src() -> None:
    assert removed_names_in_src(_real_sources()) == []


def test_the_guard_reads_the_whole_tree() -> None:
    """A scan that read nothing would pass every guard above."""
    paths = {source.path for source in _real_sources()}
    assert len(paths) > 1000
    for expected in (
        "src/auditmanager/runs/executor.py",
        "src/auditmanager/analysis/public.py",
        "tests/unit/analysis/test_ar_v1_v2_removal.py",
        "tools/evaluation/matcher.py",
    ):
        assert expected in paths


def test_run_text_analysis_has_no_default_profile() -> None:
    from auditmanager.analysis.text.stage import run_text_analysis

    assert inspect.signature(run_text_analysis).parameters["profile"].default is inspect.Parameter.empty


def test_an_unrouted_run_is_refused_not_given_the_ar_profile() -> None:
    from auditmanager.runs.executor import _pinned_text_profile
    from auditmanager.shared.errors import DomainError, ErrorCode

    run = type("Run", (), {
        "analysis_profile_id": "ap_01M25P3TH08VVTTGJRXYBZZ7RP",
        "prompt_bundle_id": "pb_01M25P3TH0PDQYVKTRQFEM0CYS",
    })()
    with pytest.raises(DomainError) as refused:
        _pinned_text_profile(run, None)  # type: ignore[arg-type]
    assert refused.value.code is ErrorCode.REQUIRED_NORM_UNAVAILABLE


def test_the_executor_has_no_recorded_v2_parameters() -> None:
    from auditmanager.runs import executor

    parameters = inspect.signature(executor.execute_run).parameters
    assert "recorded_fixture_model_id" not in parameters
    assert "recorded_generation_settings" not in parameters
    assert not hasattr(executor, "plan_recorded_v2_execution")


# --- each guard can fail: mutated copies of the real sources ---------------------------------


def _with(sources: tuple[Source, ...], path: str, extra: str) -> tuple[Source, ...]:
    out = []
    for source in sources:
        out.append(Source(source.path, source.module, source.is_package, source.text + "\n" + extra)
                   if source.path == path else source)
    assert any(source.path == path for source in sources), path
    return tuple(out)


@pytest.mark.parametrize(
    ("extra", "needle"),
    [
        ("from auditmanager.analysis.profiles.ar_v2.registered import PROFILE_ID", "ar_v2.registered"),
        ("from auditmanager.analysis.profiles import ar_v2", "ar_v2"),
        ("import auditmanager.runs.recorded_v2_stage", "recorded_v2_stage"),
        ("from auditmanager.runs import recorded_v2_merge", "recorded_v2_merge"),
        ("from .v2_publication import publish_v2_merge_plan", "v2_publication"),
        ("from auditmanager.findings.recorded_saved_plan import x", "recorded_saved_plan"),
        ("def f():\n    from auditmanager.analysis.stages.finding_merge import merge_grounded", "finding_merge"),
    ],
)
def test_a_removed_module_imported_back_is_found(extra: str, needle: str) -> None:
    mutated = _with(_real_sources(), "src/auditmanager/findings/public.py", extra)
    found = removed_module_imports(mutated)
    assert found and any(needle in item for item in found), found


def test_a_relative_import_of_a_removed_module_is_found_in_its_own_package() -> None:
    mutated = _with(_real_sources(), "src/auditmanager/runs/executor.py", "from .recorded_v2_stage import run")
    assert any("recorded_v2_stage" in item for item in removed_module_imports(mutated))


def test_an_import_in_a_test_a_tool_or_a_script_is_found() -> None:
    for path in ("tests/unit/analysis/test_text_profile_registry.py", "tools/evaluation/matcher.py"):
        mutated = _with(
            _real_sources(), path, "from auditmanager.analysis.profiles.ar_v2.response import ParsedResponse"
        )
        assert removed_module_imports(mutated), path


def test_a_removed_export_taken_back_or_listed_is_found() -> None:
    taken = _with(
        _real_sources(), "src/auditmanager/findings/queries.py",
        "from auditmanager.analysis.public import AR_V2_RECORDED_PROFILE_ID",
    )
    assert removed_names_taken_from_surfaces(taken)
    listed = _with(
        _real_sources(), "src/auditmanager/analysis/public.py", '__all__ = ["AR_V2_CATEGORIES", "ARTIFACT_ROLE"]'
    )
    assert surfaces_listing_a_removed_name(listed)
    defined = _with(
        _real_sources(), "src/auditmanager/runs/executor.py", "def plan_recorded_v2_execution():\n    pass"
    )
    assert surfaces_listing_a_removed_name(defined)


@pytest.mark.parametrize(
    "extra",
    [
        "AR_TEXT_PROFILE = None",
        "x = something.AR_TEXT_PROFILE",
        "from somewhere import resolve_profile",
        "def resolve_profile():\n    pass",
        '__all__ = ["AR_TEXT_PROFILE"]',
    ],
)
def test_the_ar_profile_constant_or_resolver_back_in_src_is_found(extra: str) -> None:
    mutated = _with(_real_sources(), "src/auditmanager/analysis/text/profile.py", extra)
    assert removed_names_in_src(mutated)


def test_the_same_name_in_a_test_is_not_a_violation_of_the_src_guard() -> None:
    """The reference profile of the tests may keep a vocabulary of its own; only ``src`` is held."""
    mutated = _with(_real_sources(), "tests/unit/analysis/test_text_profile_registry.py", "AR_TEXT_PROFILE = 1")
    assert removed_names_in_src(mutated) == []


def test_a_scan_with_nothing_in_it_is_not_clean_by_accident() -> None:
    assert removed_module_imports(()) == []
    with pytest.raises(AssertionError):
        _with((), "src/auditmanager/findings/public.py", "x")
