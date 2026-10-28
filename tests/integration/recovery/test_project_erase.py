"""`PROD-07A-PROJECT-ERASE-CORE-01`: the operator project erase removes ONE project and every guard bites.

Real PostgreSQL and a real S3-compatible bucket (the lane's), the stand in miniature of
``purge_seed`` (four projects, one of them with a published run, findings, expert decisions,
classification, assignments, price and vendor lists and an optimisation pass; a norm corpus with
custody and a verified retrieval set; accounts; a stray object). Each test gets its own clone of
that database and its own copy of the bucket.

**What "removed" and "kept" mean is measured with the TEST'S OWN queries**, not the tool's: the
project's rows are addressed by hand-written joins (``SLICES``), compared before and after by a
digest over ``row_to_json`` computed in Python, and the set of those tables is compared with the
tool's catalog-derived closure so the two cannot drift. A comparison that shared the tool's bug
would prove nothing.

**Every guard is shown able to fail.** ``# >>> guard: <name>`` / ``# <<< guard: <name>`` blocks in
``scripts/recovery/project_erase.py`` are deleted one at a time from a COPY of the source (the
convention of ``product_purge``'s tests). Each scenario makes the guard's condition true; the real
module must REFUSE with the reason in the message and (before the commit) change nothing, and the
copy without that block must not say that reason and must do what the guard prevents. Where two
guards stand in a row, the scenario names the other one (``without`` / ``also``) so that each is
shown on its own. The mutation table of ``docs/program/PROD-07A-PROJECT-ERASE-CORE-01.md`` is this
file's ``SCENARIOS`` with the observed effect.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import sys
import types
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text

from auditmanager.ingest import IngestService
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.db.session import create_session_factory, session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey, VersionUid
from auditmanager.storage import S3BlobStore, S3StorageSettings
from auditmanager.storage.public import BlobId, BlobMetadataRepository, canonical_object_key_for_recovery
from scripts.recovery import product_purge as purge
from scripts.recovery import project_erase as tool
from auditmanager.shared.db.migrations import head_revision
from scripts.recovery.schema_coverage import HEAD, TABLES
from tests.integration.recovery.purge_seed import STRAY_KEY, bucket_profile, digest_of
from tests.integration.recovery.purge_stand import (  # noqa: F401  (the fixtures are used by name)
    Stand, _line, full_purge, invoke, seeded, stand, state_of,
)

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "scripts/recovery/project_erase.py"
BUNDLES = ROOT / "fixtures/synthetic/ar/bundles"
ADMIN, EXPERT = "admin", "anna.drill@example.com"
REFERENCE = "owner message 2026-10-26, erase test"
NEVER = "prj_01M5F21PBT7E8WRN3M61BDQFDD"  # well formed, in no database
ALL_TABLES = sorted(TABLES)

REQUESTED_KEYS = {
    "project_uid", "actor_uid", "reason_code", "owner_permission_ref", "plan_sha256", "manifest_sha256",
    "rows_deleted", "blobs_exclusive", "blobs_shared",
}
COMPLETED_KEYS = REQUESTED_KEYS | {"objects_deleted", "objects_missing", "outcome"}


# --- the test's own addressing of a project's rows ---------------------------------------------

_VERSIONS = ("SELECT v.version_uid FROM document_version v JOIN document d ON d.document_uid = v.document_uid "
             "WHERE d.project_uid = :p")
_RUNS = "SELECT run_id FROM audit_run WHERE project_uid = :p"
_JOBS = f"SELECT job_id FROM job WHERE run_id IN ({_RUNS})"
_FINDINGS = "SELECT finding_uid FROM finding WHERE project_uid = :p"
_OBSERVATIONS = f"SELECT finding_observation_id FROM finding_observation WHERE finding_uid IN ({_FINDINGS})"
_PASSES = "SELECT optimisation_pass_id FROM optimisation_pass WHERE project_uid = :p"
_PROPOSALS = f"SELECT optimisation_proposal_id FROM optimisation_proposal WHERE optimisation_pass_id IN ({_PASSES})"
# `0038_comparison_foundation` (`CMP-SEAL-C0`): the comparison tables reach the project through an upload batch,
# a document version or a queue item.
_UPLOADS = "SELECT comparison_upload_id FROM comparison_upload WHERE project_uid = :p"
_UPLOAD_FILES = f"SELECT comparison_upload_file_id FROM comparison_upload_file WHERE comparison_upload_id IN ({_UPLOADS})"
_WORK = "SELECT comparison_work_id FROM comparison_work WHERE project_uid = :p"
_COMPARISON_ATTEMPTS = (
    f"SELECT comparison_work_attempt_id FROM comparison_work_attempt WHERE comparison_work_id IN ({_WORK})"
)
# `0039_comparison_core` (`CMP-SEAL-C1`): the tables of the version comparison core reach the project directly, through
# the document, or through a series and its transitions.
_DOCUMENTS = "SELECT document_uid FROM document WHERE project_uid = :p"
_SERIES = "SELECT comparison_series_id FROM comparison_series WHERE project_uid = :p"
_TRANSITIONS = f"SELECT comparison_transition_id FROM comparison_transition WHERE comparison_series_id IN ({_SERIES})"
# `0040_comparison_ai_reports` (`CMP-SEAL-C2`): a report's parts and files reach the project through the report.
_REPORTS = "SELECT comparison_report_id FROM comparison_report WHERE project_uid = :p"
SLICES: dict[str, str] = {
    "project": "project_uid = :p",
    "document": "project_uid = :p",
    "document_version": "document_uid IN (SELECT document_uid FROM document WHERE project_uid = :p)",
    "input_manifest_entry": f"version_uid IN ({_VERSIONS})",
    "document_version_classification": f"version_uid IN ({_VERSIONS})",
    "document_version_classification_correction": f"version_uid IN ({_VERSIONS})",
    "audit_run": "project_uid = :p",
    "job": f"run_id IN ({_RUNS})",
    "attempt": f"job_id IN ({_JOBS})",
    "lease": f"job_id IN ({_JOBS})",
    "stage_result": f"run_id IN ({_RUNS})",
    "model_call": f"run_id IN ({_RUNS})",
    "provider_call_effect": f"run_id IN ({_RUNS})",
    "analysis_artifact_publication": f"run_id IN ({_RUNS})",
    "executor_task": f"run_id IN ({_RUNS}) OR comparison_attempt_id IN ({_COMPARISON_ATTEMPTS})",
    "finding": "project_uid = :p",
    "finding_observation": f"finding_uid IN ({_FINDINGS})",
    "finding_evidence": f"finding_observation_id IN ({_OBSERVATIONS})",
    "finding_observation_norm_citation": f"finding_observation_id IN ({_OBSERVATIONS})",
    "expert_decision_event": f"finding_uid IN ({_FINDINGS})",
    "work_assignment": "project_uid = :p",
    "work_assignment_event": "assignment_uid IN (SELECT assignment_uid FROM work_assignment WHERE project_uid = :p)",
    "price_list_revision": "project_uid = :p",
    "price_list_position": "price_list_id IN (SELECT price_list_id FROM price_list_revision WHERE project_uid = :p)",
    "vendor_list_revision": "project_uid = :p",
    "vendor_list_entry": "vendor_list_id IN (SELECT vendor_list_id FROM vendor_list_revision WHERE project_uid = :p)",
    "optimisation_pass": "project_uid = :p",
    "optimisation_proposal": f"optimisation_pass_id IN ({_PASSES})",
    "optimisation_proposal_decision": f"optimisation_proposal_id IN ({_PROPOSALS})",
    "ar_v3_run_group": "project_uid = :p",
    "ar_v3_run_group_member": "group_id IN (SELECT group_id FROM ar_v3_run_group WHERE project_uid = :p)",
    "comparison_sheet_link": "project_uid = :p",
    "comparison_summary": "project_uid = :p",
    "comparison_upload": "project_uid = :p",
    "comparison_upload_set": f"comparison_upload_id IN ({_UPLOADS})",
    "comparison_upload_file": f"comparison_upload_id IN ({_UPLOADS})",
    "comparison_upload_part": f"comparison_upload_file_id IN ({_UPLOAD_FILES})",
    "comparison_version_order": "project_uid = :p",
    "comparison_page_profile": f"version_uid IN ({_VERSIONS})",
    "comparison_work": "project_uid = :p",
    "comparison_work_attempt": f"comparison_work_id IN ({_WORK})",
    "comparison_model_call": f"comparison_work_id IN ({_WORK})",
    "comparison_matrix": "project_uid = :p",
    "comparison_matrix_edit": "project_uid = :p",
    "comparison_ai_link": f"document_uid IN ({_DOCUMENTS})",
    "comparison_series": "project_uid = :p",
    "comparison_transition": f"comparison_series_id IN ({_SERIES})",
    "comparison_sheet_pair_result": "project_uid = :p",
    "comparison_sheet_pair": f"comparison_transition_id IN ({_TRANSITIONS})",
    # `0040_comparison_ai_reports` (`CMP-SEAL-C2`): the twelve tables of the version comparison AI, specifications, reports
    # and launch queue reach the project directly, or through a report.
    "comparison_ai_job": "project_uid = :p",
    "comparison_ai_pair_answer": "project_uid = :p",
    "comparison_ai_pair_question": "project_uid = :p",
    "comparison_sheet_description": "project_uid = :p",
    "comparison_ai_sheet_item": "project_uid = :p",
    "comparison_spec_extraction": "project_uid = :p",
    "comparison_spec_comparison": "project_uid = :p",
    "comparison_report": "project_uid = :p",
    "comparison_report_part": f"comparison_report_id IN ({_REPORTS})",
    "comparison_report_artifact": f"comparison_report_id IN ({_REPORTS})",
    "comparison_launch_queue": "project_uid = :p",
    "comparison_launch_entry": "project_uid = :p",
}
_BLOB_SOURCES = (
    f"SELECT blob_id FROM input_manifest_entry WHERE version_uid IN ({_VERSIONS}) "
    "UNION SELECT blob_id FROM price_list_revision WHERE project_uid = :p "
    f"UNION SELECT blob_id FROM analysis_artifact_publication WHERE run_id IN ({_RUNS}) "
    f"UNION SELECT blob_id FROM comparison_upload_file WHERE comparison_upload_id IN ({_UPLOADS}) "
    f"UNION SELECT blob_id FROM comparison_report_artifact WHERE comparison_report_id IN ({_REPORTS}) "
    f"UNION SELECT profile_blob_id FROM comparison_page_profile WHERE version_uid IN ({_VERSIONS}) "
    f"UNION SELECT preview_blob_id FROM comparison_page_profile WHERE version_uid IN ({_VERSIONS}) "
    f"UNION SELECT thumbnail_blob_id FROM comparison_page_profile WHERE version_uid IN ({_VERSIONS}) "
    "UNION SELECT mask_blob_id FROM comparison_sheet_pair_result WHERE project_uid = :p"
)
_KEEP_BLOBS = ("SELECT blob_id FROM norm_custody_binding UNION SELECT set_blob_id FROM norm_retrieval_set "
               "UNION SELECT catalogue_blob_id FROM norm_retrieval_set")


def slice_digest(engine: Engine, table: str, where: str, project: str) -> tuple[int, str]:
    with engine.connect() as connection:
        rows = sorted(r[0] for r in connection.execute(
            text(f'SELECT row_to_json(t)::text FROM public."{table}" t WHERE {where}'), {"p": project}))
    return len(rows), hashlib.sha256("\n".join(rows).encode()).hexdigest()


def slices(stand: Stand, project: str) -> dict[str, tuple[int, str]]:
    return {table: slice_digest(stand.engine, table, where, project) for table, where in SLICES.items()}


def scalars(stand: Stand, statement: str, **parameters: object) -> list[str]:
    with stand.engine.connect() as connection:
        return sorted(connection.execute(text(statement), parameters).scalars())


def project_like(stand: Stand, prefix: str) -> str:
    found = scalars(stand, "SELECT project_uid FROM project WHERE name LIKE :p", p=prefix + "%")
    assert len(found) == 1, (prefix, found)
    return found[0]


def other_projects(stand: Stand, target: str) -> list[str]:
    return scalars(stand, "SELECT project_uid FROM project WHERE project_uid <> :p", p=target)


def blob_ids_of(stand: Stand, project: str) -> set[str]:
    return set(scalars(stand, _BLOB_SOURCES, p=project))


def exclusive_blobs(stand: Stand, project: str) -> set[str]:
    """The test's own classification: referenced by this project only (no other project, no corpus)."""
    elsewhere: set[str] = set(scalars(stand, _KEEP_BLOBS))
    for other in other_projects(stand, project):
        elsewhere |= blob_ids_of(stand, other)
    return blob_ids_of(stand, project) - elsewhere


def tokens_of(stand: Stand, project: str) -> set[str]:
    return set(scalars(stand, f"SELECT upload_token FROM analysis_artifact_publication WHERE run_id IN ({_RUNS})",
                       p=project))


def client_texts(stand: Stand, project: str) -> set[str]:
    """Every string of the project that a client could recognise (names, file names, quotes, comments)."""
    queries = (
        "SELECT name FROM project WHERE project_uid = :p",
        "SELECT display_title FROM document WHERE project_uid = :p",
        "SELECT source_filename FROM document_version WHERE document_uid IN "
        "(SELECT document_uid FROM document WHERE project_uid = :p)",
        f"SELECT finding_text FROM finding_observation WHERE finding_uid IN ({_FINDINGS})",
        f"SELECT recommendation_text FROM finding_observation WHERE finding_uid IN ({_FINDINGS})",
        f"SELECT quote FROM finding_evidence WHERE finding_observation_id IN ({_OBSERVATIONS})",
        f"SELECT comment FROM expert_decision_event WHERE finding_uid IN ({_FINDINGS})",
    )
    found: set[str] = set()
    for query in queries:
        found |= {value for value in scalars(stand, query, p=project) if value and len(value) >= 4}
    return found


def sql(stand: Stand, statement: str, **parameters: object) -> None:
    with stand.engine.begin() as connection:
        connection.execute(text(statement), parameters)


def rows(stand: Stand, statement: str, **parameters: object) -> list[tuple[Any, ...]]:
    with stand.engine.connect() as connection:
        return [tuple(r) for r in connection.execute(text(statement), parameters)]


def count(stand: Stand, table: str, where: str = "true", **parameters: object) -> int:
    return int(rows(stand, f'SELECT count(*) FROM public."{table}" WHERE {where}', **parameters)[0][0])


def events(stand: Stand) -> list[tuple[str, str, str, dict[str, Any]]]:
    return [(a, b, c, dict(d)) for a, b, c, d in rows(
        stand, "SELECT event_type, aggregate_type, aggregate_id, payload FROM audit_event "
               "WHERE event_type LIKE 'erasure.%' ORDER BY sequence_no")]


# --- driving the tool ---------------------------------------------------------------------------


def apply_flags(project: str, sha: str | None, dump: Path, **flags: str | None) -> list[str]:
    values: dict[str, str | None] = {
        "--project": project, "--plan-sha256": sha, "--actor": ADMIN, "--reason": "test_data",
        "--owner-permission-ref": REFERENCE, "--dump-dir": str(dump),
    }
    values.update({"--" + key.replace("_", "-"): value for key, value in flags.items()})
    argv = ["--apply"]
    for flag, value in values.items():
        if value is not None:
            argv += [flag, value]
    return argv


class Harness:
    """One scenario's stand, scratch directory, target project and before-state."""

    def __init__(self, stand: Stand, tmp: Path, mp: pytest.MonkeyPatch, project: str = "Склад") -> None:
        self.stand, self.tmp, self.mp = stand, tmp, mp
        self.dump = tmp / "dump"
        self.target = project_like(stand, project)
        self.before: dict[str, Any] = {}
        self.notes: dict[str, str] = {}
        self.before_blobs = sorted(blob_ids_of(stand, self.target))

    def checkpoint(self) -> None:
        self.before = state_of(self.stand)

    def dry(self, module: types.ModuleType, project: str | None = None) -> tuple[int, str, str]:
        return invoke(module, self.stand, "--project", project or self.target)

    def apply(self, module: types.ModuleType, sha: str | None, **flags: str | None) -> tuple[int, str, str]:
        return invoke(module, self.stand, *apply_flags(self.target, sha, self.dump, **flags))

    def plan_apply(self, module: types.ModuleType, **flags: str | None) -> tuple[int, str, str]:
        """The dry run through ``module``, then the apply with its digest (or the dry run's refusal)."""
        code, out, err = self.dry(module)
        if code != 0:
            return code, out, err
        return self.apply(module, _line(out, "plan-sha256"), **flags)

    def resume(self, module: types.ModuleType, erase_id: str, **flags: str | None) -> tuple[int, str, str]:
        values: dict[str, str | None] = {"--actor": ADMIN, "--owner-permission-ref": REFERENCE,
                                         "--dump-dir": str(self.dump)}
        values.update({"--" + key.replace("_", "-"): value for key, value in flags.items()})
        argv = ["--resume", erase_id]
        for flag, value in values.items():
            if value is not None:
                argv += [flag, value]
        return invoke(module, self.stand, *argv)

    def gone(self) -> bool:
        return count(self.stand, "project", "project_uid = :p", p=self.target) == 0


def crashing(module: types.ModuleType, name: str) -> Callable[[], None]:
    """Replace ``module.<name>`` with a function that raises; returns the restoring call."""
    real = getattr(module, name)

    def boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(f"simulated crash in {name}")

    setattr(module, name, boom)
    return lambda: setattr(module, name, real)


# --- the guard-deleting harness ------------------------------------------------------------------

_BLOCK = r"^[ \t]*# >>> guard: {name}\n.*?^[ \t]*# <<< guard: {name}\n"
_MUTANTS = iter(range(10**6))


def mutant(*guards: str) -> types.ModuleType:
    """The module with exactly those guard blocks deleted, run from a copy of the source."""
    source = SOURCE.read_text(encoding="utf-8")
    for name in guards:
        source, matched = re.subn(_BLOCK.format(name=re.escape(name)), "", source, flags=re.DOTALL | re.MULTILINE)
        assert matched == 1, f"the guard markers for {name!r} are not a single block"
    module = types.ModuleType(f"scripts.recovery.project_erase_mutant_{next(_MUTANTS)}")
    module.__file__ = str(SOURCE)
    sys.modules[module.__name__] = module
    exec(compile(source, f"<project_erase without {guards}>", "exec"), module.__dict__)  # noqa: S102
    return module


def new_role(stand: Stand) -> str:
    name = f"erase_probe_{secrets.token_hex(4)}"
    with stand.engine.begin() as connection:
        connection.execute(text(f"CREATE ROLE {name} LOGIN PASSWORD 'probe-password'"))
        connection.execute(text(f'GRANT CONNECT ON DATABASE "{stand.database}" TO {name}'))
        connection.execute(text(f"GRANT USAGE ON SCHEMA public TO {name}"))
        connection.execute(text(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {name}"))
    return name


def drop_role(stand: Stand, name: str) -> None:
    with stand.engine.begin() as connection:
        connection.execute(text(f"DROP OWNED BY {name}"))
        connection.execute(text(f"DROP ROLE {name}"))


def switched_off(stand: Stand, table: str, trigger: str, statement: str, **parameters: object) -> None:
    """Run one owner statement with one named trigger off (the way a migration would)."""
    with stand.engine.begin() as connection:
        connection.execute(text(f'ALTER TABLE public."{table}" DISABLE TRIGGER {trigger}'))
        connection.execute(text(statement), parameters)
        connection.execute(text(f'ALTER TABLE public."{table}" ENABLE TRIGGER {trigger}'))


def crash_after_commit(module: types.ModuleType, h: Harness) -> str:
    """Apply, with the objects phase crashing: the database part commits. Returns the erase id."""
    restore = crashing(module, "delete_objects")
    try:
        code, out, err = h.plan_apply(module)
    finally:
        restore()
    assert code == tool.EXIT_FAILED and "simulated crash in delete_objects" in err, (code, out, err)
    assert "Resume with --resume era_" in err
    return _line(out, "erase-id")


def one_available_blob(stand: Stand, exclude: set[str]) -> str:
    blobs = scalars(stand, "SELECT blob_id FROM blob WHERE state = 'available'")
    return next(b for b in blobs if b not in exclude)


# =================================================================================================
# The declaration: what the closure is, and that the tool's lists agree with the schema
# =================================================================================================


def test_the_closure_is_read_from_the_catalog_and_agrees_with_the_hand_written_slices(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        head, closure = tool.check_schema(connection)
    assert head == HEAD == head_revision()
    # every PRODUCT table but ``worker`` is in the closure, and the test's own addressing names the same tables
    assert set(closure.tables) == purge.PRODUCT_TABLES - tool.UNSCOPED_PRODUCT_TABLES
    assert set(closure.tables) == set(SLICES)
    # `0038_comparison_foundation`: the nine comparison tables join the closure (33 -> 42); the batch, the
    # order revisions and the queue item reference the project directly. `0039_comparison_core`: the seven tables of
    # the version comparison core join it (42 -> 49); the builds, the edits, the series and the results reference the
    # project directly. `0040_comparison_ai_reports`: the twelve tables of the version comparison AI, specifications, reports
    # and launch queue join it (49 -> 61); the jobs, answers, questions, descriptions, sheet items, extractions, comparisons,
    # reports and the launch queue reference the project directly.
    assert tool.UNSCOPED_PRODUCT_TABLES == {"worker"} and len(closure.tables) == 61
    assert set(closure.direct) == {
        "ar_v3_run_group", "audit_run", "comparison_ai_job", "comparison_ai_pair_answer", "comparison_ai_pair_question",
        "comparison_ai_sheet_item", "comparison_launch_queue", "comparison_matrix", "comparison_matrix_edit",
        "comparison_report", "comparison_series", "comparison_sheet_description", "comparison_sheet_link",
        "comparison_sheet_pair_result", "comparison_spec_comparison", "comparison_spec_extraction",
        "comparison_summary", "comparison_upload",
        "comparison_version_order", "comparison_work", "document", "finding", "optimisation_pass",
        "price_list_revision", "vendor_list_revision", "work_assignment",
    }
    # `0038_comparison_foundation`: an upload batch and an order revision carry the receipt of the write
    # that made them.
    assert {key.child for key in closure.receipt_edges} == {
        "ar_v3_run_group", "audit_run", "comparison_ai_job", "comparison_launch_entry", "comparison_matrix_edit",
        "comparison_report", "comparison_series", "comparison_sheet_link",
        "comparison_summary", "comparison_upload", "comparison_version_order", "expert_decision_event",
        "optimisation_proposal_decision",
    }


def test_the_four_cycles_of_the_closure_are_deleted_in_one_statement_each(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        _, closure = tool.check_schema(connection)
    order = tool.deletion_order(closure.tables, [(k.child, k.parent) for k in closure.edges])
    assert sorted(group for group in order if len(group) > 1) == [
        ("attempt", "job"), ("comparison_work", "comparison_work_attempt"), ("document", "document_version"),
        ("finding", "finding_observation"),
    ]
    position = {table: index for index, group in enumerate(order) for table in group}
    for key in closure.edges:
        assert position[key.child] <= position[key.parent], key
    assert order[-1] == ("project",)


def test_the_non_terminal_states_are_the_complement_of_the_schemas_terminal_checks(migrated_engine: Engine) -> None:
    """A migration that adds a state must move ``NON_TERMINAL_STATES``: this fails first."""
    def states(constraint: str, table: str) -> set[str]:
        with migrated_engine.connect() as connection:
            definition = connection.execute(text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :n AND conrelid = CAST(:t AS regclass)"
            ), {"n": constraint, "t": f"public.{table}"}).scalar_one()
        return set(re.findall(r"'([a-z_]+)'::text", definition))

    for table, terminal_check in (("audit_run", "ck_audit_run_terminal_at"), ("job", "ck_job_terminal_at"),
                                  ("attempt", "ck_attempt_terminal_at"),
                                  # `CMP-SEAL-C0` (ADR-0025 decision 7): the comparison queue
                                  ("comparison_work", "ck_comparison_work_terminal_at"),
                                  ("comparison_work_attempt", "ck_comparison_work_attempt_terminal_at")):
        terminal = states(terminal_check, table)
        every = states(f"ck_{table}_state", table)
        assert terminal < every and set(tool.NON_TERMINAL_STATES[table]) == every - terminal, table
    every = states("ck_executor_task_state", "executor_task")
    assert set(tool.NON_TERMINAL_STATES["executor_task"]) == {"open", "claimed"}
    assert {"open", "claimed"} <= every and every - {"open", "claimed"} == {"answered", "failed", "expired", "cancelled"}


def test_the_purge_keeps_the_record_of_an_erasure_and_would_stop_without_the_prefix() -> None:
    assert "erasure." in purge.KEEP_EVENT_PREFIXES
    keep, delete = purge._predicates([])["audit_event"]
    assert "starts_with(t.event_type, 'erasure.')" in keep and delete == f"NOT {keep}"
    assert tool.EVENT_REQUESTED.startswith(purge.KEEP_EVENT_PREFIXES)
    assert tool.EVENT_COMPLETED.startswith(purge.KEEP_EVENT_PREFIXES)
    assert not tool.EVENT_REQUESTED.startswith(purge.PRODUCT_EVENT_PREFIXES)


# =================================================================================================
# The plan
# =================================================================================================


def test_a_dry_run_is_the_default_prints_exact_counts_and_changes_nothing(stand: Stand) -> None:
    target = project_like(stand, "Школа")
    before = state_of(stand)
    code, out, err = invoke(tool, stand, "--project", target)
    assert code == 0, err
    explicit = invoke(tool, stand, "--project", target, "--dry-run")
    assert explicit[0] == 0 and explicit[1] == out
    assert state_of(stand) == before
    own = slices(stand, target)
    for table, (rows_, _) in own.items():
        if rows_:
            assert f"  {table}  ({rows_} rows)" in out, table
        else:
            assert re.search(rf"^  {table}  ", out, re.MULTILINE) is None, table
    assert "--dry-run: NOTHING ABOVE WAS CHANGED." in out
    assert re.fullmatch(r"[0-9a-f]{64}", _line(out, "plan-sha256"))
    exclusive = exclusive_blobs(stand, target)
    assert int(_line(out, "blobs-exclusive")) == len(exclusive) == 17
    assert int(_line(out, "blobs-shared")) == len(blob_ids_of(stand, target)) - len(exclusive) == 1
    assert "run-journal events of the project (identities only): 24" in out
    assert events(stand) == []


def test_the_plan_digest_is_stable_and_moves_with_the_data(stand: Stand) -> None:
    target = project_like(stand, "Склад")
    first = _line(invoke(tool, stand, "--project", target)[1], "plan-sha256")
    assert _line(invoke(tool, stand, "--project", target)[1], "plan-sha256") == first
    other = _line(invoke(tool, stand, "--project", project_like(stand, "Детский"))[1], "plan-sha256")
    assert other != first
    sql(stand, "UPDATE project SET name = name || ' (renamed)' WHERE project_uid = :p", p=target)
    assert _line(invoke(tool, stand, "--project", target)[1], "plan-sha256") != first


# =================================================================================================
# The erase
# =================================================================================================


@dataclass
class Erased:
    """What was true before an erase (measured by the test), then what the tool reported."""

    target: str
    others: list[str]
    before_state: dict[str, Any]
    before_slices: dict[str, dict[str, tuple[int, str]]]
    exclusive: set[str]
    expected_gone: set[str]
    texts: set[str]
    blob_outside: tuple[int, str]
    receipts_before: dict[str, str]
    erase_id: str = ""
    out: str = ""
    manifest: Path | None = None

    def before_receipts_items(self) -> list[tuple[str, str]]:
        return list(self.receipts_before.items())


def before_erase(stand: Stand, prefix: str) -> Erased:
    target = project_like(stand, prefix)
    others = other_projects(stand, target)
    exclusive = exclusive_blobs(stand, target)
    ids = ", ".join(f"'{b}'" for b in sorted(exclusive)) or "''"
    return Erased(
        target=target, others=others, before_state=state_of(stand),
        before_slices={p: slices(stand, p) for p in [target, *others]}, exclusive=exclusive,
        expected_gone={canonical_object_key_for_recovery(b) for b in exclusive} | {
            f"temporary/{token}" for token in tokens_of(stand, target)},
        texts=client_texts(stand, target), blob_outside=digest_of(stand.engine, "blob", f"blob_id NOT IN ({ids})"),
        receipts_before=dict(rows(stand, "SELECT command_id, command_type FROM command_record")),
    )


def do_erase(stand: Stand, tmp: Path, prefix: str) -> Erased:
    erased = before_erase(stand, prefix)
    code, out, err = invoke(tool, stand, "--project", erased.target)
    assert code == 0, err
    sha = _line(out, "plan-sha256")
    code, out, err = invoke(tool, stand, *apply_flags(erased.target, sha, tmp / "dump"))
    assert code == 0, (out, err)
    erased.erase_id, erased.out = _line(out, "erase-id"), out
    erased.manifest = tmp / "dump" / erased.erase_id / "manifest.json"
    return erased


def assert_isolation(stand: Stand, erased: Erased) -> None:
    """The project is gone by the test's own addressing and everything else is byte for byte as it was."""
    assert all(rows_ == 0 for rows_, _ in slices(stand, erased.target).values())
    for other in erased.others:
        assert slices(stand, other) == erased.before_slices[other], other
    after = state_of(stand)
    for table in sorted(purge.KEEP_TABLES | tool.UNSCOPED_PRODUCT_TABLES):
        assert after["tables"][table] == erased.before_state["tables"][table], table
    # the run journal and the account/executor/custody events: every event that existed still exists
    assert digest_of(stand.engine, "audit_event", "event_type NOT LIKE 'erasure.%'") == \
        erased.before_state["tables"]["audit_event"]
    # the objects of every other project, the corpus and the stray object: unchanged, byte for byte
    kept = set(erased.before_state["bucket"]) - erased.expected_gone
    assert set(after["bucket"]) == kept
    assert all(after["bucket"][key] == erased.before_state["bucket"][key] for key in kept)
    assert STRAY_KEY in after["bucket"] and set(stand.summary["norm_keys"]) <= set(after["bucket"])
    # the Blob rows outside the erase are the same rows
    ids = ", ".join(f"'{b}'" for b in sorted(erased.exclusive)) or "''"
    assert digest_of(stand.engine, "blob", f"blob_id NOT IN ({ids})") == erased.blob_outside


@pytest.mark.parametrize("prefix", ["Школа", "Склад", "Детский", "Пустой"])
def test_an_erase_removes_exactly_one_project_and_nothing_else(stand: Stand, tmp_path: Path, prefix: str) -> None:
    with stand.engine.connect() as connection:
        triggers = connection.execute(text(
            "SELECT tgrelid::regclass::text, tgname, tgenabled::text FROM pg_trigger "
            "WHERE NOT tgisinternal ORDER BY 1, 2")).all()
        sequences = dict(connection.execute(text("SELECT sequencename, last_value FROM pg_sequences")).all())
    erased = do_erase(stand, tmp_path, prefix)
    assert erased.manifest is not None
    assert_isolation(stand, erased)

    # blobs: the exclusive rows are DELETED (no erased/erasure_pending row), the others are the same rows
    assert count(stand, "blob", "state IN ('erased', 'erasure_pending')") == 0
    assert not set(scalars(stand, "SELECT blob_id FROM blob")) & erased.exclusive
    # triggers (an erase must leave every guard as it found it) and sequences (monotonic)
    with stand.engine.connect() as connection:
        assert connection.execute(text(
            "SELECT tgrelid::regclass::text, tgname, tgenabled::text FROM pg_trigger "
            "WHERE NOT tgisinternal ORDER BY 1, 2")).all() == triggers
        after_sequences = dict(connection.execute(text("SELECT sequencename, last_value FROM pg_sequences")).all())
    assert all(after_sequences[name] >= value for name, value in sequences.items() if value is not None)

    # the journal: two events, identities and counts and digests only
    requested, completed = events(stand)
    assert (requested[0], completed[0]) == ("erasure.requested", "erasure.completed")
    assert requested[1] == completed[1] == "ErasureRequest" and requested[2] == completed[2] == erased.erase_id
    assert set(requested[3]) == REQUESTED_KEYS and set(completed[3]) == COMPLETED_KEYS
    assert requested[3]["project_uid"] == erased.target and requested[3]["reason_code"] == "test_data"
    assert requested[3]["owner_permission_ref"] == REFERENCE == completed[3]["owner_permission_ref"]
    assert requested[3]["blobs_exclusive"] == len(erased.exclusive) == completed[3]["blobs_exclusive"]
    assert completed[3]["outcome"] == "completed" and requested[3]["plan_sha256"] == completed[3]["plan_sha256"]
    assert requested[3]["actor_uid"] == stand.summary["admin"]
    # the rows counted are the rows the test addressed by hand, plus the receipts that left command_record
    after_receipts = dict(rows(stand, "SELECT command_id, command_type FROM command_record"))
    gone_receipts = {c: t for c, t in erased.before_receipts_items() if c not in after_receipts}
    assert set(gone_receipts.values()) <= purge.PRODUCT_COMMAND_TYPES  # an account or executor receipt never goes
    assert all(after_receipts[c] == t for c, t in after_receipts.items() if c in erased.receipts_before)
    receipts_left = len(gone_receipts)
    if prefix == "Школа":
        assert {"upload_source_document", "start_audit_run", "upload_price_list", "start_optimisation_pass",
                "decide_optimisation_proposal"} <= set(gone_receipts.values())
    assert "approve_registration" in set(after_receipts.values())  # the account side's receipt stays
    assert requested[3]["rows_deleted"] == sum(n for n, _ in erased.before_slices[erased.target].values()) + receipts_left
    present = set(erased.before_state["bucket"]) & erased.expected_gone
    assert completed[3]["objects_deleted"] == len(present)
    assert completed[3]["objects_deleted"] + completed[3]["objects_missing"] == len(erased.expected_gone)
    # the erased project's texts are nowhere in the record of the erasure
    record = json.dumps([requested[3], completed[3]], ensure_ascii=False) + erased.manifest.read_text(
        encoding="utf-8") + (erased.manifest.parent / "plan.json").read_text(encoding="utf-8")
    assert not [t for t in erased.texts if t in record]
    # the manifest: its SHA-256 IS the digest in both events, and it lists exactly the exclusive Blobs
    digest = hashlib.sha256(erased.manifest.read_bytes()).hexdigest()
    assert digest == requested[3]["manifest_sha256"] == completed[3]["manifest_sha256"]
    listed = json.loads(erased.manifest.read_text(encoding="utf-8"))
    assert {b["blob_id"] for b in listed["blobs"]} == erased.exclusive
    assert listed["erase_id"] == erased.erase_id and listed["project_uid"] == erased.target
    for entry in listed["blobs"]:
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]) and entry["size_bytes"] >= 0
    # and the stand WORKS: a project can be created
    store = S3BlobStore(S3StorageSettings.from_env())
    assert IngestService(store, session_factory=create_session_factory(stand.engine)).create_project(
        name="after the erase")


def test_the_rich_project_leaves_the_second_project_and_the_shared_blob_readable(stand: Stand, tmp_path: Path) -> None:
    """The school and the kindergarten share a Blob; erasing the school keeps it, with its object."""
    kindergarten = project_like(stand, "Детский")
    shared = blob_ids_of(stand, project_like(stand, "Школа")) & blob_ids_of(stand, kindergarten)
    assert len(shared) == 1
    key = canonical_object_key_for_recovery(next(iter(shared)))
    erased = do_erase(stand, tmp_path, "Школа")
    assert shared <= set(scalars(stand, "SELECT blob_id FROM blob")) and key in bucket_profile(stand.client, stand.bucket)
    ingest = IngestService(S3BlobStore(S3StorageSettings.from_env()), session_factory=create_session_factory(stand.engine))
    version = scalars(stand, "SELECT v.version_uid FROM document_version v JOIN document d USING (document_uid) "
                             "WHERE d.project_uid = :p", p=kindergarten)[0]
    assert ingest.read_source_bytes(VersionUid.parse(version))
    assert erased.manifest is not None
    listed = {b["blob_id"] for b in json.loads(erased.manifest.read_text(encoding="utf-8"))["blobs"]}
    assert not listed & shared


def test_a_second_apply_of_the_same_plan_finds_nothing_to_do_and_changes_nothing(stand: Stand, tmp_path: Path) -> None:
    target = project_like(stand, "Склад")
    sha = _line(invoke(tool, stand, "--project", target)[1], "plan-sha256")
    first = invoke(tool, stand, *apply_flags(target, sha, tmp_path / "dump"))
    assert first[0] == 0, first
    settled = state_of(stand)
    again = invoke(tool, stand, *apply_flags(target, sha, tmp_path / "dump"))
    assert again[0] == 0, again
    assert "nothing to do" in again[1] and _line(first[1], "erase-id") in again[1]
    assert state_of(stand) == settled and len(events(stand)) == 2
    assert len(list((tmp_path / "dump").iterdir())) == 1  # no second erase directory
    # the dry run of an erased project says the same
    dry = invoke(tool, stand, "--project", target)
    assert dry[0] == 0 and "nothing to do" in dry[1]
    # and a resume of the finished erase
    done = invoke(tool, stand, "--resume", _line(first[1], "erase-id"), "--actor", ADMIN,
                  "--owner-permission-ref", REFERENCE, "--dump-dir", str(tmp_path / "dump"))
    assert done[0] == 0 and "already complete" in done[1] and state_of(stand) == settled


def test_without_the_already_erased_path_a_second_apply_is_a_refusal_not_a_no_op(
    stand: Stand, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutation: the "nothing to do" exit is what makes the second run exit 0."""
    target = project_like(stand, "Склад")
    sha = _line(invoke(tool, stand, "--project", target)[1], "plan-sha256")
    assert invoke(tool, stand, *apply_flags(target, sha, tmp_path / "dump"))[0] == 0
    settled = state_of(stand)
    monkeypatch.setattr(tool, "_already_erased", lambda engine, project: None)
    code, out, err = invoke(tool, stand, *apply_flags(target, sha, tmp_path / "dump"))
    assert code == tool.EXIT_REFUSED and "is not a project of this database" in err
    assert state_of(stand) == settled


def test_a_stale_plan_is_refused_and_the_dry_run_after_it_is_the_new_plan(stand: Stand, tmp_path: Path) -> None:
    h = Harness(stand, tmp_path, pytest.MonkeyPatch())
    sha = _line(h.dry(tool)[1], "plan-sha256")
    sql(stand, "UPDATE project SET name = name || ' (late edit)' WHERE project_uid = :p", p=h.target)
    h.checkpoint()
    code, out, err = h.apply(tool, sha)
    assert code == tool.EXIT_REFUSED and "changed since the plan that was approved" in err
    assert state_of(stand) == h.before and not h.dump.exists()
    fresh = _line(h.dry(tool)[1], "plan-sha256")
    assert fresh != sha
    assert h.apply(tool, fresh)[0] == 0 and h.gone()


# --- the crash points -----------------------------------------------------------------------------


def test_a_crash_before_the_commit_changes_nothing_and_leaves_no_file(
    stand: Stand, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = Harness(stand, tmp_path, monkeypatch)
    h.checkpoint()
    restore = crashing(tool, "write_erase_files")
    try:
        code, out, err = h.plan_apply(tool)
    finally:
        restore()
    assert code == tool.EXIT_FAILED and "simulated crash in write_erase_files" in err
    assert state_of(stand) == h.before and events(stand) == []
    assert not h.dump.exists() or list(h.dump.rglob("*")) == [] or all(p.is_dir() for p in h.dump.rglob("*"))
    assert count(stand, "blob", "state = 'erasure_pending'") == 0
    # and the same plan applies cleanly afterwards
    assert h.plan_apply(tool)[0] == 0 and h.gone()


def test_a_crash_between_the_commit_and_the_objects_is_finished_by_resume(
    stand: Stand, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = Harness(stand, tmp_path, monkeypatch)
    exclusive = exclusive_blobs(stand, h.target)
    h.checkpoint()
    erase_id = crash_after_commit(tool, h)
    # phase 2 is whole: the project is gone, the Blobs wait in erasure_pending, the objects are all still there
    assert h.gone() and set(scalars(stand, "SELECT blob_id FROM blob WHERE state = 'erasure_pending'")) == exclusive
    assert len(events(stand)) == 1 and events(stand)[0][0] == "erasure.requested"
    assert set(bucket_profile(stand.client, stand.bucket)) == set(h.before["bucket"])
    # a second erase of anything else must wait for this one, and the same project points at the way forward
    other = invoke(tool, stand, "--project", project_like(stand, "Детский"))
    assert other[0] == tool.EXIT_REFUSED and "erasure_pending" in other[2]
    again = h.apply(tool, "0" * 64)
    assert again[0] == tool.EXIT_REFUSED and f"--resume {erase_id}" in again[2]
    # resume finishes phases 3 and 4
    code, out, err = h.resume(tool, erase_id)
    assert code == 0, (out, err)
    assert count(stand, "blob", "state = 'erasure_pending'") == 0
    assert [e[0] for e in events(stand)] == ["erasure.requested", "erasure.completed"]
    completed = events(stand)[1][3]
    assert completed["objects_deleted"] > 0 and completed["manifest_sha256"] == events(stand)[0][3]["manifest_sha256"]
    gone = set(h.before["bucket"]) - set(bucket_profile(stand.client, stand.bucket))
    assert {canonical_object_key_for_recovery(b) for b in exclusive} <= gone
    assert STRAY_KEY in bucket_profile(stand.client, stand.bucket)
    # a second resume is "already complete"
    settled = state_of(stand)
    assert "already complete" in h.resume(tool, erase_id)[1] and state_of(stand) == settled


def test_a_crash_between_the_objects_and_the_finish_is_finished_by_resume(
    stand: Stand, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = Harness(stand, tmp_path, monkeypatch, "Школа")
    exclusive = exclusive_blobs(stand, h.target)
    restore = crashing(tool, "phase_finish")
    try:
        code, out, err = h.plan_apply(tool)
    finally:
        restore()
    assert code == tool.EXIT_FAILED and "simulated crash in phase_finish" in err
    erase_id = _line(out, "erase-id")
    # the objects are gone, the rows still wait
    after_crash = set(bucket_profile(stand.client, stand.bucket))
    assert not {canonical_object_key_for_recovery(b) for b in exclusive} & after_crash
    assert set(scalars(stand, "SELECT blob_id FROM blob WHERE state = 'erasure_pending'")) == exclusive
    code, out, err = h.resume(tool, erase_id)
    assert code == 0, (out, err)
    completed = events(stand)[1][3]
    assert completed["objects_deleted"] == 0 and completed["objects_missing"] >= len(exclusive)  # a 404 counts as done
    assert count(stand, "blob", "state = 'erasure_pending'") == 0 and not set(
        scalars(stand, "SELECT blob_id FROM blob")) & exclusive
    assert set(bucket_profile(stand.client, stand.bucket)) == after_crash


def test_resume_rewrites_a_lost_manifest_from_the_rows_and_warns_about_a_lost_plan_file(
    stand: Stand, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = Harness(stand, tmp_path, monkeypatch)
    erase_id = crash_after_commit(tool, h)
    manifest = h.dump / erase_id / "manifest.json"
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    manifest.unlink()
    (h.dump / erase_id / "plan.json").unlink()
    code, out, err = h.resume(tool, erase_id)
    assert code == 0 and "manifest-rewritten" in out and "plan.json" in err and "is absent" in err
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == digest == events(stand)[1][3]["manifest_sha256"]


def test_receipts_are_found_by_the_foreign_key_and_by_the_identity_their_outcome_names(
    stand: Stand, tmp_path: Path
) -> None:
    """A decision receipt names the decision; one of the project is erased, one of another project stays."""
    school, kindergarten = project_like(stand, "Школа"), project_like(stand, "Детский")
    own = scalars(stand, f"SELECT decision_id FROM expert_decision_event WHERE finding_uid IN ({_FINDINGS})", p=school)[0]
    foreign = "dec_01M5F21PBT7E8WRN3M61BDQFDD"  # a decision of nobody the tool may touch
    for number, (command, outcome) in enumerate((("cmd_01M5F21PBT7E8WRN3M61BDQFDA", {"decision_id": own}),
                                                 ("cmd_01M5F21PBT7E8WRN3M61BDQFDB", {"decision_id": foreign}),
                                                 ("cmd_01M5F21PBT7E8WRN3M61BDQFDC", {"deep": {"list": [kindergarten]}}))):
        sql(stand, "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint, state) "
                   "VALUES (:c, 'append_decision', :k, :f, 'in_progress')", c=command, k=f"zz-{number}", f="a" * 64)
        sql(stand, "UPDATE command_record SET state = 'succeeded', outcome = CAST(:o AS jsonb) WHERE command_id = :c",
            c=command, o=json.dumps(outcome))
    do_erase(stand, tmp_path, "Школа")
    left = set(scalars(stand, "SELECT command_id FROM command_record WHERE command_id LIKE 'cmd_01M5F21PBT7E8WRN3M61BDQF%'"))
    assert left == {"cmd_01M5F21PBT7E8WRN3M61BDQFDB", "cmd_01M5F21PBT7E8WRN3M61BDQFDC"}


# --- the re-upload ----------------------------------------------------------------------------------


def test_a_byte_identical_upload_after_the_erase_succeeds_and_creates_a_fresh_blob_row(
    stand: Stand, tmp_path: Path
) -> None:
    """ADR-0022 `AD-07`, end to end at the repository level: the erased bytes can come back."""
    erased = do_erase(stand, tmp_path, "Склад")
    manifest = {b["blob_id"]: b for b in json.loads(erased.manifest.read_text(encoding="utf-8"))["blobs"]}
    assert len(manifest) == 3
    session_factory = create_session_factory(stand.engine)
    repository = BlobMetadataRepository()
    with session_scope(session_factory) as session:
        for blob_id in manifest:  # nothing meets the byte-identical upload: no row, not even an `erased` one
            assert repository.get(session, BlobId(blob_id)) is None
    store = S3BlobStore(S3StorageSettings.from_env())
    ingest = IngestService(store, session_factory=session_factory)
    project = ingest.create_project(name="Склад, повторно")
    # the SAME idempotency key as the original upload: its receipt went with the project
    outcome = ingest.upload_bundle(
        project_uid=project.project_uid, content=(BUNDLES / "pages_31.zip").read_bytes(),
        source_filename="pages_31.zip", display_title="АР, 31 страница", idempotency_key=IdempotencyKey("drill-seed-p31"))
    assert not outcome.replayed
    reborn = set(scalars(stand, "SELECT blob_id FROM input_manifest_entry WHERE version_uid = :v",
                         v=str(outcome.version.version_uid)))
    assert reborn == set(manifest)  # the identity derives from (sha256, size): the same bytes, the same id
    for blob_id, entry in manifest.items():
        row = rows(stand, "SELECT state, sha256, size_bytes, media_type FROM blob WHERE blob_id = :b", b=blob_id)
        assert row == [("available", entry["sha256"], entry["size_bytes"], entry["media_type"])]
        body = stand.client.get_object(Bucket=stand.bucket, Key=canonical_object_key_for_recovery(blob_id))["Body"].read()
        assert hashlib.sha256(body).hexdigest() == entry["sha256"]
    assert rows(stand, "SELECT count(*) FROM blob WHERE blob_id = ANY(:ids) AND created_at > "
                       "(SELECT occurred_at FROM audit_event WHERE event_type = 'erasure.completed')",
                ids=sorted(manifest)) == [(3,)]
    assert ingest.read_source_bytes(outcome.version.version_uid)[:4] == b"%PDF"


def test_a_stale_receipt_would_block_the_same_key_so_the_receipts_go_with_the_project(
    stand: Stand, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutation of the receipts step: a receipt left behind refuses the same key for the project that comes back."""
    monkeypatch.setattr(tool, "derive_receipts", lambda connection, closure, scope: ())
    h = Harness(stand, tmp_path, monkeypatch)
    assert h.plan_apply(tool)[0] == 0 and h.gone()
    assert count(stand, "command_record", "command_type = 'upload_source_document'") >= 1  # the receipt stayed
    ingest = IngestService(S3BlobStore(S3StorageSettings.from_env()), session_factory=create_session_factory(stand.engine))
    project = ingest.create_project(name="again")
    with pytest.raises(DomainError) as caught:
        ingest.upload_bundle(project_uid=project.project_uid, content=(BUNDLES / "pages_31.zip").read_bytes(),
                             source_filename="pages_31.zip", display_title="x",
                             idempotency_key=IdempotencyKey("drill-seed-p31"))
    assert caught.value.code == ErrorCode.IDEMPOTENCY_KEY_REUSE  # the stale receipt blocks the key


def test_the_reupload_check_can_fail_when_the_blob_rows_are_left_in_the_erased_state(
    stand: Stand, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutation of phase 4 (the ADR's rejected alternative 2): rows kept as `erased` make the upload meet a terminal row."""
    real = tool.phase_finish

    def keep_rows(engine: Engine, committed: Any, **kwargs: Any) -> None:
        with engine.begin() as connection:
            connection.execute(text("UPDATE public.blob SET state = 'erased' WHERE state = 'erasure_pending'"))
        # the tool's own completion event is not needed to show the upload
    monkeypatch.setattr(tool, "phase_finish", keep_rows)
    h = Harness(stand, tmp_path, monkeypatch)
    assert h.plan_apply(tool)[0] == 0
    monkeypatch.setattr(tool, "phase_finish", real)
    ingest = IngestService(S3BlobStore(S3StorageSettings.from_env()), session_factory=create_session_factory(stand.engine))
    project = ingest.create_project(name="again")
    with pytest.raises(Exception):
        ingest.upload_bundle(project_uid=project.project_uid, content=(BUNDLES / "pages_31.zip").read_bytes(),
                             source_filename="pages_31.zip", display_title="x",
                             idempotency_key=IdempotencyKey("a-different-key"))


# --- the isolation check can fail ------------------------------------------------------------------


def test_the_isolation_assertions_see_a_leak_that_the_tool_did_not_catch(
    stand: Stand, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutation: a tool that also deletes the empty project and has no `keep-unchanged` guard fails `assert_isolation`."""
    broken = mutant("keep-unchanged")
    empty = project_like(stand, "Пустой")
    real_delete = broken.delete_scope

    def leaking(connection: Any, closure: Any, scope: Any) -> Any:
        deleted = real_delete(connection, closure, scope)
        connection.execute(text("DELETE FROM public.project WHERE project_uid = :p"), {"p": empty})
        return deleted

    monkeypatch.setattr(broken, "delete_scope", leaking)
    erased = before_erase(stand, "Склад")
    code, out, err = Harness(stand, tmp_path, monkeypatch).plan_apply(broken)
    assert code == 0, (out, err)
    with pytest.raises(AssertionError):
        assert_isolation(stand, erased)


@pytest.mark.parametrize("what, statement, switch", [
    ("a custody event of the corpus", "DELETE FROM public.audit_event WHERE event_type = 'norm_custody.bound'",
     ("audit_event", "trg_audit_event_append_only")),
    ("a run-journal event of another project", "DELETE FROM public.audit_event WHERE event_type = 'audit_run.created'",
     ("audit_event", "trg_audit_event_append_only")),
    ("a Blob row that no project owns", "", None),
])
def test_the_verification_sees_a_journal_event_or_a_blob_the_delete_took_by_mistake(
    stand: Stand, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, what: str, statement: str,
    switch: tuple[str, str] | None
) -> None:
    """Mutation of the delete: it also removes ``what``; the real module refuses to commit, the copy without
    ``keep-unchanged`` commits and the row is gone (the test's own count shows it)."""
    if switch is None:  # a Blob outside the erase: an unreferenced one (a referenced one is protected by its foreign key)
        statement = f"DELETE FROM public.blob WHERE blob_id = '{orphan_blob(stand)}'"
        count_before = count(stand, "blob")
    else:
        count_before = count(stand, "audit_event")

    def leaking(module: types.ModuleType) -> None:
        real = module.delete_scope

        def wrapper(connection: Any, closure: Any, scope: Any) -> Any:
            deleted = real(connection, closure, scope)
            if switch:
                connection.execute(text(f"ALTER TABLE public.{switch[0]} DISABLE TRIGGER {switch[1]}"))
            connection.execute(text(statement))
            if switch:
                connection.execute(text(f"ALTER TABLE public.{switch[0]} ENABLE TRIGGER {switch[1]}"))
            return deleted

        monkeypatch.setattr(module, "delete_scope", wrapper)

    h = Harness(stand, tmp_path, monkeypatch, "Пустой")
    leaking(tool)
    h.checkpoint()
    code, out, err = h.plan_apply(tool)
    assert code == tool.EXIT_REFUSED and "would have changed data outside the project" in err, (what, err)
    assert state_of(stand) == h.before
    broken = mutant("keep-unchanged")
    leaking(broken)
    code, out, err = h.plan_apply(broken)
    assert code == 0, (out, err)
    after = count(stand, "blob") if switch is None else count(stand, "audit_event") - 2  # minus our two events
    assert after < count_before, what


# --- the owner, the permission, the actor ------------------------------------------------------------


def test_the_apply_as_a_role_that_does_not_own_the_tables_is_refused_and_changes_nothing(
    stand: Stand, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = Harness(stand, tmp_path, monkeypatch)
    sha = _line(h.dry(tool)[1], "plan-sha256")
    role = new_role(stand)
    h.checkpoint()
    monkeypatch.setenv("DATABASE_URL", stand.settings.url.set(
        username=role, password="probe-password").render_as_string(hide_password=False))
    try:
        code, out, err = h.apply(tool, sha)
    finally:
        monkeypatch.setenv("DATABASE_URL", stand.values["DATABASE_URL"])
        drop_role(stand, role)
    assert code == tool.EXIT_REFUSED and "does not own" in err and "the migrator" in err
    assert state_of(stand) == h.before and events(stand) == []


@pytest.mark.parametrize("reference", [None, "", "   ", "x" * 201, "two\nlines"])
def test_no_apply_and_no_resume_runs_without_a_usable_owner_permission_reference(
    stand: Stand, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reference: str | None
) -> None:
    h = Harness(stand, tmp_path, monkeypatch)
    h.checkpoint()
    code, out, err = h.plan_apply(tool, owner_permission_ref=reference)
    assert code == tool.EXIT_REFUSED and "--owner-permission-ref" in err and "R-146aj" in err
    assert state_of(stand) == h.before and not h.dump.exists()
    code, out, err = h.resume(tool, "era_01M5F21PBT7E8WRN3M61BDQFDD", owner_permission_ref=reference)
    assert code == tool.EXIT_REFUSED and "--owner-permission-ref" in err


def test_the_reference_is_recorded_as_given_and_the_dry_run_needs_none(stand: Stand, tmp_path: Path) -> None:
    target = project_like(stand, "Склад")
    assert invoke(tool, stand, "--project", target)[0] == 0  # asking for the plan to show the owner needs no permission
    sha = _line(invoke(tool, stand, "--project", target)[1], "plan-sha256")
    reference = "письмо владельца от 2026-10-26: стереть проект"
    code, out, err = invoke(tool, stand, *apply_flags(target, sha, tmp_path / "dump", owner_permission_ref=reference))
    assert code == 0, err
    assert [e[3]["owner_permission_ref"] for e in events(stand)] == [reference, reference]


# --- the stand after the erase works with the purge -----------------------------------------------


def test_a_whole_product_purge_after_an_erase_keeps_the_record_of_the_erasure(stand: Stand, tmp_path: Path) -> None:
    erased = do_erase(stand, tmp_path / "erase", "Школа")
    kept = digest_of(stand.engine, "audit_event", "event_type LIKE 'erasure.%'")
    assert kept[0] == 2
    steps = full_purge(purge, stand, tmp_path / "purge")
    assert steps["apply"][0] == 0 and steps["delete"][0] == 0, steps
    assert digest_of(stand.engine, "audit_event", "event_type LIKE 'erasure.%'") == kept
    assert erased.manifest.exists()


def test_without_the_keep_prefix_the_purge_stops_on_the_erasure_events(
    stand: Stand, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutation of the one edit in ``product_purge.py``: the purge refuses what nobody classified."""
    do_erase(stand, tmp_path / "erase", "Школа")
    monkeypatch.setattr(purge, "KEEP_EVENT_PREFIXES", ("norm_custody.", "executor.", "access."))
    before = state_of(stand)
    code, out, err = invoke(purge, stand, "plan")
    assert code == purge.EXIT_REFUSED and "event type(s) nobody classified" in err and "erasure.completed" in err
    assert state_of(stand) == before


# --- the closing message ---------------------------------------------------------------------------


def test_the_closing_message_says_what_an_erase_does_not_reach(stand: Stand, tmp_path: Path) -> None:
    erased = do_erase(stand, tmp_path, "Пустой")
    for needle in ("dumps", "OpenRouter", "disk blocks", "legal-hold", "Keep the manifest file"):
        assert needle in erased.out, needle
    assert f"manifest-sha256: {hashlib.sha256(erased.manifest.read_bytes()).hexdigest()}" in erased.out


# =================================================================================================
# Every guard shown able to fail
# =================================================================================================


@dataclass
class Scenario:
    guard: str
    says: str
    act: Callable[[types.ModuleType, Harness], tuple[int, str, str]]
    project: str = "Склад"
    prepare: Callable[[Stand, Harness], None] = lambda s, h: None
    patch: Callable[[pytest.MonkeyPatch, types.ModuleType, Harness], None] | None = None
    #: the exit code the guard produces (a refusal; a few sit after the commit and surface as FAILED)
    code: int = tool.EXIT_REFUSED
    #: the guard sits before ``COMMIT``: nothing at all changed
    unchanged: bool = True
    #: what the copy without the guard does, when that is more than "the refusal is gone"
    effect: Callable[[Stand, Harness, int, str, str], bool] | None = None
    #: guards deleted in BOTH runs (an earlier guard would refuse first)
    without: tuple[str, ...] = ()
    #: guards deleted only in the copy that shows the harm (a later guard would refuse instead)
    also: tuple[str, ...] = ()


def act_dry(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    return h.dry(m)


def act_apply(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    return h.plan_apply(m)


def act_apply_without(**flags: str | None) -> Callable[[types.ModuleType, Harness], tuple[int, str, str]]:
    return lambda m, h: h.plan_apply(m, **flags)


def _erased(s: Stand, h: Harness, code: int, out: str, err: str) -> bool:
    return code == 0 and h.gone()


def _planned(s: Stand, h: Harness, code: int, out: str, err: str) -> bool:
    return code == 0 and "plan-sha256:" in out


def act_names(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    return invoke(m, h.stand, "--project", h.target, database="some_other_database")


def act_ambient(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    import os

    os.environ["PGHOSTADDR"] = "127.0.0.1"
    try:
        return h.dry(m)
    finally:
        del os.environ["PGHOSTADDR"]


def act_not_owner(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    import os

    role = new_role(h.stand)
    previous = os.environ["DATABASE_URL"]
    os.environ["DATABASE_URL"] = h.stand.settings.url.set(
        username=role, password="probe-password").render_as_string(hide_password=False)
    try:
        return h.dry(m)
    finally:
        os.environ["DATABASE_URL"] = previous
        drop_role(h.stand, role)


def act_a_name(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    return invoke(m, h.stand, "--project", "Школа на 550 мест")


def act_never(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    return invoke(m, h.stand, "--project", NEVER)


def act_versioned(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    h.stand.client.put_bucket_versioning(Bucket=h.stand.bucket, VersioningConfiguration={"Status": "Enabled"})
    return h.dry(m)


def act_expert(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    return h.plan_apply(m, actor=EXPERT)


def act_ghost(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    return h.plan_apply(m, actor="ghost@example.com")


def act_no_digest(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    return h.apply(m, None)


def act_advisory(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    engine = create_database_engine(h.stand.settings)
    holder = engine.connect()
    holder.execute(text("SELECT pg_advisory_lock(hashtextextended(:n, 0))"), {"n": tool.ADVISORY_LOCK_NAME})
    try:
        return h.plan_apply(m)
    finally:
        holder.execute(text("SELECT pg_advisory_unlock_all()"))
        holder.close()
        engine.dispose()


def act_busy(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    engine = create_database_engine(h.stand.settings)
    holder = engine.connect()
    holder.execute(text("LOCK TABLE public.document IN ROW EXCLUSIVE MODE"))  # a writer, held until rollback
    try:
        return h.plan_apply(m)
    finally:
        holder.rollback()
        holder.close()
        engine.dispose()


def act_late_write(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    code, out, err = h.dry(m)
    assert code == 0, err
    sha = _line(out, "plan-sha256")
    sql(h.stand, "UPDATE project SET name = name || ' (late)' WHERE project_uid = :p", p=h.target)
    h.checkpoint()
    return h.apply(m, sha)


def act_crash_then(then: Callable[[types.ModuleType, Harness, str], tuple[int, str, str]]
                   ) -> Callable[[types.ModuleType, Harness], tuple[int, str, str]]:
    """Apply with phase 3 crashing (the database part commits), then run ``then`` with the erase id."""
    def act(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
        restore = crashing(m, "delete_objects")
        try:
            code, out, err = h.plan_apply(m)
        finally:
            restore()
        if code != tool.EXIT_FAILED:  # a guard before the commit refused: report that
            return code, out, err
        return then(m, h, _line(out, "erase-id"))
    return act


def after_phase_3(m: types.ModuleType, change: Callable[[Stand, Harness], None], h: Harness
                  ) -> Callable[[], None]:
    """Wrap ``m.delete_objects`` so ``change`` runs after the real objects phase."""
    real = m.delete_objects

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = real(*args, **kwargs)
        change(h.stand, h)
        return result

    m.delete_objects = wrapper
    return lambda: setattr(m, "delete_objects", real)


def _reference_pending_blob(s: Stand, h: Harness) -> None:
    """A row of another project that references a Blob waiting in erasure_pending (a late binding)."""
    blob = scalars(s, "SELECT blob_id FROM blob WHERE state = 'erasure_pending'")[0]
    version = scalars(s, "SELECT v.version_uid FROM document_version v JOIN document d USING (document_uid) "
                         "WHERE d.project_uid = :p", p=project_like(s, "Детский"))[0]
    sql(s, "INSERT INTO input_manifest_entry (version_uid, role, blob_id, sha256, size_bytes, media_type) "
           "SELECT :v, 'zz_probe', blob_id, sha256, size_bytes, media_type FROM blob WHERE blob_id = :b",
        v=version, b=blob)


def orphan_blob(s: Stand, *, last_state: str = "available") -> str:
    """An unreferenced Blob row, with its object, that no project owns."""
    body = b"an orphan blob that no row references and no erase owns"
    digest = hashlib.sha256(body).hexdigest()
    blob_id = "blob_" + "7ZZZZZZZZZZZZZZZZZZZZZZZZ9"
    sql(s, "INSERT INTO blob (blob_id, state, sha256, size_bytes, media_type) "
           "VALUES (:b, 'temporary', :h, :n, 'application/pdf')", b=blob_id, h=digest, n=len(body))
    for state in ("verifying", "available", "erasure_pending"):
        sql(s, "UPDATE blob SET state = :s WHERE blob_id = :b", s=state, b=blob_id)
        if state == last_state:
            break
    s.client.put_object(Bucket=s.bucket, Key=canonical_object_key_for_recovery(blob_id), Body=body,
                        ContentType="application/pdf", Metadata={
                            "blob-id": blob_id, "blob-role": "source_document", "content-sha256": digest,
                            "content-size": str(len(body))})
    return blob_id


def _mark_innocent_pending(s: Stand, h: Harness) -> None:
    """An unreferenced Blob, with its object, that something else moved to erasure_pending (not this erase's)."""
    h.notes["innocent"] = orphan_blob(s, last_state="erasure_pending")


def act_objects_still_referenced(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    def then(module: types.ModuleType, harness: Harness, erase_id: str) -> tuple[int, str, str]:
        _reference_pending_blob(harness.stand, harness)
        return harness.resume(module, erase_id)
    return act_crash_then(then)(m, h)


def act_phase_4_reference(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    restore = after_phase_3(m, _reference_pending_blob, h)
    try:
        return h.plan_apply(m)
    finally:
        restore()


def act_innocent_in_phase_4(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    restore = after_phase_3(m, _mark_innocent_pending, h)
    try:
        return h.plan_apply(m)
    finally:
        restore()


def act_resume_unknown(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    return h.resume(m, "era_01M5F21PBT7E8WRN3M61BDQFDD")


def act_resume_with_extra_pending(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    def then(module: types.ModuleType, harness: Harness, erase_id: str) -> tuple[int, str, str]:
        _mark_innocent_pending(harness.stand, harness)
        return harness.resume(module, erase_id)
    return act_crash_then(then)(m, h)


def act_resume_with_edited_manifest(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    def then(module: types.ModuleType, harness: Harness, erase_id: str) -> tuple[int, str, str]:
        path = harness.dump / erase_id / "manifest.json"
        path.write_text(path.read_text(encoding="utf-8").replace("application/pdf", "application/zip"), encoding="utf-8")
        return harness.resume(module, erase_id)
    return act_crash_then(then)(m, h)


def act_resume_with_edited_plan(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    def then(module: types.ModuleType, harness: Harness, erase_id: str) -> tuple[int, str, str]:
        path = harness.dump / erase_id / "plan.json"
        envelope = json.loads(path.read_text(encoding="utf-8"))
        envelope["plan"]["objects"].append(["blobs/ZZ/ZZ/ZZZZZZZZZZZZZZZZZZZZZZZZZZ", "temporary", "x"])
        path.write_text(json.dumps(envelope), encoding="utf-8")
        return harness.resume(module, erase_id)
    return act_crash_then(then)(m, h)


class _NoDelete:
    """An S3 client whose deletes are accepted and do nothing."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def delete_object(self, **kwargs: Any) -> dict[str, Any]:
        return {}

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def _leave_object_behind(mp: pytest.MonkeyPatch, m: types.ModuleType, h: Harness) -> None:
    real = purge.s3_client
    mp.setattr(purge, "s3_client", lambda settings: _NoDelete(real(settings)))


def _widen_keep(mp: pytest.MonkeyPatch, m: types.ModuleType, h: Harness) -> None:
    real = m.classify_blobs

    def widened(connection: Any, closure: Any, scope: Any) -> Any:
        exclusive, shared, keep_ids = real(connection, closure, scope)
        return exclusive, shared, set(keep_ids) | {fact.blob_id for fact in exclusive}

    mp.setattr(m, "classify_blobs", widened)


def _also_touch_accounts(mp: pytest.MonkeyPatch, m: types.ModuleType, h: Harness) -> None:
    real = m.delete_scope

    def touching(connection: Any, closure: Any, scope: Any) -> Any:
        deleted = real(connection, closure, scope)
        connection.execute(text("UPDATE public.app_user SET failed_sign_ins = 9 WHERE login = 'admin'"))
        return deleted

    mp.setattr(m, "delete_scope", touching)


def _put_the_project_back(mp: pytest.MonkeyPatch, m: types.ModuleType, h: Harness) -> None:
    real = m.delete_scope

    def returning(connection: Any, closure: Any, scope: Any) -> Any:
        deleted = real(connection, closure, scope)
        connection.execute(text("INSERT INTO public.project (project_uid, name) VALUES (:p, 'put back')"),
                           {"p": scope["project"][0]})
        return deleted

    mp.setattr(m, "delete_scope", returning)


def _prepare_cross_reference(s: Stand, h: Harness) -> None:
    """A run of another project that is a re-audit of this project's run (a cross-project reference)."""
    school_run = scalars(s, "SELECT run_id FROM audit_run WHERE project_uid = :p", p=h.target)[0]
    switched_off(s, "audit_run", "trg_audit_run_frozen_guard",
                 "UPDATE audit_run SET reaudit_of_run_id = :r WHERE project_uid = :o", r=school_run,
                 o=project_like(s, "legacy"))


def _prepare_shared_receipt(s: Stand, h: Harness) -> None:
    """A run of another project that carries the receipt of this project's run."""
    command = scalars(s, "SELECT command_id FROM audit_run WHERE project_uid = :p", p=h.target)[0]
    sql(s, "UPDATE audit_run SET command_id = :c WHERE project_uid = :o", c=command, o=project_like(s, "legacy"))


def _prepare_account_receipt(s: Stand, h: Harness) -> None:
    version = scalars(s, "SELECT v.version_uid FROM document_version v JOIN document d USING (document_uid) "
                         "WHERE d.project_uid = :p", p=h.target)[0]
    sql(s, "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint, state) "
           "VALUES ('cmd_01M5F21PBT7E8WRN3M61BDQFDD', 'approve_registration', 'zz-1', :f, 'in_progress')",
        f="a" * 64)
    sql(s, "UPDATE command_record SET state = 'succeeded', outcome = CAST(:o AS jsonb) "
           "WHERE command_id = 'cmd_01M5F21PBT7E8WRN3M61BDQFDD'", o=json.dumps({"version_uid": version}))


def _prepare_unsettled_blob(s: Stand, h: Harness) -> None:
    blob = sorted(exclusive_blobs(s, h.target))[0]
    switched_off(s, "blob", "trg_blob_state_guard", "UPDATE blob SET state = 'verifying' WHERE blob_id = :b", b=blob)


def _prepare_a_pending_blob(s: Stand, h: Harness) -> None:
    sql(s, "UPDATE blob SET state = 'erasure_pending' WHERE blob_id = :b",
        b=one_available_blob(s, blob_ids_of(s, h.target)))


def _prepare_delete_trigger(s: Stand, h: Harness) -> None:
    sql(s, "CREATE FUNCTION zz_noop() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN OLD; END $$")
    sql(s, "CREATE TRIGGER zz_delete BEFORE DELETE ON document FOR EACH ROW EXECUTE FUNCTION zz_noop()")


def _prepare_stray_schema(s: Stand, h: Harness) -> None:
    sql(s, "CREATE SCHEMA zz_stray")
    sql(s, "CREATE TABLE zz_stray.t (a int)")


def _unprotected_module_table(s: Stand, h: Harness) -> None:
    sql(s, "ALTER TABLE price_list_revision DROP CONSTRAINT fk_price_list_revision_project")


def _bucket_lost(s: Stand, h: Harness, blob: str) -> bool:
    return canonical_object_key_for_recovery(blob) not in bucket_profile(s.client, s.bucket)


def _probe_blob(s: Stand) -> str:
    return scalars(s, "SELECT blob_id FROM input_manifest_entry WHERE role = 'zz_probe'")[0]


SCENARIOS: tuple[Scenario, ...] = (
    Scenario("relations-recognised", "a relation the erase does not understand", act_dry,
             prepare=_prepare_stray_schema, effect=lambda s, h, c, o, e: _planned(s, h, c, o, e)),
    Scenario("classification-total", "classified as neither PRODUCT, KEEP nor MIXED: ['zz_throwaway']", act_dry,
             prepare=lambda s, h: sql(s, "CREATE TABLE zz_throwaway (a int)"), effect=lambda s, h, c, o, e: c == 0),
    Scenario("declaration-matches-coverage", "the classification is inconsistent", act_dry,
             patch=lambda mp, m, h: mp.setattr(purge, "TABLES", frozenset(TABLES - {"project"})),
             effect=lambda s, h, c, o, e: c == 0),
    Scenario("head-is-declared", "the tool was written for", act_dry,
             prepare=lambda s, h: sql(s, "UPDATE alembic_version SET version_num = '0099_a_later_migration'"),
             effect=lambda s, h, c, o, e: c == 0),
    Scenario("blob-columns-closed", "differ from blob_reference_audit's closed set", act_dry,
             prepare=lambda s, h: sql(s, "ALTER TABLE app_user_role ADD COLUMN zz_blob text REFERENCES blob (blob_id)"),
             effect=lambda s, h, c, o, e: c == 0),
    Scenario("closure-is-product", "is not the product tables the tool knows", act_dry,
             prepare=lambda s, h: sql(s, "ALTER TABLE app_user_role ADD COLUMN zz_project text "
                                         "REFERENCES project (project_uid)"),
             effect=lambda s, h, c, o, e: c == 0),
    Scenario("blob-refs-in-closure", "neither KEEP nor in the project closure", act_dry,
             prepare=_unprotected_module_table, without=("closure-is-product",),
             effect=lambda s, h, c, o, e: c == 0),
    Scenario("delete-triggers-known", "a DELETE trigger the erase does not know how to switch off", act_apply,
             prepare=_prepare_delete_trigger, effect=_erased),
    Scenario("owner-may-write", "does not own", act_not_owner, effect=lambda s, h, c, o, e: c == 0),
    Scenario("project-identity-shape", "must be a project identity", act_a_name,
             effect=lambda s, h, c, o, e: c == tool.EXIT_REFUSED and "is not a project of this database" in e),
    Scenario("project-exists", "is not a project of this database", act_never,
             effect=lambda s, h, c, o, e: c == 0),
    Scenario("scope-is-pure", "belongs to another project", act_apply, project="Школа",
             prepare=_prepare_cross_reference, also=("quiescent",),
             effect=lambda s, h, c, o, e: c == 0 and count(s, "audit_run", "project_uid = :p",
                                                           p=project_like(s, "legacy")) == 0),
    Scenario("quiescent", "work of this project is not terminal", act_dry, project="legacy",
             effect=lambda s, h, c, o, e: c == 0),
    Scenario("no-pending-erasure", "erasure_pending", act_dry, prepare=_prepare_a_pending_blob,
             effect=lambda s, h, c, o, e: c == 0),
    Scenario("receipts-are-product-commands", "not product commands", act_apply, prepare=_prepare_account_receipt,
             effect=lambda s, h, c, o, e: c == 0 and h.gone() and count(
                 s, "command_record", "command_id = 'cmd_01M5F21PBT7E8WRN3M61BDQFDD'") == 0),
    Scenario("receipts-not-shared", "also referenced by rows outside it", act_apply, project="Школа",
             prepare=_prepare_shared_receipt,
             effect=lambda s, h, c, o, e: c == tool.EXIT_FAILED and "foreign key" in e.lower() and not h.gone()),
    Scenario("blobs-available", "are not 'available'", act_dry, prepare=_prepare_unsettled_blob,
             effect=lambda s, h, c, o, e: c == 0),
    Scenario("bucket-unversioned", "is versioned", act_versioned, effect=lambda s, h, c, o, e: c == 0),
    Scenario("norm-owned-key", "the norm custody ledger owns", act_dry, patch=_widen_keep,
             effect=lambda s, h, c, o, e: c == 0),
    Scenario("actor-is-active-account", "must be the login of an active", act_ghost,
             effect=lambda s, h, c, o, e: c == tool.EXIT_FAILED and not h.gone()),
    Scenario("actor-is-admin", "must hold the admin role", act_expert, effect=_erased),
    Scenario("plan-digest-required", "needs --plan-sha256", act_no_digest, also=("plan-unchanged",), effect=_erased),
    Scenario("reason-closed-list", "--reason must be one of", act_apply_without(reason="the client wrote to me"),
             effect=lambda s, h, c, o, e: c == 0 and events(s)[0][3]["reason_code"] == "the client wrote to me"),
    Scenario("owner-permission-ref", "--owner-permission-ref is required", act_apply_without(owner_permission_ref=None),
             effect=_erased),
    Scenario("dump-dir-required", "--dump-dir is required", act_apply_without(dump_dir=None),
             effect=lambda s, h, c, o, e: c == tool.EXIT_FAILED and not h.gone()),
    Scenario("names-match", "the typed names are not the connected ones", act_names,
             effect=lambda s, h, c, o, e: c == 0),
    Scenario("no-ambient-libpq", "can redirect the connection that DATABASE_URL names", act_ambient,
             effect=lambda s, h, c, o, e: c == 0),
    Scenario("erase-lock-free", "another erase holds the lock", act_advisory, effect=_erased),
    Scenario("lock-available", "could not lock the tables", act_busy,
             patch=lambda mp, m, h: mp.setattr(m, "LOCK_TIMEOUT", "300ms"),
             effect=lambda s, h, c, o, e: c == tool.EXIT_FAILED and not h.gone()),
    Scenario("plan-unchanged", "changed since the plan that was approved", act_late_write, effect=_erased),
    Scenario("blobs-pending", "moved to erasure_pending", act_apply, prepare=_prepare_unsettled_blob,
             without=("blobs-available",),
             effect=lambda s, h, c, o, e: c == tool.EXIT_FAILED and h.gone()),
    Scenario("keep-unchanged", "would have changed data outside the project", act_apply, patch=_also_touch_accounts,
             effect=lambda s, h, c, o, e: c == 0 and rows(
                 s, "SELECT failed_sign_ins FROM app_user WHERE login = 'admin'") == [(9,)]),
    Scenario("project-emptied", "rows of the project remain after the erase", act_apply, patch=_put_the_project_back,
             effect=lambda s, h, c, o, e: c == 0 and not h.gone()),
    Scenario("triggers-restored", "a trigger's state differs after the erase", act_apply,
             prepare=lambda s, h: sql(s, "ALTER TABLE document_version DISABLE TRIGGER trg_document_version_immutable"),
             effect=_erased),
    Scenario("object-key-shape", "this tool deletes exact keys it can derive", act_resume_with_edited_plan,
             code=tool.EXIT_FAILED, unchanged=False, without=("resume-plan-file-matches",),
             effect=lambda s, h, c, o, e: c == 0 and STRAY_KEY not in bucket_profile(s.client, s.bucket)),
    Scenario("objects-unreferenced", "a row references Blob(s) of the erase list", act_objects_still_referenced,
             code=tool.EXIT_FAILED, unchanged=False, also=("pending-unreferenced",),
             effect=lambda s, h, c, o, e: c == tool.EXIT_FAILED and _bucket_lost(s, h, _probe_blob(s))),
    Scenario("objects-gone", "is still in the bucket after its delete", act_apply, patch=_leave_object_behind,
             code=tool.EXIT_FAILED, unchanged=False,
             effect=lambda s, h, c, o, e: c == 0 and set(bucket_profile(s.client, s.bucket)) == set(h.before["bucket"])),
    Scenario("finish-matches-manifest", "are not the manifest of", act_innocent_in_phase_4, code=tool.EXIT_FAILED,
             unchanged=False, also=("pending-cleared",),
             effect=lambda s, h, c, o, e: c == 0 and count(s, "blob", "state = 'erasure_pending'") == 1),
    Scenario("pending-unreferenced", "row(s) reference Blob(s) of the manifest", act_phase_4_reference,
             code=tool.EXIT_FAILED, unchanged=False,
             effect=lambda s, h, c, o, e: c == tool.EXIT_FAILED and "foreign key" in e.lower()),
    Scenario("pending-cleared", "still pending; rolled back", act_innocent_in_phase_4, code=tool.EXIT_FAILED,
             unchanged=False, without=("finish-matches-manifest",),
             effect=lambda s, h, c, o, e: c == 0 and count(s, "blob", "state = 'erasure_pending'") == 1),
    Scenario("erase-id-known", "has no erasure.requested event", act_resume_unknown,
             effect=lambda s, h, c, o, e: c == tool.EXIT_FAILED),
    Scenario("resume-manifest-file-matches", "differs from the manifest", act_resume_with_edited_manifest, unchanged=False,
             effect=lambda s, h, c, o, e: c == 0 and hashlib.sha256(
                 next(h.dump.glob("*/manifest.json")).read_bytes()).hexdigest() != events(s)[1][3]["manifest_sha256"]),
    Scenario("resume-manifest-matches", "recorded when it committed", act_resume_with_extra_pending, unchanged=False,
             also=("resume-manifest-file-matches",),
             effect=lambda s, h, c, o, e: c == tool.EXIT_FAILED and _bucket_lost(s, h, h.notes["innocent"])),
    Scenario("resume-plan-file-matches", "is not the plan era_", act_resume_with_edited_plan, unchanged=False,
             also=("object-key-shape",),
             effect=lambda s, h, c, o, e: c == 0 and STRAY_KEY not in bucket_profile(s.client, s.bucket)),
)


def test_every_guard_in_the_module_has_a_scenario() -> None:
    body = SOURCE.read_text(encoding="utf-8")
    markers = re.findall(r"^[ \t]*# >>> guard: ([a-z-]+)$", body, re.MULTILINE)
    assert len(markers) == len(set(markers)) == len(SCENARIOS)
    assert sorted(markers) == sorted(s.guard for s in SCENARIOS)
    for name in markers:
        assert len(re.findall(rf"^[ \t]*# <<< guard: {re.escape(name)}$", body, re.MULTILINE)) == 1


def _setup(scenario: Scenario, stand: Stand, tmp_path: Path, mp: pytest.MonkeyPatch) -> Harness:
    h = Harness(stand, tmp_path, mp, scenario.project)
    scenario.prepare(stand, h)
    h.checkpoint()
    return h


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s.guard for s in SCENARIOS])
def test_the_guard_refuses_and_a_refusal_before_the_commit_changes_nothing(
    scenario: Scenario, stand: Stand, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = _setup(scenario, stand, tmp_path, monkeypatch)
    base = mutant(*scenario.without) if scenario.without else tool
    if scenario.patch:
        scenario.patch(monkeypatch, base, h)
    code, out, err = scenario.act(base, h)
    assert code == scenario.code, (code, out, err)
    assert scenario.says in err, err
    if scenario.unchanged:
        assert state_of(stand) == h.before, "a refusal must leave the database and the bucket as they were"
        assert not h.dump.exists() or not any(h.dump.iterdir()), "a refusal must leave no plan or manifest file"
        assert events(stand) == []
    else:
        names = set(bucket_profile(stand.client, stand.bucket))
        assert STRAY_KEY in names and set(stand.summary["norm_keys"]) <= names


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s.guard for s in SCENARIOS])
def test_deleting_the_guard_removes_the_refusal_and_lets_the_harm_through(
    scenario: Scenario, stand: Stand, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = _setup(scenario, stand, tmp_path, monkeypatch)
    broken = mutant(*scenario.without, scenario.guard, *scenario.also)
    if scenario.patch:
        scenario.patch(monkeypatch, broken, h)
    code, out, err = scenario.act(broken, h)
    assert scenario.says not in err, (
        f"the {scenario.guard} guard was deleted and the refusal happened anyway, so the scenario "
        f"was never testing that guard: {err}")
    if scenario.effect is not None:
        assert scenario.effect(stand, h, code, out, err), (
            f"{scenario.guard}: the copy without the guard did not do what the guard prevents "
            f"(exit {code}): {err or out[-300:]}")


def test_each_of_two_guards_in_a_row_refuses_on_its_own() -> None:
    """The layered pairs: deleting one alone still refuses (with the other's message); only the pair lets the harm through."""
    pairs = {s.guard: s.also for s in SCENARIOS if s.also} | {s.guard: s.without for s in SCENARIOS if s.without}
    assert set(pairs) == {
        "scope-is-pure", "plan-digest-required", "objects-unreferenced", "finish-matches-manifest",
        "blob-refs-in-closure", "blobs-pending", "pending-cleared", "object-key-shape", "resume-plan-file-matches",
        "resume-manifest-matches",
    }


@pytest.mark.parametrize("deleted, says", [
    (("plan-digest-required",), "changed since the plan that was approved"),
    (("scope-is-pure",), "work of this project is not terminal"),
])
def test_deleting_one_guard_of_a_pair_leaves_the_other_refusing(
    deleted: tuple[str, ...], says: str, stand: Stand, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = next(s for s in SCENARIOS if s.guard == deleted[0])
    h = _setup(scenario, stand, tmp_path, monkeypatch)
    code, out, err = scenario.act(mutant(*scenario.without, scenario.guard), h)
    assert code == tool.EXIT_REFUSED and says in err, err
    assert state_of(stand) == h.before
