"""A drawing set uploaded as plain PDFs is profiled, matrixed, compared and tiled by the product's own path (`CMP-C1-FIX-C` item 1).

Every other suite of the comparison module seeds its versions by hand, under the manifest role of a portal version
(``source.document``). The plain-PDF upload of `CMP-INGEST-01` writes a different role (``comparison.source_pdf``), and the
page profile, the engine and the tile reader all read the version through ``load_source_version``, which accepted only the
first: a version admitted through the product's own upload failed every page with ``page_profile_source_unreadable``, and
no test saw it (`MEASURE-ENGINE-01.md` section 2).

Nothing here is seeded. The composed application (``create_app``) is driven over HTTP by an expert: ``createProject``,
``createComparisonUpload``, one ``uploadComparisonUploadPart`` per file, ``completeComparisonUploadFile`` (the product reads
each PDF in its ceilinged children), ``getComparisonUploadProposal``, ``confirmComparisonUploadSet``. The confirmation
releases the set to the queue and **the worker's own comparison runner** (the one ``composition.build_comparison_work``
builds from the shipped handler tuple, real page children, real engine child) takes the items in the order the product
chains them: the ``page_profile`` items, the ``matrix_build`` item of ``prepareComparisonMatrix``, the ``series_drive`` and
``series_pair`` items of ``startComparisonSeries``. At the end the pair results are read and one pair tile and one
page-profile tile are streamed. The oracle is the synthetic corpus' answer key (``fixtures/comparison/vs1``), authored next
to the content.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE
from auditmanager.comparison.series.verdict import verdict_codes
from auditmanager.documents.public import MANIFEST_ROLE_COMPARISON_PDF, MANIFEST_ROLE_SOURCE_DOCUMENT
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.db.session import create_session_factory
from auditmanager.shared.identity import new_ulid
from auditmanager.storage.public import S3BlobStore, S3StorageSettings, StorageError
from tests.integration.comparison.series.support import drain, runner_with

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "fixtures" / "comparison"
SECRET = "comparison-upload-to-series-e2e"
PNG = b"\x89PNG\r\n\x1a\n"
#: The first three versions of VS-1 (six pages each): two transitions, twelve sheet pairs.
FILES = ("v1.pdf", "v2.pdf", "v3.pdf")
_NAMES = (
    "DATABASE_URL", "S3_ENDPOINT_URL", "S3_API_PORT", "S3_REGION", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "S3_BUCKET",
)
#: Held back from the worker: the batch's own polling and its abort sweep (the test finishes one set, the batch is not under test).
HELD = ("comparison_batch_drive", "upload_abort_sweep")


def _load_dotenv() -> None:
    dotenv = ROOT / ".env"
    if not dotenv.is_file():
        return
    for raw in dotenv.read_text(encoding="utf-8").splitlines():
        name, separator, value = raw.strip().partition("=")
        if separator and name in _NAMES and not os.environ.get(name):
            os.environ[name] = value.strip().strip("\"'")


@pytest.fixture(scope="module")
def engine() -> Engine:
    _load_dotenv()
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail("DATABASE_URL is not set: run `make up` and `make migrate` for this lane. These tests never skip.")
    built = create_database_engine(DatabaseSettings(url=parse_database_url(raw)))
    yield built
    built.dispose()


@pytest.fixture(scope="module")
def sessions(engine: Engine) -> sessionmaker[Session]:
    return create_session_factory(engine)


@pytest.fixture(scope="module")
def blob_store() -> S3BlobStore:
    _load_dotenv()
    try:
        store = S3BlobStore(S3StorageSettings.from_env())
        store.check_access()
    except StorageError as failure:
        pytest.fail(f"the lane's private bucket is not reachable: {failure}")
    return store


@pytest.fixture(scope="module")
def http(engine: Engine) -> TestClient:
    environ = dict(os.environ) | {API_TOKEN_VARIABLE: SECRET}
    application = create_app(environ=environ)
    return TestClient(create_asgi_app(environ=environ, application=application), raise_server_exceptions=False)


@pytest.fixture(scope="module")
def token() -> str:
    from am_test_accounts import provisioned_credential

    return provisioned_credential(SECRET, "comparison-upload-e2e")


@pytest.fixture(scope="module")
def worker_id(sessions: sessionmaker[Session]) -> str:
    from auditmanager.workers.public import WorkerRegistry

    with sessions() as session:
        registered = WorkerRegistry().register(session, version="cmp-c1-fix-c-e2e", slots=1)
        session.commit()
    return str(registered)


class Client:
    """The expert's calls: every write carries a key of its own, every answer is checked against the status it must have."""

    def __init__(self, http: TestClient, token: str) -> None:
        self.http, self.token = http, token

    def call(self, method: str, path: str, *, expect: int | tuple[int, ...], **kwargs: Any) -> Any:
        headers = {"Authorization": f"Bearer {self.token}"}
        if method in ("POST", "PUT"):
            headers["Idempotency-Key"] = f"e2e-{new_ulid()}"
        if "content" in kwargs:
            headers["content-type"] = "application/octet-stream"
        response = self.http.request(method, path, headers=headers, **kwargs)
        expected = (expect,) if isinstance(expect, int) else expect
        assert response.status_code in expected, f"{method} {path}: {response.status_code} {response.text[:400]}"
        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
        return response


def _rows(sessions: sessionmaker[Session], sql: str, **params: Any) -> list[dict[str, Any]]:
    with sessions() as session:
        return [dict(row) for row in session.execute(text(sql), params).mappings()]


def _upload_and_confirm(api: Client) -> dict[str, Any]:
    """Create a project, upload the three PDFs as a comparison batch, confirm the one proposed set; the ids it made."""
    project = api.call("POST", "/projects", json={"name": "Сравнение: загрузка до серии"}, expect=201)["project_uid"]
    data = {name: (FIXTURES / "vs1" / name).read_bytes() for name in FILES}
    declared = [
        {"display_name": name, "size_bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()} for name, body in data.items()
    ]
    created = api.call(
        "POST", f"/projects/{project}/comparison-uploads",
        json={"files": declared, "compare_after_preparation": False}, expect=201,
    )
    upload, part_size = created["upload_id"], int(created["part_size_bytes"])
    file_ids = {item["display_name"]: item["file_id"] for item in created["files"]}
    for name, body in data.items():
        for number, offset in enumerate(range(0, len(body), part_size), start=1):
            api.call(
                "PUT", f"/comparison-uploads/{upload}/files/{file_ids[name]}/parts?part_number={number}",
                content=body[offset : offset + part_size], expect=200,
            )
        done = api.call("POST", f"/comparison-uploads/{upload}/files/{file_ids[name]}/completion", expect=200)
        assert done["state"] == "verified", (name, done)
    proposal = api.call("GET", f"/comparison-uploads/{upload}/proposal", expect=200)
    assert len(proposal["sets"]) == 1, "the stamps of the three files agree: one set to confirm"
    only = proposal["sets"][0]
    body: dict[str, Any] = {"files": [{"file_id": item["file_id"]} for item in sorted(only["files"], key=lambda f: f["position"])]}
    for field in ("project_stage", "section_code"):
        if only.get(field):
            body[field] = only[field]
    confirmed = api.call("POST", f"/comparison-uploads/{upload}/sets/{only['set_id']}/confirmation", json=body, expect=200)
    assert confirmed["state"] == "done" and confirmed["document_uid"], confirmed
    return {"project": project, "document": confirmed["document_uid"], "upload": upload}


def test_a_set_of_plain_pdfs_is_profiled_matrixed_compared_and_tiled_through_the_products_own_path(
    http: TestClient, token: str, sessions: sessionmaker[Session], engine: Engine, blob_store: S3BlobStore, worker_id: str,
) -> None:
    api = Client(http, token)
    key = json.loads((FIXTURES / "vs1" / "answer_key.json").read_text(encoding="utf-8"))
    ids = _upload_and_confirm(api)
    project, document = ids["project"], ids["document"]

    # -- what the upload made: comparison-only versions, bound under the distinct manifest role -------------------
    versions = _rows(
        sessions,
        "SELECT version_uid, version_ordinal, page_count, upload_kind FROM document_version WHERE document_uid = :d ORDER BY version_ordinal",
        d=document,
    )
    assert [v["page_count"] for v in versions] == [6, 6, 6] and {v["upload_kind"] for v in versions} == {"comparison_pdf"}
    uids = [v["version_uid"] for v in versions]
    roles = _rows(sessions, "SELECT role FROM input_manifest_entry WHERE version_uid = ANY(CAST(:v AS text[]))", v=uids)
    assert {r["role"] for r in roles} == {MANIFEST_ROLE_COMPARISON_PDF} != {MANIFEST_ROLE_SOURCE_DOCUMENT}, (
        "the product's own upload binds the PDF under comparison.source_pdf, which is what this test must not paper over"
    )
    queued = _rows(sessions, "SELECT kind, state, dedupe_key FROM comparison_work WHERE project_uid = :p ORDER BY dedupe_key", p=project)
    assert Counter(r["kind"] for r in queued) == {"page_profile": 3, "comparison_batch_drive": 1}, queued

    runner = runner_with(sessions, engine, blob_store)

    # -- the worker takes the page_profile items ------------------------------------------------------------------
    ran = drain(runner, worker_id, engine, sessions, project, hold=HELD)
    profile_items = _rows(
        sessions, "SELECT state, attempt_count, failure_reason FROM comparison_work WHERE project_uid = :p AND kind = 'page_profile'", p=project
    )
    assert profile_items == [{"state": "succeeded", "attempt_count": 1, "failure_reason": None}] * 3, profile_items
    assert ran == [("page_profile", "succeeded")] * 3, ran
    profiles = _rows(
        sessions,
        "SELECT version_uid, status, reason FROM comparison_page_profile WHERE version_uid = ANY(CAST(:v AS text[]))",
        v=uids,
    )
    assert Counter(p["version_uid"] for p in profiles) == {uid: 6 for uid in uids}
    assert not [p for p in profiles if p["reason"] == "RENDER_FAILED"], "no page ended without a result"

    # -- the matrix ---------------------------------------------------------------------------------------------
    matrix_path = f"/projects/{project}/documents/{document}/comparison-matrix"
    api.call("POST", f"{matrix_path}/preparation", expect=(200, 202))
    assert drain(runner, worker_id, engine, sessions, project, hold=HELD) == [("matrix_build", "succeeded")]
    matrix = api.call("GET", matrix_path, expect=200)
    assert matrix["state"] == "ready", matrix["state"]

    # -- the series and its pair results -----------------------------------------------------------------------
    series = api.call("POST", f"/projects/{project}/documents/{document}/comparison-series", json={}, expect=201)
    ran = drain(runner, worker_id, engine, sessions, project, hold=HELD, limit=200)
    assert {kind for kind, _ in ran} == {"series_drive", "series_pair"}, ran
    assert all(state == "succeeded" for _, state in ran), ran
    done = api.call("GET", f"/comparison-series/{series['series_id']}", expect=200)
    assert done["state"] == "completed", (done["state"], done.get("failure_reason"))
    assert [t["state"] for t in done["transitions"]] == ["completed", "completed"]

    pairs: list[dict[str, Any]] = []
    for transition in done["transitions"]:
        listed = api.call("GET", f"/comparison-transitions/{transition['transition_id']}/sheet-pairs", expect=200)
        pairs += listed["items"]
    compared = [p for p in pairs if p["status"] not in ("added", "removed")]
    results = _rows(
        sessions,
        "SELECT p.comparison_sheet_pair_id AS pair, r.status, r.algo_version FROM comparison_sheet_pair p "
        "JOIN comparison_sheet_pair_result r ON r.comparison_sheet_pair_result_id = p.result_id "
        "JOIN comparison_transition t ON t.comparison_transition_id = p.comparison_transition_id WHERE t.comparison_series_id = :s",
        s=series["series_id"],
    )
    assert len(compared) == len(results) > 0, "every compared pair carries a stored result of the engine"
    assert all(r["algo_version"].startswith("cmp-engine/") for r in results)

    # the answer key, sheet by sheet, for the two transitions this set has
    for transition_key, transition in zip(key["transitions"][:2], done["transitions"], strict=True):
        wanted = {s["sheet_id"]: s["expected_status"] for s in transition_key["sheets"]}
        seen: dict[str, str] = {}
        listed = api.call("GET", f"/comparison-transitions/{transition['transition_id']}/sheet-pairs", expect=200)
        for pair in listed["items"]:
            side = pair.get("page_a") or pair.get("page_b")
            version_id = transition_key["from"] if pair.get("page_a") else transition_key["to"]
            number = side["page"]["page_number"]
            sheet = next(s["sheet_id"] for s in key["sheet_identity"] if number in s["pages"].get(version_id, []))
            seen[sheet] = pair["status"]
        assert seen == wanted, (transition_key["id"], seen, wanted)
        counts = transition_key["status_counts"]
        assert transition["verdict"] == verdict_codes(
            {"different": counts["different"], "needs_review": counts["needs_review"], "added": counts["added"],
             "removed": counts["removed"], "failed": 0, "zones_only": counts["same_zones_changed"]},
            pairs_total=transition["items_total"], pairs_done=transition["items_total"]), transition_key["id"]

    # -- one pair tile and one page-profile tile (the reader that streams the source) ---------------------------
    pair = compared[0]
    tile = api.call("GET", f"/comparison-sheet-pairs/{pair['sheet_pair_id']}/tile?mode=a&level=0&column=0&row=0", expect=200)
    assert tile.headers["content-type"] == "image/png" and tile.content.startswith(PNG)
    page_tile = api.call(
        "GET", f"/page-profiles/{pair['page_a']['page']['page_profile_id']}/tile?level=0&column=0&row=0", expect=200
    )
    assert page_tile.headers["content-type"] == "image/png" and page_tile.content.startswith(PNG)
