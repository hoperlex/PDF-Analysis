"""``tests/support/worker_services.stop_all``: the teardown every worker-starting fixture shares can fail.

A teardown that only ever succeeded would be a comment. Each case below is a way the old fixtures left a worker
running; the last two feed it a service that cannot be stopped, and require the red.
"""

from __future__ import annotations

import threading

import pytest

from tests.support.worker_services import LOOP_THREAD_NAMES, live_loop_threads, stop_all


class _Service:
    """Starts one loop thread under a real worker loop name; ``stop`` ends it, unless it is told not to."""

    def __init__(self, *, name: str = LOOP_THREAD_NAMES[0], drain_raises: bool = False,
                 stop_raises: bool = False, stop_ends_thread: bool = True) -> None:
        self._release = threading.Event()
        self.drain_raises, self.stop_raises, self.stop_ends_thread = drain_raises, stop_raises, stop_ends_thread
        self.drained = self.stopped = False
        self.thread = threading.Thread(target=self._release.wait, name=name, daemon=True)
        self.thread.start()

    def drain(self, timeout: float | None = None) -> bool:
        self.drained = True
        if self.drain_raises:
            raise RuntimeError("drain failed")
        return True

    def stop(self) -> None:
        self.stopped = True
        if self.stop_ends_thread:
            self._release.set()
            self.thread.join(5)
        if self.stop_raises:
            raise RuntimeError("stop failed")

    def release(self) -> None:
        self._release.set()
        self.thread.join(5)


@pytest.fixture(autouse=True)
def _no_loop_thread_survives_this_module():
    yield
    assert live_loop_threads() == [], "a test of this module left a worker loop thread running"


def test_every_service_is_drained_and_stopped_and_its_thread_ends() -> None:
    services = [_Service(), _Service(name=LOOP_THREAD_NAMES[1])]
    stop_all(services, drain_timeout=1, settle_seconds=2)
    assert all(s.drained and s.stopped for s in services) and live_loop_threads() == []


def test_a_drain_that_raises_does_not_leave_the_others_or_itself_running() -> None:
    services = [_Service(drain_raises=True), _Service(), _Service(name=LOOP_THREAD_NAMES[2])]
    with pytest.raises(RuntimeError, match="drain failed"):
        stop_all(services, drain_timeout=1, settle_seconds=2)
    assert all(s.stopped for s in services), "a service whose drain raised, and those after it, are stopped"
    assert live_loop_threads() == []


def test_a_stop_that_raises_does_not_skip_the_next_service() -> None:
    services = [_Service(stop_raises=True), _Service()]
    with pytest.raises(RuntimeError, match="stop failed"):
        stop_all(services, drain_timeout=1, settle_seconds=2)
    assert all(s.stopped for s in services) and live_loop_threads() == []


def test_a_service_whose_stop_leaves_its_thread_alive_is_a_failure_naming_the_thread() -> None:
    stuck = _Service(name=LOOP_THREAD_NAMES[1], stop_ends_thread=False)
    try:
        with pytest.raises(AssertionError, match="auditmanager-worker-dispatch"):
            stop_all([stuck], drain_timeout=1, settle_seconds=0.3)
    finally:
        stuck.release()


def test_the_original_error_is_kept_beside_a_thread_that_is_left() -> None:
    stuck = _Service(drain_raises=True, stop_ends_thread=False)
    try:
        with pytest.raises(AssertionError) as caught:
            stop_all([stuck], drain_timeout=1, settle_seconds=0.3)
        assert isinstance(caught.value.__cause__, RuntimeError)
    finally:
        stuck.release()
