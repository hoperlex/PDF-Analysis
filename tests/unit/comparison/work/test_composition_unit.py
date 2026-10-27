"""The composition root builds the comparison runner from the module flag and the handler tuple
(`CMP-WORK-01`, ADR-0025 decisions 4 and 23). Container-free: the engine and the object-store client
are lazy, so a configuration that points at nothing builds.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.bootstrap import composition
from auditmanager.bootstrap.public import ConfigurationError, build_worker_runtime
from auditmanager.comparison.public import COMPARISON_MODULES_ENV, ComparisonWorkRunner

_ENV = {
    "DATABASE_URL": "postgresql+psycopg://user:password@127.0.0.1:9/nothing",
    "S3_ENDPOINT_URL": "http://127.0.0.1:9", "S3_REGION": "us-east-1",
    "S3_ACCESS_KEY_ID": "an-access-key", "S3_SECRET_ACCESS_KEY": "a-secret-key", "S3_BUCKET": "a-bucket",
}
_WORKER = {**_ENV, "EXECUTION_ROLE": "worker"}


class Handler:
    def __init__(self, kind: str) -> None:
        self.kind = kind

    def run(self, item: Any) -> Any:  # pragma: no cover
        raise AssertionError


def build(environ: dict[str, str]) -> ComparisonWorkRunner:
    return composition.build_comparison_work(
        sessions=lambda: None, engine=None, blob_store=None, environ=environ,  # type: ignore[arg-type]
    )


@pytest.mark.parametrize(("value", "modules"), [
    (None, set()), ("", set()), ("   ", set()), ("none", set()),
    ("versions", {"versions"}), ("versions,stages", {"versions", "stages"}),
])
def test_the_module_flag_names_what_the_worker_may_claim(value: str | None, modules: set[str]) -> None:
    environ = dict(_WORKER) if value is None else {**_WORKER, COMPARISON_MODULES_ENV: value}
    assert build(environ).modules == frozenset(modules)


@pytest.mark.parametrize("value", ["stages", "versions,stages,extra", "on", "VERSIONS", "versions, stages"])
def test_an_unknown_module_set_stops_the_worker_while_it_is_wiring_not_a_quiet_none(value: str) -> None:
    with pytest.raises(ConfigurationError, match=COMPARISON_MODULES_ENV):
        build({**_WORKER, COMPARISON_MODULES_ENV: value})


def test_a_kind_registered_twice_stops_the_worker_while_it_is_wiring(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(composition, "COMPARISON_HANDLER_FACTORIES",
                        (lambda dependencies: Handler("page_profile"), lambda dependencies: Handler("page_profile")))
    with pytest.raises(ConfigurationError, match="page_profile"):
        build(dict(_WORKER))


def test_one_dependency_bundle_is_built_once_and_every_factory_receives_it(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[Any] = []

    def factory(kind: str):  # type: ignore[no-untyped-def]
        def build_handler(dependencies: Any) -> Handler:
            seen.append(dependencies)
            return Handler(kind)
        return build_handler

    monkeypatch.setattr(composition, "COMPARISON_HANDLER_FACTORIES", (factory("page_profile"), factory("pair_check")))
    sessions, engine, store = object(), object(), object()
    runner = composition.build_comparison_work(sessions=sessions, engine=engine, blob_store=store, environ=_WORKER)  # type: ignore[arg-type]
    assert runner.kinds == {"page_profile", "pair_check"}
    assert len(seen) == 2 and seen[0] is seen[1]
    assert (seen[0].engine, seen[0].session_factory, seen[0].blob_store) == (engine, sessions, store)
    assert seen[0].work is runner.repository


def test_the_spend_settlers_of_the_public_tuple_reach_the_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    def settle(session: Any, attempt_id: str) -> bool:
        return False

    monkeypatch.setattr(composition, "COMPARISON_SPEND_SETTLERS", (settle,))
    assert build(dict(_WORKER))._settlers == (settle,)


def test_the_worker_runtime_carries_the_runner_for_the_service_to_host() -> None:
    runtime = build_worker_runtime(environ={**_WORKER, COMPARISON_MODULES_ENV: "versions,stages"})
    assert isinstance(runtime.comparison_work, ComparisonWorkRunner)
    assert runtime.comparison_work.modules == {"versions", "stages"}
    off = build_worker_runtime(environ=dict(_WORKER))
    assert isinstance(off.comparison_work, ComparisonWorkRunner) and off.comparison_work.modules == frozenset(), (
        "built even when every module is off: it reclaims expired leases and claims nothing")


def test_the_application_is_not_given_a_runner() -> None:
    assert "comparison_work" not in {f for f in composition.Application.__dataclass_fields__}
