"""`EXEC2-FOLLOWUP-01` (N1): the stale-rates refusal is raised only by operations that declare ``422``.

A group whose rate snapshot is not the provider lock's is refused ``422 analysis_input_invalid`` / ``cost_estimate_binding_changed`` by one
explicit seam, ``ai_jobs.estimate.require_group_rates_hold``. The contract lists, per operation, the answers it may give, and
``estimateComparisonAiPairCheck``, ``estimateComparisonSheetDescription``, ``estimateComparisonSpecification`` and
``finishComparisonAiSheetChanges`` declare no 422 (neither do the queue, series and upload resumes). Those must never reach the refusal: their
estimate is computed at the group's snapshot and the start that follows refuses with the message; a finish proceeds and the first call of the
job refuses it (``consent_stale``).

This test reads **the contract** (``contracts/api/v1/openapi.json``) and **the source** (an AST of ``src/auditmanager``) and holds the two to a
static map from ``operationId`` to the service entry that runs it and to the place the check sits:

* the seam is called from exactly the places the map names -- add a call anywhere else, or take one away, and the sets differ;
* every operation the map says reaches the check declares 422 -- drop the 422 from the contract, or map an operation without one to a seam, and
  it fails;
* the operations that must not reach it are mapped to no seam, and what they reach in the core (``estimate``, ``finish``) cannot reach a
  seam-bearing method -- a call graph of ``ComparisonAiJobService`` built from the source, with a positive control: ``start``, ``resume``,
  ``retry`` and ``resume_in_session`` do reach one;
* the non-AI operations (queue, series, upload) touch neither the core nor a route reader.

The map is hand-written, which is its limit: a new operation that reaches the core is not found by this test unless someone adds it. Everything
the map does say is checked against the tree, and every entry it names must exist.

Written and **not run** in EXEC-2 (`R-149d`).
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "src" / "auditmanager"
CONTRACT = ROOT / "contracts" / "api" / "v1" / "openapi.json"

SEAM = "require_group_rates_hold"
CORE_PATH, CORE = "comparison/ai_jobs/service.py", "ComparisonAiJobService"
#: What a service that is not an AI job must not touch: the core, a route reader, or the seam.
NOT_FOR_NON_AI = frozenset({"ComparisonAiJobService", "estimate", "estimate_in", "read_route", "route_of_group_revision", SEAM})


@dataclass(frozen=True)
class Entry:
    """Where an operation is served: the file and ``Class.method`` that runs it (``None`` when the entry is in the composition root's
    adapter, which is not resolved), the method of the core it goes through (``None`` for a service that is not an AI job) and the place that
    calls the seam (``None`` when the operation must not reach it)."""

    path: str | None
    qualified: str | None
    core: str | None
    seam: tuple[str, str] | None


START = (CORE_PATH, f"{CORE}.start_in_session")
RENEW = (CORE_PATH, f"{CORE}._renew_consent")
SHEETS_ESTIMATE = ("comparison/ai_sheets/service.py", "ComparisonAiSheetService.estimate_series")
PAIRS, SHEETS = "comparison/ai_pairs/service.py", "comparison/ai_sheets/service.py"
REPORTS, STAGE = "comparison/report/service.py", "comparison/stage_ai/runtime.py"

#: operationId -> where it is served and whether it reaches the seam.
OPERATIONS: dict[str, Entry] = {
    # -- operations that declare 422 and run the check ----------------------------------------------------------------------------
    "startComparisonAiPairCheck": Entry(PAIRS, "ComparisonAiPairService.start", "start", START),
    "resumeComparisonAiPairCheck": Entry(PAIRS, "ComparisonAiPairService.resume", "resume", RENEW),
    "estimateComparisonAiSheetChanges": Entry(SHEETS, "ComparisonAiSheetService.estimate_series", None, SHEETS_ESTIMATE),
    "startComparisonAiSheetChanges": Entry(SHEETS, "ComparisonAiSheetService.start_series", "start", START),
    "resumeComparisonAiSheetChanges": Entry(SHEETS, "ComparisonAiSheetService.resume", "resume", RENEW),
    "retryComparisonAiSheetChanges": Entry(SHEETS, "ComparisonAiSheetService.retry", "retry", RENEW),
    "startComparisonSheetDescription": Entry(SHEETS, "ComparisonAiSheetService.start_description", "start", START),
    "startComparisonSpecification": Entry(None, None, "start", START),
    "startComparisonReport": Entry(REPORTS, "ComparisonReportService.start_report", "start", START),
    "continueComparisonReport": Entry(REPORTS, "ComparisonReportService.continue_report", "resume", RENEW),
    "startStageChainRun": Entry(STAGE, "StageAiRuntime.prepare", "start_in_session", START),
    "resumeStageChainRun": Entry(STAGE, "StageAiRuntime.resume", "resume_in_session", RENEW),
    # -- operations that declare NO 422 and must not reach the check ----------------------------------------------------------------
    "estimateComparisonAiPairCheck": Entry(PAIRS, "ComparisonAiPairService.estimate", "estimate", None),
    "estimateComparisonSheetDescription": Entry(SHEETS, "ComparisonAiSheetService.estimate_description", "estimate", None),
    "estimateComparisonSpecification": Entry(None, None, "estimate", None),
    "finishComparisonAiSheetChanges": Entry(SHEETS, "ComparisonAiSheetService.finish", "finish", None),
    "resumeComparisonLaunchQueue": Entry("comparison/queue/service.py", "ComparisonLaunchQueueService.resume_queue", None, None),
    "resumeComparisonSeries": Entry("comparison/series/service.py", "ComparisonSeriesService.resume_series", None, None),
    "finishComparisonSeries": Entry("comparison/series/service.py", "ComparisonSeriesService.finish_series", None, None),
    "retryComparisonUploadSet": Entry("ingest/comparison_batch/service.py", "ComparisonBatchService.retry_set", None, None),
    "resumeComparisonUpload": Entry("ingest/comparison_batch/service.py", "ComparisonBatchService.resume_upload", None, None),
}

#: The four the integrator named: they declare no 422, and the check must never be reachable from them.
MUST_NOT_REFUSE = (
    "estimateComparisonAiPairCheck", "estimateComparisonSheetDescription", "estimateComparisonSpecification",
    "finishComparisonAiSheetChanges",
)
NON_AI = ("resumeComparisonLaunchQueue", "resumeComparisonSeries", "finishComparisonSeries", "retryComparisonUploadSet", "resumeComparisonUpload")


# -- the contract -------------------------------------------------------------------------------------------------------------------


def declared() -> dict[str, frozenset[str]]:
    document = json.loads(CONTRACT.read_text(encoding="utf-8"))
    return {
        operation["operationId"]: frozenset(operation["responses"])
        for item in document["paths"].values() for operation in item.values()
        if isinstance(operation, dict) and "operationId" in operation
    }


# -- the source ---------------------------------------------------------------------------------------------------------------------


def parse(path: str) -> ast.Module:
    return ast.parse((SRC / path).read_text(encoding="utf-8"))


def method_of(path: str, qualified: str) -> ast.FunctionDef | None:
    cls, _, name = qualified.partition(".")
    for node in parse(path).body:
        if isinstance(node, ast.ClassDef) and node.name == cls:
            return next((item for item in node.body if isinstance(item, ast.FunctionDef) and item.name == name), None)
    return None


def methods_of(path: str, cls: str) -> dict[str, ast.FunctionDef]:
    for node in parse(path).body:
        if isinstance(node, ast.ClassDef) and node.name == cls:
            return {item.name: item for item in node.body if isinstance(item, ast.FunctionDef)}
    raise AssertionError(f"{path} has no class {cls}")


def calls_named(function: ast.AST, name: str) -> bool:
    """Does the function (a nested closure included) call ``name``, as a function or as a method?"""
    return any(
        isinstance(node, ast.Call) and (
            (isinstance(node.func, ast.Name) and node.func.id == name) or (isinstance(node.func, ast.Attribute) and node.func.attr == name))
        for node in ast.walk(function)
    )


def seam_call_sites() -> set[tuple[str, str]]:
    """Every ``(file, Class.method)`` or ``(file, function)`` in the package whose body calls the seam."""
    found: set[tuple[str, str]] = set()
    for file in sorted(SRC.rglob("*.py")):
        text = file.read_text(encoding="utf-8")
        if SEAM not in text:
            continue
        relative = file.relative_to(SRC).as_posix()
        for node in ast.parse(text).body:
            if isinstance(node, ast.FunctionDef) and calls_named(node, SEAM):
                found.add((relative, node.name))
            elif isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and calls_named(item, SEAM):
                        found.add((relative, f"{node.name}.{item.name}"))
    return found


def reachable(path: str, cls: str, start: str) -> set[str]:
    """The methods of ``cls`` that ``start`` can reach through ``self.<method>(...)`` calls (closures passed as ``apply`` included)."""
    members, seen, todo = methods_of(path, cls), set(), [start]
    while todo:
        name = todo.pop()
        if name in seen or name not in members:
            continue
        seen.add(name)
        for node in ast.walk(members[name]):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name) and node.func.value.id == "self"):
                todo.append(node.func.attr)
    return seen


def core_seam_bearers() -> set[str]:
    """The methods of the core whose own body calls the seam."""
    return {name for name, function in methods_of(CORE_PATH, CORE).items() if calls_named(function, SEAM)}


def references(function: ast.AST) -> set[str]:
    return {node.id for node in ast.walk(function) if isinstance(node, ast.Name)} | {
        node.attr for node in ast.walk(function) if isinstance(node, ast.Attribute)}


# -- the tests ----------------------------------------------------------------------------------------------------------------------


def test_every_operation_the_map_names_is_in_the_contract() -> None:
    assert set(OPERATIONS) <= set(declared()), set(OPERATIONS) - set(declared())


def test_every_operation_that_reaches_the_check_declares_422() -> None:
    responses = declared()
    reaching = {name for name, entry in OPERATIONS.items() if entry.seam is not None}
    assert reaching, "the map names at least one operation that runs the check"
    assert {name for name in reaching if "422" not in responses[name]} == set()


def test_the_seam_is_called_from_exactly_the_places_the_map_names() -> None:
    mapped = {entry.seam for entry in OPERATIONS.values() if entry.seam is not None}
    assert seam_call_sites() == mapped


def test_the_four_operations_the_integrator_named_declare_no_422_and_reach_no_seam() -> None:
    responses = declared()
    for name in MUST_NOT_REFUSE:
        assert "422" not in responses[name], f"{name}: the premise of the choice (a contract that gains a 422 here may lift the rule)"
        entry = OPERATIONS[name]
        assert entry.seam is None, name
        assert entry.core is not None
        assert reachable(CORE_PATH, CORE, entry.core).isdisjoint(core_seam_bearers()), (name, entry.core)


def test_the_core_methods_a_start_a_resume_and_a_retry_go_through_do_reach_the_seam_and_the_estimate_and_the_finish_do_not() -> None:
    """The positive control of the call graph: it can say yes."""
    bearers = core_seam_bearers()
    assert bearers == {"start_in_session", "_renew_consent"}
    for name in ("start", "start_in_session", "resume", "resume_in_session", "retry"):
        assert reachable(CORE_PATH, CORE, name) & bearers, name
    for name in ("estimate", "estimate_in", "finish", "pause", "cancel", "dequeue", "view_in", "latest", "consent_for_calls"):
        assert not reachable(CORE_PATH, CORE, name) & bearers, name


def test_each_operation_goes_through_the_core_method_the_map_says_and_that_method_reaches_its_seam() -> None:
    for name, entry in OPERATIONS.items():
        if entry.core is None:
            continue
        reached = reachable(CORE_PATH, CORE, entry.core)
        if entry.seam is None:
            assert not reached & core_seam_bearers(), name
        else:
            path, qualified = entry.seam
            assert path == CORE_PATH and qualified.split(".", 1)[1] in reached, (name, entry.core, qualified)


def test_every_entry_the_map_names_exists_and_calls_what_the_map_says() -> None:
    for name, entry in OPERATIONS.items():
        if entry.path is None or entry.qualified is None:
            continue  # served by an adapter of the composition root, which delegates to the core
        function = method_of(entry.path, entry.qualified)
        assert function is not None, f"{name}: {entry.path} has no {entry.qualified}"
        if entry.seam is not None and entry.seam[1] == entry.qualified:
            assert calls_named(function, SEAM), name
        elif entry.core is not None and entry.path != CORE_PATH and entry.path != STAGE:
            assert calls_named(function, entry.core) or entry.core in references(function), f"{name}: {entry.qualified} does not call {entry.core}"


@pytest.mark.parametrize("name", NON_AI)
def test_the_queue_series_and_upload_resumes_touch_neither_the_core_nor_a_route_reader(name: str) -> None:
    """They declare no 422; none of them reaches an estimate."""
    entry = OPERATIONS[name]
    assert "422" not in declared()[name] and entry.seam is None and entry.core is None
    assert entry.path is not None and entry.qualified is not None
    cls = entry.qualified.partition(".")[0]
    for member in reachable(entry.path, cls, entry.qualified.partition(".")[2]):
        assert not references(methods_of(entry.path, cls)[member]) & NOT_FOR_NON_AI, (name, member)
