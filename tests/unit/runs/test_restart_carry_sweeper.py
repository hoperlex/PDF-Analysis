"""`RUN-RESTART-01`: the worker's sweeper finishes the decision carry of a restart run that published and whose carry is not complete.

The executor carries right after the run's terminal transaction and leaves a failure to this pass; the carry itself is ``decisions``' (idempotent), so the pass
only asks it, for the run's starter, for every run ``pending_restart_carries`` names -- and survives a carry that fails.
"""

from __future__ import annotations

import logging
import sys
import types
from types import SimpleNamespace as NS

import pytest

from auditmanager.workers import service
from auditmanager.workers.service import RESTART_CARRY_ATTEMPTS, RESTART_CARRY_SECONDS, WorkerService


class _Sessions:
    def __call__(self):
        return self

    def __enter__(self):
        return NS(commit=lambda: None)

    def __exit__(self, *_):
        return False


def _service():
    return NS(_sessions=_Sessions(), _worker_id="worker-1", _carry_attempts={})


@pytest.fixture
def decisions(monkeypatch):
    module = types.ModuleType("auditmanager.decisions.public")
    asked: list[tuple[str, str]] = []
    module.asked = asked  # type: ignore[attr-defined]
    module.pending_restart_carries = lambda session: ["run_a", "run_b"]  # type: ignore[attr-defined]
    module.carry_restart_decisions = lambda factory, *, run_id, actor_user_uid: asked.append((run_id, actor_user_uid))  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "auditmanager.decisions.public", module)
    monkeypatch.setattr(service, "RunRepository", lambda: NS(get=lambda session, run_id: NS(started_by_user_uid="usr_" + run_id[-1])))
    return module


def test_every_restart_run_with_an_incomplete_carry_is_carried_for_its_starter(decisions) -> None:
    WorkerService._sweep_restart_carries(_service())
    assert decisions.asked == [("run_a", "usr_a"), ("run_b", "usr_b")]


def test_a_carry_that_fails_is_logged_and_the_next_run_is_still_carried(decisions, caplog) -> None:
    def failing(factory, *, run_id, actor_user_uid):
        decisions.asked.append((run_id, actor_user_uid))
        if run_id == "run_a":
            raise RuntimeError("the database went away")

    decisions.carry_restart_decisions = failing
    with caplog.at_level(logging.ERROR):
        WorkerService._sweep_restart_carries(_service())
    assert [run for run, _ in decisions.asked] == ["run_a", "run_b"]
    assert "the decision carry of restart run run_a failed" in caplog.text


def test_a_run_whose_carry_keeps_failing_is_given_up_after_a_cap_and_a_completed_one_is_forgotten(decisions, caplog) -> None:
    service_ = _service()

    def failing(factory, *, run_id, actor_user_uid):
        decisions.asked.append((run_id, actor_user_uid))
        if run_id == "run_a":
            raise RuntimeError("an item that cannot be carried")

    decisions.carry_restart_decisions = failing
    with caplog.at_level(logging.INFO):
        for _ in range(RESTART_CARRY_ATTEMPTS + 3):
            WorkerService._sweep_restart_carries(service_)
    assert [run for run, _ in decisions.asked].count("run_a") == RESTART_CARRY_ATTEMPTS, "a pass past the cap does not try it again"
    assert [run for run, _ in decisions.asked].count("run_b") == RESTART_CARRY_ATTEMPTS + 3, "another run is not held back by it"
    assert caplog.text.count("is given up by this process") == 1, "given up once, at the cap, loudly"
    # Its carry completed elsewhere (the marker is written, the run is no longer pending): the count is forgotten.
    decisions.pending_restart_carries = lambda session: ["run_b"]
    WorkerService._sweep_restart_carries(service_)
    assert "run_a" not in service_._carry_attempts


def test_the_report_of_a_carry_is_logged(decisions, caplog) -> None:
    decisions.carry_restart_decisions = lambda factory, *, run_id, actor_user_uid: NS(as_fields=lambda: {"carried": 2, "run_id": run_id})
    with caplog.at_level(logging.INFO):
        WorkerService._sweep_restart_carries(_service())
    assert "'carried': 2" in caplog.text


def test_a_failure_to_read_the_pending_runs_is_logged_and_never_stops_the_worker(decisions, caplog) -> None:
    decisions.pending_restart_carries = lambda session: (_ for _ in ()).throw(RuntimeError("no database"))
    with caplog.at_level(logging.ERROR):
        WorkerService._sweep_restart_carries(_service())
    assert decisions.asked == [] and "restart carry pass failed" in caplog.text


def test_a_build_without_the_carry_has_nothing_to_sweep(monkeypatch) -> None:
    module = types.ModuleType("auditmanager.decisions.public")  # the lane that owns the carry has not merged: no such names
    monkeypatch.setitem(sys.modules, "auditmanager.decisions.public", module)
    WorkerService._sweep_restart_carries(_service())  # no ImportError, no exception


def test_the_pass_runs_in_the_dispatch_loop_at_a_cadence_of_its_own() -> None:
    assert 0 < RESTART_CARRY_SECONDS <= 300
    import inspect

    assert "_sweep_restart_carries" in inspect.getsource(WorkerService._dispatch_loop.fget if isinstance(WorkerService._dispatch_loop, property) else WorkerService._dispatch_loop)
