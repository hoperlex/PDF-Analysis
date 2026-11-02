"""`EXEC2-PULL-01` (ADR-0026 decision 3): ``runner_instance_id`` travels router -> port -> adapter -> claim.

Three seams, one name. A declared parameter that an adapter swallows is worse than one that is refused
(`D-74`): the claim would run without an instance and look as if it had worked. So this file checks the
three signatures against each other and drives the router and the adapter with the name.

No database and no network. The adapter test replaces ``executors.public.claim_task`` and reads what it
was given.
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from auditmanager.api.routers.ports import RunnerPort
from auditmanager.api.routers.runner import build_runner_routes
from auditmanager.api.security import RunnerIdentity, current_runner

NAME = "agent-instance-aaaa"
IDENTITY = RunnerIdentity("ern_TOKEN", "exc_CONN")


class _Port:
    """The runner port, recording what the router asked of ``claim_task``."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def claim_task(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)
        return None


def _client(port: _Port) -> TestClient:
    router = APIRouter()
    build_runner_routes(router, port)  # type: ignore[arg-type]
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[current_runner] = lambda: IDENTITY
    return TestClient(app)


# -- the router -------------------------------------------------------------------------------------


def test_a_claim_that_names_an_instance_reaches_the_port_with_it() -> None:
    port = _Port()
    answer = _client(port).post("/runner/tasks/claim", json={"wait_seconds": 0, "runner_instance_id": NAME})
    assert answer.status_code == 204
    assert port.calls == [{"runner": IDENTITY, "wait_seconds": 0, "max_images": None, "runner_instance_id": NAME}]


def test_a_claim_that_names_none_reaches_the_port_with_the_arguments_it_always_had() -> None:
    """The body of every agent and bridge deployed before the field: the port is called as it was, so a
    port written before the field (a stand-in in a suite) still accepts it."""
    port = _Port()
    for body in ({}, {"wait_seconds": 3}, {"wait_seconds": 0, "max_images": 4}):
        assert _client(port).post("/runner/tasks/claim", json=body).status_code == 204
    assert [set(call) for call in port.calls] == [{"runner", "wait_seconds", "max_images"}] * 3
    assert port.calls[0]["wait_seconds"] == 25 and port.calls[2]["max_images"] == 4


@pytest.mark.parametrize("bad", ["short", "x" * 65, "has space inside", "slash/in-name", "", 12345678])
def test_a_name_outside_the_wire_pattern_is_refused_before_the_port(bad: Any) -> None:
    port = _Port()
    answer = _client(port).post("/runner/tasks/claim", json={"wait_seconds": 0, "runner_instance_id": bad})
    assert answer.status_code == 422 and port.calls == []


# -- the three signatures ---------------------------------------------------------------------------


def test_the_port_declares_an_optional_instance() -> None:
    parameter = inspect.signature(RunnerPort.claim_task).parameters["runner_instance_id"]
    assert parameter.default is None and parameter.kind is parameter.KEYWORD_ONLY


def test_the_runner_adapter_accepts_every_parameter_the_port_declares() -> None:
    """Fails until the adapter that serves the runner (``bootstrap/runner.py``, which `EXEC2-PULL-01` was
    not granted) takes ``runner_instance_id``: the router would otherwise answer every claim that names
    an instance with a ``TypeError`` and a 500."""
    from auditmanager.bootstrap.runner import RunnerAdapter

    declared = {n for n in inspect.signature(RunnerPort.claim_task).parameters if n != "self"}
    accepted = {n for n in inspect.signature(RunnerAdapter.claim_task).parameters if n != "self"}
    assert declared <= accepted, f"RunnerAdapter.claim_task does not accept {sorted(declared - accepted)}"


# -- the adapter ------------------------------------------------------------------------------------


def test_the_runner_adapter_hands_the_instance_to_the_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    from auditmanager.bootstrap.runner import RunnerAdapter
    from auditmanager.executors import public

    seen: dict[str, Any] = {}

    def fake_claim(sessions: Any, principal: Any, **kwargs: Any) -> None:
        seen.update(kwargs, principal=principal)

    monkeypatch.setattr(public, "claim_task", fake_claim)
    adapter = RunnerAdapter(lambda: None)  # type: ignore[arg-type]
    assert adapter.claim_task(runner=IDENTITY, wait_seconds=0, max_images=2, runner_instance_id=NAME) is None
    assert seen["wait_seconds"] == 0 and seen["max_images"] == 2 and seen["runner_instance_id"] == NAME
    assert (seen["principal"].token_id, seen["principal"].connection_id) == ("ern_TOKEN", "exc_CONN")


def test_the_runner_adapter_passes_none_for_a_claim_that_names_none(monkeypatch: pytest.MonkeyPatch) -> None:
    from auditmanager.bootstrap.runner import RunnerAdapter
    from auditmanager.executors import public

    seen: dict[str, Any] = {}
    monkeypatch.setattr(public, "claim_task", lambda sessions, principal, **kwargs: seen.update(kwargs))
    adapter = RunnerAdapter(lambda: None)  # type: ignore[arg-type]
    assert adapter.claim_task(runner=IDENTITY, wait_seconds=0) is None
    assert seen["runner_instance_id"] is None
