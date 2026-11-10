"""`EMBED-01`: ``getVectorControl`` and ``setVectorPaused`` answer through the port, and keep the sealed answer without one (contract 1.51.0).

The two routes are mounted alone on a bare application, as the seal's own test does, with a fake port that returns the contract's shape. What is shown:
the port is asked with the caller's identity and the key and body the route parsed (the route decides nothing), the answer is the contract's
``VectorControl`` with an optional member absent and never null, a refusal of the port reaches the caller as its error, and a router built with no
port still answers ``503 dependency_unavailable`` -- so the composition root's wiring is the only thing that wakes them.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from starlette.testclient import TestClient

from auditmanager.api.routers.handlers import install_exception_handlers
from auditmanager.api.routers.precedents import build_precedent_routes
from auditmanager.api.security import Subject, current_runner, current_subject, RunnerIdentity
from auditmanager.shared.errors import DomainError, ErrorCode

USER = "usr_01M2545JSD15ETSNNV904X991K"
KEY = {"Idempotency-Key": "vector-control-key"}
MOMENT = datetime(2026, 11, 11, 1, 0, tzinfo=UTC)


class FakePort:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.refuse: DomainError | None = None
        self.view: dict[str, Any] = {
            "paused": False, "window_state": "closed", "window_changed_at": MOMENT,
            "window": {"start": "01:00", "end": "06:00", "tz": "Asia/Yekaterinburg"},
        }

    def get_vector_control(self, *, user_uid: str) -> Mapping[str, Any]:
        self.calls.append(("get", {"user_uid": user_uid}))
        if self.refuse:
            raise self.refuse
        return self.view

    def set_vector_paused(self, *, paused: bool, user_uid: str, idempotency_key: str) -> Mapping[str, Any]:
        self.calls.append(("set", {"paused": paused, "user_uid": user_uid, "idempotency_key": idempotency_key}))
        if self.refuse:
            raise self.refuse
        return {**self.view, "paused": paused, "paused_since": MOMENT} if paused else self.view


def client_for(port: Any) -> TestClient:
    app = FastAPI()
    install_exception_handlers(app)
    router = APIRouter()
    build_precedent_routes(router, port)
    app.include_router(router)
    app.dependency_overrides[current_subject] = lambda: Subject(user_uid=USER, login="a@suite.invalid", token_epoch=1, display_label="A")
    app.dependency_overrides[current_runner] = lambda: RunnerIdentity(token_id="ert_01M2545JSD15ETSNNV904X991K", connection_id=None,
                                                                      host_id="exh_01M2545JSD15ETSNNV904X991K")
    return TestClient(app, raise_server_exceptions=False)


def test_the_read_is_the_ports_answer_in_the_contracts_shape_with_nothing_null() -> None:
    port = FakePort()
    answer = client_for(port).get("/vector-control")
    assert answer.status_code == 200, answer.text
    assert answer.json() == {"paused": False, "window_state": "closed", "window_changed_at": "2026-11-11T01:00:00Z",
                             "window": {"start": "01:00", "end": "06:00", "tz": "Asia/Yekaterinburg"}}
    assert port.calls == [("get", {"user_uid": USER})], "the route asked once, with the caller's identity"


def test_a_skipped_window_and_the_admins_counts_come_through() -> None:
    port = FakePort()
    port.view = {**port.view, "window_state": "skipped", "window_reason": "encoder_out_of_memory", "pending_intents": 7, "poisoned_intents": 1}
    body = client_for(port).get("/vector-control").json()
    assert (body["window_state"], body["window_reason"], body["pending_intents"], body["poisoned_intents"]) == ("skipped", "encoder_out_of_memory", 7, 1)


def test_the_pause_passes_the_body_the_key_and_the_identity_to_the_port_and_answers_the_control() -> None:
    port = FakePort()
    answer = client_for(port).put("/vector-control/paused", json={"paused": True}, headers=KEY)
    assert answer.status_code == 200, answer.text
    assert answer.json()["paused"] is True and answer.json()["paused_since"] == "2026-11-11T01:00:00Z"
    assert port.calls == [("set", {"paused": True, "user_uid": USER, "idempotency_key": "vector-control-key"})]


def test_a_refusal_of_the_port_reaches_the_caller_as_its_error() -> None:
    port = FakePort()
    port.refuse = DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:admin")
    answer = client_for(port).put("/vector-control/paused", json={"paused": True}, headers=KEY)
    assert answer.status_code == 403 and answer.json()["error_code"] == "permission_denied"


def test_a_pause_without_its_key_or_with_a_malformed_body_never_reaches_the_port() -> None:
    port = FakePort()
    client = client_for(port)
    assert client.put("/vector-control/paused", json={"paused": True}).status_code == 422
    assert client.put("/vector-control/paused", json={"paused": "maybe"}, headers=KEY).status_code == 422
    assert client.put("/vector-control/paused", json={}, headers=KEY).status_code == 422
    assert port.calls == []


@pytest.mark.parametrize(("method", "path", "body"), [("get", "/vector-control", None), ("put", "/vector-control/paused", {"paused": True})])
def test_with_no_port_the_sealed_answer_stays(method: str, path: str, body: Any) -> None:
    answer = getattr(client_for(None), method)(path, **({"json": body, "headers": KEY} if body is not None else {}))
    assert answer.status_code == 503 and answer.json()["error_code"] == "dependency_unavailable"
    assert answer.json()["details"] == {"dependency": "vector_control"}
