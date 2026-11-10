"""`REVIEW-FIX-TESTS-1102` (S6-02): the served application starts a paid Run only with a priced consent.

The composition root closes the gate with one literal (``require_cost_consent=True``; pinned
container-free by ``tests/unit/bootstrap/test_composition_pins_the_cost_consent_gate.py``). This is the
behavioural half, over the composed ASGI application and the lane's own PostgreSQL, with the recorded
provider: a start that carries no consent, an unconfirmed consent, or a consent for another digest is
refused **and writes nothing** -- no ``audit_run``, no ``job``, no ``command_record`` for the version or
the keys used -- and a repeat (``reauditRun``) of a finished Run without a consent is refused the same
way. A start with the consent taken from the estimate of the same version is accepted, which is what
shows the refusals are about the consent and not about anything else the request lacks.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text
from starlette.testclient import TestClient

from auditmanager.api.routers.idempotency import IDEMPOTENCY_HEADER
from auditmanager.api.security import API_TOKEN_VARIABLE
from tests.support.run_consent import estimate_run_cost, plain_analysis_pricing, run_consent

DEPLOYMENT_SECRET = "served-start-requires-a-priced-consent-token"
BASELINE_BUNDLE = Path(__file__).resolve().parents[3] / "fixtures" / "synthetic" / "ar" / "bundles" / "ar_baseline.zip"


def _token() -> str:
    from am_test_accounts import provisioned_credential

    return provisioned_credential(DEPLOYMENT_SECRET, "served-start-consent")


def _counts(world: dict[str, Any]) -> tuple[int, int, int]:
    """Rows this suite's version and keys could have gained: Runs, their Jobs, and the command ledger."""
    from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
    from auditmanager.shared.db.engine import create_database_engine

    engine = create_database_engine(DatabaseSettings(url=parse_database_url(os.environ["DATABASE_URL"])))
    try:
        with engine.connect() as connection:
            runs = connection.execute(
                text("SELECT count(*) FROM audit_run WHERE version_uid = :v"), {"v": world["version_uid"]}
            ).scalar_one()
            jobs = connection.execute(
                text("SELECT count(*) FROM job j JOIN audit_run r ON r.run_id = j.run_id WHERE r.version_uid = :v"),
                {"v": world["version_uid"]},
            ).scalar_one()
            commands = connection.execute(
                text("SELECT count(*) FROM command_record WHERE idempotency_key LIKE :p"),
                {"p": f"{world['tag']}-%"},
            ).scalar_one()
        return int(runs), int(jobs), int(commands)
    finally:
        engine.dispose()


def _headers(world: dict[str, Any], label: str) -> dict[str, str]:
    return world["auth"] | {IDEMPOTENCY_HEADER: f"{world['tag']}-{label}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def world() -> dict[str, Any]:
    assert os.environ.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    for leaked in ("ANTHROPIC_API_KEY", "PROXY_LLM_BASE_URL", "PROXY_LLM_TOKEN"):
        assert leaked not in os.environ, f"{leaked} reached this suite; a recorded run must not be able to spend"
    from auditmanager.api.app import create_asgi_app

    app = create_asgi_app(environ=dict(os.environ) | {
        "AUDITMANAGER_PROVIDER_MODE": "recorded",
        API_TOKEN_VARIABLE: DEPLOYMENT_SECRET,
    })
    client = TestClient(app, raise_server_exceptions=False)
    auth = {"Authorization": f"Bearer {_token()}"}
    tag = f"consent-{uuid.uuid4().hex[:10]}"
    world: dict[str, Any] = {"app": app, "client": client, "auth": auth, "tag": tag}

    answer = client.post("/projects", headers=_headers(world, "prj"), content=json.dumps({"name": f"Consent gate {tag}"}).encode())
    assert answer.status_code == 201, answer.content
    project_uid = answer.json()["project_uid"]
    boundary = "consentgateboundary"
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="ar_baseline.zip"\r\nContent-Type: application/zip\r\n\r\n'
    ).encode()
    tail = f"\r\n--{boundary}--\r\n".encode()
    answer = client.post(
        f"/projects/{project_uid}/documents",
        headers=auth | {IDEMPOTENCY_HEADER: f"{tag}-doc", "Content-Type": f"multipart/form-data; boundary={boundary}"},
        content=head + BASELINE_BUNDLE.read_bytes() + tail,
    )
    assert answer.status_code == 201, answer.content
    version = answer.json()
    answer = client.put(
        f"/projects/{project_uid}/documents/{version['document_uid']}/versions/{version['version_uid']}/classification",
        headers=auth | {"Content-Type": "application/json"},
        content=json.dumps({"project_stage": "R", "section_code": "PB"}).encode(),
    )
    assert answer.status_code == 200, answer.content
    world["version_uid"] = version["version_uid"]
    return world


def _start(world: dict[str, Any], label: str, body: dict[str, Any]) -> Any:
    return world["client"].post("/runs", headers=_headers(world, label), content=json.dumps(body).encode())


def _assert_confirmation_required(answer: Any) -> None:
    assert answer.status_code == 422, answer.content
    body = answer.json()
    assert body["error_code"] == "validation_failed", body
    assert body["details"]["field"] == "cost_consent" and body["details"]["constraint"] == "confirmation_required", body


@pytest.fixture(scope="module")
def finished_run(world: dict[str, Any]) -> str:
    """The positive control: the same request with the estimate's consent is accepted, and the Run finishes."""
    with plain_analysis_pricing():
        priced = estimate_run_cost(world["client"], world["auth"], {"version_uid": world["version_uid"]})
        answer = _start(world, "run", {"version_uid": world["version_uid"], "cost_consent": run_consent(priced)})
    assert answer.status_code == 202, answer.content
    assert world["app"].state.run_carrier.drain(timeout=300), "the run never finished"
    return answer.json()["run_id"]


def test_a_start_without_a_consent_is_refused_and_writes_nothing(world: dict[str, Any], finished_run: str) -> None:
    before = _counts(world)
    bare = _start(world, "bare", {"version_uid": world["version_uid"]})
    _assert_confirmation_required(bare)
    unconfirmed = _start(world, "unconfirmed", {
        "version_uid": world["version_uid"],
        "cost_consent": {"estimate_digest": "a" * 64, "ceiling_micros": 1, "confirmed": False},
    })
    _assert_confirmation_required(unconfirmed)
    assert _counts(world) == before


def test_a_consent_for_another_estimate_is_a_stale_conflict_and_writes_nothing(
    world: dict[str, Any], finished_run: str
) -> None:
    with plain_analysis_pricing():
        priced = estimate_run_cost(world["client"], world["auth"], {"version_uid": world["version_uid"]})
        consent = run_consent(priced)
        consent["estimate_digest"] = "f" * 64 if consent["estimate_digest"] != "f" * 64 else "e" * 64
        before = _counts(world)
        stale = _start(world, "stale", {"version_uid": world["version_uid"], "cost_consent": consent})
    assert stale.status_code == 409, stale.content
    assert stale.json()["details"]["conflict_reason"] == "run_cost_estimate_stale", stale.json()
    assert _counts(world) == before


def test_a_repeat_of_a_finished_run_without_a_consent_is_refused_and_writes_nothing(
    world: dict[str, Any], finished_run: str
) -> None:
    before = _counts(world)
    refused = world["client"].post(f"/runs/{finished_run}/reaudit", headers=_headers(world, "reaudit-bare"))
    _assert_confirmation_required(refused)
    assert _counts(world) == before
