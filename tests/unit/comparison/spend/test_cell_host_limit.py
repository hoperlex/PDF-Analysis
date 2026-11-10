"""`D-677` (`HOSTS-DEBTS-01`): the ceiling a host agent is told for a comparison call is the limit of the request that is sent.

A comparison job's cell holds the answer limit the owner chose for that kind of work; ``apply_cell`` sends ``min(module limit, cell limit)`` in the
request. The host call (``payload.host``) used to carry the cell's limit alone, so the agent could be told it may answer more than the request asks.
``host_call_of`` builds one call per route while the limit is per request, so the host call reads the request being sent (``answer_limit_of``,
entered by ``PublishedPullAdapter.complete``).

Container-free: the real ``PullAdapter`` and ``PublishedPullAdapter`` over the scripted task table of ``tests/unit/executors/test_pull_adapter.py``.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from auditmanager.analysis.public import CellSettings, ModelRequest
from auditmanager.comparison.spend.cell import answer_limit_of, apply_cell, host_call_of
from auditmanager.comparison.spend.model import CallEstimate
from auditmanager.comparison.spend.pull_images import PublishedPullAdapter
from auditmanager.executors import pull
from auditmanager.executors.public import HostCall
from auditmanager.executors.pull import PullAdapter
from tests.unit.executors.test_pull_adapter import MODEL, REQUEST, Clock, FakeStore, Sessions, revision

CELL = CellSettings("comparison_pair_check:main", MODEL, "medium", 800, 600)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    fake = Clock()
    monkeypatch.setattr(pull.time, "sleep", fake.sleep)
    return fake


def _answer(c: Clock, store: FakeStore) -> None:
    if store.task is not None and store.task.state == "open":
        store.claim()
        store.answered('{"observations": []}', MODEL)


class _NoPublisher:
    def publish(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("a request with no image publishes nothing")


def _request(max_tokens: int | None) -> ModelRequest:
    body = {key: value for key, value in REQUEST.body.items() if key != "max_tokens"}
    if max_tokens is not None:
        body["max_tokens"] = max_tokens
    return replace(REQUEST, body=body)


def _routes(clock: Clock) -> tuple[HostCall, FakeStore, PullAdapter, PublishedPullAdapter]:
    """What ``_ComparisonRoutes.route`` makes for a job with a cell: the host call of the cell, the pull adapter that carries it, and the wrapper."""
    call = host_call_of(CELL, provider="claude_code", access="subscription")
    store = FakeStore(clock, _answer)
    adapter = PullAdapter(session_factory=Sessions(), revision=revision(deadline=3600), context=None, repository=store,  # type: ignore[arg-type]
                          poll_seconds=2.0, monotonic=clock.monotonic, host_call=call)
    return call, store, adapter, PublishedPullAdapter(adapter, _NoPublisher())


def _told(store: FakeStore) -> int:
    assert store.payload is not None
    return store.payload["host"]["max_output_tokens"]


@pytest.mark.parametrize(
    ("module_limit", "told"),
    [(1_200, 800), (600, 600), (800, 800), (None, 800)],
    ids=["module_above_cell", "module_below_cell", "equal", "request_names_none"],
)
def test_the_task_tells_the_agent_the_limit_of_the_request_that_is_sent(clock: Clock, module_limit: int | None, told: int) -> None:
    _call, store, _adapter, route = _routes(clock)
    # the request as the wrapper sends it: the module's own, held to the cell's by `apply_cell` (what `ComparisonModelCaller.call` does)
    sent, _estimate = apply_cell(CELL, _request(module_limit), CallEstimate(input_tokens=1, output_tokens=module_limit or 1))
    route.complete(sent)
    assert _told(store) == told
    assert _told(store) == sent.body["max_tokens"], "the agent is told what the request asks, whatever the module's limit was"


def test_the_ceiling_is_never_above_the_cells_even_if_a_request_names_more(clock: Clock) -> None:
    """A request that did not pass through ``apply_cell`` cannot raise the agent's ceiling over the cell's."""
    _call, store, _adapter, route = _routes(clock)
    route.complete(_request(5_000))
    assert _told(store) == CELL.max_output_tokens


def test_without_the_wrapper_the_host_call_is_the_cells_alone(clock: Clock) -> None:
    """A pull call that is not made through ``PublishedPullAdapter`` (nothing enters ``answer_limit_of``) keeps the cell's ceiling."""
    _call, store, adapter, _route = _routes(clock)
    adapter.complete(_request(600))
    assert _told(store) == 800


def test_the_request_limit_ends_with_the_call_even_when_the_call_fails(clock: Clock) -> None:
    call, store, adapter, route = _routes(clock)
    assert call.members(100)["max_output_tokens"] == 800
    with answer_limit_of(_request(600)):
        assert call.members(100)["max_output_tokens"] == 600, "inside the block the request's limit is told"
    assert call.members(100)["max_output_tokens"] == 800, "and outside it the cell's"

    def refuse(c: Clock, s: FakeStore) -> None:
        raise RuntimeError("the table failed")

    store.script = refuse
    with pytest.raises(RuntimeError):
        route.complete(_request(600))
    assert call.members(100)["max_output_tokens"] == 800, "a call that raised leaves nothing behind"


def test_the_host_call_is_still_a_host_call_with_the_seven_members(clock: Clock) -> None:
    call, store, _adapter, route = _routes(clock)
    assert isinstance(call, HostCall) and call.cell_key == "comparison_pair_check:main" and call.timeout_seconds == 600
    route.complete(_request(600))
    assert store.payload is not None and set(store.payload["host"]) == {
        "provider", "access", "model_id", "effort", "max_output_tokens", "timeout_seconds", "cell_key"}
