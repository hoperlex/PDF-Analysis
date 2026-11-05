"""`EXEC2-FOLLOWUP-01` item 3: where the worker takes the comparison jobs' offline sweep (ADR-0026 decision 15).

The dispatch loop keeps the Runs admitted on a group true every ``GROUP_WAIT_SECONDS``; the same step now also ends the comparison AI jobs
whose group has had no eligible member for longer than the limit. Container-free; the worker's sweep is a value:

* the sweep is called with the limit the service read (``AUDITMANAGER_GROUP_OFFLINE_WAIT_SECONDS``), once per step;
* it runs **only** for a worker that dispatches groups (``dispatch_groups``, the `database` provider source), as the claim of a pending
  group Run does, and not at all when none was given;
* it is a step of its own: a Run sweep that fails does not stop it, and a comparison sweep that fails is logged by its category (never
  its text) and does not stop the loop;
* the dispatch loop calls it beside the Runs' step, in the same interval.

The sweep itself is ``tests/unit/comparison/ai_jobs/test_group_waits.py``.

Written and **not run** in EXEC-2 (`R-149d`).
"""

from __future__ import annotations

import inspect
import logging
import re
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest

import auditmanager.workers.service as service_module
from auditmanager.workers.service import GROUP_WAIT_SECONDS, WorkerService


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


@pytest.fixture
def made(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    services: list[WorkerService] = []

    def make(**options: Any) -> WorkerService:
        service = WorkerService(
            engine=None, session_factory=_Session, execute=lambda run, worker: None, version="unit",  # type: ignore[arg-type]
            registry=_Registry(), heartbeat_seconds=3600.0, group_offline_wait_seconds=75.0, **options,  # type: ignore[arg-type]
        )
        service._worker_id = "wrk_unit"
        services.append(service)
        return service

    yield make
    for service in services:
        service.stop()


def test_the_sweep_is_called_with_the_offline_limit_the_service_read(made: Any) -> None:
    calls: list[float] = []

    def sweep(limit: float) -> SimpleNamespace:
        calls.append(limit)
        return SimpleNamespace(expired=0, skipped=0, failed=0)

    made(comparison_group_waits=sweep)._expire_comparison_waits()
    assert calls == [75.0]


def test_a_worker_that_does_not_dispatch_groups_never_runs_it(made: Any) -> None:
    """The `environment` source has no connection to bind a group job to, so it has no group job to expire either."""
    calls: list[float] = []
    made(dispatch_groups=False, comparison_group_waits=lambda limit: calls.append(limit))._expire_comparison_waits()
    assert calls == []


def test_a_worker_given_no_sweep_does_nothing_and_does_not_fail(made: Any) -> None:
    made()._expire_comparison_waits()


def test_a_sweep_that_fails_is_logged_by_category_and_does_not_stop_the_loop(made: Any, caplog: pytest.LogCaptureFixture) -> None:
    def failing(limit: float) -> None:
        raise RuntimeError("a row quoted: secret-value-123")

    with caplog.at_level(logging.ERROR, logger=service_module.__name__):
        made(comparison_group_waits=failing)._expire_comparison_waits()
    text = " ".join(record.getMessage() for record in caplog.records)
    assert "RuntimeError" in text and "secret-value-123" not in text


def test_a_failed_job_in_a_pass_is_reported_as_an_error_and_an_ended_one_as_information(made: Any, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger=service_module.__name__):
        made(comparison_group_waits=lambda limit: SimpleNamespace(expired=2, skipped=0, failed=1))._expire_comparison_waits()
    levels = {record.levelno: record.getMessage() for record in caplog.records}
    assert "2 comparison job(s) ended no_executor_online" in levels[logging.INFO]
    assert "1 comparison job(s) could not be decided" in levels[logging.ERROR]


def test_a_failing_run_sweep_does_not_stop_the_comparison_sweep_and_the_reverse(
    made: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    ran: list[str] = []

    class Repository:
        def __init__(self, **options: Any) -> None: ...

        def refresh_group_waits(self, session: object, **options: Any) -> None:
            ran.append("runs")
            raise RuntimeError("the Run sweep failed")

    monkeypatch.setattr(service_module, "JobRepository", Repository)

    def comparison(limit: float) -> SimpleNamespace:
        ran.append("comparison")
        return SimpleNamespace(expired=0, skipped=0, failed=0)

    service = made(comparison_group_waits=comparison)
    service._refresh_group_waits()
    service._expire_comparison_waits()
    assert ran == ["runs", "comparison"]

    ran.clear()
    service = made(comparison_group_waits=lambda limit: (_ for _ in ()).throw(RuntimeError("the comparison sweep failed")))
    service._expire_comparison_waits()
    service._refresh_group_waits()
    assert ran == ["runs"]


def test_the_dispatch_loop_takes_the_comparison_step_beside_the_runs_in_the_same_interval() -> None:
    source = inspect.getsource(WorkerService._dispatch_loop)
    block = re.search(r"if now >= next_waits:\n(?P<body>(?:\s+.*\n){1,6}?)\s+if self\._poll_now", source)
    assert block is not None, "the loop's group-wait step"
    body = block.group("body")
    assert body.index("self._refresh_group_waits()") < body.index("self._expire_comparison_waits()") < body.index("next_waits = monotonic() + GROUP_WAIT_SECONDS")
    assert GROUP_WAIT_SECONDS == 5.0
