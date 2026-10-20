"""`W59-DECISION-CARRYOVER-01`, end to end: a decision carried to the next version over HTTP.

The composed ASGI application (``create_asgi_app``) with the recorded provider, against the
lane's own PostgreSQL and MinIO, driven with a real expert credential. One portal bundle is
uploaded and a second version of the **same** document is published from the same manifest
(the upload operation always starts a new document), both are classified and analysed by
recorded runs, so every finding of the older run is proposed ``unchanged`` against the newer
one. Then, in order: no candidate while nothing is decided; an expert accepts one source
finding and it becomes a candidate; ``carryOverDecision`` appends one event on the matched
target finding, authored by the caller, with the provenance in its comment; an exact repeat
under another key answers the same event; the target is no longer a candidate; a pair the
comparison does not propose, a stale source decision and a decided target are ``409`` with a
``conflict_reason``; a missing key or body is ``422``.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from auditmanager.api.routers.idempotency import IDEMPOTENCY_HEADER
from auditmanager.api.security import API_TOKEN_VARIABLE

DEPLOYMENT_SECRET = "w59-decision-carryover-over-http-token"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BASELINE_BUNDLE = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar" / "bundles" / "ar_baseline.zip"


def _token() -> str:
    from am_test_accounts import provisioned_credential

    return provisioned_credential(DEPLOYMENT_SECRET, "w59-decision-carryover")


def _upload(client: TestClient, auth: dict[str, str], project_uid: str, tag: str) -> dict[str, Any]:
    boundary = "w59carryoverboundary"
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="ar_baseline.zip"\r\nContent-Type: application/zip\r\n\r\n'
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    answer = client.post(
        f"/projects/{project_uid}/documents",
        headers=auth | {
            IDEMPOTENCY_HEADER: f"w59carry-{tag}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        content=head + BASELINE_BUNDLE.read_bytes() + tail,
    )
    assert answer.status_code == 201, answer.content
    return answer.json()


def _second_version(document_uid: str, version_uid: str) -> str:
    from sqlalchemy.orm import Session

    from auditmanager.documents.public import DocumentRepository
    from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
    from auditmanager.shared.db.engine import create_database_engine
    from auditmanager.shared.identity import DocumentUid, VersionUid

    engine = create_database_engine(
        DatabaseSettings(url=parse_database_url(os.environ["DATABASE_URL"]))
    )
    try:
        with engine.begin() as connection:
            session = Session(bind=connection)
            documents = DocumentRepository()
            base = documents.get_version(session, VersionUid.parse(version_uid))
            published = documents.publish_version(
                session,
                document_uid=DocumentUid.parse(document_uid),
                media_type=base.media_type,
                byte_size=base.byte_size,
                sha256=base.sha256,
                page_count=base.page_count,
                source_filename="ar_baseline_v2.zip",
                entries=base.manifest,
                text_character_count=base.text_character_count,
                textless_pages=base.textless_pages,
                recognised_character_count=base.recognised_character_count,
            )
            session.flush()
            return str(published)
    finally:
        engine.dispose()


def _json(world: dict[str, Any], key: str | None = None) -> dict[str, str]:
    headers = world["auth"] | {"Content-Type": "application/json"}
    return headers if key is None else headers | {IDEMPOTENCY_HEADER: key}


def _key(world: dict[str, Any], label: str) -> str:
    return f"w59carry-{world['tag']}-{label}"


@pytest.fixture(scope="module")
def world() -> dict[str, Any]:
    assert os.environ.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    for leaked in ("ANTHROPIC_API_KEY", "PROXY_LLM_BASE_URL", "PROXY_LLM_TOKEN"):
        assert leaked not in os.environ, f"{leaked} reached this suite"
    from auditmanager.api.app import create_asgi_app

    app = create_asgi_app(environ=dict(os.environ) | {
        "AUDITMANAGER_PROVIDER_MODE": "recorded",
        API_TOKEN_VARIABLE: DEPLOYMENT_SECRET,
    })
    client = TestClient(app, raise_server_exceptions=False)
    auth = {"Authorization": f"Bearer {_token()}"}
    tag = uuid.uuid4().hex[:12]
    world: dict[str, Any] = {"app": app, "client": client, "auth": auth, "tag": tag}
    answer = client.post(
        "/projects", headers=_json(world, f"w59carry-{tag}-prj"),
        content=json.dumps({"name": f"W59 carryover {tag}"}).encode("utf-8"),
    )
    assert answer.status_code == 201, answer.content
    project_uid = answer.json()["project_uid"]
    first = _upload(client, auth, project_uid, f"{tag}-v1")
    v2 = _second_version(first["document_uid"], first["version_uid"])
    world |= {
        "project_uid": project_uid, "document_uid": first["document_uid"],
        "v1": first["version_uid"], "v2": v2,
    }
    for version_uid in (world["v1"], v2):
        classified = client.put(
            f"/projects/{project_uid}/documents/{world['document_uid']}"
            f"/versions/{version_uid}/classification",
            headers=_json(world),
            content=json.dumps({"project_stage": "P", "section_code": "AR"}).encode("utf-8"),
        )
        assert classified.status_code == 200, classified.content
        started = client.post(
            "/runs", headers=_json(world, _key(world, version_uid[-6:])),
            content=json.dumps({"version_uid": version_uid}).encode("utf-8"),
        )
        assert started.status_code == 202, started.content
    assert app.state.run_carrier.drain(timeout=300), "the runs never finished"
    return world


def _version_path(world: dict[str, Any]) -> str:
    return (
        f"/projects/{world['project_uid']}/documents/{world['document_uid']}"
        f"/versions/{world['v1']}"
    )


def _findings(world: dict[str, Any]) -> dict[str, Any]:
    answer = world["client"].get(
        f"{_version_path(world)}/comparison",
        params={"target_version_uid": world["v2"]}, headers=world["auth"],
    )
    assert answer.status_code == 200, answer.content
    body = answer.json()
    assert body["outcome"] == "compared", body["refusal"]
    return body["findings"]


def _carry(world: dict[str, Any], body: dict[str, Any], key: str | None) -> Any:
    headers = _json(world) if key is None else _json(world, key)
    return world["client"].post(
        f"{_version_path(world)}/comparison/carryovers",
        headers=headers, content=json.dumps(body).encode("utf-8"),
    )


def _accept(world: dict[str, Any], finding_uid: str, label: str) -> str:
    finding = world["client"].get(f"/findings/{finding_uid}", headers=world["auth"]).json()
    answer = world["client"].post(
        f"/findings/{finding_uid}/decisions", headers=_json(world, _key(world, label)),
        content=json.dumps({
            "event_type": "accept",
            "finding_observation_id": finding["observation"]["finding_observation_id"],
            "comment": "Подтверждаю замечание.",
        }).encode("utf-8"),
    )
    assert answer.status_code == 201, answer.content
    return answer.json()["event"]["decision_id"]


def test_a_confirmed_carryover_over_http(world) -> None:
    findings = _findings(world)
    pairs = [p for p in findings["proposals"] if p["kind"] == "unchanged"]
    assert len(pairs) >= 2, findings["proposals"]
    assert findings["carryover_candidates"] == []
    first, second = pairs[0], pairs[1]
    source_uid = first["source_finding"]["finding_uid"]
    target_uid = first["target_finding"]["finding_uid"]

    decision_id = _accept(world, source_uid, "accept-first")
    (candidate,) = _findings(world)["carryover_candidates"]
    assert candidate["source_finding_uid"] == source_uid
    assert candidate["target_finding_uid"] == target_uid
    assert candidate["proposal_sha256"] == first["proposal_sha256"]
    assert candidate["source_decision"]["decision_id"] == decision_id
    assert candidate["source_decision"]["verdict"] == "accepted"
    assert candidate["source_decision"]["comment"] == "Подтверждаю замечание."

    body = {
        "target_version_uid": world["v2"], "mode": "version",
        "source_finding_uid": source_uid, "target_finding_uid": target_uid,
        "source_decision_id": decision_id,
    }
    carried = _carry(world, body, _key(world, "carry-first"))
    assert carried.status_code == 201, carried.content
    answer = carried.json()
    assert answer["replayed"] is False and answer["current_verdict"] == "accepted"
    event = answer["event"]
    assert (event["finding_uid"], event["event_type"], event["verdict"]) == (
        target_uid, "accept", "accepted",
    )
    assert "severity" not in event
    assert event["comment"].startswith("Решение перенесено из версии 1 (сравнение версий)")
    for identity in (decision_id, source_uid, world["v1"], world["v2"]):
        assert identity in event["comment"]
    assert (answer["source_decision_id"], answer["source_version_ordinal"]) == (decision_id, 1)

    history = world["client"].get(f"/findings/{target_uid}/decisions", headers=world["auth"])
    assert [item["decision_id"] for item in history.json()["items"]] == [event["decision_id"]]
    source_history = world["client"].get(f"/findings/{source_uid}/decisions", headers=world["auth"])
    assert [item["decision_id"] for item in source_history.json()["items"]] == [decision_id]

    repeat = _carry(world, body, _key(world, "carry-first-again"))
    assert repeat.status_code == 201, repeat.content
    assert repeat.json()["replayed"] is True and repeat.json()["event"] == event
    assert _findings(world)["carryover_candidates"] == []

    crossed = _carry(world, body | {
        "target_finding_uid": second["target_finding"]["finding_uid"],
    }, _key(world, "crossed"))
    assert crossed.status_code == 409, crossed.content
    assert crossed.json()["details"]["conflict_reason"] == "carryover_pair_not_proposed"

    newer = _accept(world, source_uid, "accept-first-again")
    decided = _carry(world, body | {"source_decision_id": newer}, _key(world, "decided"))
    assert decided.status_code == 409, decided.content
    assert decided.json()["details"]["conflict_reason"] == "carryover_target_already_decided"

    second_source = second["source_finding"]["finding_uid"]
    second_decision = _accept(world, second_source, "accept-second")
    _accept(world, second_source, "accept-second-again")
    stale = _carry(world, body | {
        "source_finding_uid": second_source,
        "target_finding_uid": second["target_finding"]["finding_uid"],
        "source_decision_id": second_decision,
    }, _key(world, "stale"))
    assert stale.status_code == 409, stale.content
    assert stale.json()["details"]["conflict_reason"] == "carryover_source_decision_not_current"


def test_a_carryover_without_its_key_or_its_body_is_refused(world) -> None:
    body = {
        "target_version_uid": world["v2"], "mode": "version",
        "source_finding_uid": "fnd_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        "target_finding_uid": "fnd_01ARZ3NDEKTSV4RRFFQ69G5FAW",
        "source_decision_id": "dec_01ARZ3NDEKTSV4RRFFQ69G5FAV",
    }
    no_key = _carry(world, body, None)
    assert no_key.status_code == 422, no_key.content
    assert no_key.json()["details"]["field"] == "Idempotency-Key"
    no_mode = _carry(world, {k: v for k, v in body.items() if k != "mode"}, _key(world, "no-mode"))
    assert no_mode.status_code == 422, no_mode.content
    unknown = _carry(world, body, _key(world, "unknown"))
    assert unknown.status_code == 409, unknown.content
    assert unknown.json()["details"]["conflict_reason"] == "carryover_pair_not_proposed"
