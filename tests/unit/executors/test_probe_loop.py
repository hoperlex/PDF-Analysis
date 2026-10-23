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


def test_the_worker_runs_probes_with_or_without_a_private_ring() -> None:
    from auditmanager.bootstrap.composition import build_worker_runtime

    base = {
        "DATABASE_URL": "postgresql+psycopg://u:p@127.0.0.1:9/d", "S3_ENDPOINT_URL": "http://127.0.0.1:9",
        "S3_REGION": "r", "S3_ACCESS_KEY_ID": "a", "S3_SECRET_ACCESS_KEY": "b", "S3_BUCKET": "c",
        "EXECUTION_ROLE": "worker",
    }
    ring = "k1:AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE="
    assert build_worker_runtime(environ={**base, "AUDITMANAGER_SECRETS_KEYS": ring,
                                         "AUDITMANAGER_SECRETS_ACTIVE_KID": "k1"}).probe_runner is not None
    assert build_worker_runtime(environ=base).probe_runner is not None


def test_serve_hands_the_runtimes_probe_runner_to_the_worker_service(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """The wiring in ``python -m auditmanager.workers serve``: what the runtime carries reaches the
    service, so a worker that holds the ring really does take probes."""
    from types import SimpleNamespace

    import auditmanager.bootstrap.public as bootstrap_public
    import auditmanager.jobs.public as jobs_public
    import auditmanager.workers.__main__ as entry
    import auditmanager.workers.service as service_module

    marker = lambda: 0  # noqa: E731
    runtime = SimpleNamespace(engine=None, session_factory=None, execute=None, version="v",
                              settings=SimpleNamespace(provider_source="environment"),
                              slots=1, state_dir=None, probe_runner=marker)
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
    assert entry.serve({}) == 1  # the fake reports itself failed, which is how serve ends here
    assert captured["probe_runner"] is marker


def test_worker_registers_the_env_baseline_before_accepting_work(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from types import SimpleNamespace

    import auditmanager.bootstrap.public as bootstrap_public
    import auditmanager.executors.operations as operations
    import auditmanager.jobs.public as jobs_public
    import auditmanager.workers.__main__ as entry
    import auditmanager.workers.service as service_module

    events: list[str] = []
    runtime = SimpleNamespace(
        engine=None, session_factory=object(), execute=None, version="v", slots=1,
        state_dir=None, probe_runner=None,
        settings=SimpleNamespace(provider_source="database", secrets_private_ring=object()),
    )

    def register(*args, **kwargs):  # type: ignore[no-untyped-def]
        events.append("baseline registered")
        assert kwargs["queue_only"] is True
        return SimpleNamespace(connection_id="exc_test", created=True)

    class FakeService:
        failed = True
        worker_id = "wrk_test"
        busy = 0

        def __init__(self, **kwargs):  # type: ignore[no-untyped-def]
            events.append("service built")

        def start(self) -> None:
            events.append("service started")

        def drain(self, timeout: float | None = None) -> bool:
            return True

        def stop(self) -> None: ...

    monkeypatch.setattr(bootstrap_public, "build_worker_runtime", lambda environ: runtime)
    monkeypatch.setattr(operations, "import_env", register)
    monkeypatch.setattr(jobs_public, "sweep_stale_temporaries", lambda: None)
    monkeypatch.setattr(service_module, "WorkerService", FakeService)
    monkeypatch.setattr(entry.signal, "signal", lambda *args: None)
    assert entry.serve({"PROXY_LLM_BASE_URL": "https://openrouter.ai/api/v1"}) == 1
    assert events == ["baseline registered", "service built", "service started"]
