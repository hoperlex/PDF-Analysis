"""The one hand-over `CMP-WORK-01` could not make inside its grant (container-free).

``python -m auditmanager.workers serve`` builds the runtime and hands its parts to ``WorkerService``.
The runtime carries ``comparison_work`` (the comparison loop's runner) and the service accepts it, but
the row of the wave brief does not name ``src/auditmanager/workers/__main__.py``, so the one argument
that joins them is the integrator's::

    # src/auditmanager/workers/__main__.py, in serve(), the WorkerService(...) call
            probe_runner=runtime.probe_runner,
    +       comparison_work=runtime.comparison_work,

Until it is applied the worker process never runs comparison work (nothing is registered and the module
flag defaults to ``none``, so nothing is lost, but nothing would run once a lane registers a handler).
This test says so: it is an expected failure *and strict*, so it turns red the moment the hunk is
applied, which is when the marker is to be removed and the test left as the permanent pin.

The two stand-in runtimes of ``tests/unit/executors/test_probe_loop.py`` (lines 79 and 117) then need
``comparison_work=None`` too; that file belongs to ``CMP-EXEC-IMAGES-01``'s directory in this wave.
"""

from __future__ import annotations

from types import SimpleNamespace



def test_serve_hands_the_runtimes_comparison_runner_to_the_worker_service(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import auditmanager.bootstrap.public as bootstrap_public
    import auditmanager.jobs.public as jobs_public
    import auditmanager.workers.__main__ as entry
    import auditmanager.workers.service as service_module

    marker = object()
    runtime = SimpleNamespace(
        engine=None, session_factory=None, execute=None, version="v", slots=1, state_dir=None,
        probe_runner=None, comparison_work=marker,
        settings=SimpleNamespace(provider_source="environment"),
    )
    captured: dict[str, object] = {}

    class FakeService:
        failed = True
        worker_id = "wrk_test"
        busy = 0

        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

        def start(self) -> None: ...

        def drain(self, timeout: float | None = None) -> bool:
            return True

        def stop(self) -> None: ...

    monkeypatch.setattr(bootstrap_public, "build_worker_runtime", lambda environ: runtime)
    monkeypatch.setattr(jobs_public, "sweep_stale_temporaries", lambda: None)
    monkeypatch.setattr(service_module, "WorkerService", FakeService)
    monkeypatch.setattr(entry.signal, "signal", lambda *args: None)
    assert entry.serve({}) == 1
    assert captured["comparison_work"] is marker
