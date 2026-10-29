"""The three reads of part B over HTTP on the composed application (`CMP-VC-SPEC-01`): the specifications of a series, the
specification of a transition and its changes -- real PostgreSQL, the shipped routers, the module gate, any one role, cursors."""

from __future__ import annotations

import json
import os

import pytest
from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE, Subject, build_signer
from auditmanager.comparison.public import COMPARISON_MODULES_ENV, TransitionRun
from auditmanager.comparison.specification import transition as transition_module
from auditmanager.comparison.specification.repository import SpecificationRepository
from auditmanager.shared.db import session_scope

from .conftest import SECRET, _account, faithful_answer

ABSENT_SERIES = "cser_01ARZ3NDEKTSV4RRFFQ69G5FAV"
ABSENT_TRANSITION = "ctn_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def _client(modules: str | None) -> TestClient:
    environ = {k: v for k, v in os.environ.items() if k != COMPARISON_MODULES_ENV} | {API_TOKEN_VARIABLE: SECRET}
    if modules is not None:
        environ[COMPARISON_MODULES_ENV] = modules
    return TestClient(create_asgi_app(environ=environ, application=create_app(environ=environ)), raise_server_exceptions=False)


@pytest.fixture(scope="module")
def on(engine) -> TestClient:
    return _client("versions")


@pytest.fixture(scope="module")
def off(engine) -> TestClient:
    return _client(None)


@pytest.fixture
def viewer(sessions) -> dict[str, str]:
    from auditmanager.access.repository import UserRepository
    from tests.support.accounts import suite_login

    _account(sessions, "spec-http-reader", ("admin",))
    with sessions() as session:
        record = UserRepository().find_by_login(session, suite_login("spec-http-reader"))
    token = build_signer({API_TOKEN_VARIABLE: SECRET}).issue(
        Subject(user_uid=str(record.user_uid), login=record.login, token_epoch=record.token_epoch, display_label=record.display_label),
        is_default_credential=False).token
    return {"Authorization": f"Bearer {token}"}


def _model(prompt_text: str) -> transition_module.Answer:
    packet = json.loads(prompt_text.split("Входные данные (JSON):\n", 1)[1])
    return transition_module.Answer(payload=faithful_answer(packet), model_identity="recorded", recorded=True)


@pytest.fixture
def compared(sessions, blob_store, job_for, started):
    doc, series = started()
    repository = SpecificationRepository()
    with session_scope(sessions) as session:
        scope = repository.transition(session, next(t["transition_id"] for t in series["transitions"] if t["source_version_uid"] == doc.versions[1]))
    job = job_for(scope)
    with session_scope(sessions) as session:
        repository.open_whole(session, scope, job_id=job, sheets_a=1, sheets_b=1)
        repository.set_state(session, scope.transition_id, to_state="running", from_states=("queued",), phase="comparing")
    TransitionRun(sessions, blob_store).run(scope, ask=_model)
    return series, scope


def test_the_specification_of_a_transition_is_read_over_http(on, compared, viewer) -> None:
    series, scope = compared
    response = on.get(f"/comparison-transitions/{scope.transition_id}/specification", headers=viewer)
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["state"], body["method"], body["sheets_a"], body["sheets_b"]) == ("completed", "whole", 1, 1)
    assert body["totals"] == {"changed": 1, "added": 1, "removed": 1, "unclear": 0, "renumbered": 0, "moved": 0}
    assert body["coverage_a"]["rows_unresolved"] == 0 and body["job_id"].startswith("cai_")
    assert on.get(f"/comparison-transitions/{scope.transition_id}/specification").status_code == 401


def test_the_changes_are_paged_and_filtered_over_http(on, compared, viewer) -> None:
    _series, scope = compared
    base = f"/comparison-transitions/{scope.transition_id}/specification/changes"
    first = on.get(base, params={"limit": 2}, headers=viewer).json()
    assert [c["kind"] for c in first["items"]] == ["changed", "removed"] and first["page"]["next_cursor"]
    second = on.get(base, params={"limit": 2, "cursor": first["page"]["next_cursor"]}, headers=viewer).json()
    assert [c["kind"] for c in second["items"]] == ["added"] and second["page"]["next_cursor"] is None
    removed = on.get(base, params={"kind": "removed"}, headers=viewer).json()
    assert [c["old"]["pos"] for c in removed["items"]] == ["6"] and removed["items"][0]["old"]["page"]["page_number"] == 6
    assert on.get(base, params={"cursor": "not-a-cursor"}, headers=viewer).status_code == 422


def test_the_specifications_of_a_series_list_the_transitions_that_have_one(on, compared, viewer) -> None:
    series, scope = compared
    page = on.get(f"/comparison-series/{series['series_id']}/specifications", headers=viewer).json()
    assert len(page["items"]) == 2  # V3 -> V4 and V4 -> V5 both have a specification sheet on each side
    assert {i["transition_id"] for i in page["items"]} >= {scope.transition_id}
    states = {i["transition_id"]: i["state"] for i in page["items"]}
    # V3 and V4 read the same text, so once V4 -> V5 is read both readings of V3 -> V4 are stored: it is read without a job
    assert states[scope.transition_id] == "completed" and set(states.values()) == {"completed"}
    free = next(i for i in page["items"] if i["transition_id"] != scope.transition_id)
    assert "job_id" not in free and "comparison_id" not in free and free["totals"]["changed"] == 0
    one = on.get(f"/comparison-series/{series['series_id']}/specifications", params={"limit": 1}, headers=viewer).json()
    assert len(one["items"]) == 1 and one["page"]["next_cursor"]


def test_an_absent_series_or_transition_is_not_found_and_never_an_empty_answer(on, viewer) -> None:
    for path in (f"/comparison-series/{ABSENT_SERIES}/specifications", f"/comparison-transitions/{ABSENT_TRANSITION}/specification",
                 f"/comparison-transitions/{ABSENT_TRANSITION}/specification/changes"):
        response = on.get(path, headers=viewer)
        assert response.status_code == 404 and response.json()["error_code"] == "not_found", path


@pytest.mark.parametrize("path", [f"/comparison-series/{ABSENT_SERIES}/specifications", f"/comparison-transitions/{ABSENT_TRANSITION}/specification",
                                  f"/comparison-transitions/{ABSENT_TRANSITION}/specification/changes"])
def test_while_the_versions_module_is_off_nothing_is_read(off, viewer, path) -> None:
    response = off.get(path, headers=viewer)
    assert response.status_code == 503 and response.json()["details"]["dependency"] == "comparison_modules"
