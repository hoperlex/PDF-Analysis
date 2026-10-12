"""The seven norms operations on the composed application, by role (`W55A-SEARCH-01`).

Window: the lane's PostgreSQL ``57230`` and S3 ``60830/60831`` (its ``.env``), the
application ``create_app`` builds -- the seam, the composition root and the shipped
adapters. `R-80`: a role-less account reaches none of the seven; `R-113`: the history and
the designation are ``admin``'s, so an ``expert`` is refused them and reaches the five reads.
What a refusal says is the seam's ``403 permission_denied`` with the capability it lacks.
"""

from __future__ import annotations

import json
import os
from typing import Any

import pytest
from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE

DEPLOYMENT_SECRET = "norms-roles-window-token"
ABSENT_DOC = "ndoc_01ARZ3NDEKTSV4RRFFQ69G5FAV"
ABSENT_SNAPSHOT = "ns_01ARZ3NDEKTSV4RRFFQ69G5FAV"

SEVEN: dict[str, tuple[str, str, dict[str, Any] | None]] = {
    "searchNorms": ("GET", "/norms/search?q=%D0%B7%D0%B4%D0%B0%D0%BD%D0%B8%D0%B5", None),
    "getNormDocument": ("GET", f"/norm-documents/{ABSENT_DOC}", None),
    "listNormParagraphs": ("GET", f"/norm-documents/{ABSENT_DOC}/paragraphs", None),
    "streamNormDocumentContent": ("GET", f"/norm-documents/{ABSENT_DOC}/content", None),
    "listNormSnapshots": ("GET", "/norms/snapshots", None),
    "listNormSnapshotEvents": ("GET", "/norms/snapshots/events", None),
    "setCurrentNormSnapshot": (
        "PUT", "/norms/snapshots/current",
        {"norms_snapshot_id": ABSENT_SNAPSHOT, "expected_current": None},
    ),
}
ADMIN_ONLY = {"listNormSnapshotEvents", "setCurrentNormSnapshot"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    assert os.environ.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    environ = dict(os.environ) | {API_TOKEN_VARIABLE: DEPLOYMENT_SECRET}
    application = create_app(environ=environ)
    return TestClient(
        create_asgi_app(environ=environ, application=application),
        raise_server_exceptions=False,
    )


def _credential(label: str, roles: frozenset[str]) -> str:
    """A complete account of this suite holding exactly ``roles``, and a credential for it."""
    from am_test_accounts import database_url, provisioned_credential, provisioned_record
    from sqlalchemy.orm import Session

    from auditmanager.access.accounts import AccountRepository
    from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
    from auditmanager.shared.db.engine import create_database_engine

    record = provisioned_record(label)
    # `app_user_role.granted_by` references `app_user`: the grantor is a real account of this
    # suite, and never the subject itself (removing one's own role is refused).
    actor = provisioned_record("norms-roles-grantor")
    engine = create_database_engine(DatabaseSettings(url=parse_database_url(database_url())))
    try:
        with Session(engine) as session:
            AccountRepository().set_roles(
                session, actor_uid=str(actor.user_uid), user_uid=str(record.user_uid),
                roles=roles,
            )
            session.commit()
    finally:
        engine.dispose()
    return provisioned_credential(DEPLOYMENT_SECRET, label)


def _call(client: TestClient, token: str, operation: str) -> tuple[int, Any]:
    method, path, body = SEVEN[operation]
    response = client.request(
        method, path,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        content=None if body is None else json.dumps(body),
    )
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, response.content


def test_a_role_less_account_reaches_none_of_the_seven(client: TestClient) -> None:
    token = _credential("norms-roles-none", frozenset())
    for operation in SEVEN:
        status, body = _call(client, token, operation)
        assert status == 403, (operation, status, body)
        assert body["error_code"] == "permission_denied", (operation, body)
        expected = "role:admin" if operation in ADMIN_ONLY else "role:admin|expert"
        assert body["details"]["required_capability"] == expected, (operation, body)


def test_an_expert_reads_and_is_refused_the_history_and_the_designation(
    client: TestClient,
) -> None:
    token = _credential("norms-roles-expert", frozenset({"expert"}))
    for operation in SEVEN:
        status, body = _call(client, token, operation)
        if operation in ADMIN_ONLY:
            assert (status, body["details"]["required_capability"]) == (403, "role:admin")
        else:
            assert status != 403, (operation, status, body)
            assert status < 500, (operation, status, body)


def test_an_administrator_reads_the_history(client: TestClient) -> None:
    token = _credential("norms-roles-admin", frozenset({"admin"}))
    status, body = _call(client, token, "listNormSnapshotEvents")
    assert status == 200 and isinstance(body["items"], list), body
    status, body = _call(client, token, "setCurrentNormSnapshot")
    assert (status, body["error_code"]) == (404, "not_found"), body
