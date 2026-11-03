"""Stopping the ``WorkerService`` instances a test started, whatever became of the test.

A ``WorkerService`` runs daemon threads (heartbeat, dispatch, temporaries sweep, optional probe loop) that
hold database connections and write to the registry until ``stop()`` sets their event. A test that fails
with the service half-built, a fixture whose ``drain`` raises before the next service is reached, a
``stop`` that returns while a thread is still inside a database call -- each leaves a worker that keeps
logging ``heartbeat failed; retried next tick`` into the tests that follow it and keeps its connections
for the rest of the session.

:func:`stop_all` is the one teardown the worker-starting fixtures share:

* every service is drained and stopped, **each in its own ``try``**, so a failure on the first does not
  leave the rest running;
* a service is stopped even when its ``drain`` raised, and a service that was registered with the fixture
  *before* ``start()`` is stopped even when ``start()`` raised half way;
* afterwards no thread of the worker loops may be left: a loop thread still alive after
  ``settle_seconds`` is an ``AssertionError`` naming it, not a warning in a log that nobody reads;
* the first error that occurred is re-raised after everything has been stopped (chained under the thread
  assertion when both happen), so the test still fails with its real cause.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Sequence
from typing import Any

#: The names ``WorkerService.start`` gives its loop threads (``auditmanager.workers.service``).
LOOP_THREAD_NAMES = (
    "auditmanager-worker-heartbeat",
    "auditmanager-worker-dispatch",
    "auditmanager-worker-temporaries",
    "auditmanager-worker-probes",
)


def live_loop_threads() -> list[str]:
    """The names of the worker loop threads alive in this process (one entry per thread)."""
    return sorted(thread.name for thread in threading.enumerate() if thread.name in LOOP_THREAD_NAMES)


def stop_all(services: Sequence[Any], *, drain_timeout: float, settle_seconds: float = 10.0) -> None:
    """Drain and stop every service, then require that no worker loop thread is left in the process."""
    first_error: BaseException | None = None
    for service in services:
        try:
            service.drain(timeout=drain_timeout)
        except BaseException as error:  # noqa: BLE001 - the others must still be stopped
            first_error = first_error or error
        finally:
            try:
                service.stop()
            except BaseException as error:  # noqa: BLE001
                first_error = first_error or error
    deadline = time.monotonic() + settle_seconds
    while live_loop_threads() and time.monotonic() < deadline:
        time.sleep(0.05)
    left = live_loop_threads()
    if left:
        raise AssertionError(
            f"worker loop threads still alive {settle_seconds:g} s after stop(): {left}"
        ) from first_error
    if first_error is not None:
        raise first_error
