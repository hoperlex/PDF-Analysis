"""`PREC-SETTINGS-01`, `CRIT-CAPTURE-01` part C: the composition root wires the surfaces and the pass of the night window, and only so.

Read from the source of ``build_application`` and ``build_worker_runtime``, as ``test_hosts_int_wiring.py`` reads its own wiring (a wiring that is
built by hand in a test proves the test, not the root). What is shown: the router is handed the vector control and the settings service built on the
application's own session factory; the worker's pass holds the window pass **only when the process is set up for the encoder** (``Exchange.from_environment``
answered a directory); and the pass is built with no ``after_import`` (the «Прецеденты» pass is not wired yet).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from auditmanager.bootstrap import composition

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


def test_the_window_pass_rides_the_workers_pass_only_when_the_process_has_an_exchange_directory() -> None:
    worker = _function("build_worker_runtime")
    (exchange,) = [node for node in ast.walk(worker) if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == "exchange"]
    assert ast.unparse(exchange.value) == "Exchange.from_environment(env)", "the process's own environment, as every other read of the worker"
    (passes,) = [node for node in ast.walk(worker) if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == "vector_passes"]
    assert ast.unparse(passes.value) == "() if exchange is None else (VectorWindowPass(sessions, exchange, after_import=None),)"
    (runtime,) = _calls(worker, "WorkerRuntime")
    (chain,) = _calls(runtime, "_passes")
    assert [ast.unparse(arg) for arg in chain.args][-1] == "*vector_passes", "after the memory's sweep, in the same housekeeping pass"
    assert "MemoryCaptureSweep" in ast.unparse(chain.args[2])


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
