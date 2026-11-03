"""`EXEC2-GROUP-RUN-01` (ADR-0026 decisions 12, 14 and 15): what the worker's dispatch loop does with a Run admitted on a group,
without a database.

The hint offers a group Run once; the claim that refuses it stores why (the carrier's step, covered on PostgreSQL in
``tests/integration/jobs/test_group_dispatch.py``). Here the worker is the subject, with a hint, a registry and a comparison
runner that are values:

* a claim that finds no member for a group Run does not hold the worker: the Run is kept out of the next hint for one sweep
  interval, the refusal is not a lost claim to be counted, and the dispatch loop goes on to the next Run and, when there is
  none, to the comparison claim (``test_a_refused_group_run_never_starves_the_comparison_claim``);
* an ordinary lost claim is counted as it always was;
* the hint is asked by a repository that knows whether this worker dispatches groups (the provider source is ``database``).

Written and **not run** in EXEC-2 (`R-149d`).
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest

import auditmanager.workers.service as service_module
from auditmanager.jobs.repository import ExecutionNotClaimed, GroupDispatchWaiting
from auditmanager.shared.errors import ErrorCode
from auditmanager.workers.service import GROUP_REFUSAL_HOLD_SECONDS, GROUP_WAIT_SECONDS, WorkerService


class _Session:
    def __enter__(self) -> "_Session":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def commit(self) -> None:
        return None


class _Registry:
    def intake_enabled(self, _session: object, _worker_id: str) -> bool:
        return True


class _Comparison:
    """The comparison runner, as the worker sees it: it hands out one item and records that it was asked."""

    def __init__(self) -> None:
        self.asked: list[str] = []
        self.ran: list[str] = []

    def verify(self) -> None:
        return None

    def claim(self, worker_id: str) -> Any:
        self.asked.append(worker_id)
        return SimpleNamespace(work_id=f"work_{len(self.asked)}") if len(self.asked) == 1 else None

    def execute(self, item: Any) -> None:
        self.ran.append(item.work_id)

    def reclaim(self) -> int:
        return 0


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    """A repository that answers the first queued Run not in ``submitted`` (the hint's own contract), and records how it was built."""
    state = SimpleNamespace(built=[], asked=[], queue=[], clock=1000.0, services=[])

    class Repository:
        def __init__(self, **options: Any) -> None:
            state.built.append(options)

        def next_queued_run(self, _session: object, *, submitted: tuple[str, ...] = ()) -> str | None:
            state.asked.append(tuple(submitted))
            return next((run for run in state.queue if run not in submitted), None)

    monkeypatch.setattr(service_module, "JobRepository", Repository)
    monkeypatch.setattr(service_module, "monotonic", lambda: state.clock)

    def make(execute: Any, **options: Any) -> WorkerService:
        service = WorkerService(
            engine=None, session_factory=_Session, execute=execute, version="unit",  # type: ignore[arg-type]
            registry=_Registry(), heartbeat_seconds=3600.0, group_offline_wait_seconds=60.0, **options,  # type: ignore[arg-type]
        )
        service._worker_id = "wrk_unit"
        state.services.append(service)
        return service

    state.make = make
    yield state
    for service in state.services:
        service.stop()


def _refuse_like_a_full_group(run_id: str, worker_id: str) -> None:
    raise GroupDispatchWaiting("executor_at_capacity")


def test_the_hold_is_one_sweep_interval() -> None:
    assert GROUP_REFUSAL_HOLD_SECONDS == GROUP_WAIT_SECONDS == 5.0


def test_a_group_run_the_claim_refused_is_not_counted_as_a_lost_claim_and_is_held_out_of_the_next_hint(
    world: SimpleNamespace,
) -> None:
    service = world.make(_refuse_like_a_full_group)
    service._run_one("run_group")
    assert service._refused_in_a_row == 0, "the dispatch loop is not told to stop asking"
    assert service._group_refused == {"run_group": world.clock + GROUP_REFUSAL_HOLD_SECONDS}

    world.queue = ["run_group", "run_other"]
    assert service._offer_next_run() == "run_offered"
    assert world.asked[-1] == ("run_group",), "the refused Run is handed to the hint as one that must not be offered again"
    assert service.drain(timeout=5)


def test_the_hold_lapses_after_one_interval_and_the_durable_reason_takes_over(world: SimpleNamespace) -> None:
    service = world.make(_refuse_like_a_full_group)
    service._run_one("run_group")
    world.clock += GROUP_REFUSAL_HOLD_SECONDS + 0.1
    world.queue = []
    assert service._offer_next_run() == "no_run"
    assert world.asked[-1] == () and service._group_refused == {}


def test_an_ordinary_lost_claim_is_still_counted_and_not_held(world: SimpleNamespace) -> None:
    def lose(run_id: str, worker_id: str) -> None:
        raise ExecutionNotClaimed(ErrorCode.CONFLICT)

    service = world.make(lose)
    service._run_one("run_busy_connection")
    assert service._refused_in_a_row == 1 and service._group_refused == {}


def test_a_refused_group_run_never_starves_the_comparison_claim(world: SimpleNamespace) -> None:
    """One Run no member can take, then nothing else: the next pass reaches the comparison runner."""
    comparison = _Comparison()
    service = world.make(_refuse_like_a_full_group, comparison_work=comparison)  # type: ignore[arg-type]
    world.queue = ["run_group"]

    assert service._claim_next() is True, "the group Run is offered once"
    assert service.drain(timeout=5)
    assert comparison.asked == [], "a Run was claimable: the comparison runner is not asked in that pass"
    assert service._group_refused == {"run_group": world.clock + GROUP_REFUSAL_HOLD_SECONDS}

    assert service._claim_next() is True, "the hint offers the refused Run to nobody, so the comparison claim is next"
    assert comparison.asked == ["wrk_unit"]
    assert service.drain(timeout=5) and comparison.ran == ["work_1"]


def test_the_worker_asks_the_hint_through_a_repository_that_knows_whether_it_dispatches_groups(world: SimpleNamespace) -> None:
    default = world.make(_refuse_like_a_full_group)
    default._offer_next_run()
    assert world.built[-1] == {"dispatch_groups": True}

    environment = world.make(_refuse_like_a_full_group, dispatch_groups=False)
    environment._offer_next_run()
    assert world.built[-1] == {"dispatch_groups": False}
