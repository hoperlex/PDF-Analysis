"""The wiring ``python -m auditmanager.workers serve`` does, against the lane's database (`CMP-WORK-01`).

``build_worker_runtime`` is run from the lane's own configuration with the module flag set, one handler
factory is put in the public tuple, and the service is built from what the runtime carries (the same
arguments the entry point hands it). The item runs, with the real gates and the real handler registry;
a duplicate kind in the tuple stops the build.
"""

from __future__ import annotations

import os
import time
from typing import Any

import pytest

from auditmanager.bootstrap import composition
from auditmanager.bootstrap.public import ConfigurationError, build_worker_runtime
from auditmanager.comparison.public import COMPARISON_MODULES_ENV, Completed
from auditmanager.workers.public import WorkerService

pytestmark = pytest.mark.usefixtures("quiet_runs")

_NAMES = ("DATABASE_URL", "S3_ENDPOINT_URL", "S3_REGION", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "S3_BUCKET")


def _environ(modules: str) -> dict[str, str]:
    return {**{name: os.environ[name] for name in _NAMES}, "EXECUTION_ROLE": "worker",
            COMPARISON_MODULES_ENV: modules}


class Recording:
    def __init__(self, kind: str) -> None:
        self.kind = kind
        self.items: list[Any] = []

    def run(self, item: Any) -> Any:
        self.items.append(item)
        return Completed()


def test_the_runtime_the_entry_point_builds_runs_an_item_through_its_registered_handler(
    queue, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = Recording(queue.kind)
    monkeypatch.setattr(composition, "COMPARISON_HANDLER_FACTORIES", (lambda dependencies: handler,))
    runtime = build_worker_runtime(environ=_environ("versions"))
    work_id = queue.enqueue(payload={"page": 9})
    service = WorkerService(
        engine=runtime.engine, session_factory=runtime.session_factory, execute=runtime.execute,
        version=runtime.version, slots=runtime.slots, state_dir=runtime.state_dir,
        probe_runner=runtime.probe_runner, comparison_work=runtime.comparison_work,
        poll_seconds=0.2, heartbeat_seconds=0.5, reclaim_seconds=0.5,
    )
    service.start()
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and queue.work(work_id)["state"] != "succeeded":
            time.sleep(0.05)
        assert queue.work(work_id)["state"] == "succeeded"
        assert [dict(item.payload) for item in handler.items] == [{"page": 9}]
    finally:
        service.drain(timeout=30)
        service.stop()
        runtime.engine.dispose()


def test_the_default_flag_builds_a_runner_that_claims_nothing(queue, monkeypatch: pytest.MonkeyPatch) -> None:
    handler = Recording(queue.kind)
    monkeypatch.setattr(composition, "COMPARISON_HANDLER_FACTORIES", (lambda dependencies: handler,))
    runtime = build_worker_runtime(environ={k: v for k, v in _environ("none").items()})
    try:
        work_id = queue.enqueue()
        assert runtime.comparison_work.claim("wrk_" + "0" * 26) is None
        assert queue.work(work_id)["state"] == "queued" and handler.items == []
    finally:
        runtime.engine.dispose()


def test_a_duplicate_kind_in_the_public_tuple_stops_the_build(queue, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(composition, "COMPARISON_HANDLER_FACTORIES",
                        (lambda dependencies: Recording(queue.kind), lambda dependencies: Recording(queue.kind)))
    with pytest.raises(ConfigurationError, match=queue.kind):
        build_worker_runtime(environ=_environ("versions"))
