"""The nine operations over HTTP on the composed application (`CMP-SERIES-01`): real PostgreSQL, the shipped routers,
roles, keys, cursors and the refusals as the client reads them."""

from __future__ import annotations

import os
from typing import Any

import pytest
from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE, Subject, build_signer
from auditmanager.shared.identity import new_ulid

from .conftest import SECRET
from .support import ScriptedEngine, build, drain, runner_with


def _token(sessions, label: str, roles: tuple[str, ...]) -> dict[str, str]:
    from auditmanager.access.accounts import AccountRepository
    from auditmanager.access.repository import UserRepository
    from tests.support.accounts import SUITE_NAMES, SUITE_PASSWORD, suite_login

    users = UserRepository()
    with sessions() as session:
        record = users.find_by_login(session, suite_login(label))
        if record is None:
            created = users.create_user(session, suite_login(label), SUITE_PASSWORD)
            accounts = AccountRepository()
            accounts.complete_profile(session, user_uid=str(created.user_uid), email=None,
                                      last_name=SUITE_NAMES[0], first_name=SUITE_NAMES[1])
            for role in roles:
                accounts.grant_role(session, user_uid=str(created.user_uid), role=role, granted_by=None)
            record = users.find_by_login(session, suite_login(label))
            session.commit()
        signer = build_signer({API_TOKEN_VARIABLE: SECRET})
        token = signer.issue(
            Subject(user_uid=str(record.user_uid), login=record.login, token_epoch=record.token_epoch,
                    display_label=record.display_label),
            is_default_credential=False,
        ).token
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def api(engine) -> TestClient:
    environ = dict(os.environ) | {API_TOKEN_VARIABLE: SECRET}
    application = create_app(environ=environ)
    return TestClient(create_asgi_app(environ=environ, application=application), raise_server_exceptions=False)


@pytest.fixture
def expert(sessions) -> dict[str, str]:
    return _token(sessions, "series-http-expert", ("expert",))


@pytest.fixture
def admin(sessions) -> dict[str, str]:
    return _token(sessions, "series-http-admin", ("admin",))


def _series_url(doc, tail: str = "") -> str:
    return f"/projects/{doc.project_uid}/documents/{doc.document_uid}/comparison-series{tail}"


def _write(api: TestClient, path: str, headers: dict[str, str], body: Any | None = None, key: str | None = None):
    return api.post(path, json={} if body is None and path.endswith("comparison-series") else body,
                    headers={**headers, "Idempotency-Key": key or f"http-{new_ulid()}"})


def test_a_series_is_started_read_listed_steered_and_its_pairs_are_read_over_http(
    api, lab, sessions, engine, blob_store, worker_id, matrix_service, expert, admin,
) -> None:
    doc = lab.clone()
    build(matrix_service, doc)

    assert _write(api, _series_url(doc), admin).status_code == 403  # an administrator is not an expert
    token = f"http-{new_ulid()}"
    started = _write(api, _series_url(doc), expert, {"restart": False}, key=token)
    assert started.status_code == 201, started.text
    series = started.json()
    assert series["state"] == "queued" and len(series["transitions"]) == 4 and series["transitions_total"] == 4
    assert _write(api, _series_url(doc), expert, {"restart": False}, key=token).json()["series_id"] == series["series_id"]
    live = _write(api, _series_url(doc), expert, {})
    assert live.status_code == 409 and live.json()["details"]["conflict_reason"] == "comparison_series_active"
    stale = _write(api, _series_url(doc), expert, {"base_order_revision_no": 3})
    assert stale.status_code == 409  # a live series answers first; the order is judged after it

    sid = series["series_id"]
    got = api.get(f"/comparison-series/{sid}", headers=admin)  # any one role reads
    assert got.status_code == 200 and got.json()["series_id"] == sid
    listed = api.get(_series_url(doc), headers=admin)
    assert listed.status_code == 200 and [i["series_id"] for i in listed.json()["items"]] == [sid]
    assert "transitions" not in listed.json()["items"][0]

    assert _write(api, f"/comparison-series/{sid}/resume", expert).status_code == 409  # not paused
    paused = _write(api, f"/comparison-series/{sid}/pause", expert)
    assert paused.status_code == 200 and paused.json()["state"] == "paused"
    assert _write(api, f"/comparison-series/{sid}/pause", admin).status_code == 403
    assert _write(api, f"/comparison-series/{sid}/resume", expert).json()["state"] == "running"
    drain(runner_with(sessions, engine, blob_store, compare=ScriptedEngine(sessions)), worker_id, engine, sessions, doc.project_uid)

    done = api.get(f"/comparison-series/{sid}", headers=admin).json()
    assert done["state"] == "completed"
    transition = done["transitions"][1]
    assert transition["verdict"] == ["composition_changed"] and transition["summary"]["added"] == 1
    pairs = api.get(f"/comparison-transitions/{transition['transition_id']}/sheet-pairs?limit=3", headers=admin)
    assert pairs.status_code == 200 and len(pairs.json()["items"]) == 3
    cursor = pairs.json()["page"]["next_cursor"]
    rest = api.get(f"/comparison-transitions/{transition['transition_id']}/sheet-pairs?limit=10&cursor={cursor}", headers=admin)
    assert len(rest.json()["items"]) == 4 and rest.json()["page"]["next_cursor"] is None
    changes = api.get(f"/comparison-transitions/{transition['transition_id']}/sheet-pairs?only_changes=true", headers=admin).json()
    assert {p["status"] for p in changes["items"]} == {"added", "removed"}
    same = api.get(f"/comparison-transitions/{transition['transition_id']}/sheet-pairs?status=same", headers=admin).json()
    assert len(same["items"]) == 5
    one = api.get(f"/comparison-sheet-pairs/{same['items'][0]['sheet_pair_id']}", headers=admin)
    assert one.status_code == 200 and one.json()["canvas"] == {"width_pt": 1190.55, "height_pt": 841.89}

    cancelled = _write(api, f"/comparison-series/{sid}/cancellation", expert)
    assert cancelled.status_code == 409 and cancelled.json()["details"]["conflict_reason"] == "comparison_series_state"
    assert _write(api, f"/comparison-series/{sid}/finish", expert).status_code == 409  # nothing left


def test_the_refusals_of_the_reads_and_the_requests(api, lab, matrix_service, expert, admin) -> None:
    doc = lab.clone()
    build(matrix_service, doc)
    assert api.get("/comparison-series/cser_01ARZ3NDEKTSV4RRFFQ69G5FAV", headers=admin).status_code == 404
    assert api.get("/comparison-sheet-pairs/ctp_01ARZ3NDEKTSV4RRFFQ69G5FAV", headers=admin).status_code == 404
    assert api.get("/comparison-transitions/ctn_01ARZ3NDEKTSV4RRFFQ69G5FAV/sheet-pairs", headers=admin).status_code == 404
    assert api.get(f"/projects/{doc.project_uid}/documents/doc_01ARZ3NDEKTSV4RRFFQ69G5FAV/comparison-series", headers=admin).status_code == 404
    assert api.get("/comparison-series/not-an-identity", headers=admin).status_code == 404  # an address that names nothing
    assert api.post(_series_url(doc), json={}, headers=expert).status_code == 422  # a write needs its key
    bad_cursor = api.get(_series_url(doc) + "?cursor=!!", headers=admin)
    assert bad_cursor.status_code == 422
    unknown_project = api.post("/projects/prj_01ARZ3NDEKTSV4RRFFQ69G5FAV/documents/doc_01ARZ3NDEKTSV4RRFFQ69G5FAV/comparison-series",
                               json={}, headers={**expert, "Idempotency-Key": f"http-{new_ulid()}"})
    assert unknown_project.status_code == 404
    assert _write(api, _series_url(doc), expert, {}).status_code == 201  # the matrix was built above
