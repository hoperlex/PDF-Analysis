"""The six operations over HTTP on the composed application (`CMP-MATRIX-01`): real PostgreSQL, the shipped routers,
roles, keys, cursors, the registered reasons as the client reads them."""

from __future__ import annotations

import os
from typing import Any

import pytest
from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE, Subject, build_signer
from auditmanager.shared.identity import new_ulid

from .conftest import SECRET


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
    return _token(sessions, "matrix-http-expert", ("expert",))


@pytest.fixture
def admin(sessions) -> dict[str, str]:
    return _token(sessions, "matrix-http-admin", ("admin",))


def _url(doc, tail: str = "") -> str:
    return f"/projects/{doc.project_uid}/documents/{doc.document_uid}/comparison-matrix{tail}"


def _write(api: TestClient, path: str, headers: dict[str, str], body: Any | None = None, key: str | None = None):
    return api.post(path, json=body, headers={**headers, "Idempotency-Key": key or f"http-{new_ulid()}"})


def test_the_matrix_flows_from_nothing_to_edits_and_back_over_http(api, service, lab, expert, admin) -> None:
    doc = lab.clone()
    absent = api.get(_url(doc), headers=admin)
    assert absent.status_code == 200 and absent.json()["state"] == "absent" and "rows" not in absent.json()

    prepared = _write(api, _url(doc, "/preparation"), expert)
    assert prepared.status_code == 200 and prepared.json()["state"] == "building"
    service.build_matrix(project_uid=doc.project_uid, document_uid=doc.document_uid)

    built = api.get(_url(doc), headers=admin)  # any one role reads
    assert built.status_code == 200
    matrix = built.json()
    assert matrix["state"] == "ready" and matrix["revision"]["edit_no"] == 0 and len(matrix["rows"]) == 8
    assert all(row["row_id"].startswith("cpr_") for row in matrix["rows"])

    page = {"version_uid": doc.versions[4], "page_number": 8}
    edit = {"base_revision": matrix["revision"], "edits": [{"kind": "unlink", "page": page}]}
    assert _write(api, _url(doc, "/edits"), admin, edit).status_code == 403  # an administrator is not an expert
    applied = _write(api, _url(doc, "/edits"), expert, edit)
    assert applied.status_code == 200 and applied.json()["revision"]["edit_no"] == 1
    assert applied.json()["counts"]["manual"] == 1

    stale = _write(api, _url(doc, "/edits"), expert, edit)  # the same draft against the revision that moved
    assert stale.status_code == 409
    assert stale.json()["error_code"] == "conflict" and stale.json()["details"]["conflict_reason"] == "comparison_matrix_stale"

    listed = api.get(_url(doc, "/edits") + "?limit=1", headers=admin)
    assert listed.status_code == 200 and listed.json()["items"][0]["kind"] == "unlink" and listed.json()["page"]["next_cursor"] is None
    assert api.get(_url(doc, "/edits") + "?limit=1&cursor=!!", headers=admin).status_code == 422

    now = applied.json()["revision"]
    undone = _write(api, _url(doc, "/edits/undo"), expert, {"base_revision": now})
    assert undone.status_code == 200 and undone.json()["revision"]["edit_no"] == 2 and undone.json()["counts"]["manual"] == 0
    none = _write(api, _url(doc, "/edits/undo"), expert, {"base_revision": undone.json()["revision"]})
    assert none.status_code == 409 and none.json()["details"]["conflict_reason"] == "comparison_edit_none"


def test_paging_the_edit_history_follows_the_cursor(api, service, lab, expert, admin) -> None:
    doc = lab.clone()
    service.build_matrix(project_uid=doc.project_uid, document_uid=doc.document_uid)
    revision = api.get(_url(doc), headers=admin).json()["revision"]
    for number in (8, 3):
        body = {"base_revision": revision, "edits": [{"kind": "unlink", "page": {"version_uid": doc.versions[4], "page_number": number}}]}
        response = _write(api, _url(doc, "/edits"), expert, body)
        assert response.status_code == 200
        revision = response.json()["revision"]
    first = api.get(_url(doc, "/edits") + "?limit=1", headers=admin).json()
    assert [e["edit_no"] for e in first["items"]] == [2] and first["page"]["next_cursor"]
    second = api.get(_url(doc, "/edits") + f"?limit=1&cursor={first['page']['next_cursor']}", headers=admin).json()
    assert [e["edit_no"] for e in second["items"]] == [1] and second["page"]["next_cursor"] is None


def test_the_refusals_are_the_contracts(api, service, lab, expert, admin) -> None:
    doc = lab.clone()
    service.build_matrix(project_uid=doc.project_uid, document_uid=doc.document_uid)
    revision = api.get(_url(doc), headers=admin).json()["revision"]
    unknown = f"/projects/{doc.project_uid}/documents/doc_{new_ulid()}/comparison-matrix"
    assert api.get(unknown, headers=admin).status_code == 404
    assert api.get(unknown.replace("/comparison-matrix", "/comparison-ai-links"), headers=admin).status_code == 404
    other_project = lab.clone(versions=1)
    wrong = f"/projects/{other_project.project_uid}/documents/{doc.document_uid}/comparison-matrix"
    assert api.get(wrong, headers=admin).status_code == 404, "a document of another project is not found"
    invalid = {"base_revision": revision, "edits": [{"kind": "unlink", "page": {"version_uid": doc.versions[0], "page_number": 99}}]}
    refused = _write(api, _url(doc, "/edits"), expert, invalid)
    assert refused.status_code == 422 and refused.json()["details"]["constraint"] == "comparison_edit_invalid"
    too_many = {"base_revision": revision, "edits": [{"kind": "unlink", "page": {"version_uid": doc.versions[0], "page_number": 1}}] * 501}
    over = _write(api, _url(doc, "/edits"), expert, too_many)
    # The request schema (``maxItems: 500``) refuses a longer batch at the edge, before the service: the client reads
    # ``constraint: length``, not the registered ``comparison_edits_limit`` (the service raises that one for a caller
    # that does not come through the edge; see the report, FIX-slot item).
    assert over.status_code == 422 and over.json()["error_code"] == "validation_failed"
    assert over.json()["details"] == {"field": "edits", "constraint": "length"}
    links = api.get(f"/projects/{doc.project_uid}/documents/{doc.document_uid}/comparison-ai-links", headers=admin)
    assert links.status_code == 200 and links.json()["items"] == [] and links.json()["page"]["next_cursor"] is None
    assert api.get(_url(doc)).status_code == 401
