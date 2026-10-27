"""The worker's hook for the comparison loop, without a database (`CMP-WORK-01`). Container-free.

The dispatch loop asks the comparison runner for an item only when it found no Run to hand a slot, the
item runs in the worker's pool and counts as a busy slot, a drain waits for it, the reclaim pass covers
comparison leases, and ``start`` refuses before it registers. Driven directly, as the probe loop's
unit tests drive theirs.
"""

from __future__ import annotations

import threading
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.workers import service as service_module
from auditmanager.workers.service import WorkerService


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.item: Any = SimpleNamespace(work_id="cq_1")
        self.gate = threading.Event()
        self.gate.set()
        self.verify_error: Exception | None = None
        self.claim_error: Exception | None = None
        self.reclaim_error: Exception | None = None
        self.execute_error: Exception | None = None

    def verify(self) -> None:
        self.calls.append("verify")
        if self.verify_error:
            raise self.verify_error

    def claim(self, worker_id: str) -> Any:
        self.calls.append(f"claim:{worker_id}")
        if self.claim_error:
            raise self.claim_error
        item, self.item = self.item, None
        return item

    def execute(self, item: Any) -> None:
        self.calls.append(f"execute:{item.work_id}")
        assert self.gate.wait(timeout=10)
        if self.execute_error:
            raise self.execute_error

    def reclaim(self) -> int:
        self.calls.append("reclaim")
        if self.reclaim_error:
            raise self.reclaim_error
        return 0


def make_service(runner: FakeRunner | None, **options: Any) -> WorkerService:
    service = WorkerService(
        engine=None, session_factory=None, execute=lambda run_id, worker: None,  # type: ignore[arg-type]
        version="test", comparison_work=runner, **options,
    )
    service._worker_id = "wrk_test"
    return service


@pytest.mark.parametrize(("found", "asked", "claimed"), [
    (service_module._RUN_OFFERED, False, True),   # a Run was handed to a slot: no second claim
    (service_module._RUN_UNKNOWN, False, False),  # intake off or the queue unreadable: not "no Run"
    (service_module._NO_RUN, True, True),         # the only case in which comparison work is asked for
])
def test_comparison_work_is_asked_for_only_when_no_run_is_claimable(
    monkeypatch: pytest.MonkeyPatch, found: str, asked: bool, claimed: bool
) -> None:
    runner = FakeRunner()
    service = make_service(runner)
    monkeypatch.setattr(service, "_offer_next_run", lambda: found)
    assert service._claim_next() is claimed
    assert any(call.startswith("claim:") for call in runner.calls) is asked
    service.drain(timeout=10)
    service._pool.shutdown(wait=True)


def test_a_worker_without_a_comparison_runner_claims_exactly_what_it_did_before(monkeypatch: pytest.MonkeyPatch) -> None:
    service = make_service(None)
    monkeypatch.setattr(service, "_offer_next_run", lambda: service_module._NO_RUN)
    assert service._claim_next() is False
    service._pool.shutdown(wait=True)


def test_a_runner_that_declines_or_fails_to_claim_leaves_the_slot_free(monkeypatch: pytest.MonkeyPatch, caplog) -> None:  # type: ignore[no-untyped-def]
    runner = FakeRunner()
    runner.item = None
    service = make_service(runner)
    monkeypatch.setattr(service, "_offer_next_run", lambda: service_module._NO_RUN)
    assert service._claim_next() is False and service.busy == 0
    runner.claim_error = RuntimeError("database down")
    with caplog.at_level("ERROR"):
        assert service._claim_next() is False
    assert "could not claim comparison work" in caplog.text
    service._pool.shutdown(wait=True)


def test_a_claimed_item_runs_in_the_pool_counts_as_a_busy_slot_and_a_drain_waits_for_it(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = FakeRunner()
    runner.gate.clear()
    service = make_service(runner)
    monkeypatch.setattr(service, "_offer_next_run", lambda: service_module._NO_RUN)
    assert service._claim_next() is True
    assert service.busy == 1, "the item occupies a slot"
    assert service.drain(timeout=0.2) is False, "a drain waits for it"
    runner.gate.set()
    assert service.drain(timeout=10) is True
    assert service.busy == 0 and "execute:cq_1" in runner.calls
    assert service._poll_now.is_set(), "a finished item wakes the dispatch loop for the next look"
    service._pool.shutdown(wait=True)


def test_a_fault_ending_an_item_is_logged_and_frees_the_slot(monkeypatch: pytest.MonkeyPatch, caplog) -> None:  # type: ignore[no-untyped-def]
    runner = FakeRunner()
    runner.execute_error = RuntimeError("final transaction failed")
    service = make_service(runner)
    monkeypatch.setattr(service, "_offer_next_run", lambda: service_module._NO_RUN)
    with caplog.at_level("ERROR"):
        service._claim_next()
        assert service.drain(timeout=10) is True
    assert service.busy == 0 and "its lease will expire" in caplog.text
    service._pool.shutdown(wait=True)


def test_the_reclaim_pass_covers_comparison_leases_even_when_the_runs_reclaim_fails(caplog) -> None:  # type: ignore[no-untyped-def]
    runner = FakeRunner()
    service = make_service(runner)

    class Broken:
        def __call__(self) -> Any:
            raise RuntimeError("no database")

    service._sessions = Broken()  # type: ignore[assignment]
    with caplog.at_level("ERROR"):
        service._reclaim()
    assert runner.calls == ["reclaim"], "the comparison reclaim ran after the runs' reclaim failed"
    runner.reclaim_error = RuntimeError("comparison reclaim failed")
    with caplog.at_level("ERROR"):
        service._reclaim()
    assert "comparison lease reclaim pass failed" in caplog.text


def test_start_verifies_the_comparison_runner_before_it_registers_anything() -> None:
    runner = FakeRunner()
    runner.verify_error = RuntimeError("live work of a kind no handler serves")
    registered: list[str] = []
    registry = SimpleNamespace(register=lambda session, **options: registered.append("registered"))
    service = make_service(runner, registry=registry)
    with pytest.raises(RuntimeError, match="no handler"):
        service.start()
    assert registered == [] and runner.calls == ["verify"]
    service._pool.shutdown(wait=True)


def test_an_item_is_counted_as_a_busy_slot_from_the_instant_it_starts(monkeypatch: pytest.MonkeyPatch) -> None:
    """The item may start the moment it is submitted; ``busy`` and ``drain`` must already count it.
    Submitted and registered under one lock, so an item that reads the count from inside itself
    never sees a slot in use that is not counted (a race that made a slot invisible to a drain)."""
    counted: list[int] = []
    service_box: list[WorkerService] = []

    class Probe(FakeRunner):
        def claim(self, worker_id: str) -> Any:
            return SimpleNamespace(work_id="cq_1")

        def execute(self, item: Any) -> None:
            counted.append(service_box[0].busy)

    service = make_service(Probe(), slots=1)
    service_box.append(service)
    monkeypatch.setattr(service, "_offer_next_run", lambda: service_module._NO_RUN)
    for _ in range(300):
        assert service._claim_next() is True
        assert service.drain(timeout=10) is True
    assert counted == [1] * 300
    service._pool.shutdown(wait=True)
