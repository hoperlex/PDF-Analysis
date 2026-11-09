"""`HOSTS-BACKEND-01` (ADR-0028 decisions 4, 5 and 15): a run frozen with a ``stage_plan`` is bound by cell in the claim transaction, or waits.

No database: a recording session and monkeypatched executors seams. What is proved: a pending planned run takes the planned path (not the group path, not the
connection path); **a run that waits spends no attempt** (the claim raises before the Attempt, the Lease and the Job move are written, and nothing at all is
written); every pool a cell might be bound in is locked, in the order the decision reads them, **before** the control row, the run and the job; a bound planned run's
retry holds its own pools and is refused when one is full; the sweep keeps a planned run's wait true, ends only a ``model_unavailable`` wait that outlived the
limit, never a capacity wait, and clears a wait that nothing holds any more; a process that does not dispatch planned runs refuses one before any lock. The same
paths on PostgreSQL (the lock, the trigger, the attempt budget) are ``tests/integration/executors/test_hosts_backend.py``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.executors import public as executors_public
from auditmanager.executors.cell_binding import BindOutcome, BoundCell, CellRequest, CellWait
from auditmanager.jobs import repository as jobs
from auditmanager.jobs.repository import ExecutionNotClaimed, GroupDispatchWaiting, JobRepository
from auditmanager.shared.errors import DomainError, ErrorCode

RUN = "run_01M2545JSD15ETSNNV904X991K"
PLAN = {"cells": [{"cell_key": "text:main", "model_id": "claude-opus-5-5", "access": "subscription"}]}
POOL_A, POOL_B, POOL_C = ("exh_01M2545JSD15ETSNNV904X991" + tail + ":claude_code" for tail in ("A", "B", "C"))


class _Result:
    def __init__(self, row: Any = None) -> None:
        self.row = row

    def first(self) -> Any:
        return self.row

    def scalar_one(self) -> Any:
        return self.row

    def scalar_one_or_none(self) -> Any:
        return self.row


class Session:
    """Answers the claim's first read with a planned run's binding row and records every statement."""

    def __init__(self, row: Any, *, after: Any = None) -> None:
        self.row, self.after, self.statements = row, after, []

    def execute(self, statement: Any, params: Any = None) -> Any:
        self.statements.append((statement, dict(params or {})))
        if statement is jobs._CLAIM_BINDING:
            return _Result(self.row)
        return _Result(self.after)

    def sql(self) -> list[str]:
        return [str(statement) for statement, _ in self.statements]


def _bound(pool: str = POOL_A) -> BoundCell:
    host, provider = pool.split(":")
    return BoundCell("text:main", "exgr_X", "exc_X", "excr_X", host, provider, "subscription", "claude-opus-5-5")


# --- a run that waits spends no attempt -------------------------------------------------------------------------------


def test_a_pending_planned_run_with_no_available_member_waits_before_anything_is_written(monkeypatch: pytest.MonkeyPatch) -> None:
    def waiting(session: Any, *, run_id: str, stage_plan: Any) -> Any:
        raise GroupDispatchWaiting("model_unavailable")

    monkeypatch.setattr(JobRepository, "_select_cells", staticmethod(waiting))
    session = Session(("pending", None, PLAN))
    with pytest.raises(GroupDispatchWaiting) as waited:
        JobRepository(worker_id=None).start_execution(session, run_id=RUN)  # type: ignore[arg-type]
    assert waited.value.wait_reason == "model_unavailable" and isinstance(waited.value, ExecutionNotClaimed)
    assert session.statements == [(jobs._CLAIM_BINDING, {"run_id": RUN})], "the binding was read and then nothing: no lock, no attempt, no lease"
    for forbidden in ("INSERT INTO attempt", "INSERT INTO lease", "UPDATE job", "UPDATE audit_run", "INSERT INTO audit_run_cell_binding"):
        assert not any(forbidden in sql for sql in session.sql()), forbidden


def test_a_capacity_wait_is_the_same_refusal_with_its_own_word(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(JobRepository, "_select_cells", staticmethod(lambda session, *, run_id, stage_plan: (_ for _ in ()).throw(
        GroupDispatchWaiting("executor_at_capacity"))))
    with pytest.raises(GroupDispatchWaiting) as waited:
        JobRepository().start_execution(Session(("pending", None, PLAN)), run_id=RUN)  # type: ignore[arg-type]
    assert waited.value.wait_reason == "executor_at_capacity"


def test_the_planned_path_is_taken_for_a_pending_run_with_a_plan_and_neither_other_path_is(monkeypatch: pytest.MonkeyPatch) -> None:
    taken: list[str] = []
    monkeypatch.setattr(JobRepository, "_select_cells", staticmethod(lambda session, *, run_id, stage_plan: taken.append("cells") or (_ for _ in ()).throw(
        GroupDispatchWaiting("model_unavailable"))))
    monkeypatch.setattr(JobRepository, "_select_member", lambda self, session, **kw: taken.append("member"))
    monkeypatch.setattr(JobRepository, "_hold_connection_limit", staticmethod(lambda session, **kw: taken.append("connection")))
    with pytest.raises(GroupDispatchWaiting):
        JobRepository().start_execution(Session(("pending", None, PLAN)), run_id=RUN)  # type: ignore[arg-type]
    assert taken == ["cells"]


def test_a_bound_planned_run_takes_the_pool_hold_and_not_the_connection_hold(monkeypatch: pytest.MonkeyPatch) -> None:
    taken: list[str] = []
    monkeypatch.setattr(JobRepository, "_hold_pool_limits", staticmethod(lambda session, *, run_id: taken.append("pools") or (_ for _ in ()).throw(
        DomainError(ErrorCode.CONFLICT, message="full"))))
    monkeypatch.setattr(JobRepository, "_hold_connection_limit", staticmethod(lambda session, **kw: taken.append("connection")))
    with pytest.raises(ExecutionNotClaimed):
        JobRepository().start_execution(Session(("bound", None, PLAN)), run_id=RUN)  # type: ignore[arg-type]
    assert taken == ["pools"]


def test_a_process_that_does_not_dispatch_refuses_a_pending_planned_run_before_any_lock() -> None:
    session = Session(("pending", None, PLAN))
    with pytest.raises(ExecutionNotClaimed) as refused:
        JobRepository(worker_id="wrk_x", dispatch_groups=False).start_execution(session, run_id=RUN)  # type: ignore[arg-type]
    assert not isinstance(refused.value, GroupDispatchWaiting) and getattr(refused.value, "wait_reason", None) is None
    assert len(session.statements) == 1, "only the binding was read"


def test_a_run_with_no_plan_reads_as_it_did() -> None:
    assert JobRepository._claim_view(Session(("frozen_at_start", None, None)), run_id=RUN) == ("frozen_at_start", None, None)  # type: ignore[arg-type]
    assert JobRepository._claim_view(Session(("pending", "exgr_X", None)), run_id=RUN) == ("pending", "exgr_X", None)  # type: ignore[arg-type]
    assert JobRepository._claim_view(Session(("pending", None, PLAN)), run_id=RUN) == ("pending", None, PLAN)  # type: ignore[arg-type]
    assert JobRepository._claim_view(Session(("bound", None, PLAN)), run_id=RUN) == ("bound", None, PLAN)  # type: ignore[arg-type]
    assert JobRepository._claim_view(Session(None), run_id=RUN) == (None, None, None)  # type: ignore[arg-type]
    with pytest.raises(DomainError):
        JobRepository._claim_view(Session(("pending", None, None)), run_id=RUN)  # type: ignore[arg-type]


# --- the pool locks -----------------------------------------------------------------------------------------------------


def test_every_pool_a_cell_might_be_bound_in_is_locked_before_the_decision_and_a_pool_a_revision_added_is_locked_too(monkeypatch: pytest.MonkeyPatch) -> None:
    reads = iter([[POOL_A, POOL_C], [POOL_A, POOL_B, POOL_C]])
    order: list[str] = []
    monkeypatch.setattr(executors_public, "pools_of", lambda session, cells: next(reads))
    monkeypatch.setattr(executors_public, "bind_cells", lambda session, *, run_id, cells: order.append("decide") or BindOutcome((_bound(),), None))

    class Locks(Session):
        def execute(self, statement: Any, params: Any = None) -> Any:
            if statement is jobs._LOCK_POOL:
                order.append(f"lock:{params['pool']}")
            return super().execute(statement, params)

    bound = JobRepository._select_cells(Locks(None), run_id=RUN, stage_plan=PLAN)  # type: ignore[arg-type]
    assert order == [f"lock:{POOL_A}", f"lock:{POOL_C}", f"lock:{POOL_B}", "decide"], "locks first, in the order read; the decision under them"
    assert len(bound) == 1


def test_a_decision_that_binds_nothing_is_the_runs_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(executors_public, "pools_of", lambda session, cells: [POOL_A])
    outcome = BindOutcome(None, "executor_at_capacity", (CellWait("text:main", "claude-opus-5-5", "subscription", "at_capacity"),))
    monkeypatch.setattr(executors_public, "bind_cells", lambda session, *, run_id, cells: outcome)
    with pytest.raises(GroupDispatchWaiting) as waited:
        JobRepository._select_cells(Session(None), run_id=RUN, stage_plan=PLAN)  # type: ignore[arg-type]
    assert waited.value.wait_reason == "executor_at_capacity"


def test_the_pool_locks_are_taken_before_the_control_row_the_run_and_the_job(monkeypatch: pytest.MonkeyPatch) -> None:
    """ADR-0028 decision 15: worker intake, pools ascending, control, run, job. The planned path's first statement after the binding read is the
    pool lock (through ``_select_cells``), and the control row is not touched before it."""
    monkeypatch.setattr(executors_public, "pools_of", lambda session, cells: [POOL_A, POOL_B])
    monkeypatch.setattr(executors_public, "bind_cells", lambda session, *, run_id, cells: BindOutcome((_bound(),), None))

    class Stops(Session):
        def execute(self, statement: Any, params: Any = None) -> Any:
            super().execute(statement, params)
            if statement is jobs._ENSURE_CONTROL:
                raise RuntimeError("stop at the control row")
            return _Result(self.after)

    session = Stops(("pending", None, PLAN))
    with pytest.raises(RuntimeError, match="control row"):
        JobRepository().start_execution(session, run_id=RUN)  # type: ignore[arg-type]
    kinds = ["claim" if s is jobs._CLAIM_BINDING else "pool" if s is jobs._LOCK_POOL else "control" if s is jobs._ENSURE_CONTROL else "other"
             for s, _ in session.statements]
    assert kinds == ["claim", "pool", "pool", "control"]


# --- the retry of a bound planned run ---------------------------------------------------------------------------------------


def test_a_retry_locks_all_of_its_pools_and_then_counts_each_without_itself(monkeypatch: pytest.MonkeyPatch) -> None:
    steps: list[str] = []
    monkeypatch.setattr(executors_public, "bound_pools_of_run", lambda session, run_id: [POOL_A, POOL_B])
    monkeypatch.setattr(executors_public, "pool_has_room", lambda session, pool, *, exclude_run_id: steps.append(f"room:{pool}:{exclude_run_id}") or True)

    class Locks(Session):
        def execute(self, statement: Any, params: Any = None) -> Any:
            if statement is jobs._LOCK_POOL:
                steps.append(f"lock:{params['pool']}")
            return _Result(None)

    JobRepository._hold_pool_limits(Locks(None), run_id=RUN)  # type: ignore[arg-type]
    assert steps == [f"lock:{POOL_A}", f"lock:{POOL_B}", f"room:{POOL_A}:{RUN}", f"room:{POOL_B}:{RUN}"]


def test_a_retry_whose_pool_is_full_is_refused_as_a_full_connection_is(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(executors_public, "bound_pools_of_run", lambda session, run_id: [POOL_A, POOL_B])
    monkeypatch.setattr(executors_public, "pool_has_room", lambda session, pool, *, exclude_run_id: pool != POOL_B)
    with pytest.raises(DomainError) as refused:
        JobRepository._hold_pool_limits(Session(None), run_id=RUN)  # type: ignore[arg-type]
    assert refused.value.code is ErrorCode.CONFLICT and refused.value.detail_fields["aggregate_type"] == "ExecutorHost"


# --- the write, once -------------------------------------------------------------------------------------------------------------


def test_binding_writes_one_row_per_cell_then_moves_the_run_and_a_second_move_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    written: list[Any] = []
    monkeypatch.setattr(executors_public, "write_bindings", lambda session, *, run_id, bound: written.append((run_id, len(bound))))
    events: list[dict[str, Any]] = []
    monkeypatch.setattr(jobs, "append_execution_event", lambda session, **kw: events.append(kw))

    class Moves(Session):
        def __init__(self, rows: int) -> None:
            super().__init__(None)
            self.rows = rows

        def execute(self, statement: Any, params: Any = None) -> Any:
            self.statements.append((statement, dict(params or {})))
            return SimpleNamespace(rowcount=self.rows)

    JobRepository()._bind_planned(Moves(1), run_id=RUN, bound=[_bound(), _bound(POOL_B)])  # type: ignore[arg-type]
    assert written == [(RUN, 2)]
    assert [event["event_type"] for event in events] == ["executor.cell_bound", "executor.cell_bound"]
    from auditmanager.jobs.events import _SAFE_KEYS

    assert set(events[0]["payload"]) <= _SAFE_KEYS and events[0]["payload"]["reason"] == "stage_plan"
    with pytest.raises(DomainError):
        JobRepository()._bind_planned(Moves(0), run_id=RUN, bound=[_bound()])  # type: ignore[arg-type]


def test_the_binding_update_names_the_pending_state_and_the_plan() -> None:
    sql = str(jobs._BIND_PLANNED_RUN)
    assert "binding_state = 'pending' AND stage_plan IS NOT NULL" in sql and "wait_reason = NULL, waiting_since = NULL" in sql


def test_the_events_of_a_cell_carry_only_journal_safe_keys() -> None:
    from auditmanager.jobs.events import _SAFE_KEYS

    for key in ("cell_key", "host_id", "connection_id", "provider", "access", "model_id", "from_state", "to_state", "reason", "enabled", "slots"):
        assert key in _SAFE_KEYS


# --- waits and the sweep ---------------------------------------------------------------------------------------------------------


def test_the_run_only_wait_word_is_stored_and_a_foreign_one_is_refused() -> None:
    class Writes:
        def execute(self, statement: Any, params: Any = None) -> Any:
            assert statement is jobs._WRITE_WAIT
            return SimpleNamespace(rowcount=1)

    assert JobRepository().record_group_wait(Writes(), run_id=RUN, reason="model_unavailable") is True  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        JobRepository().record_group_wait(Writes(), run_id=RUN, reason="no_such_reason")  # type: ignore[arg-type]


class Page:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def mappings(self) -> Page:
        return self

    def all(self) -> list[dict[str, Any]]:
        return self.rows

    def first(self) -> dict[str, Any] | None:
        return self.rows[0] if self.rows else None


class PlannedSweeper:
    def __init__(self, *, wait: str | None, expired: bool) -> None:
        self.wait, self.expired, self.statements = wait, expired, []

    def execute(self, statement: Any, params: Any = None) -> Any:
        self.statements.append(str(statement))
        if statement is jobs._PENDING_PLANNED_RUNS:
            if params["after_run_id"] is not None:
                return Page([])
            return Page([{"run_id": RUN, "stage_plan": PLAN, "created_at": 1, "wait_reason": self.wait}])
        if statement is jobs._LOCK_PENDING_RUN:
            return Page([{"run_id": RUN, "wait_reason": self.wait, "waiting_since": None, "wait_expired": self.expired}])
        return Page([])


@pytest.fixture
def planned(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    seen = SimpleNamespace(written=[], ended=[], outcome=None, evaluated=0)

    def evaluate(session: Any, *, run_id: str, cells: Any) -> BindOutcome:
        seen.evaluated += 1
        assert cells == [CellRequest("text:main", "claude-opus-5-5", "subscription")]
        return seen.outcome

    monkeypatch.setattr(executors_public, "evaluate_wait", evaluate)
    monkeypatch.setattr(JobRepository, "record_group_wait", lambda self, session, *, run_id, reason: seen.written.append(reason) or True)
    monkeypatch.setattr(JobRepository, "_end_without_executor", lambda self, session, *, run_id: seen.ended.append(run_id))
    monkeypatch.setattr(JobRepository, "group_offline_wait_seconds", staticmethod(lambda environ=None: 1800))
    return seen


def _wait(reason: str, cause: str) -> BindOutcome:
    return BindOutcome(None, reason, (CellWait("text:main", "claude-opus-5-5", "subscription", cause),))


def test_a_planned_run_waiting_for_a_model_longer_than_the_limit_ends_no_executor_online(planned: SimpleNamespace) -> None:
    planned.outcome = _wait("model_unavailable", "login_required")
    report = JobRepository().refresh_group_waits(PlannedSweeper(wait="model_unavailable", expired=True), batch_size=50)  # type: ignore[arg-type]
    assert planned.ended == [RUN] and planned.written == [] and report.expired == 1


def test_a_planned_run_still_inside_the_limit_keeps_its_wait(planned: SimpleNamespace) -> None:
    planned.outcome = _wait("model_unavailable", "host_offline")
    report = JobRepository().refresh_group_waits(PlannedSweeper(wait="model_unavailable", expired=False), batch_size=50)  # type: ignore[arg-type]
    assert planned.ended == [] and report.expired == 0, "an unchanged reason rewrites nothing that restarts the clock"


def test_a_capacity_wait_never_ends_however_long_it_has_lasted(planned: SimpleNamespace) -> None:
    planned.outcome = _wait("executor_at_capacity", "at_capacity")
    report = JobRepository().refresh_group_waits(PlannedSweeper(wait="executor_at_capacity", expired=True), batch_size=50)  # type: ignore[arg-type]
    assert planned.ended == [] and planned.written == [] and report.expired == 0


def test_the_wait_follows_the_decision_when_it_changes(planned: SimpleNamespace) -> None:
    planned.outcome = _wait("executor_at_capacity", "at_capacity")
    JobRepository().refresh_group_waits(PlannedSweeper(wait="model_unavailable", expired=True), batch_size=50)  # type: ignore[arg-type]
    assert planned.written == ["executor_at_capacity"] and planned.ended == [], "another reason restarts the clock and cannot end the run"


def test_a_wait_nothing_holds_any_more_is_cleared_so_the_hint_offers_the_run(planned: SimpleNamespace) -> None:
    planned.outcome = BindOutcome((_bound(),), None)
    report = JobRepository().refresh_group_waits(PlannedSweeper(wait="model_unavailable", expired=True), batch_size=50)  # type: ignore[arg-type]
    assert planned.written == [None] and planned.ended == [] and report.updated == 1


def test_a_planned_run_that_waits_for_nothing_new_is_not_locked(planned: SimpleNamespace) -> None:
    planned.outcome = _wait("executor_at_capacity", "at_capacity")
    session = PlannedSweeper(wait="executor_at_capacity", expired=False)
    JobRepository().refresh_group_waits(session, batch_size=50)  # type: ignore[arg-type]
    assert str(jobs._LOCK_PENDING_RUN) not in session.statements, "nothing to write and nothing that can end: no lock is held for it"
