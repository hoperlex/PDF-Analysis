"""`SEC-RUNNER-CAP-01` (`F-06`): one runner token cannot hold the API's synchronous pool.

``claimExecutorTask`` is a synchronous handler that sleeps in its pool thread for up to 25 s
(``executors.runner.claim_task``). The API's pool is anyio's default, 40 threads. Before this
slice one token, or sixteen, could park enough claims to leave no thread for sign-in, reads or
the next upload; every other sync handler then queued behind them.

The scenario is the real thing, container-free: the real router
(``build_runner_routes``), the real ``claim_task`` loop, an ASGI client that opens the claims
at the same moment, and a stand-in for ``getMe`` that runs in the same pool. Only two things
are fakes: the rows (there is never a task) and the sleep, which blocks on an event the test
controls so that no assertion depends on a stopwatch for the green side.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Callable
from pathlib import Path
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi import APIRouter, FastAPI, Request

from auditmanager.api.routers.runner import build_runner_routes
from auditmanager.api.security import RunnerIdentity, current_runner
from auditmanager.executors import runner as runner_module
from auditmanager.executors.runner import RunnerPrincipal, claim_task
from auditmanager.executors.runner_repository import ClaimedRow

#: The API's synchronous pool: anyio's default limiter (measured in `EXPOSURE-REVIEW-02`).
POOL_THREADS = 40
#: The threads the stand promises to leave to everything else while long polls are parked.
RESERVE = 24
CLAIMS = 45  # more than the pool, so that an unbounded implementation fills it


class _Session:
    def __enter__(self) -> _Session:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def commit(self) -> None:
        return None


class _Executors:
    def current_revisions(self, session: Any, connection_ids: Any) -> dict[str, Any]:
        return {}


class _Rows:
    """The runner repository with the rows taken out: ``row`` is what ``claim_next`` returns."""

    def __init__(self, row: ClaimedRow | None = None, *, fail: bool = False,
                 on_look: Callable[[], None] | None = None) -> None:
        self.row = row
        self.fail = fail
        self.looks = 0
        self._on_look = on_look

    def sweep(self, session: Any, connection_id: str) -> None:
        self.looks += 1
        if self._on_look is not None:
            self._on_look()
        if self.fail:
            raise RuntimeError("database is down")

    def clear_terminal_payloads(self, session: Any, **kwargs: Any) -> None:
        return None

    def redeliver(self, session: Any, **kwargs: Any) -> None:
        return None

    def held_claims(self, session: Any, token_id: str) -> int:
        return 0

    def claim_next(self, session: Any, **kwargs: Any) -> ClaimedRow | None:
        return self.row


def _row() -> ClaimedRow:
    now = datetime.now(UTC)
    return ClaimedRow(
        task_id="ext_01M2545JSD15ETSNNV904X991K", claim_expires_at=now + timedelta(seconds=120),
        deadline_at=now + timedelta(seconds=600), expected_model="m",
        payload={"system": "s", "user_text": "u", "output_schema": {}},
    )


class _Parking:
    """A sleep that parks its thread until ``release`` and counts the threads parked at once."""

    def __init__(self) -> None:
        self._gate = threading.Event()
        self._lock = threading.Lock()
        self.parked = 0
        self.peak = 0
        self._skew = 0.0

    def sleep(self, seconds: float) -> None:
        with self._lock:
            self.parked += 1
            self.peak = max(self.peak, self.parked)
        try:
            self._gate.wait(30)
        finally:
            with self._lock:
                self.parked -= 1
                self._skew += 1000.0  # the wait is over: the claim's clock jumps past its stop

    def monotonic(self) -> float:
        return time.monotonic() + self._skew

    def release(self) -> None:
        self._gate.set()


class _Port:
    """What the composition root's ``RunnerAdapter.claim_task`` does, over the real loop."""

    def __init__(self, parking: _Parking, rows: _Rows) -> None:
        self._parking = parking
        self._rows = rows

    def claim_task(self, *, runner: RunnerIdentity, wait_seconds: int) -> None:
        claim_task(
            _Session, RunnerPrincipal(runner.token_id, runner.connection_id),
            wait_seconds=wait_seconds, executors=_Executors(), repository=self._rows,  # type: ignore[arg-type]
            sleep=self._parking.sleep, monotonic=self._parking.monotonic,
        )
        return None


def _app(port: _Port) -> FastAPI:
    router = APIRouter()
    build_runner_routes(router, port)  # type: ignore[arg-type]

    @router.get("/me")
    def get_me() -> dict[str, str]:  # a synchronous handler: it needs a pool thread
        return {"who": "me"}

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[current_runner] = _identity
    return app


def _identity(request: Request) -> RunnerIdentity:
    return RunnerIdentity(token_id=request.headers["x-token"], connection_id="exc_1")


async def _open_claims(tokens: list[str], parking: _Parking) -> tuple[
    list[httpx.Response], bool, int, int
]:
    """Open one claim per entry of ``tokens`` at the same moment, then ask ``getMe`` in the same
    pool. Returns (every claim's response, whether ``getMe`` answered in time, claims already
    answered while the sleepers were still parked, the peak of parked threads)."""
    port = _Port(parking, _Rows())
    transport = httpx.ASGITransport(app=_app(port))
    async with httpx.AsyncClient(transport=transport, base_url="http://api.test",
                                 timeout=60) as client:
        claims = [
            asyncio.create_task(client.post(
                "/runner/tasks/claim", json={"wait_seconds": 25}, headers={"x-token": token}))
            for token in tokens
        ]
        await asyncio.sleep(0.6)  # long enough for every claim that can to reach its sleep
        answered_early = sum(1 for claim in claims if claim.done())
        peak_while_parked = parking.parked
        me = asyncio.create_task(client.get("/me"))
        try:
            answered, _ = await asyncio.wait({me}, timeout=2.0)
            me_answered = bool(answered)
        finally:
            parking.release()
        await me  # ends once the parked claims have: it was only queued behind them
        responses = await asyncio.gather(*claims)
    return list(responses), me_answered, answered_early, peak_while_parked


def _run(tokens: list[str]) -> tuple[list[httpx.Response], bool, int, int, _Parking]:
    parking = _Parking()
    responses, me_answered, early, parked = asyncio.run(_open_claims(tokens, parking))
    return responses, me_answered, early, parked, parking


def test_many_claims_from_one_token_leave_the_pool_to_everything_else() -> None:
    """The finding itself: 45 simultaneous claims of ONE token. Unbounded, 40 of them park in
    pool threads and ``getMe`` waits behind them; bounded, one parks and the rest are answered
    ``204`` at once."""
    responses, me_answered, answered_early, parked, parking = _run(["amr_token_one"] * CLAIMS)

    assert me_answered, f"getMe waited behind {parked} parked claims"
    assert parking.peak == 1, f"{parking.peak} claims of one token slept at once"
    assert answered_early == CLAIMS - 1, "the others were answered while the one still waited"
    assert {response.status_code for response in responses} == {204}
    assert all(response.content == b"" for response in responses)


def test_many_tokens_cannot_park_more_than_the_stated_share_of_the_pool() -> None:
    """Forty tokens, one claim each: no per-token bound is breached, so only the total keeps
    ``RESERVE`` threads free."""
    tokens = [f"amr_token_{index:02d}" for index in range(POOL_THREADS)]
    responses, me_answered, _, parked, parking = _run(tokens)

    assert me_answered, f"getMe waited behind {parked} parked claims"
    assert parking.peak <= POOL_THREADS - RESERVE, f"{parking.peak} threads parked at once"
    assert parking.peak >= 1
    assert {response.status_code for response in responses} == {204}


def test_a_waiting_token_does_not_stop_another_token_waiting() -> None:
    """The bound is per token: two tokens each wait once, so the second is not refused by
    the first's presence (a single global slot would make this fail)."""
    _, me_answered, _, _, parking = _run(["amr_token_a"] * 6 + ["amr_token_b"] * 6)

    assert me_answered
    assert parking.peak == 2


def test_the_shipped_shares_state_the_reserve() -> None:
    assert runner_module.MAX_WAITING_CLAIMS_PER_TOKEN == 1
    assert runner_module.SYNC_POOL_THREADS == POOL_THREADS
    assert POOL_THREADS - runner_module.MAX_WAITING_CLAIMS_TOTAL >= RESERVE
    assert runner_module.RESERVED_SYNC_THREADS == (
        POOL_THREADS - runner_module.MAX_WAITING_CLAIMS_TOTAL)


def test_the_pool_figure_is_the_one_anyio_really_has() -> None:
    """The share is stated against 40 threads; this is what the installed anyio gives a
    synchronous handler."""
    import anyio
    import anyio.to_thread

    async def measured() -> float:
        return anyio.to_thread.current_default_thread_limiter().total_tokens

    assert anyio.run(measured) == runner_module.SYNC_POOL_THREADS


def test_nothing_in_the_application_resizes_the_pool() -> None:
    """If a later slice sets the limiter, the constant above no longer describes the pool: this
    fails so that the share is restated with it (and `RESERVED_SYNC_THREADS` with it)."""
    root = Path(runner_module.__file__).resolve().parents[1]
    hits = [str(path.relative_to(root)) for path in sorted(root.rglob("*.py"))
            if any(word in path.read_text(encoding="utf-8")
                   for word in ("total_tokens", "CapacityLimiter", "set_default_thread_limiter"))]
    assert hits == [], f"a thread limiter is configured in {hits}"


def test_the_process_state_is_empty_after_the_claims_end() -> None:
    _run(["amr_token_one"] * 3)
    assert runner_module.long_polls_waiting() == 0


# -- the slots themselves -----------------------------------------------------------------------


def _slots(per_token: int = 1, total: int = 2) -> Any:
    return runner_module.LongPollSlots(per_token=per_token, total=total)


def test_slots_bound_per_token_and_in_total_and_give_back() -> None:
    slots = _slots(per_token=1, total=2)
    assert slots.try_acquire("a")
    assert not slots.try_acquire("a"), "the token already waits"
    assert slots.try_acquire("b")
    assert not slots.try_acquire("c"), "the total is spent"
    assert slots.waiting == 2
    slots.release("a")
    assert slots.try_acquire("c"), "a released slot is reusable"
    slots.release("b")
    slots.release("c")
    assert slots.waiting == 0


def test_a_slot_is_given_back_when_the_claim_raises() -> None:
    slots = _slots()
    with pytest.raises(RuntimeError):
        claim_task(
            _Session, RunnerPrincipal("tok_1", "exc_1"), wait_seconds=5,
            executors=_Executors(), repository=_Rows(fail=True),  # type: ignore[arg-type]
            slots=slots,
        )
    assert slots.waiting == 0, "an error left a slot held for ever"
    assert slots.try_acquire("tok_1")


def test_a_claim_that_waits_holds_its_slot_while_it_sleeps() -> None:
    slots = _slots(per_token=1, total=1)
    seen: list[int] = []

    def sleep(_: float) -> None:
        seen.append(slots.waiting)

    clock = iter([0.0, 0.5, 100.0])
    claim_task(
        _Session, RunnerPrincipal("tok_1", "exc_1"), wait_seconds=5, executors=_Executors(),
        repository=_Rows(), slots=slots, sleep=sleep,  # type: ignore[arg-type]
        monotonic=lambda: next(clock),
    )
    assert seen == [1]
    assert slots.waiting == 0


def _no_sleep(_: float) -> None:
    raise AssertionError("an over-the-bound claim must not sleep")


def test_a_claim_over_the_bound_still_looks_once_and_returns_a_ready_task_at_once() -> None:
    slots = _slots(per_token=1, total=1)
    assert slots.try_acquire("tok_1")  # the token already waits somewhere else
    rows = _Rows(_row())
    task = claim_task(
        _Session, RunnerPrincipal("tok_1", "exc_1"), wait_seconds=25, executors=_Executors(),
        repository=rows, slots=slots, sleep=_no_sleep,  # type: ignore[arg-type]
    )
    assert task is not None and task.task_id == "ext_01M2545JSD15ETSNNV904X991K"
    assert slots.waiting == 1, "it neither took nor gave back the slot of the other claim"


def test_a_claim_over_the_bound_with_nothing_open_answers_none_at_once() -> None:
    slots = _slots(per_token=1, total=1)
    assert slots.try_acquire("tok_1")
    rows = _Rows()
    answer = claim_task(
        _Session, RunnerPrincipal("tok_1", "exc_1"), wait_seconds=25, executors=_Executors(),
        repository=rows, slots=slots, sleep=_no_sleep,  # type: ignore[arg-type]
    )
    assert answer is None
    assert rows.looks == 1, "exactly one look at the rows"


def test_wait_zero_never_takes_a_slot() -> None:
    slots = _slots(per_token=1, total=1)
    held_during_the_look: list[int] = []
    rows = _Rows(on_look=lambda: held_during_the_look.append(slots.waiting))
    assert claim_task(
        _Session, RunnerPrincipal("tok_1", "exc_1"), wait_seconds=0, executors=_Executors(),
        repository=rows, slots=slots, sleep=_no_sleep,  # type: ignore[arg-type]
    ) is None
    assert held_during_the_look == [0], "a claim that cannot sleep held a slot while it looked"
    assert slots.waiting == 0
    assert slots.try_acquire("tok_1"), "wait 0 left the slot free"


def test_the_wait_is_still_clamped_to_the_contract() -> None:
    """The existing semantics: 0..25 seconds, the poll once a second."""
    slots = _slots(per_token=1, total=1)
    slept: list[float] = []
    now = [0.0]

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        now[0] += seconds

    claim_task(
        _Session, RunnerPrincipal("tok_1", "exc_1"), wait_seconds=999, executors=_Executors(),
        repository=_Rows(), slots=slots, sleep=sleep, monotonic=lambda: now[0],  # type: ignore[arg-type]
    )
    assert sum(slept) == pytest.approx(25.0)
    assert set(slept) == {1.0}


def test_two_instances_do_not_share_state() -> None:
    """The state is the process's: another process (a second API worker) has its own, which
    is right because its pool is its own."""
    first, second = _slots(), _slots()
    assert first.try_acquire("a")
    assert second.try_acquire("a")
    first.release("a")
    second.release("a")
