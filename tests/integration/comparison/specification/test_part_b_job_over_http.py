"""The estimate, the start with consent and the cancel over HTTP on the composed application (`CMP-VC-SPEC-01`): the module gate, the
expert's act, the key and its replay, the consent -- as the client meets them. A recorded process: no provider is reachable."""

from __future__ import annotations

import os

import pytest
from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE, Subject, build_signer
from auditmanager.comparison.public import COMPARISON_MODULES_ENV
from auditmanager.shared.identity import new_ulid

from .conftest import SECRET, _account

ABSENT_TRANSITION = "ctn_01ARZ3NDEKTSV4RRFFQ69G5FAV"
ABSENT_JOB = "cai_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def _client(modules: str | None) -> TestClient:
    environ = {k: v for k, v in os.environ.items() if k != COMPARISON_MODULES_ENV} | {API_TOKEN_VARIABLE: SECRET, "AUDITMANAGER_PROVIDER_MODE": "recorded"}
    if modules is not None:
        environ[COMPARISON_MODULES_ENV] = modules
    return TestClient(create_asgi_app(environ=environ, application=create_app(environ=environ)), raise_server_exceptions=False)


def _headers(sessions, label: str, roles: tuple[str, ...]) -> dict[str, str]:
    from auditmanager.access.repository import UserRepository
    from tests.support.accounts import suite_login

    _account(sessions, label, roles)
    with sessions() as session:
        record = UserRepository().find_by_login(session, suite_login(label))
    token = build_signer({API_TOKEN_VARIABLE: SECRET}).issue(
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
def expert(sessions) -> dict[str, str]:
    return _headers(sessions, "spec-job-expert", ("expert",))


@pytest.fixture
def admin(sessions) -> dict[str, str]:
    return _headers(sessions, "spec-job-admin", ("admin",))


@pytest.fixture
def transition_path(started, committed_route, sessions):
    doc, series = started()
    transition = next(t["transition_id"] for t in series["transitions"] if t["source_version_uid"] == doc.versions[1])
    return f"/comparison-transitions/{transition}/specification"


def _consent(estimate: dict, *, confirmed: bool = True) -> dict:
    return {"consent": {"estimate_digest": estimate["estimate_digest"], "confirmed": confirmed}}


def test_the_estimate_is_read_by_any_role_and_starts_nothing(on, transition_path, admin, expert) -> None:
    for headers in (admin, expert):
        response = on.get(f"{transition_path}/estimate", headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["method"] == "spec" and body["calls"] == 2 and body["reused"] == 0 and body["images"] == 0 and len(body["estimate_digest"]) == 64
    assert on.get(transition_path, headers=expert).json()["state"] == "not_started"


def test_a_start_is_the_experts_act_keyed_and_replayed_and_needs_the_consent(on, transition_path, admin, expert) -> None:
    estimate = on.get(f"{transition_path}/estimate", headers=expert).json()
    key = {"Idempotency-Key": f"spec-{new_ulid()}"}
    assert on.post(transition_path, json=_consent(estimate), headers={**admin, **key}).status_code == 403
    assert on.post(transition_path, json=_consent(estimate), headers=expert).status_code == 422  # no key
    unconfirmed = on.post(transition_path, json=_consent(estimate, confirmed=False), headers={**expert, **key})
    assert unconfirmed.status_code == 422 and unconfirmed.json()["details"]["constraint"] == "comparison_consent_required"
    stale = on.post(transition_path, json={"consent": {"estimate_digest": "c" * 64, "confirmed": True}}, headers={**expert, **key})
    assert stale.status_code == 409 and stale.json()["details"]["conflict_reason"] == "comparison_estimate_stale"
    first = on.post(transition_path, json=_consent(estimate), headers={**expert, **key})
    assert first.status_code == 201, first.text
    job = first.json()
    assert job["method"] == "spec" and job["state"] == "queued" and job["consented_by"]
    replay = on.post(transition_path, json=_consent(estimate), headers={**expert, **key})
    assert replay.status_code == 201 and replay.json()["job_id"] == job["job_id"]
    other = on.post(transition_path, json=_consent(estimate), headers={**expert, "Idempotency-Key": f"spec-{new_ulid()}"})
    assert other.status_code == 409 and other.json()["details"]["conflict_reason"] == "comparison_ai_job_active"
    assert on.get(transition_path, headers=expert).json()["state"] == "running"  # queued: the row waits for the worker


def test_a_cancel_stops_the_job_and_the_comparison_and_is_refused_twice(on, transition_path, admin, expert) -> None:
    estimate = on.get(f"{transition_path}/estimate", headers=expert).json()
    job = on.post(transition_path, json=_consent(estimate), headers={**expert, "Idempotency-Key": f"spec-{new_ulid()}"}).json()
    cancel = f"/comparison-ai-spec-jobs/{job['job_id']}/cancellation"
    assert on.post(cancel, headers={**admin, "Idempotency-Key": f"c-{new_ulid()}"}).status_code == 403
    done = on.post(cancel, headers={**expert, "Idempotency-Key": f"c-{new_ulid()}"})
    assert done.status_code == 200 and done.json()["state"] == "cancelled"
    assert on.get(transition_path, headers=expert).json()["state"] == "cancelled"
    again = on.post(cancel, headers={**expert, "Idempotency-Key": f"c-{new_ulid()}"})
    assert again.status_code == 409 and again.json()["details"]["conflict_reason"] == "comparison_ai_job_state"
    absent = on.post(f"/comparison-ai-spec-jobs/{ABSENT_JOB}/cancellation", headers={**expert, "Idempotency-Key": f"c-{new_ulid()}"})
    assert absent.status_code == 404


@pytest.mark.parametrize("method,path,body", [
    ("GET", f"/comparison-transitions/{ABSENT_TRANSITION}/specification/estimate", None),
    ("POST", f"/comparison-transitions/{ABSENT_TRANSITION}/specification", {"consent": {"estimate_digest": "a" * 64, "confirmed": True}}),
    ("POST", f"/comparison-ai-spec-jobs/{ABSENT_JOB}/cancellation", None),
])
def test_while_the_versions_module_is_off_nothing_is_read_written_or_sent(off, expert, method, path, body) -> None:
    response = off.request(method, path, headers={**expert, "Idempotency-Key": f"off-{new_ulid()}"}, **({} if body is None else {"json": body}))
    assert response.status_code == 503 and response.json()["details"]["dependency"] == "comparison_modules"


def test_an_absent_transition_is_not_found_for_the_estimate_and_the_start(on, expert) -> None:
    assert on.get(f"/comparison-transitions/{ABSENT_TRANSITION}/specification/estimate", headers=expert).status_code == 404
    start = on.post(f"/comparison-transitions/{ABSENT_TRANSITION}/specification", headers={**expert, "Idempotency-Key": f"a-{new_ulid()}"},
                    json={"consent": {"estimate_digest": "a" * 64, "confirmed": True}})
    assert start.status_code == 404
