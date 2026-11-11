"""`PREC-SETTINGS-01`, `CRIT-CAPTURE-01` parts C and D: the composition root wires the surfaces, the «Прецеденты» pass and the pass of the night window.

Read from the source of ``build_application`` and ``build_worker_runtime``, as ``test_hosts_int_wiring.py`` reads its own wiring (a wiring that is
built by hand in a test proves the test, not the root), and then built for real with a closed port as ``test_one_tile_renderer.py`` does, so each claim is
also proved on the objects the root made. What is shown: the router is handed the vector control, the settings service, the precedents' reads and the
runner adapter as the context port, each built on the application's own session factory and store; the worker's pass holds the «Прецеденты» pass **whatever
the process has for the encoder**, and the window pass **only when the process is set up for it** (``Exchange.from_environment`` answered a directory),
and then the window's ``after_import`` is the pass's own hook.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.bootstrap import composition
from auditmanager.bootstrap.adapters import MemoryCaptureSweep
from auditmanager.bootstrap.runner import RunnerAdapter
from auditmanager.precedents.public import EXCHANGE_DIR_ENV, PrecedentPass, PrecedentService, VectorWindowPass

COMPOSITION = Path(composition.__file__)


def _function(name: str) -> ast.FunctionDef:
    tree = ast.parse(COMPOSITION.read_text(encoding="utf-8"))
    return next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)


def _calls(scope: ast.AST, name: str) -> list[ast.Call]:
    return [node for node in ast.walk(scope) if isinstance(node, ast.Call) and ast.unparse(node.func).rsplit(".", 1)[-1] == name]


def _keyword(call: ast.Call, name: str) -> str | None:
    found = [ast.unparse(item.value) for item in call.keywords if item.arg == name]
    return found[0] if found else None


def test_the_router_is_handed_the_vector_control_and_the_settings_service_over_the_applications_sessions() -> None:
    (router,) = _calls(_function("build_application"), "build_router")
    assert _keyword(router, "vector_control") == "VectorControlService(sessions)"
    assert _keyword(router, "precedent_settings") == "PrecedentSettingService(sessions)"


def test_the_router_is_handed_the_precedents_reads_over_the_same_extended_review_the_pass_reads() -> None:
    application, worker = _function("build_application"), _function("build_worker_runtime")
    (router,) = _calls(application, "build_router")
    reader = "_extended_review_reader(sessions, store)"
    assert _keyword(router, "precedents") == f"PrecedentService(sessions, read_extended_review={reader})"
    (precedent_pass,) = [node for node in ast.walk(worker) if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == "precedent_pass"]
    assert ast.unparse(precedent_pass.value) == f"PrecedentPass(sessions, read_extended_review={reader})", "the same reader, over the same stores"


def test_one_runner_adapter_is_the_pull_channel_and_the_context_port() -> None:
    """`CTX-STAND`: ``runner=`` and ``task_context=`` are the same local name, bound once to one adapter built on the application's sessions and store."""
    application = _function("build_application")
    (router,) = _calls(application, "build_router")
    assert _keyword(router, "runner") == "runner_adapter" and _keyword(router, "task_context") == "runner_adapter"
    bound = [node for node in ast.walk(application) if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == "runner_adapter"]
    assert [ast.unparse(node.value) for node in bound] == ["RunnerAdapter(sessions, blob_store=store)"]


def test_the_window_pass_rides_the_workers_pass_only_when_the_process_has_an_exchange_directory() -> None:
    worker = _function("build_worker_runtime")
    (exchange,) = [node for node in ast.walk(worker) if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == "exchange"]
    assert ast.unparse(exchange.value) == "Exchange.from_environment(env)", "the process's own environment, as every other read of the worker"
    (passes,) = [node for node in ast.walk(worker) if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == "vector_passes"]
    assert ast.unparse(passes.value) == (
        "() if exchange is None else (VectorWindowPass(sessions, exchange, after_import=precedent_pass.after_import),)"), "the hook is the pass's own"
    (runtime,) = _calls(worker, "WorkerRuntime")
    (chain,) = _calls(runtime, "_passes")
    arguments = [ast.unparse(arg) for arg in chain.args]
    assert arguments[-1] == "*vector_passes", "after the memory's sweep, in the same housekeeping pass"
    assert "MemoryCaptureSweep" in arguments[2]
    assert arguments[3] == "precedent_pass", "the «Прецеденты» pass is a pass of its own, NOT inside the vector branch: it queues the probes even with no exchange"


def test_the_precedent_pass_is_built_outside_the_vector_branch() -> None:
    worker = _function("build_worker_runtime")
    (assign,) = [node for node in ast.walk(worker) if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == "precedent_pass"]
    # a statement of the function's own body, not of an ``if`` or a conditional expression that depends on the exchange
    assert assign in worker.body


class _Pass:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> int:
        self.calls += 1
        return 1


def test_the_window_pass_is_one_of_the_passes_and_a_failing_one_does_not_starve_the_others(monkeypatch: pytest.MonkeyPatch) -> None:
    """The chain is ``_passes``: a window pass that raises is logged and the probes and the memory's sweep still run."""
    window, other = _Pass(), _Pass()

    def broken() -> int:
        raise RuntimeError("the exchange directory is gone")

    assert composition._passes(broken, window, other)() == 2
    assert (window.calls, other.calls) == (1, 1)


def test_the_exchange_is_none_without_its_directory_and_the_pass_is_built_with_one() -> None:
    from auditmanager.precedents.public import EXCHANGE_DIR_ENV, Exchange

    assert Exchange.from_environment({}) is None and Exchange.from_environment({EXCHANGE_DIR_ENV: "  "}) is None
    assert Exchange.from_environment({EXCHANGE_DIR_ENV: "/tmp/exchange"}) is not None


# -- built for real (no database is dialled: an engine and an object-store client are lazy) ----------------------------------------------


_ENV = {
    "DATABASE_URL": "postgresql+psycopg://user:password@127.0.0.1:9/nothing",
    "S3_ENDPOINT_URL": "http://127.0.0.1:9", "S3_REGION": "us-east-1",
    "S3_ACCESS_KEY_ID": "an-access-key", "S3_SECRET_ACCESS_KEY": "a-secret-key", "S3_BUCKET": "a-bucket",
}


def _runners(runtime: Any) -> tuple[Any, ...]:
    """The runners the worker's housekeeping pass chains, read off the closure of ``_passes``'s ``one_pass``."""
    return tuple(inspect.getclosurevars(runtime.probe_runner).nonlocals["runners"])


def test_the_worker_runs_the_precedent_pass_whether_or_not_it_has_an_exchange_directory() -> None:
    without = _runners(composition.build_worker_runtime(environ=_ENV | {"EXECUTION_ROLE": "worker"}))
    assert [type(runner) for runner in without if isinstance(runner, (PrecedentPass, VectorWindowPass))] == [PrecedentPass], \
        "no exchange directory: the probes are still queued, and no window is run in this process"
    assert any(isinstance(runner, MemoryCaptureSweep) for runner in without)


def test_with_an_exchange_directory_the_window_hands_its_round_to_the_pass(tmp_path: Path) -> None:
    runners = _runners(composition.build_worker_runtime(environ=_ENV | {"EXECUTION_ROLE": "worker", EXCHANGE_DIR_ENV: str(tmp_path)}))
    (precedent_pass,) = [runner for runner in runners if isinstance(runner, PrecedentPass)]
    (window,) = [runner for runner in runners if isinstance(runner, VectorWindowPass)]
    # a bound method equals the same method of the same object: the window's hook is THIS pass's, not another instance's
    assert window._after_import == precedent_pass.after_import
    assert runners.index(precedent_pass) < runners.index(window), "the pass is ahead of the window; the window's hook computes again after a round"


class _Ports:
    """Spies ``build_router`` of the composition root: it keeps what the root handed it and builds the real router."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.kwargs: dict[str, Any] = {}
        real = composition.build_router

        def spy(*args: Any, **kwargs: Any) -> Any:
            self.kwargs = kwargs
            return real(*args, **kwargs)

        monkeypatch.setattr(composition, "build_router", spy)


def test_the_application_hands_the_router_the_precedents_reads_and_the_runner_adapter_as_the_context_port(monkeypatch: pytest.MonkeyPatch) -> None:
    ports = _Ports(monkeypatch)
    composition.build_application(environ=_ENV | {"AUDITMANAGER_API_TOKEN": "a-token-of-the-unit-test"})
    precedents, runner, task_context = ports.kwargs["precedents"], ports.kwargs["runner"], ports.kwargs["task_context"]
    assert isinstance(precedents, PrecedentService)
    assert isinstance(runner, RunnerAdapter) and task_context is runner, "one adapter: the pull channel and the reference data of its tasks"
    assert callable(getattr(task_context, "get_task_context"))


def test_both_the_pass_and_the_reads_read_the_extended_review_through_the_run_modules_reader(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[Any, Any, str]] = []
    monkeypatch.setattr(composition, "read_extended_review", lambda sessions, store, run_id: calls.append((sessions, store, run_id)) or {"status": "x"})
    sessions, store = object(), object()
    read = composition._extended_review_reader(sessions, store)
    assert read("run_1") == {"status": "x"} and calls == [(sessions, store, "run_1")]
