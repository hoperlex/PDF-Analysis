"""`CMP-VC-AIPAIR-01`: the seven operations over HTTP on the composed application -- the shipped routers, the roles of real credentials,
the keys, the registered reasons as a client reads them, and the module flag (real PostgreSQL; the data is committed, as the
application reads it through connections of its own, and is left in the lane's disposable database)."""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE, Subject, build_signer
from auditmanager.comparison.public import COMPARISON_MODULES_ENV
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import new_ulid

from .conftest import core, support

SECRET = "cmp-vc-aipair-01-http-secret-0123456789"
GHOST_PROJECT = "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV"
GHOST_DOCUMENT = "doc_01ARZ3NDEKTSV4RRFFQ69G5FAV"
GHOST_JOB = "cai_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def _client(modules: str | None) -> TestClient:
    environ = {k: v for k, v in os.environ.items() if k != COMPARISON_MODULES_ENV} | {API_TOKEN_VARIABLE: SECRET}
    if modules is not None:
        environ[COMPARISON_MODULES_ENV] = modules
    application = create_app(environ=environ)
    return TestClient(create_asgi_app(environ=environ, application=application), raise_server_exceptions=False)


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    assert os.environ.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    built = create_database_engine(DatabaseSettings(url=parse_database_url(os.environ["DATABASE_URL"])))
    yield built
    built.dispose()


def _token(engine: Engine, label: str, roles: tuple[str, ...]) -> dict[str, str]:
    from auditmanager.access.accounts import AccountRepository
    from auditmanager.access.repository import UserRepository
    from tests.support.accounts import SUITE_NAMES, SUITE_PASSWORD, suite_login

    sessions = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    users = UserRepository()
    with sessions() as session:
        record = users.find_by_login(session, suite_login(label))
        if record is None:
            created = users.create_user(session, suite_login(label), SUITE_PASSWORD)
            accounts = AccountRepository()
            accounts.complete_profile(session, user_uid=str(created.user_uid), email=None, last_name=SUITE_NAMES[0], first_name=SUITE_NAMES[1])
            for role in roles:
                accounts.grant_role(session, user_uid=str(created.user_uid), role=role, granted_by=None)
            record = users.find_by_login(session, suite_login(label))
            session.commit()
        signer = build_signer({API_TOKEN_VARIABLE: SECRET})
        token = signer.issue(
            Subject(user_uid=str(record.user_uid), login=record.login, token_epoch=record.token_epoch, display_label=record.display_label),
            is_default_credential=False,
        ).token
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def on() -> TestClient:
    return _client("versions")


@pytest.fixture(scope="module")
def off() -> TestClient:
    return _client(None)


@pytest.fixture(scope="module")
def expert(engine: Engine) -> dict[str, str]:
    return _token(engine, "aipair-http-expert", ("expert",))


@pytest.fixture(scope="module")
def admin(engine: Engine) -> dict[str, str]:
    return _token(engine, "aipair-http-admin", ("admin",))


@pytest.fixture
def document(engine: Engine) -> Any:
    """A committed document set with a ready matrix of one doubtful cell, and the work kind routed in «Назначения»."""
    with engine.begin() as connection:
        core.recorded_route(connection, support.KIND)
        world = support.new_world(connection, versions=2)
        support.place_matrix(connection, world, [
            [support.matched(world, 1, 2), support.unmatched(world, 2, [2, 3], ref=1)],
            [support.unmatched(world, 1, [2], ref=2), support.matched(world, 2, 3)],
            [support.absent(world, 1), support.matched(world, 2, 2)],
        ])
    return world


def _base(world: Any) -> str:
    return f"/projects/{world.project}/documents/{world.document}"


def _post(api: TestClient, path: str, headers: dict[str, str], body: Any = None, key: str | None = None):
    return api.post(path, json=body, headers={**headers, "Idempotency-Key": key or f"http-{new_ulid()}"})


def test_every_operation_answers_the_module_class_while_the_versions_module_is_off(off: TestClient, expert: dict[str, str]) -> None:
    base = f"/projects/{GHOST_PROJECT}/documents/{GHOST_DOCUMENT}"
    consent = {"consent": {"estimate_digest": "a" * 64, "confirmed": True}}
    responses = [
        off.get(f"{base}/comparison-ai-pair-check/estimate", headers=expert),
        off.get(f"{base}/comparison-ai-pair-check", headers=expert),
        off.get(f"{base}/comparison-ai-pair-hints", headers=expert),
        _post(off, f"{base}/comparison-ai-pair-check", expert, consent),
        _post(off, f"/comparison-ai-pair-checks/{GHOST_JOB}/pause", expert),
        _post(off, f"/comparison-ai-pair-checks/{GHOST_JOB}/resume", expert, {}),
        _post(off, f"/comparison-ai-pair-checks/{GHOST_JOB}/cancellation", expert),
    ]
    for response in responses:
        assert response.status_code == 503 and response.json()["details"]["dependency"] == "comparison_modules", response.text


def test_what_names_nothing_is_not_found_and_never_an_empty_answer(on: TestClient, admin: dict[str, str], expert: dict[str, str]) -> None:
    base = f"/projects/{GHOST_PROJECT}/documents/{GHOST_DOCUMENT}"
    for path in (f"{base}/comparison-ai-pair-check/estimate", f"{base}/comparison-ai-pair-check", f"{base}/comparison-ai-pair-hints"):
        response = on.get(path, headers=admin)
        assert response.status_code == 404 and response.json()["error_code"] == "not_found", path
    consent = {"consent": {"estimate_digest": "a" * 64, "confirmed": True}}
    assert _post(on, f"{base}/comparison-ai-pair-check", expert, consent).status_code == 404
    for tail, body in (("pause", None), ("resume", {}), ("cancellation", None)):
        response = _post(on, f"/comparison-ai-pair-checks/{GHOST_JOB}/{tail}", expert, body)
        assert response.status_code == 404 and response.json()["error_code"] == "not_found", tail


def test_a_check_flows_from_the_estimate_to_a_cancelled_job_over_http(on: TestClient, admin: dict[str, str], expert: dict[str, str], document: Any) -> None:
    base = _base(document)
    estimate = on.get(f"{base}/comparison-ai-pair-check/estimate", headers=admin)  # any one role reads
    assert estimate.status_code == 200
    shown = estimate.json()
    assert shown["method"] == "pair_check" and shown["questions"] == 1 and shown["calls"] == 2 and len(shown["estimate_digest"]) == 64
    consent = {"consent": {"estimate_digest": shown["estimate_digest"], "confirmed": True}}

    no_key = on.post(f"{base}/comparison-ai-pair-check", json=consent, headers=expert)
    assert no_key.status_code == 422 and no_key.json()["error_code"] == "validation_failed"
    assert _post(on, f"{base}/comparison-ai-pair-check", admin, consent).status_code == 403, "an administrator is not an expert"
    unconfirmed = _post(on, f"{base}/comparison-ai-pair-check", expert, {"consent": {**consent["consent"], "confirmed": False}})
    assert unconfirmed.status_code == 422 and unconfirmed.json()["details"]["constraint"] == "comparison_consent_required"
    stale = _post(on, f"{base}/comparison-ai-pair-check", expert, {"consent": {"estimate_digest": "0" * 64, "confirmed": True}})
    assert stale.status_code == 409 and stale.json()["details"]["conflict_reason"] == "comparison_estimate_stale"

    started = _post(on, f"{base}/comparison-ai-pair-check", expert, consent, key="http-pair-start")
    assert started.status_code == 201, started.text
    job = started.json()
    assert job["state"] == "queued" and job["method"] == "pair_check" and job["estimate"]["units"] == 1
    replay = _post(on, f"{base}/comparison-ai-pair-check", expert, consent, key="http-pair-start")
    assert replay.status_code == 201 and replay.json()["job_id"] == job["job_id"]
    second = _post(on, f"{base}/comparison-ai-pair-check", expert, consent)
    assert second.status_code == 409 and second.json()["details"]["conflict_reason"] == "comparison_ai_job_active"

    got = on.get(f"{base}/comparison-ai-pair-check", headers=admin)
    assert got.status_code == 200 and got.json()["job"]["job_id"] == job["job_id"] and got.json()["counts"]["questions"] == 1
    hints = on.get(f"{base}/comparison-ai-pair-hints", headers=admin)
    assert hints.status_code == 200 and hints.json()["items"] == []

    path = f"/comparison-ai-pair-checks/{job['job_id']}"
    assert _post(on, f"{path}/pause", admin).status_code == 403
    paused = _post(on, f"{path}/pause", expert)
    assert paused.status_code == 200 and paused.json()["state"] == "paused" and paused.json()["pause_reason"] == "user"
    resumed = _post(on, f"{path}/resume", expert, {})
    assert resumed.status_code == 200 and resumed.json()["state"] == "queued"
    cancelled = _post(on, f"{path}/cancellation", expert)
    assert cancelled.status_code == 200 and cancelled.json()["state"] == "cancelled"
    again = _post(on, f"{path}/cancellation", expert)
    assert again.status_code == 409 and again.json()["details"]["conflict_reason"] == "comparison_ai_job_state"
