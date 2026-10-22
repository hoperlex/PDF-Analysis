"""The worker service's probe thread (`EXEC-HTTP-01`): it polls, it survives a failing pass, and a
draining worker takes no new probe. Container-free: the service is built with no engine and the
loop is driven directly."""

from __future__ import annotations

import threading
import time

from auditmanager.workers.service import WorkerService


def _service(runner) -> WorkerService:  # type: ignore[no-untyped-def]
    return WorkerService(
        engine=None, session_factory=None, execute=lambda run_id, worker_id: None,  # type: ignore[arg-type]
        version="test", probe_runner=runner, probe_poll_seconds=0.01,
    )


def _run(service: WorkerService, seconds: float) -> None:
    thread = threading.Thread(target=service._probe_loop, daemon=True)
    thread.start()
    time.sleep(seconds)
    service._stopped.set()
    thread.join(timeout=2)
    assert not thread.is_alive()


def test_the_loop_polls_the_runner_and_survives_a_failing_pass() -> None:
    calls: list[int] = []

    def runner() -> int:
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("one bad pass")
        return 0

    _run(_service(runner), 0.3)
    assert len(calls) >= 3, "the loop kept polling after the failure"


def test_a_draining_worker_takes_no_new_probe() -> None:
    calls: list[int] = []
    service = _service(lambda: calls.append(1) or 0)
    service._draining.set()
    _run(service, 0.2)
    assert calls == []


def test_the_loop_is_only_started_when_a_runner_is_given() -> None:
    assert _service(None)._probe_runner is None
