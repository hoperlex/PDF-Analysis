"""`COMPARE-PERSISTED-SUMMARY-01` (B1), end to end: an expert's approval of a sheet pairing over HTTP.

The composed ASGI application (``create_asgi_app``) with the recorded provider, against the lane's
PostgreSQL (migrated to ``0035`` or later) and MinIO, driven with real credentials. One portal
bundle is uploaded and a second version of the **same** document is published from the same
manifest (the upload operation always starts a new document), both are classified and analysed by
recorded runs, so every sheet of the older version is proposed as an exact-text pair of the newer
one. Then, in order: nothing is approved yet; an administrator who is not an expert is refused;
an expert approves one proposed pair and the read serves it sealed with its (here all-equal) raw
differences; the same key and another key both answer that approval, `replayed`; a proposal the
digest of which is not the one shown, and a comparison view that is refused, are `409`; the
expert withdraws the link, a second withdrawal is `409`, an unknown link `404`; the audit trail
holds one event per write; a missing key or body is `422`.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from auditmanager.api.routers.idempotency import IDEMPOTENCY_HEADER
from auditmanager.api.security import API_TOKEN_VARIABLE

DEPLOYMENT_SECRET = "comparison-records-over-http-token"
EXPERT, ADMIN = "comparison-records", "comparison-records-admin"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BASELINE_BUNDLE = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar" / "bundles" / "ar_baseline.zip"


def _expert() -> dict[str, str]:
    from am_test_accounts import provisioned_credential

    return {"Authorization": f"Bearer {provisioned_credential(DEPLOYMENT_SECRET, EXPERT)}"}


def _admin() -> dict[str, str]:
    """An administrator who is not an expert: the suite's account, its expert role swapped."""
    from am_test_accounts import provisioned_credential, provisioned_record

    from auditmanager.access.public import AccountRepository

    record = provisioned_record(ADMIN)
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with Session(engine) as session:
            accounts = AccountRepository()
            if accounts.roles_of(session, str(record.user_uid)) != frozenset({"admin"}):
                seed = session.execute(
                    text("SELECT user_uid FROM app_user WHERE login = 'admin'")
                ).scalar_one()
                accounts.set_roles(
                    session, actor_uid=str(seed), user_uid=str(record.user_uid),
                    roles=frozenset({"admin"}),
                )
            session.commit()
    finally:
        engine.dispose()
    return {"Authorization": f"Bearer {provisioned_credential(DEPLOYMENT_SECRET, ADMIN)}"}


def _upload(client: TestClient, auth: dict[str, str], project_uid: str, tag: str) -> dict[str, Any]:
    boundary = "comparisonrecordsboundary"
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="ar_baseline.zip"\r\nContent-Type: application/zip\r\n\r\n'
    ).encode("utf-8")
    answer = client.post(
        f"/projects/{project_uid}/documents",
        headers=auth | {
            IDEMPOTENCY_HEADER: f"cmprec-{tag}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        content=head + BASELINE_BUNDLE.read_bytes() + f"\r\n--{boundary}--\r\n".encode("utf-8"),
    )
    assert answer.status_code == 201, answer.content
    return answer.json()


def _second_version(document_uid: str, version_uid: str) -> str:
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


def _json(world: dict[str, Any], who: str = "expert", key: str | None = None) -> dict[str, str]:
    headers = world[who] | {"Content-Type": "application/json"}
    return headers if key is None else headers | {IDEMPOTENCY_HEADER: key}


def _key(world: dict[str, Any], label: str) -> str:
    return f"cmprec-{world['tag']}-{label}"


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
    tag = uuid.uuid4().hex[:12]
    world: dict[str, Any] = {
        "app": app, "client": client, "expert": _expert(), "admin": _admin(), "tag": tag,
    }
    answer = client.post(
        "/projects", headers=_json(world, key=_key(world, "prj")),
        content=json.dumps({"name": f"Записи сравнения {tag}"}).encode("utf-8"),
    )
    assert answer.status_code == 201, answer.content
    project_uid = answer.json()["project_uid"]
    first = _upload(client, world["expert"], project_uid, f"{tag}-v1")
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
            content=json.dumps({"project_stage": "P", "section_code": "PB"}).encode("utf-8"),
        )
        assert classified.status_code == 200, classified.content
        started = client.post(
            "/runs", headers=_json(world, key=_key(world, version_uid[-6:])),
            content=json.dumps({"version_uid": version_uid}).encode("utf-8"),
        )
        assert started.status_code == 202, started.content
    assert app.state.run_carrier.drain(timeout=300), "the runs never finished"
    return world


def _base(world: dict[str, Any]) -> str:
    return (
        f"/projects/{world['project_uid']}/documents/{world['document_uid']}"
        f"/versions/{world['v1']}/comparison"
    )


def _compare(world: dict[str, Any], **params: Any) -> dict[str, Any]:
    answer = world["client"].get(
        _base(world), params={"target_version_uid": world["v2"]} | params, headers=world["expert"],
    )
    assert answer.status_code == 200, answer.content
    return answer.json()


def _approve(world: dict[str, Any], body: dict[str, Any], key: str | None, who: str = "expert") -> Any:
    return world["client"].post(
        f"{_base(world)}/sheet-pairings", headers=_json(world, who, key),
        content=json.dumps(body).encode("utf-8"),
    )


def _withdraw(world: dict[str, Any], link: str, body: dict[str, Any] | None, key: str | None,
              who: str = "expert") -> Any:
    return world["client"].post(
        f"{_base(world)}/sheet-pairings/{link}/withdrawals", headers=_json(world, who, key),
        content=json.dumps({"mode": "version"} if body is None else body).encode("utf-8"),
    )


def _proposal(world: dict[str, Any]) -> dict[str, Any]:
    rows = [r for r in _compare(world)["sheets"] if r["status"] == "unchanged"]
    assert rows, "the same manifest must propose exact-text pairs"
    return rows[0]


def _body(world: dict[str, Any], row: dict[str, Any], **changes: Any) -> dict[str, Any]:
    return {
        "target_version_uid": world["v2"], "mode": "version",
        "source_page_number": row["source_page_number"],
        "target_page_number": row["target_page_number"],
        "suggestion_sha256": row["suggestion_sha256"],
    } | changes


def _events(world: dict[str, Any], comparison_id: str) -> list[str]:
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with engine.connect() as connection:
            return list(connection.execute(
                text("SELECT event_type FROM audit_event WHERE aggregate_id = :c ORDER BY sequence_no"),
                {"c": comparison_id},
            ).scalars())
    finally:
        engine.dispose()


def test_nothing_is_approved_before_an_expert_does_it(world) -> None:
    approved = _compare(world)["approved_pairs"]
    assert approved == {
        "link_revision": None, "evidence_state": "none", "raw_evidence_seal_sha256": None, "items": [],
    }


def test_the_approval_replay_withdrawal_and_audit_trail_over_http(world) -> None:
    row = _proposal(world)
    body = _body(world, row)

    # an administrator who is not an expert decides nothing
    refused = _approve(world, body, _key(world, "admin"), who="admin")
    assert refused.status_code == 403, refused.content
    assert refused.json()["details"]["required_capability"] == "role:expert"
    assert _compare(world)["approved_pairs"]["evidence_state"] == "none"

    approved = _approve(world, body, _key(world, "approve-1"))
    assert approved.status_code == 201, approved.content
    event = approved.json()
    assert event["event_kind"] == "approved" and event["replayed"] is False
    assert event["link_revision"] == 1
    assert event["comparison_id"].startswith("cmp_") and event["sheet_link_id"].startswith("sln_")
    assert (event["source_page_number"], event["target_page_number"]) == (
        row["source_page_number"], row["target_page_number"],
    )
    assert event["suggestion_sha256"] == row["suggestion_sha256"]
    assert event["raw_evidence_seal_sha256"] and event["actor_label"]

    # the read serves the pair sealed; the pages are equal, so every span is an equal span
    approved_pairs = _compare(world)["approved_pairs"]
    assert approved_pairs["evidence_state"] == "sealed" and approved_pairs["link_revision"] == 1
    assert approved_pairs["raw_evidence_seal_sha256"] == event["raw_evidence_seal_sha256"]
    (item,) = approved_pairs["items"]
    assert item["sheet_link_id"] == event["sheet_link_id"] and item["state"] == "verified"
    assert item["approved_by_label"] == event["actor_label"]
    assert item["diff"] is not None
    assert all(h["tag"] == "equal" and h["hunk_id"] is None for h in item["diff"]["hunks"])
    assert (item["diff"]["added_line_count"], item["diff"]["removed_line_count"]) == (0, 0)

    # the same key, and another key for the exact same pair, answer the stored approval
    for label in ("approve-1", "approve-2"):
        again = _approve(world, body, _key(world, label))
        assert again.status_code == 201, again.content
        assert again.json() == event | {"replayed": True}
    # a changed body under a used key is the existing refusal
    reused = _approve(world, _body(world, row, mode="stage"), _key(world, "approve-1"))
    assert reused.status_code == 409 and reused.json()["error_code"] == "idempotency_key_reuse"

    # what was not shown is not approved: a digest that is not the proposal's, and a view the
    # comparison refuses (the pair is not a design-to-working pair)
    stale = _approve(world, _body(world, row, suggestion_sha256="0" * 64), _key(world, "stale"))
    assert stale.status_code == 409, stale.content
    assert stale.json()["details"]["conflict_reason"] == "sheet_pair_not_proposed"
    refused_view = _approve(world, _body(world, row, mode="stage"), _key(world, "stage"))
    assert refused_view.status_code == 409, refused_view.content
    assert refused_view.json()["details"]["conflict_reason"] == "sheet_pair_not_proposed"

    # withdrawal: a new row; the same key replays; a second withdrawal is refused; an unknown link is 404
    withdrawn = _withdraw(world, event["sheet_link_id"], None, _key(world, "withdraw-1"), who="admin")
    assert withdrawn.status_code == 403, withdrawn.content
    withdrawn = _withdraw(world, event["sheet_link_id"], None, _key(world, "withdraw-1"))
    assert withdrawn.status_code == 201, withdrawn.content
    ended = withdrawn.json()
    assert ended["event_kind"] == "withdrawn" and ended["link_revision"] == 2
    assert ended["sheet_link_id"] == event["sheet_link_id"] and ended["raw_evidence_seal_sha256"] is None
    assert _withdraw(world, event["sheet_link_id"], None, _key(world, "withdraw-1")).json() == (
        ended | {"replayed": True}
    )
    second = _withdraw(world, event["sheet_link_id"], None, _key(world, "withdraw-2"))
    assert second.status_code == 409, second.content
    assert second.json()["details"]["conflict_reason"] == "sheet_link_not_active"
    unknown = _withdraw(world, "sln_01ARZ3NDEKTSV4RRFFQ69G5FAV", None, _key(world, "withdraw-3"))
    assert unknown.status_code == 404, unknown.content
    after = _compare(world)["approved_pairs"]
    assert (after["evidence_state"], after["items"], after["link_revision"]) == ("none", [], 2)

    # one audit event per write, none for a refusal
    assert _events(world, event["comparison_id"]) == [
        "comparison.sheet_link_approved", "comparison.sheet_link_withdrawn",
    ]


def test_a_pairing_without_its_key_or_its_body_is_refused(world) -> None:
    row = _proposal(world)
    body = _body(world, row)
    no_key = _approve(world, body, None)
    assert no_key.status_code == 422, no_key.content
    assert no_key.json()["details"]["field"] == "Idempotency-Key"
    no_pages = _approve(
        world, {k: v for k, v in body.items() if k != "source_page_number"}, _key(world, "no-page"),
    )
    assert no_pages.status_code == 422, no_pages.content
    extra = _approve(world, body | {"actor_label": "Другой"}, _key(world, "extra"))
    assert extra.status_code == 422, extra.content  # the actor is the verified subject, never the body
    no_mode = _withdraw(world, "sln_01ARZ3NDEKTSV4RRFFQ69G5FAV", {}, _key(world, "no-mode"))
    assert no_mode.status_code == 422, no_mode.content
    foreign = world["client"].post(
        f"/projects/prj_01ARZ3NDEKTSV4RRFFQ69G5FAV/documents/{world['document_uid']}"
        f"/versions/{world['v1']}/comparison/sheet-pairings",
        headers=_json(world, key=_key(world, "foreign")), content=json.dumps(body).encode("utf-8"),
    )
    assert foreign.status_code == 404, foreign.content
