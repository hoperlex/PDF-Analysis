"""The runner's decisions without a database (`CMP-WORK-01`, ADR-0025 decisions 4, 6, 23). Container-free.

A fake repository records what the runner asks of it, so each gate is shown to stop the claim *before*
the queue is touched, and each outcome to reach ``finish`` as the contract says. The same behaviours
are shown against PostgreSQL in ``tests/integration/comparison/work``.
"""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.comparison.public import (
    ClaimGates,
    ComparisonWorkRunner,
    Completed,
    Failed,
    HandlerRegistry,
    UnhandledKindError,
    Yielded,
)
from auditmanager.comparison.work.heartbeat import ItemHeartbeat
from auditmanager.comparison.work.model import ItemAuthority, WorkItem
from auditmanager.shared.errors import DomainError, ErrorCode


class FakeSession:
    def __init__(self, log: list[str]) -> None:
        self._log = log

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def rollback(self) -> None:
        self._log.append("rollback")

    def commit(self) -> None:
        self._log.append("commit")


class FakeRepository:
    def __init__(self, log: list[str], *, item: WorkItem | None = None) -> None:
        self.log = log
        self.item = item
        self.finished: list[Any] = []
        self.finish_error: Exception | None = None
        self.live: frozenset[str] = frozenset()
        self.reclaimed_with: list[Any] = []
        self.heartbeats = 0
        self.heartbeat_answers: list[bool] = []
        self.cancel_answer = False

    def claim(self, session: Any, *, worker_id: str, modules: Any, kinds: Any) -> WorkItem | None:
        self.log.append(f"claim:{worker_id}:{sorted(modules)}:{sorted(kinds)}")
        return self.item

    def finish(self, session: Any, authority: Any, outcome: Any) -> str:
        self.finished.append(outcome)
        if self.finish_error is not None:
            raise self.finish_error
        return {"Completed": "succeeded", "Failed": "failed", "Yielded": "queued"}[type(outcome).__name__]

    def live_kinds(self, session: Any, *, modules: Any) -> frozenset[str]:
        self.log.append(f"live:{sorted(modules)}")
        return self.live

    def reclaim_expired(self, session: Any, **options: Any) -> int:
        self.reclaimed_with.append(options)
        return 2

    def heartbeat(self, session: Any, authority: Any) -> bool:
        self.heartbeats += 1
        return self.heartbeat_answers.pop(0) if self.heartbeat_answers else True

    def cancel_requested(self, session: Any, work_id: str) -> bool:
        return self.cancel_answer


class Handler:
    def __init__(self, kind: str, result: Any = None, raises: Exception | None = None) -> None:
        self.kind, self._result, self._raises, self.items = kind, result, raises, []

    def run(self, item: Any) -> Any:
        self.items.append(item)
        if self._raises is not None:
            raise self._raises
        return self._result


def make_item(kind: str = "page_profile") -> WorkItem:
    return WorkItem(
        work_id="cq_X", attempt_id="cqa_X", attempt_no=1, project_uid="prj_X", module="versions", kind=kind,
        payload={}, comparison_upload_id=None, created_by_user_uid=None, max_attempts=3,
        authority=ItemAuthority("cq_X", "cqa_X", "token"),
    )


def make_runner(
    handler: Handler | None = None, *, modules: frozenset[str] = frozenset({"versions"}),
    paused: bool = False, run_claimable: bool = False, item: WorkItem | None = None, settlers: tuple[Any, ...] = (),
):  # type: ignore[no-untyped-def]
    log: list[str] = []
    repository = FakeRepository(log, item=item if item is not None else make_item())
    handler = handler or Handler("page_profile", Completed())
    gates = ClaimGates(
        paused=lambda session: log.append("gate:paused") or paused,
        run_claimable=lambda session: log.append("gate:run_claimable") or run_claimable,
    )
    runner = ComparisonWorkRunner(
        lambda: FakeSession(log), registry=HandlerRegistry({handler.kind: handler}), modules=modules,  # type: ignore[arg-type]
        repository=repository, gates=gates, spend_settlers=settlers,  # type: ignore[arg-type]
        heartbeat_seconds=999.0,
    )
    return runner, repository, handler, log


# --- the gates ------------------------------------------------------------------------------------


def test_with_no_module_on_the_runner_asks_nothing_of_anyone() -> None:
    runner, repository, _, log = make_runner(modules=frozenset())
    assert runner.claim("wrk_1") is None
    assert log == [], "no gate and no queue was touched"


def test_with_no_handler_there_is_nothing_to_claim() -> None:
    log: list[str] = []
    runner = ComparisonWorkRunner(
        lambda: FakeSession(log), registry=HandlerRegistry({}), modules=frozenset({"versions"}),  # type: ignore[arg-type]
        repository=FakeRepository(log), gates=ClaimGates(paused=lambda s: False, run_claimable=lambda s: False),  # type: ignore[arg-type]
    )
    assert runner.claim("wrk_1") is None and log == []


def test_the_global_pause_stops_the_claim_before_the_priority_check_and_before_the_queue() -> None:
    runner, repository, _, log = make_runner(paused=True)
    assert runner.claim("wrk_1") is None
    assert log == ["gate:paused", "rollback"]


def test_a_claimable_run_stops_the_claim_and_its_row_lock_is_released_first() -> None:
    runner, repository, _, log = make_runner(run_claimable=True)
    assert runner.claim("wrk_1") is None
    assert log == ["gate:paused", "gate:run_claimable", "rollback"]


def test_when_every_gate_is_open_the_runner_claims_for_the_enabled_modules_and_the_handled_kinds() -> None:
    runner, repository, _, log = make_runner(modules=frozenset({"versions", "stages"}))
    item = runner.claim("wrk_7")
    assert item is repository.item
    assert log == [
        "gate:paused", "gate:run_claimable", "rollback",
        "claim:wrk_7:['stages', 'versions']:['page_profile']", "commit",
    ]


def test_the_claim_answers_none_when_the_queue_has_nothing() -> None:
    runner, repository, _, log = make_runner()
    repository.item = None
    assert runner.claim("wrk_1") is None
    assert log[-1] == "commit"


# --- the outcomes ---------------------------------------------------------------------------------


@pytest.mark.parametrize(("result", "state"), [
    (Completed(), "succeeded"), (Failed("page_unreadable"), "failed"), (Yielded(2.0), "queued"),
])
def test_the_handlers_outcome_reaches_finish_as_it_is(result: Any, state: str) -> None:
    runner, repository, handler, _ = make_runner(Handler("page_profile", result))
    item = make_item()
    assert runner.execute(item) == state
    assert repository.finished == [result] and handler.items == [item]


def test_a_handler_that_raises_ends_the_attempt_failed_and_retryable_and_the_fault_is_logged(caplog) -> None:  # type: ignore[no-untyped-def]
    runner, repository, _, _ = make_runner(Handler("page_profile", raises=RuntimeError("boom")))
    with caplog.at_level("ERROR"):
        assert runner.execute(make_item()) == "failed"
    assert repository.finished == [Failed("handler_error", retry=True)]
    assert "the handler raised" in caplog.text


def test_a_handler_that_returns_something_that_is_not_an_outcome_is_a_typed_failure(caplog) -> None:  # type: ignore[no-untyped-def]
    runner, repository, _, _ = make_runner(Handler("page_profile", "done"))
    with caplog.at_level("ERROR"):
        runner.execute(make_item())
    assert repository.finished == [Failed("handler_outcome_invalid")]
    assert "not an outcome" in caplog.text


def test_an_item_of_a_kind_the_registry_does_not_hold_is_failed_typed_never_dropped(caplog) -> None:  # type: ignore[no-untyped-def]
    runner, repository, _, _ = make_runner()
    with caplog.at_level("ERROR"):
        runner.execute(make_item(kind="some_other_kind"))
    assert repository.finished == [Failed("no_handler_for_kind")]


@pytest.mark.parametrize("code", [ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID])
def test_an_attempt_that_lost_its_lease_drops_its_outcome_and_says_so(code: ErrorCode, caplog) -> None:  # type: ignore[no-untyped-def]
    runner, repository, _, _ = make_runner()
    repository.finish_error = DomainError(code)
    with caplog.at_level("WARNING"):
        assert runner.execute(make_item()) is None
    assert "no longer holds its lease" in caplog.text


def test_a_fault_of_the_final_transaction_that_is_not_a_fence_is_not_swallowed() -> None:
    runner, repository, _, _ = make_runner()
    repository.finish_error = DomainError(ErrorCode.NOT_FOUND)
    with pytest.raises(DomainError):
        runner.execute(make_item())


# --- verify and reclaim ----------------------------------------------------------------------------


def test_verify_refuses_live_work_of_an_unhandled_kind_for_an_enabled_module_only() -> None:
    runner, repository, _, log = make_runner()
    repository.live = frozenset({"page_profile", "stage_review"})
    with pytest.raises(UnhandledKindError) as refused:
        runner.verify()
    assert refused.value.kinds == {"stage_review"} and "stage_review" in str(refused.value)
    repository.live = frozenset({"page_profile"})
    runner.verify()
    off, off_repository, _, off_log = make_runner(modules=frozenset())
    off_repository.live = frozenset({"anything"})
    off.verify()
    assert off_log == [], "a module that is off needs no handler"


def test_reclaim_runs_whatever_the_module_set_says_and_hands_the_settlers_on() -> None:
    def settle(session: Any, attempt_id: str) -> bool:
        return False

    runner, repository, _, _ = make_runner(modules=frozenset(), settlers=(settle,))
    assert runner.reclaim() == 2
    assert repository.reclaimed_with == [{"spend_settlers": (settle,)}]


# --- the heartbeat ---------------------------------------------------------------------------------


def _beat(repository: FakeRepository, item: WorkItem, *, watchdog: float = 60.0, fence: Any = None) -> ItemHeartbeat:
    return ItemHeartbeat(
        lambda: FakeSession([]), repository, item,  # type: ignore[arg-type]
        interval_seconds=0.02, watchdog_seconds=watchdog, fence=fence or (lambda session, attempt: 0),
    )


def _wait(predicate: Any, what: str) -> None:
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError(f"timed out waiting for {what}")


def test_the_heartbeat_keeps_beating_until_it_is_stopped() -> None:
    repository, item = FakeRepository([]), make_item()
    beat = _beat(repository, item)
    beat.start()
    _wait(lambda: repository.heartbeats >= 3, "three beats")
    beat.stop()
    count = repository.heartbeats
    time.sleep(0.1)
    assert repository.heartbeats == count and not item.lease_lost.is_set()


def test_a_heartbeat_that_finds_the_lease_gone_says_so_and_stops() -> None:
    repository, item = FakeRepository([]), make_item()
    repository.heartbeat_answers = [True, False]
    beat = _beat(repository, item)
    beat.start()
    _wait(item.lease_lost.is_set, "the lease to be reported lost")
    beat.stop()
    assert repository.heartbeats == 2


def test_a_cancel_requested_while_the_item_runs_reaches_the_handler() -> None:
    repository, item = FakeRepository([]), make_item()
    repository.cancel_answer = True
    beat = _beat(repository, item)
    beat.start()
    _wait(item.cancelled.is_set, "the cancel to be seen")
    beat.stop()
    assert not item.lease_lost.is_set()


def test_past_the_watchdog_the_heartbeat_fences_its_own_attempt_and_stops_extending() -> None:
    repository, item = FakeRepository([]), make_item()
    fenced: list[str] = []
    beat = _beat(repository, item, watchdog=0.05, fence=lambda session, attempt_id: fenced.append(attempt_id))
    beat.start()
    _wait(item.lease_lost.is_set, "the watchdog")
    beat.stop()
    assert fenced == ["cqa_X"]
    count = repository.heartbeats
    time.sleep(0.1)
    assert repository.heartbeats == count


def test_a_failing_heartbeat_is_logged_and_retried_not_fatal(caplog) -> None:  # type: ignore[no-untyped-def]
    repository, item = FakeRepository([]), make_item()
    calls = {"n": 0}

    def flaky(session: Any, authority: Any) -> bool:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("database hiccup")
        return True

    repository.heartbeat = flaky  # type: ignore[method-assign]
    beat = _beat(repository, item)
    with caplog.at_level("ERROR"):
        beat.start()
        _wait(lambda: calls["n"] >= 3, "the heartbeat to retry")
        beat.stop()
    assert "heartbeat failed" in caplog.text and "token" not in caplog.text
    assert not item.lease_lost.is_set()
