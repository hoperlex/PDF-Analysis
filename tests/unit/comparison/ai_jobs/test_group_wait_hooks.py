"""`EXEC2-FOLLOWUP-01` (H1): the wait sweep ends a comparison job the way its own method ends it.

Every handler answers ``CallRefused(no_executor_online)`` with ``ComparisonAiJobService.pause_for_spend`` -- the job ends ``failed`` -- and three
methods do more in the same transaction. The sweep used to call only ``pause_for_spend``, so a ``stage_review`` job left its run, its step and
its unit running for ever and a ``report`` job left its report ``running`` under a failed job. These tests drive the sweep with **real hooks over
the real repositories' code** (recording sessions stand in for the database), for:

* ``stage_review`` -- against ``StageAiRuntime._failed``, the in-call path itself, run on the same facts: the unit at work fails, the run and its
  step fail, the pending units are cancelled, **then** the job ends;
* ``report`` -- through the real ``sync_report``: the report row is walked to ``failed`` with the job's failure reason, **after** the job ended;
* ``sheet_changes`` -- the pair a handler would have moved ``running -> queued`` is moved;
* ``pair_check`` and ``spec`` -- nothing more, as their handlers do nothing more.

Written and **not run** in EXEC-2 (`R-149d`). The SQL of the new stage statements is shown by its text and by what it is asked; it has not met
PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.comparison.ai_jobs.group_waits import ENDED_BY_PAUSE_ONLY, ComparisonGroupWaitSweep
from auditmanager.comparison.ai_jobs.model import METHODS
from auditmanager.comparison.ai_jobs.repository import PendingWait
from auditmanager.comparison.ai_sheets.repository import AiSheetRepository
from auditmanager.comparison.group_wait_hooks import build_group_wait_sweep, end_hooks
from auditmanager.comparison.report.repository import ReportRepository
from auditmanager.comparison.spend.errors import REASON_NO_EXECUTOR_ONLINE
from auditmanager.comparison.spend.model import JOB_KEY
from auditmanager.comparison.stage_ai.repository import StageAiRepository
from auditmanager.comparison.stage_ai.runtime import StageAiRuntime
from auditmanager.executors.public import MemberFacts

BASE = datetime(2026, 11, 3, 9, 0, tzinfo=timezone.utc)
GROUP_REVISION = "exgr_01"
JOB, RUN, UNIT, PROJECT, REPORT, PAIR = "cmj_01", "scr_01", "saunit_01", "prj_01", "crt_01", "ctp_01"
REASON = REASON_NO_EXECUTOR_ONLINE
LIMIT = 1800.0
DARK = [
    MemberFacts(connection_id="exc_A", tie_break_order=None, revision_is_snapshot=True, archived=False, served=True, probed_ok=True,
                runner_online=False, capacity=1, used=0),
]


# --- the wiring -------------------------------------------------------------------------------------------------------------------


def test_every_method_is_swept_by_the_sweep_the_worker_runs_and_each_has_its_hook_or_is_pause_only() -> None:
    hooks = end_hooks()
    assert set(hooks) | ENDED_BY_PAUSE_ONLY == set(METHODS), "a method added to the core must be given a hook or be declared pause-only"
    assert set(hooks) & ENDED_BY_PAUSE_ONLY == set()
    assert build_group_wait_sweep(lambda: None).methods == tuple(sorted(METHODS))  # type: ignore[arg-type]


# --- stage_review: the in-call path and the hook, on the same facts -------------------------------------------------------------------


class StageSession:
    """A database that answers the one SELECT of ``end_without_executor`` with the units at work, writes the unit it fails into ``events`` (so
    its place among the other writes is the order they happen in) and records every statement."""

    def __init__(self, working: list[dict[str, Any]], events: list[tuple[Any, ...]] | None = None) -> None:
        self.working, self.events, self.statements = working, [] if events is None else events, []

    def execute(self, statement: Any, parameters: Any = None) -> Any:
        sql = " ".join(str(statement).split())
        params = dict(parameters or {})
        self.statements.append((sql, params))
        if sql.startswith("UPDATE stage_ai_unit SET state='failed'"):
            self.events.append(("unit", params["unit"], "failed", params["reason"]))
        rows = self.working if sql.startswith("SELECT stage_ai_unit_id, kind FROM stage_ai_unit") else []

        class Result:
            def mappings(self) -> list[dict[str, Any]]:
                return rows

        return Result()

    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...


class Recorder(StageAiRepository):
    """The stage repository with its writers replaced by records, so the order of what the in-call path and the hook write can be compared."""

    def __init__(self, events: list[tuple[Any, ...]]) -> None:
        self.events = events

    def run(self, session: Any, run_id: str) -> dict[str, Any]:
        return {"project_uid": PROJECT, "comparison_ai_job_id": JOB}

    def update_unit(self, session: Any, unit_id: str, *, payload: Any, state: str, reason: str | None = None, job_id: str | None = None) -> None:
        self.events.append(("unit", unit_id, state, reason))

    def fail_run(self, session: Any, *, run_id: str, phase: str | None, reason: str) -> None:
        self.events.append(("fail_run", run_id, phase, reason))

    def cancel_pending_units(self, session: Any, run_id: str, *, excluding_job_id: str | None = None, excluding_unit_id: str | None = None) -> int:
        self.events.append(("cancel_pending", run_id))
        return 0


def in_call_events() -> list[tuple[Any, ...]]:
    """What ``StageAiRuntime._failed`` writes when the call it was making is refused ``no_executor_online``."""
    events: list[tuple[Any, ...]] = []
    runtime = StageAiRuntime(lambda: StageSession([]), repository=Recorder(events))  # type: ignore[arg-type]
    item = SimpleNamespace(project_uid=PROJECT, payload={JOB_KEY: JOB}, require_current=lambda session: None)
    jobs = SimpleNamespace(fail=lambda session, job_id, reason: events.append(("job_fail", job_id, reason)))
    unit = {"stage_ai_unit_id": UNIT, "kind": "review", "payload": {}, "stage_chain_run_id": RUN}
    outcome = runtime._failed(item, RUN, unit, jobs, JOB, REASON)
    assert getattr(outcome, "reason", None) == REASON
    return events


def hook_events(working: list[dict[str, Any]], *, run_id: str | None = RUN) -> tuple[list[tuple[Any, ...]], StageSession]:
    """What the sweep's hook writes, then the job layer's ending, for the same unit at work."""
    events: list[tuple[Any, ...]] = []
    session = StageSession(working, events)
    hook = end_hooks(stages=Recorder(events))["stage_review"]
    assert hook.before is not None and hook.after is None
    job = SimpleNamespace(job_id=JOB, stage_chain_run_id=run_id, method="stage_review")
    hook.before(session, job)  # type: ignore[arg-type]
    events.append(("job_fail", JOB, REASON))
    return events, session


def test_a_stage_review_job_is_ended_by_the_sweep_as_the_runtime_ends_it_unit_run_step_pending_units_then_the_job() -> None:
    expected = in_call_events()
    assert [event[0] for event in expected] == ["unit", "fail_run", "cancel_pending", "job_fail"], "the in-call order"
    events, _ = hook_events([{"stage_ai_unit_id": UNIT, "kind": "review"}])
    assert events == expected, "the unit at work, the run and its step, the pending units, then the job: the same writes in the same order"


def test_the_step_of_the_phase_that_was_at_work_is_failed_with_the_run() -> None:
    for kind in ("review", "classify", "synthesize"):
        events, _ = hook_events([{"stage_ai_unit_id": UNIT, "kind": kind}])
        assert ("fail_run", RUN, kind, REASON) in events


def test_a_job_none_of_whose_units_is_at_work_still_fails_its_run_with_no_step_and_cancels_what_waits() -> None:
    events, _ = hook_events([])
    assert events == [("fail_run", RUN, None, REASON), ("cancel_pending", RUN), ("job_fail", JOB, REASON)]


def test_the_units_looked_for_are_the_jobs_own_and_only_the_ones_at_work_and_are_locked_first() -> None:
    _, session = hook_events([{"stage_ai_unit_id": UNIT, "kind": "review"}])
    sql, params = session.statements[0]
    assert params == {"run": RUN, "job": JOB}
    assert "comparison_ai_job_id=:job" in sql and "state='running'" in sql and sql.endswith("FOR UPDATE")


def test_a_job_with_no_stage_run_is_given_no_stage_write() -> None:
    events, session = hook_events([{"stage_ai_unit_id": UNIT, "kind": "review"}], run_id=None)
    assert events == [("job_fail", JOB, REASON)] and session.statements == []


# --- report: sync_report after the job ended ----------------------------------------------------------------------------------------


class Reports(ReportRepository):
    def __init__(self, events: list[tuple[Any, ...]], *, linked: bool = True, state: str = "running") -> None:
        self.events, self.linked, self.state = events, linked, state

    def by_job(self, session: Any, job_id: str) -> Any:
        return SimpleNamespace(report_id=REPORT) if self.linked else None

    def get(self, session: Any, report_id: str, *, lock: bool = False) -> Any:
        self.events.append(("report_lock", report_id))
        return SimpleNamespace(report_id=report_id, state=self.state, job_id=JOB, stage="analysis")

    def move(self, session: Any, report_id: str, *, from_states: Any, to_state: str, stage: str | None = None, failure_reason: str | None = None) -> bool:
        self.events.append(("report_move", report_id, tuple(from_states), to_state, failure_reason))
        return True


class JobRows:
    """``AiJobRepository.get`` after the job ended: failed, with the reason the job layer gave it."""

    def __init__(self, events: list[tuple[Any, ...]]) -> None:
        self.events = events

    def get(self, session: Any, job_id: str, *, lock: bool = False) -> Any:
        self.events.append(("job_read", job_id))
        return SimpleNamespace(job_id=job_id, state="failed", failure_reason=REASON)


def test_a_report_job_is_ended_by_the_sweep_and_its_report_row_is_walked_to_failed_with_the_jobs_reason() -> None:
    events: list[tuple[Any, ...]] = []
    hook = end_hooks(reports=Reports(events), jobs=JobRows(events))["report"]  # type: ignore[arg-type]
    assert hook.before is None and hook.after is not None
    hook.after(None, SimpleNamespace(job_id=JOB, method="report"))  # type: ignore[arg-type]
    assert events[0] == ("job_read", JOB), "the report follows the job as it is now, not as it was read before it ended"
    assert ("report_move", REPORT, ("running",), "failed", REASON) in events


def test_a_report_that_is_not_linked_to_the_job_is_left_alone() -> None:
    events: list[tuple[Any, ...]] = []
    hook = end_hooks(reports=Reports(events, linked=False), jobs=JobRows(events))["report"]  # type: ignore[arg-type]
    hook.after(None, SimpleNamespace(job_id=JOB, method="report"))  # type: ignore[arg-type]
    assert events == []


# --- sheet_changes: the pair a handler was at goes back to queued -----------------------------------------------------------------------


class Sheets(AiSheetRepository):
    def __init__(self, events: list[tuple[Any, ...]], states: dict[str, str]) -> None:
        self.events, self.states = events, states

    def items_of_job(self, session: Any, job_id: str) -> list[Any]:
        return [SimpleNamespace(pair_id=pair, state=state) for pair, state in self.states.items()]

    def move_item(self, session: Any, *, job_id: str, pair_id: str, from_states: Any, to_state: str, **kw: Any) -> bool:
        self.events.append(("move_item", job_id, pair_id, tuple(from_states), to_state))
        return True


def test_a_sheet_changes_job_moves_each_pair_that_was_running_back_to_queued_and_no_other() -> None:
    events: list[tuple[Any, ...]] = []
    hook = end_hooks(sheets=Sheets(events, {"p1": "running", "p2": "queued", "p3": "done", "p4": "running"}))["sheet_changes"]
    assert hook.before is None and hook.after is not None
    hook.after(None, SimpleNamespace(job_id=JOB, method="sheet_changes"))  # type: ignore[arg-type]
    assert events == [
        ("move_item", JOB, "p1", ("running",), "queued"), ("move_item", JOB, "p4", ("running",), "queued"),
    ]


# --- through the sweep: the method decides what is written ---------------------------------------------------------------------------------


class OneJob:
    """A job repository with one expired offline job of ``method``; its ending is the job layer's, recorded in the shared event list."""

    def __init__(self, events: list[tuple[Any, ...]], method: str) -> None:
        self.events, self.method = events, method
        self.row = PendingWait(JOB, BASE + timedelta(seconds=1), method, GROUP_REVISION, "runner_offline", True)

    def pending_waits(self, session: Any, *, methods: Any, offline_seconds: float, batch_size: int, after: Any = None) -> list[PendingWait]:
        return [self.row] if self.method in methods and after is None else []

    def lock_live_items(self, session: Any, job_id: str) -> bool:
        return True

    def lock_pending_wait(self, session: Any, job_id: str, *, offline_seconds: float) -> PendingWait:
        return self.row

    def get(self, session: Any, job_id: str, *, lock: bool = False) -> Any:
        return SimpleNamespace(job_id=job_id, method=self.method, stage_chain_run_id=RUN, state="running")


class Ends:
    def __init__(self, events: list[tuple[Any, ...]]) -> None:
        self.events = events

    def pause_for_spend(self, session: Any, job_id: str, spend_reason: str) -> bool:
        self.events.append(("job_fail", job_id, spend_reason))
        return True


@pytest.mark.parametrize(("method", "expected"), [
    ("pair_check", [("job_fail", JOB, REASON)]),
    ("spec", [("job_fail", JOB, REASON)]),
    ("sheet_changes", [("job_fail", JOB, REASON), ("move_item", JOB, "p1", ("running",), "queued")]),
    ("report", [("job_fail", JOB, REASON), ("job_read", JOB), ("report_lock", REPORT), ("report_move", REPORT, ("running",), "failed", REASON)]),
    ("stage_review", [("unit", UNIT, "failed", REASON), ("fail_run", RUN, "review", REASON), ("cancel_pending", RUN), ("job_fail", JOB, REASON)]),
])
def test_the_sweep_ends_each_method_with_exactly_what_its_own_handler_writes(
    monkeypatch: pytest.MonkeyPatch, method: str, expected: list[tuple[Any, ...]],
) -> None:
    from auditmanager.executors import public

    events: list[tuple[Any, ...]] = []
    monkeypatch.setattr(public, "group_revision_of", lambda session, revision_id, groups=None: SimpleNamespace(group_revision_id=revision_id))
    monkeypatch.setattr(public, "member_facts", lambda session, revision, repository=None: DARK)
    stage_session = StageSession([{"stage_ai_unit_id": UNIT, "kind": "review"}], events)
    hooks = end_hooks(
        jobs=JobRows(events), sheets=Sheets(events, {"p1": "running"}), reports=Reports(events), stages=Recorder(events),  # type: ignore[arg-type]
    )
    sweep = ComparisonGroupWaitSweep(
        lambda: _Open(stage_session), hooks=hooks, repository=OneJob(events, method), service=Ends(events),  # type: ignore[arg-type]
    )
    report = sweep.sweep(LIMIT)
    assert report.expired == 1 and report.failed == 0
    assert events == expected


class _Open:
    """A session that is its own context manager, so the sweep can open and close it."""

    def __init__(self, session: StageSession) -> None:
        self._session = session

    def __enter__(self) -> StageSession:
        return self._session

    def __exit__(self, *exc: object) -> bool:
        return False
