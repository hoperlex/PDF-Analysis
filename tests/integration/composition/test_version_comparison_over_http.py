"""`W59-VERSION-COMPARE-01`, end to end: two versions of one set compared over HTTP.

The composed ASGI application (``create_asgi_app``) with the recorded provider, against the
lane's own PostgreSQL and MinIO, driven with a real expert credential. One portal bundle is
uploaded; a second version of the **same** document is published from the same manifest
(the upload operation always starts a new document), so both versions carry identical text.
Then, in order: an unclassified pair is refused, a classified pair without analysis is
refused, both versions are analysed by recorded runs, and the comparison answers every sheet
as an exact-text pair with no difference and every finding of the older run proposed as
``unchanged`` against the newer one. The text layers are read from MinIO by the shipped
adapter, held to the digests their stage rows recorded.

A third version of the same set is classified ``R``: ``mode=version`` refuses the P/R pair
(``project_stage_mismatch``, never relabelled) and ``mode=stage`` compares it -- the W62
П/Р slice. A path that names no version of the document is ``404``.
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

DEPLOYMENT_SECRET = "w59-version-compare-over-http-token"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BASELINE_BUNDLE = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar" / "bundles" / "ar_baseline.zip"


def _token() -> str:
    from am_test_accounts import provisioned_credential

    return provisioned_credential(DEPLOYMENT_SECRET, "w59-version-compare")


def _upload(client: TestClient, auth: dict[str, str], project_uid: str, tag: str) -> dict[str, Any]:
    boundary = "w59comparisonboundary"
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="ar_baseline.zip"\r\nContent-Type: application/zip\r\n\r\n'
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    answer = client.post(
        f"/projects/{project_uid}/documents",
        headers=auth | {
            IDEMPOTENCY_HEADER: f"w59cmp-{tag}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        content=head + BASELINE_BUNDLE.read_bytes() + tail,
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
            from sqlalchemy.orm import Session

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
    answer = client.post(
        "/projects",
        headers=auth | {IDEMPOTENCY_HEADER: f"w59cmp-{tag}-prj", "Content-Type": "application/json"},
        content=json.dumps({"name": f"W59 compare {tag}"}).encode("utf-8"),
    )
    assert answer.status_code == 201, answer.content
    project_uid = answer.json()["project_uid"]
    first = _upload(client, auth, project_uid, f"{tag}-v1")
    other = _upload(client, auth, project_uid, f"{tag}-other")
    v2 = _second_version(first["document_uid"], first["version_uid"])
    v3 = _second_version(first["document_uid"], first["version_uid"])
    return {
        "app": app, "client": client, "auth": auth, "tag": tag, "project_uid": project_uid,
        "document_uid": first["document_uid"], "v1": first["version_uid"], "v2": v2, "v3": v3,
        "other_version": other["version_uid"], "other_document": other["document_uid"],
    }


def _compare(world: dict[str, Any], *, source: str, target: str, **query: Any) -> Any:
    path = (
        f"/projects/{world['project_uid']}/documents/{world['document_uid']}"
        f"/versions/{source}/comparison"
    )
    return world["client"].get(
        path, params={"target_version_uid": target, **query}, headers=world["auth"],
    )


def _classify(world: dict[str, Any], version_uid: str, stage: str = "P") -> None:
    answer = world["client"].put(
        f"/projects/{world['project_uid']}/documents/{world['document_uid']}"
        f"/versions/{version_uid}/classification",
        headers=world["auth"] | {"Content-Type": "application/json"},
        # `PROD-11-AR-V1-V2-REMOVAL-01`: the served startRun refuses an АР version, so the version that must run is classified ПБ, whose recording carries the corpus run's findings.
        content=json.dumps({"project_stage": stage, "section_code": "PB"}).encode("utf-8"),
    )
    assert answer.status_code == 200, answer.content


def _run(world: dict[str, Any], version_uid: str) -> str:
    answer = world["client"].post(
        "/runs",
        headers=world["auth"] | {
            IDEMPOTENCY_HEADER: f"w59cmp-{world['tag']}-{version_uid[-6:]}",
            "Content-Type": "application/json",
        },
        content=json.dumps({"version_uid": version_uid}).encode("utf-8"),
    )
    assert answer.status_code == 202, answer.content
    return answer.json()["run_id"]


def test_the_comparison_refuses_then_compares_as_its_inputs_appear(world) -> None:
    unclassified = _compare(world, source=world["v1"], target=world["v2"])
    assert unclassified.status_code == 200, unclassified.content
    body = unclassified.json()
    assert (body["outcome"], body["refusal"]) == (
        "refused", {"reason": "stage_unclassified", "side": "source"},
    )
    assert body["sheets"] == [] and body["sheet_diffs"] is None and body["findings"] is None

    _classify(world, world["v1"])
    _classify(world, world["v2"])
    unanalysed = _compare(world, source=world["v1"], target=world["v2"]).json()
    assert unanalysed["refusal"] == {"reason": "analysis_missing", "side": "source"}
    assert unanalysed["source"]["project_stage"] == "P"
    assert unanalysed["source"]["section_code"] == "PB"

    source_run, target_run = _run(world, world["v1"]), _run(world, world["v2"])
    assert world["app"].state.run_carrier.drain(timeout=300), "the runs never finished"
    states = {
        run: world["client"].get(f"/runs/{run}", headers=world["auth"]).json()["state"]
        for run in (source_run, target_run)
    }
    assert set(states.values()) == {"published"}, states

    compared = _compare(world, source=world["v1"], target=world["v2"])
    assert compared.status_code == 200, compared.content
    body = compared.json()
    assert body["outcome"] == "compared" and body["refusal"] is None
    assert (body["source"]["run_id"], body["target"]["run_id"]) == (source_run, target_run)
    # Each text layer names its own version, so the two artifacts differ by digest while
    # every page text is identical -- which is what the sheet list below shows.
    assert body["source"]["text_layer_sha256"] != body["target"]["text_layer_sha256"]
    pages = body["source"]["page_count"]
    assert [row["status"] for row in body["sheets"]] == ["unchanged"] * len(body["sheets"])
    assert len(body["sheets"]) == pages
    assert body["sheet_diffs"] == {
        "offset": 0, "limit": 10, "total": 0, "next_offset": None, "items": [],
    }
    findings = body["findings"]
    assert findings["status"] == "compared"
    assert findings["source_finding_count"] == findings["target_finding_count"] > 0
    assert {p["kind"] for p in findings["proposals"]} == {"unchanged"}
    assert len(body["comparison_sha256"]) == 64
    assert body["mode"] == "version"

    _classify(world, world["v3"], stage="R")
    working_run = _run(world, world["v3"])
    assert world["app"].state.run_carrier.drain(timeout=300), "the R run never finished"
    as_versions = _compare(world, source=world["v1"], target=world["v3"]).json()
    assert (as_versions["mode"], as_versions["refusal"]) == (
        "version", {"reason": "project_stage_mismatch", "side": None},
    )
    as_stages = _compare(world, source=world["v1"], target=world["v3"], mode="stage").json()
    assert (as_stages["mode"], as_stages["outcome"]) == ("stage", "compared")
    assert (as_stages["source"]["project_stage"], as_stages["target"]["project_stage"]) == (
        "P", "R",
    )
    assert as_stages["target"]["run_id"] == working_run
    assert [row["status"] for row in as_stages["sheets"]] == ["unchanged"] * pages
    same_stage = _compare(world, source=world["v1"], target=world["v2"], mode="stage").json()
    assert same_stage["refusal"] == {"reason": "stage_pair_invalid", "side": None}


@pytest.mark.parametrize(
    ("pick", "reason"),
    [
        (lambda w: (w["v1"], w["v1"]), "same_version"),
        (lambda w: (w["v2"], w["v1"]), "version_order_invalid"),
        (lambda w: (w["v1"], w["other_version"]), "different_set"),
    ],
)
def test_pairs_outside_the_rule_are_refused_with_a_reason(world, pick, reason) -> None:
    source, target = pick(world)
    answer = _compare(world, source=source, target=target)
    assert answer.status_code == 200, answer.content
    assert answer.json()["refusal"]["reason"] == reason


def test_a_path_that_names_no_version_of_the_document_is_404(world) -> None:
    """`D-67`: the source version under another document is not this path's resource."""
    answer = world["client"].get(
        f"/projects/{world['project_uid']}/documents/{world['other_document']}"
        f"/versions/{world['v1']}/comparison",
        params={"target_version_uid": world["v2"]}, headers=world["auth"],
    )
    assert answer.status_code == 404, answer.content
    assert answer.json()["error_code"] == "not_found"


@pytest.mark.parametrize(
    "query",
    [{"diff_limit": 26}, {"diff_offset": -1}, {"source_run_id": "x"}, {"mode": "object"}],
)
def test_malformed_paging_or_run_identity_is_422(world, query) -> None:
    answer = _compare(world, source=world["v1"], target=world["v2"], **query)
    assert answer.status_code == 422, answer.content
    assert answer.json()["error_code"] == "validation_failed"
