"""The two reads of part A over HTTP on the composed application (`CMP-VC-SPEC-01`): real PostgreSQL and object store, the shipped
routers, the module gate and the roles as the client meets them.

Two operations are wired by this lane (they leave the stub registers of ``tests/integration/composition``), so the module-flag test
of the stub suite no longer judges them: this file does, and shows the gate failing when it is removed.
"""

from __future__ import annotations

import os

import pytest
from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE, Subject, build_signer
from auditmanager.comparison.public import COMPARISON_MODULES_ENV

from .conftest import SECRET, SPEC_PAGE, _account

ABSENT_PROFILE = "cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
ABSENT_PAIR = "ctp_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def _client(modules: str | None) -> TestClient:
    environ = {k: v for k, v in os.environ.items() if k != COMPARISON_MODULES_ENV} | {API_TOKEN_VARIABLE: SECRET}
    if modules is not None:
        environ[COMPARISON_MODULES_ENV] = modules
    return TestClient(create_asgi_app(environ=environ, application=create_app(environ=environ)), raise_server_exceptions=False)


def _headers(sessions, label: str, roles: tuple[str, ...]) -> dict[str, str]:
    from auditmanager.access.repository import UserRepository
    from tests.support.accounts import suite_login

    _account(sessions, label, roles)
    with sessions() as session:
        record = UserRepository().find_by_login(session, suite_login(label))
    signer = build_signer({API_TOKEN_VARIABLE: SECRET})
    token = signer.issue(
        Subject(user_uid=str(record.user_uid), login=record.login, token_epoch=record.token_epoch, display_label=record.display_label),
        is_default_credential=False).token
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def on(engine) -> TestClient:
    return _client("versions")


@pytest.fixture(scope="module")
def off(engine) -> TestClient:
    return _client(None)


@pytest.fixture
def admin(sessions) -> dict[str, str]:
    return _headers(sessions, "spec-http-admin", ("admin",))


@pytest.fixture
def expert(sessions) -> dict[str, str]:
    return _headers(sessions, "spec-http-expert", ("expert",))


def test_the_positions_of_a_page_are_read_over_http_by_any_one_role(on, lab, admin, expert) -> None:
    doc = lab.clone()
    path = f"/page-profiles/{lab.profile_id(doc, 2, SPEC_PAGE['vs1/v5.pdf'])}/spec-positions"
    for headers in (admin, expert):
        response = on.get(path, headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["is_specification"] is True and len(body["positions"]) == 6
        assert body["positions"][2]["quantity"] == "3" and body["positions"][5]["pos"] == "7"
    assert on.get(path).status_code == 401


def test_the_changes_of_a_sheet_pair_are_read_over_http(on, lab, started, admin) -> None:
    _doc, series = started()
    found = lab.rows(
        "SELECT p.comparison_sheet_pair_id AS id FROM comparison_sheet_pair p "
        "JOIN comparison_transition t ON t.comparison_transition_id = p.comparison_transition_id "
        "JOIN comparison_page_profile pb ON pb.comparison_page_profile_id = p.page_b_profile_id "
        "WHERE t.comparison_series_id = :s AND t.transition_no = 2 AND pb.page_number = 7", s=series["series_id"])
    response = on.get(f"/comparison-sheet-pairs/{found[0]['id']}/spec-positions", headers=admin)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["is_specification"] is True and body["totals"]["changed"] == 1
    assert [c["kind"] for c in body["changes"]] == ["changed", "removed", "added"]


def test_an_absent_page_or_pair_is_not_found_and_never_an_empty_answer(on, admin) -> None:
    for path in (f"/page-profiles/{ABSENT_PROFILE}/spec-positions", f"/comparison-sheet-pairs/{ABSENT_PAIR}/spec-positions"):
        response = on.get(path, headers=admin)
        assert response.status_code == 404 and response.json()["error_code"] == "not_found", path


@pytest.mark.parametrize("path", [f"/page-profiles/{ABSENT_PROFILE}/spec-positions", f"/comparison-sheet-pairs/{ABSENT_PAIR}/spec-positions"])
def test_while_the_versions_module_is_off_nothing_is_read(off, admin, path) -> None:
    """ADR-0025 decision 23: the answer names the module before any read, so even an absent identity is `503`, not `404`."""
    response = off.get(path, headers=admin)
    assert response.status_code == 503 and response.json()["details"]["dependency"] == "comparison_modules"
