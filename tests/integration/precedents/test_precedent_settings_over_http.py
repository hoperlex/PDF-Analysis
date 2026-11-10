"""`PREC-SETTINGS-01`, `EMBED-01` part C: the routes answer when the composition root wires their services (contract 1.51.0).

The routes are mounted alone on a bare application with the principal the authorization seam would publish (the seam's own refusal of the viewer is the
register's, held by ``tests/unit/api/test_precedent_sleeping_routes.py``), and the **real** services over a database whose transaction is rolled back at the
end. What is shown: the list and the append answer in the contract's shapes, the append is ``201`` for a new revision and for the replay of its key, a
value that is refused is a ``422`` that names its constraint (``one_list_not_ready`` among them), and ``getVectorControl`` and ``setVectorPaused`` -- which
the composition root had not wired before -- answer ``200`` and journal the pause with its actor.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient

from auditmanager.api.routers.handlers import install_exception_handlers
from auditmanager.api.routers.precedents import build_precedent_routes
from auditmanager.api.schemas import models
from auditmanager.api.security import RunnerIdentity, Subject, current_runner, current_subject
from auditmanager.precedents import settings as journal
from auditmanager.precedents.public import PrecedentSettingService, VectorControlService


@pytest.fixture
def client(journalled_sessions: sessionmaker[Session], admin_uid: str) -> TestClient:
    app = FastAPI()
    install_exception_handlers(app)
    router = APIRouter()
    build_precedent_routes(router, VectorControlService(journalled_sessions), PrecedentSettingService(journalled_sessions))
    app.include_router(router)
    app.dependency_overrides[current_subject] = lambda: Subject(user_uid=admin_uid, login="admin", token_epoch=1, display_label="A")
    app.dependency_overrides[current_runner] = lambda: RunnerIdentity(token_id="ert_01M2545JSD15ETSNNV904X991K", connection_id=None,
                                                                      host_id="exh_01M2545JSD15ETSNNV904X991K")
    return TestClient(app, raise_server_exceptions=False)


def headers() -> dict[str, str]:
    return {"Idempotency-Key": f"prec-settings-http-{uuid.uuid4()}"}


def test_an_append_is_201_with_the_revision_and_the_list_shows_it(client: TestClient, admin_uid: str) -> None:
    sent = {"setting_name": "critic_context", "value": {"enabled": True}}
    answer = client.post("/precedent-settings", json=sent, headers=headers())
    assert answer.status_code == 201, answer.text
    made = models.PrecedentSetting.model_validate(answer.json())
    assert (made.setting_name.value, made.value, made.actor_user_uid) == ("critic_context", {"enabled": True}, admin_uid)
    listed = client.get("/precedent-settings")
    assert listed.status_code == 200, listed.text
    body = models.PrecedentSettingList.model_validate(listed.json())
    assert any(item.setting_name == made.setting_name and item.revision == made.revision for item in body.current)
    assert body.events[0].revision == made.revision and body.events[0].setting_name == made.setting_name


def test_the_replay_of_a_key_is_201_with_the_same_body_and_adds_nothing(client: TestClient) -> None:
    same = headers()
    sent = {"setting_name": "stop_words", "value": {"words": ["срочно"]}}
    first = client.post("/precedent-settings", json=sent, headers=same)
    again = client.post("/precedent-settings", json=sent, headers=same)
    assert first.status_code == again.status_code == 201 and again.json() == first.json()
    other = client.post("/precedent-settings", json={"setting_name": "stop_words", "value": {"words": []}}, headers=same)
    assert other.status_code == 409 and other.json()["error_code"] == "idempotency_key_reuse"


def test_a_refused_value_is_a_422_that_names_its_constraint(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(journal, "ONE_LIST_READY", False)
    answer = client.post("/precedent-settings", json={"setting_name": "one_list", "value": {"enabled": True}}, headers=headers())
    assert answer.status_code == 422 and answer.json()["error_code"] == "validation_failed"
    assert answer.json()["details"] == {"field": "value", "constraint": "one_list_not_ready"}
    bad = client.post("/precedent-settings", json={"setting_name": "vector_window", "value": {"start": "01:00"}}, headers=headers())
    assert bad.status_code == 422 and bad.json()["details"] == {"field": "value", "constraint": "vector_window_shape"}
    assert client.post("/precedent-settings", json={"setting_name": "one_list", "value": {"enabled": False}}, headers=headers()).status_code == 201


def test_the_vector_control_routes_answer_when_they_are_wired(
    client: TestClient, journalled_sessions: sessionmaker[Session], admin_uid: str,
) -> None:
    read = client.get("/vector-control")
    assert read.status_code == 200, read.text
    control = models.VectorControl.model_validate(read.json())
    assert control.paused is False and control.window.tz, "the window in force is shown"
    paused = client.put("/vector-control/paused", json={"paused": True}, headers=headers())
    assert paused.status_code == 200, paused.text
    assert paused.json()["paused"] is True and "paused_since" in paused.json()
    with journalled_sessions() as session:
        last = session.execute(text(
            "SELECT kind, actor_user_uid FROM vector_control_event WHERE control_key = 'default' ORDER BY event_no DESC LIMIT 1")).one()
    assert tuple(last) == ("paused", admin_uid), "journalled with the administrator"
    resumed = client.put("/vector-control/paused", json={"paused": False}, headers=headers())
    assert resumed.status_code == 200 and resumed.json()["paused"] is False
