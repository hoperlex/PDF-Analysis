"""A serving process reclaims a killed predecessor's temporaries as it starts (`RUN-ROBUSTNESS-01`, D-170).

The sweep itself is proved in ``tests/unit/jobs/test_stale_temporaries.py``. What is shown here
is that the two process starts that matter call it, before they take any work:

* the API and the all-in-one process, through ``start_serving_carrier`` (a serving carrier
  only -- the inert carriers of constructed applications and tests sweep nothing);
* the worker service, through ``python -m auditmanager.workers serve``, after its
  configuration is accepted and before it registers.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.runs import public as runs_public
from auditmanager.runs.carrier import InlineCarrier, ReclaimingCarrier


class _RecordingCarrier(ReclaimingCarrier):
    """A reclaiming carrier that records the order of events and starts no thread."""

    def __init__(self, events: list[str]) -> None:  # noqa: D107 - no session factory needed
        self.events = events

    def start(self) -> None:
        self.events.append("carrier started")


def test_a_serving_carrier_is_started_after_the_sweep(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    monkeypatch.setattr(runs_public, "sweep_stale_temporaries", lambda: events.append("swept"))

    runs_public.start_serving_carrier(_RecordingCarrier(events))

    assert events == ["swept", "carrier started"]


def test_an_inert_carrier_sweeps_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    monkeypatch.setattr(runs_public, "sweep_stale_temporaries", lambda: events.append("swept"))

    runs_public.start_serving_carrier(InlineCarrier())

    assert events == []


def test_the_worker_sweeps_after_its_configuration_is_accepted_and_before_it_registers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import auditmanager.bootstrap.public as bootstrap_public
    import auditmanager.jobs.public as jobs_public
    import auditmanager.workers.service as worker_service
    from auditmanager.workers import __main__ as worker_main

    events: list[str] = []

    class Runtime:
        engine = session_factory = execute = version = slots = state_dir = probe_runner = None
        settings = type("Settings", (), {"provider_source": "environment"})()

    class FakeService:
        failed = True  # the loop in `serve` ends at once
        worker_id = "wrk_fake"
        busy = 0

        def __init__(self, **_arguments: Any) -> None:
            events.append("service built")

        def start(self) -> None:
            events.append("service started")

        def drain(self, timeout: float) -> bool:
            return True

        def stop(self) -> None:
            events.append("service stopped")

    def build(environ: dict[str, str]) -> Runtime:
        events.append("configuration accepted")
        return Runtime()

    monkeypatch.setattr(bootstrap_public, "build_worker_runtime", build)
    monkeypatch.setattr(worker_service, "WorkerService", FakeService)
    monkeypatch.setattr(jobs_public, "sweep_stale_temporaries", lambda: events.append("swept"))
    monkeypatch.setattr(worker_main.signal, "signal", lambda *_a, **_k: None)

    assert worker_main.serve({}) == 1  # `failed` is true, so the service reports failure
    assert events[:3] == ["configuration accepted", "swept", "service built"]
    assert events.index("swept") < events.index("service started")


def test_a_refused_configuration_sweeps_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    import auditmanager.bootstrap.public as bootstrap_public
    import auditmanager.jobs.public as jobs_public
    from auditmanager.workers import __main__ as worker_main

    events: list[str] = []

    def refuse(environ: dict[str, str]) -> None:
        raise bootstrap_public.ConfigurationError("no database")

    monkeypatch.setattr(bootstrap_public, "build_worker_runtime", refuse)
    monkeypatch.setattr(jobs_public, "sweep_stale_temporaries", lambda: events.append("swept"))

    assert worker_main.serve({}) == 2
    assert events == []
