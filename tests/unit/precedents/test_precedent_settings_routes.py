"""`PREC-SETTINGS-01`: ``listPrecedentSettings`` and ``appendPrecedentSetting`` answer through the port, and keep the sealed answer without one.

The two routes are mounted alone on a bare application, as the seal's own test does, with a fake port that returns the contract's shape. What is shown:
the port is asked with the caller's identity and the key, name and body the route parsed (the route decides nothing), the answers are the contract's
``PrecedentSettingList`` and ``PrecedentSetting`` (``201`` for a new revision and for a replay), a refusal of the port reaches the caller as its error,
a missing key or a body that is not the declared one never reaches the port, and a router built with no port still answers ``503``.
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
from auditmanager.api.routers.precedents_ports import PrecedentSettingsPort
from auditmanager.api.security import RunnerIdentity, Subject, current_runner, current_subject
from auditmanager.precedents.public import PrecedentSettingService
from auditmanager.shared.errors import DomainError, ErrorCode

USER = "usr_01M2545JSD15ETSNNV904X991K"
KEY = {"Idempotency-Key": "precedent-setting-key"}
MOMENT = datetime(2026, 11, 11, 1, 0, tzinfo=UTC)


def _setting(name: str, revision: int, value: dict[str, Any]) -> dict[str, Any]:
    return {"setting_name": name, "revision": revision, "value": value, "actor_user_uid": USER, "created_at": MOMENT}


class FakePort:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.refuse: DomainError | None = None

    def list_precedent_settings(self, *, user_uid: str) -> Mapping[str, Any]:
        self.calls.append(("list", {"user_uid": user_uid}))
        if self.refuse:
            raise self.refuse
        return {"current": [_setting("one_list", 2, {"enabled": False})],
                "events": [_setting("one_list", 2, {"enabled": False}), _setting("one_list", 1, {"enabled": False})]}

    def append_precedent_setting(self, *, setting_name: str, value: Mapping[str, Any], user_uid: str, idempotency_key: str) -> Mapping[str, Any]:
        self.calls.append(("append", {"setting_name": setting_name, "value": dict(value), "user_uid": user_uid, "idempotency_key": idempotency_key}))
        if self.refuse:
            raise self.refuse
        return _setting(setting_name, 3, dict(value))


def client_for(port: Any) -> TestClient:
    app = FastAPI()
    install_exception_handlers(app)
    router = APIRouter()
    build_precedent_routes(router, None, port)
    app.include_router(router)
    app.dependency_overrides[current_subject] = lambda: Subject(user_uid=USER, login="a@suite.invalid", token_epoch=1, display_label="A")
    app.dependency_overrides[current_runner] = lambda: RunnerIdentity(token_id="ert_01M2545JSD15ETSNNV904X991K", connection_id=None,
                                                                      host_id="exh_01M2545JSD15ETSNNV904X991K")
    return TestClient(app, raise_server_exceptions=False)


def test_the_read_is_the_ports_answer_in_the_contracts_shape() -> None:
    port = FakePort()
    answer = client_for(port).get("/precedent-settings")
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert set(body) == {"current", "events"} and [item["revision"] for item in body["events"]] == [2, 1]
    assert body["current"] == [{"setting_name": "one_list", "revision": 2, "value": {"enabled": False}, "actor_user_uid": USER,
                                "created_at": "2026-11-11T01:00:00Z"}]
    assert port.calls == [("list", {"user_uid": USER})], "the route asked once, with the caller's identity"


def test_the_append_passes_the_name_the_body_the_key_and_the_identity_and_answers_201() -> None:
    port = FakePort()
    answer = client_for(port).post("/precedent-settings", json={"setting_name": "vector_window",
                                    "value": {"start": "01:00", "end": "06:00", "tz": "UTC"}}, headers=KEY)
    assert answer.status_code == 201, answer.text
    assert answer.json()["setting_name"] == "vector_window" and answer.json()["revision"] == 3
    assert port.calls == [("append", {"setting_name": "vector_window", "value": {"start": "01:00", "end": "06:00", "tz": "UTC"},
                                      "user_uid": USER, "idempotency_key": "precedent-setting-key"})]


@pytest.mark.parametrize("method", ["get", "post"])
def test_a_refusal_of_the_port_reaches_the_caller_as_its_error(method: str) -> None:
    port = FakePort()
    port.refuse = DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:admin")
    client = client_for(port)
    answer = client.get("/precedent-settings") if method == "get" else client.post(
        "/precedent-settings", json={"setting_name": "one_list", "value": {"enabled": False}}, headers=KEY)
    assert answer.status_code == 403 and answer.json()["error_code"] == "permission_denied"


def test_a_value_the_service_refuses_is_a_422_with_the_constraint_it_names() -> None:
    port = FakePort()
    port.refuse = DomainError(ErrorCode.VALIDATION_FAILED, field="value", constraint="one_list_not_ready", message="not ready")
    answer = client_for(port).post("/precedent-settings", json={"setting_name": "one_list", "value": {"enabled": True}}, headers=KEY)
    assert answer.status_code == 422 and answer.json()["error_code"] == "validation_failed"
    assert answer.json()["details"] == {"field": "value", "constraint": "one_list_not_ready"}


def test_an_append_without_its_key_or_with_a_body_that_is_not_the_declared_one_never_reaches_the_port() -> None:
    port = FakePort()
    client = client_for(port)
    assert client.post("/precedent-settings", json={"setting_name": "one_list", "value": {"enabled": False}}).status_code == 422
    for body in ({"setting_name": "ar_v3", "value": {}}, {"setting_name": "one_list", "value": [1]}, {"setting_name": "one_list"},
                 {"value": {}}, {"setting_name": "one_list", "value": {}, "actor": "x"}):
        assert client.post("/precedent-settings", json=body, headers=KEY).status_code == 422, body
    assert port.calls == []


@pytest.mark.parametrize(("method", "body"), [("get", None), ("post", {"setting_name": "one_list", "value": {"enabled": False}})])
def test_with_no_port_the_sealed_answer_stays(method: str, body: Any) -> None:
    client = client_for(None)
    answer = client.get("/precedent-settings") if body is None else client.post("/precedent-settings", json=body, headers=KEY)
    assert answer.status_code == 503 and answer.json()["error_code"] == "dependency_unavailable"
    assert answer.json()["details"] == {"dependency": "precedent_settings"}


def test_the_service_is_the_port_the_router_asks() -> None:
    port: PrecedentSettingsPort = PrecedentSettingService(None)  # type: ignore[arg-type]
    assert callable(port.list_precedent_settings) and callable(port.append_precedent_setting)
