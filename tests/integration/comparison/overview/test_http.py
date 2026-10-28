"""The two reads over HTTP on the composed application (`CMP-VC-OVERVIEW-01`): real PostgreSQL, the shipped router and
adapter, the roles and the refusals as a client reads them."""

from __future__ import annotations

import os
from typing import Any

import pytest
from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE
from auditmanager.comparison.modules import COMPARISON_MODULES_ENV

from .conftest import SECRET, Lab, token_for
from .test_bounded import populate


def _client(extra: dict[str, str] | None = None) -> TestClient:
    environ = {k: v for k, v in os.environ.items() if k != COMPARISON_MODULES_ENV} | {API_TOKEN_VARIABLE: SECRET} | (extra or {})
    application = create_app(environ=environ)
    return TestClient(create_asgi_app(environ=environ, application=application), raise_server_exceptions=False)


@pytest.fixture(scope="module")
def api(engine) -> TestClient:
    return _client()


@pytest.fixture
def expert(sessions) -> dict[str, str]:
    return token_for(sessions, "overview-http-expert", ("expert",))


@pytest.fixture
def admin(sessions) -> dict[str, str]:
    return token_for(sessions, "overview-http-admin", ("admin",))


def test_the_overview_is_served_to_an_expert_and_to_an_administrator_alike(api: TestClient, lab: Lab, expert, admin) -> None:
    project = populate(lab, 4)
    answers = []
    for headers in (expert, admin):
        response = api.get(f"/projects/{project}/comparison-overview", headers=headers)
        assert response.status_code == 200, response.text
        answers.append(response.json())
    assert answers[0]["sets"] == answers[1]["sets"] and answers[0]["counters"] == answers[1]["counters"]
    body = answers[0]
    assert body["project_uid"] == project and len(body["sets"]) == 4
    assert body["counters"]["all"] == 4
    assert len(body["pending_uploads"]) == 1
    for row in body["sets"]:
        assert [s["step"] for s in row["steps"]] == ["upload", "profile", "matrix", "ai_pairs", "series", "ai_changes", "report"]
        assert None not in row.values(), "an absent optional member is omitted, never null"
        for step in row["steps"]:
            assert "counts" not in step or None not in step["counts"].values()


def test_an_absent_project_and_an_address_that_names_nothing_are_404(api: TestClient, expert) -> None:
    absent = api.get("/projects/prj_01ARZ3NDEKTSV4RRFFQ69G5FAV/comparison-overview", headers=expert)
    assert absent.status_code == 404 and absent.json()["error_code"] == "not_found"
    assert api.get("/projects/not-an-identity/comparison-overview", headers=expert).status_code == 404  # names nothing


def test_no_credential_is_refused_before_anything_is_read(api: TestClient, lab: Lab) -> None:
    project = lab.project()
    for path in (f"/projects/{project}/comparison-overview", "/execution/comparison-queue"):
        response = api.get(path)
        assert response.status_code == 401 and response.json()["error_code"] == "authentication_required", path


def test_the_queue_summary_is_served_to_both_roles_and_names_the_module_set(lab: Lab, expert, admin) -> None:
    lab.work(lab.project(), "page_profile", "queued")
    for extra, expected in ((None, "none"), ({COMPARISON_MODULES_ENV: "versions"}, "versions"),
                            ({COMPARISON_MODULES_ENV: "versions,stages"}, "versions,stages")):
        client = _client(extra)
        for headers in (expert, admin):
            response = client.get("/execution/comparison-queue", headers=headers)
            assert response.status_code == 200, response.text
            body: dict[str, Any] = response.json()
            assert body["modules"] == expected and isinstance(body["paused"], bool)
            assert set(body["counts"]) == {"queued", "leased", "running", "retry_wait", "paused", "spend_unknown",
                                           "succeeded", "failed", "cancelled"}
            assert body["counts"]["queued"] >= 1 and any(k["kind"] == "page_profile" for k in body["kinds"])


def test_the_module_set_none_still_answers_the_reads(api: TestClient, lab: Lab, expert) -> None:
    """As the matrix and series reads do: the flag gates the worker, not a read."""
    project = lab.project()
    lab.document(project)
    assert api.get(f"/projects/{project}/comparison-overview", headers=expert).status_code == 200
