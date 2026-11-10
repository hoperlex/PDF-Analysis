"""`LIMITS-01` (`R-153n`): no answer cap reaches a host agent for a comparison call -- the guard that replaces `D-677`.

`D-677` (`HOSTS-DEBTS-01`) told the agent the smaller of the request's limit and the cell's limit. The owner's ruling `R-153n` removes every answer
cap, so the task of a comparison call carries **none**: whatever ``max_tokens`` the request names (the module's own figure, which prices the call), the
``payload.host`` of the task has six members and no ``max_output_tokens``.

Container-free: the real ``PullAdapter`` and ``PublishedPullAdapter`` over the scripted task table of ``tests/unit/executors/test_pull_adapter.py``.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from auditmanager.analysis.public import CellSettings, ModelRequest
from auditmanager.comparison.spend.cell import apply_cell, host_call_of
from auditmanager.comparison.spend.model import CallEstimate
from auditmanager.comparison.spend.pull_images import PublishedPullAdapter
from auditmanager.executors import pull
from auditmanager.executors.public import HostCall
from auditmanager.executors.pull import PullAdapter
from tests.unit.executors.test_pull_adapter import MODEL, REQUEST, Clock, FakeStore, Sessions, revision

CELL = CellSettings("comparison_pair_check:main", MODEL, "medium")


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


def _host(store: FakeStore) -> dict[str, Any]:
    assert store.payload is not None
    return store.payload["host"]


@pytest.mark.parametrize("module_limit", [1_200, 600, None, 65_000], ids=["module_figure", "small", "request_names_none", "huge"])
def test_the_task_of_a_comparison_call_carries_no_answer_cap_whatever_the_request_names(clock: Clock, module_limit: int | None) -> None:
    _call, store, _adapter, route = _routes(clock)
    sent, _estimate = apply_cell(CELL, _request(module_limit), CallEstimate(input_tokens=1, output_tokens=module_limit or 1))
    route.complete(sent)
    host = _host(store)
    assert "max_output_tokens" not in host and "max_tokens" not in host, "no answer cap reaches the agent"
    assert sent.body.get("max_tokens") == module_limit, "the request keeps the module's own figure: it prices the call, it is not sent as a cap"


def test_the_pull_call_without_the_wrapper_carries_no_cap_either(clock: Clock) -> None:
    _call, store, adapter, _route = _routes(clock)
    adapter.complete(_request(600))
    assert "max_output_tokens" not in _host(store)


def test_the_host_call_has_six_members_and_the_kinds_window(clock: Clock) -> None:
    call, store, _adapter, route = _routes(clock)
    assert isinstance(call, HostCall) and call.cell_key == "comparison_pair_check:main" and call.timeout_seconds == 900
    assert "max_output_tokens" not in HostCall.__dataclass_fields__
    route.complete(_request(600))
    assert set(_host(store)) == {"provider", "access", "model_id", "effort", "timeout_seconds", "cell_key"}
    assert _host(store)["timeout_seconds"] == 900, "the window of the pair check is the original's 900 s (cut only by the watchdog)"
