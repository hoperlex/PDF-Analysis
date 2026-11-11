"""`RUN-DELETE-01`: every reader that LISTS or PICKS runs leaves a deleted run out; every reader of ONE run, of the work and of the money keeps it.

The classification is the one in ``docs/program/tasks/RUN-DELETE-01.md``, written here as two tables the statements are checked against:

* ``EXCLUDED`` -- a list of runs, a "the newest run that ..." pick, or a display aggregate of runs. Each statement names ``audit_run_deletion``
  (a ``NOT EXISTS`` over the tombstone table), so a run an expert deleted from the run lists is not in its answer;
* ``KEPT`` -- a read of one run by its identity, the workers' and the executors' own reads, the reconciliation, and the accounting of cost.
  None names ``audit_run_deletion``: the tombstone hides a run from a list, it does not make the run not exist, and a run that is executing can
  never be deleted (the command refuses every state but partial, failed and cancelled), so a worker never meets one.

The guard is a **static** one (the SQL text), and it is shown able to fail below: the checker reports a statement that lost its clause, and a
statement that gained one it must not have. The behaviour -- what ``listRuns``, the audit state, the dashboard and the execution queue answer after
a delete -- is held on real PostgreSQL by ``tests/integration/runs/test_delete_run.py``.
"""

from __future__ import annotations

import importlib
from typing import Any

import pytest

TOMBSTONE = "audit_run_deletion"

#: (module, attribute holding the SQL text or a ``text()`` of it, why it is a list, a pick or a display aggregate)
EXCLUDED: tuple[tuple[str, str, str], ...] = (
    ("auditmanager.runs.repository", "_LIST_RUNS_FOR_VERSION", "listRuns, and every walk of a version's runs newest first"),
    ("auditmanager.dashboard.repository", "_RUNS_BY_STATE", "the dashboard's runs by state"),
    ("auditmanager.dashboard.audit_state", "_RESULT_RUN_RULES", "the result run of a document's audit state"),
    ("auditmanager.schedule.service", "_FACTS", "the result run behind «График работ»'s checked documents"),
    ("auditmanager.execution.public", "_QUEUE", "the execution queue (a list of the jobs of runs)"),
    ("auditmanager.execution.public", "_OVERVIEW", "the queue's counts by state"),
    ("auditmanager.execution.eta", "_HISTORY", "the durations the estimate is made of"),
    ("auditmanager.precedents.run_pass.reads", "_TO_SCHEDULE", "the runs a «Прецеденты» pass is started for"),
    ("auditmanager.precedents.run_pass.reads", "_REFRESHABLE", "the runs a «Прецеденты» pass is refreshed for"),
)

#: The reads that must NOT carry the clause.
KEPT: tuple[tuple[str, str, str], ...] = (
    ("auditmanager.runs.repository", "_SELECT_RUN", "one run by its identity: getRunStatus still answers a deleted run"),
    ("auditmanager.runs.repository", "_STALE_IN_STATE", "the reconciliation of runs stranded in queued or running (never deletable)"),
    ("auditmanager.runs.repository", "_COST_SUMMARY", "what a run cost: money spent stays counted"),
    ("auditmanager.dashboard.repository", "_SPEND", "the deployment's spend"),
    ("auditmanager.dashboard.repository", "_SPEND_IN_PROJECT", "a project's spend"),
    ("auditmanager.dashboard.audit_state", "_ACTIVE_RUN_RULE", "the run in flight (never deletable)"),
    ("auditmanager.execution.public", "_QUEUE_ITEM", "one queue item by its job identity"),
    ("auditmanager.execution.public", "_JOURNAL_ALL", "the journal is the audit trail and keeps every event"),
    ("auditmanager.execution.public", "_JOURNAL_RUN", "the journal of one run"),
    ("auditmanager.execution.eta", "_RUN_FACTS", "the facts of one run's estimate, by identity"),
    ("auditmanager.precedents.run_pass.reads", "_RUN", "one run by its identity"),
)


def _sql(module: str, attribute: str) -> str:
    value: Any = getattr(importlib.import_module(module), attribute)
    return str(value)


def mentions_tombstone(sql: str) -> bool:
    return TOMBSTONE in sql


def classification_problems(
    excluded: tuple[tuple[str, str, str], ...], kept: tuple[tuple[str, str, str], ...], read: Any = _sql,
) -> list[str]:
    """What is wrong with the two tables against the statements they name (empty when both hold)."""
    problems = [
        f"{module}.{attribute} ({why}) does not name {TOMBSTONE}"
        for module, attribute, why in excluded if not mentions_tombstone(read(module, attribute))
    ]
    problems += [
        f"{module}.{attribute} ({why}) names {TOMBSTONE} and must not"
        for module, attribute, why in kept if mentions_tombstone(read(module, attribute))
    ]
    return problems


def test_every_list_or_pick_of_runs_leaves_a_deleted_run_out_and_every_direct_read_keeps_it() -> None:
    assert classification_problems(EXCLUDED, KEPT) == []


def test_the_guard_reports_a_list_that_lost_its_clause() -> None:
    """Shown able to fail: the same checker, a reader that reads the run list without the tombstone condition."""
    stale = {("auditmanager.runs.repository", "_LIST_RUNS_FOR_VERSION"): "SELECT run_id FROM audit_run WHERE version_uid = :v"}

    def read(module: str, attribute: str) -> str:
        return stale.get((module, attribute)) or _sql(module, attribute)

    problems = classification_problems(EXCLUDED, KEPT, read)
    assert problems == [
        "auditmanager.runs.repository._LIST_RUNS_FOR_VERSION (listRuns, and every walk of a version's runs newest first) "
        f"does not name {TOMBSTONE}"
    ]


def test_the_guard_reports_a_direct_read_that_gained_the_clause() -> None:
    gained = {("auditmanager.runs.repository", "_SELECT_RUN"): f"SELECT * FROM audit_run r WHERE NOT EXISTS (SELECT 1 FROM {TOMBSTONE})"}

    def read(module: str, attribute: str) -> str:
        return gained.get((module, attribute)) or _sql(module, attribute)

    problems = classification_problems(EXCLUDED, KEPT, read)
    assert len(problems) == 1 and "_SELECT_RUN" in problems[0] and "must not" in problems[0]


@pytest.mark.parametrize("module", sorted({module for module, _, _ in (*EXCLUDED, *KEPT)}))
def test_every_named_statement_exists(module: str) -> None:
    for owner, attribute, _ in (*EXCLUDED, *KEPT):
        if owner == module:
            assert _sql(owner, attribute).strip(), f"{owner}.{attribute} is empty"
