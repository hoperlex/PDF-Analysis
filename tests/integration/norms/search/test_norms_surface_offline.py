"""The norms operations' bodies, driven without a container (`W55A-SEARCH-01`).

The router (``build_norm_routes``) over the **shipped** ``NormsSearchAdapter`` and
``NormContentAdapter``, the exception handlers and the envelope middleware; only the two
edges are stood in for: the database (``support.FakeNorms``, which answers the exact
statements the modules send) and the S3 client (one ``GetObject``). What the SQL selects is
the window suites' (``test_search_window.py``, ``test_current_snapshot_window.py``).

Each case fails without the behaviour it names:

* a search the statement timeout cancelled is ``422 validation_failed``
  (``norms_search_too_broad``), never a page -- and the timeout is set before any read;
* the scope rule: none current, or a named snapshot never current, is
  ``required_norm_unavailable`` (``norms_snapshot``); a once-current one is searched;
* a cursor is refused with another query;
* the setter's order: unknown, replay, build, sources, stale, then one history row;
* the PDF only through a confirmed binding, the range resolved against the binding's size
  before the store is touched, a tampered whole read stopped short.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
from types import SimpleNamespace
from typing import Any

import pytest
from botocore.exceptions import ClientError
from fastapi import APIRouter, FastAPI
from starlette.testclient import TestClient

from auditmanager.api.routers import (
    CorrelationMiddleware,
    FailureEnvelopeMiddleware,
    install_exception_handlers,
)
from auditmanager.api.routers.norms import build_norm_routes
from auditmanager.api.schemas.content import CONTENT_CHUNK_BYTES
from auditmanager.bootstrap.adapters import NormContentAdapter, NormsSearchAdapter
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage import S3BlobStore, S3StorageSettings, derive_blob_id
from tests.integration.norms.search.support import AT, Document, FakeNorms

SNAPSHOT = "ns_01M2545JSD15ETSNNV904X991N"
OTHER = "ns_01M2545JSD15ETSNNV904X992N"
NEVER = "ns_01M2545JSD15ETSNNV904X993N"
NDOC = "ndoc_01M2545JSD15ETSNNV904X991V"
BARE = "ndoc_01M2545JSD15ETSNNV904X992V"
ABSENT = "ndoc_01ARZ3NDEKTSV4RRFFQ69G5FAV"
ADMIN = "usr_01M2545JSD15ETSNNV904X991S"

DATA = b"%PDF-1.7\n" + bytes(range(256)) * 2100  # two full chunks and a short third
DIGEST = hashlib.sha256(DATA).hexdigest()
BLOB_ID = derive_blob_id(sha256=DIGEST, size=len(DATA))


class _Body(io.BytesIO):
    pass


class FakeS3:
    def __init__(self, stored: bytes = DATA) -> None:
        self.stored = stored
        self.metadata = {"content-sha256": DIGEST, "content-size": str(len(DATA))}
        self.requests: list[dict[str, Any]] = []
        self.missing = False

    def get_object(self, **request: Any) -> dict[str, Any]:
        self.requests.append(request)
        if self.missing:
            raise ClientError(
                {"Error": {"Code": "NoSuchKey"}, "ResponseMetadata": {"HTTPStatusCode": 404}},
                "GetObject",
            )
        response: dict[str, Any] = {"Metadata": dict(self.metadata)}
        header = request.get("Range")
        if header is None:
            payload = self.stored
        else:
            first, last = (int(part) for part in header.removeprefix("bytes=").split("-"))
            payload = self.stored[first: last + 1]
            response["ContentRange"] = f"bytes {first}-{last}/{len(self.stored)}"
        response["ContentLength"] = len(payload)
        response["Body"] = _Body(payload)
        return response


def _hit_row(index: int, rank: float = 0.5) -> SimpleNamespace:
    return SimpleNamespace(
        hit_rank=rank,
        norm_paragraph_id=f"npar_01M2545JSD15ETSNNV904X9{index:03d}",
        norm_document_id=NDOC,
        slug="СП_54_13330_2022__Свод_правил__Здания_жилые",
        title="Свод правил. Здания жилые многоквартирные",
        doc_type="СП",
        source_attribution="consultant_plus",
        clause_number="7.1.4",
        page_label=12,
        block_ref=f"blk_{index:04d}",
        ordinal=index,
        text="7.1.4 Лестницы жилых зданий",
        headline="7.1.4 Лестницы жилых зданий",
    )


class Surface:
    def __init__(self, database: FakeNorms | None = None, stored: bytes = DATA) -> None:
        self.db = database or FakeNorms()
        self.s3 = FakeS3(stored)
        store = S3BlobStore(
            S3StorageSettings(
                endpoint_url="http://127.0.0.1:1", region="us-east-1", bucket="offline",
                access_key_id="offline", secret_access_key="offline",
            ),
            client=self.s3,  # type: ignore[arg-type]
        )
        self.norms = NormsSearchAdapter(self.db, timeout_ms=1234)  # type: ignore[arg-type]
        self.content = NormContentAdapter(self.db, blob_store=store)  # type: ignore[arg-type]
        router = APIRouter()
        build_norm_routes(router, self.norms, self.content)
        app = FastAPI()
        install_exception_handlers(app)
        app.include_router(router)
        app.add_middleware(FailureEnvelopeMiddleware)
        app.add_middleware(CorrelationMiddleware)
        self.app = app
        self.client = TestClient(app, raise_server_exceptions=False)

    def get(self, path: str, **headers: str) -> Any:
        return self.client.get(path, headers=headers)


def _searchable() -> FakeNorms:
    database = FakeNorms()
    database.snapshots = {SNAPSHOT: (True, True), OTHER: (True, True)}
    database.designate(SNAPSHOT)
    database.search_rows = [_hit_row(index) for index in range(3)]
    return database


def _envelope(response: Any) -> tuple[int, str, dict[str, Any]]:
    body = response.json()
    assert "items" not in body, body
    return response.status_code, body["error_code"], body.get("details") or {}


# --- the timeout ---------------------------------------------------------------------------


def test_a_cancelled_search_is_too_broad_and_never_a_page() -> None:
    database = _searchable()
    database.search_failure = "cancel"
    surface = Surface(database)
    status, code, details = _envelope(surface.get("/norms/search?q=здания"))
    assert (status, code) == (422, "validation_failed")
    assert details == {"field": "q", "constraint": "norms_search_too_broad"}
    # The timeout is the adapter's setting, set before the scope or the search is read.
    assert database.timeouts == ["1234"]
    assert database.sent[0] == "set_timeout" and database.sent[-1] == "search"


def test_another_database_failure_is_not_reported_as_too_broad() -> None:
    database = _searchable()
    database.search_failure = "other"
    response = Surface(database).get("/norms/search?q=здания")
    assert response.status_code >= 500
    assert "norms_search_too_broad" not in response.text


def test_the_adapter_refuses_a_timeout_that_is_not_positive() -> None:
    with pytest.raises(ValueError):
        NormsSearchAdapter(FakeNorms(), timeout_ms=0)  # type: ignore[arg-type]


# --- the scope rule ------------------------------------------------------------------------


def test_with_none_current_search_is_refused_not_empty() -> None:
    database = FakeNorms()
    status, code, details = _envelope(Surface(database).get("/norms/search?q=здания"))
    assert (status, code, details) == (
        422, "required_norm_unavailable", {"reference_kind": "norms_snapshot"}
    )
    assert "search" not in database.sent


def test_a_snapshot_never_current_is_refused_and_a_once_current_one_is_searched() -> None:
    database = _searchable()
    database.designate(OTHER)  # SNAPSHOT was current once; OTHER is current now
    surface = Surface(database)
    status, code, details = _envelope(
        surface.get(f"/norms/search?q=здания&norms_snapshot_id={NEVER}")
    )
    assert (status, code) == (422, "required_norm_unavailable")
    assert details == {"reference_kind": "norms_snapshot", "norms_snapshot_id": NEVER}
    response = surface.get(f"/norms/search?q=здания&norms_snapshot_id={SNAPSHOT}")
    assert response.status_code == 200
    assert {item["norms_snapshot_id"] for item in response.json()["items"]} == {SNAPSHOT}


# --- the page and its cursor ---------------------------------------------------------------


def test_a_page_carries_hits_with_attribution_offsets_and_a_bound_cursor() -> None:
    surface = Surface(_searchable())
    response = surface.get("/norms/search?q=здания&limit=2")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    hit = body["items"][0]
    assert hit["designation"] == "СП 54 13330 2022"
    assert hit["source_attribution"] == "consultant_plus"
    assert hit["page_label"] == 12 and hit["clause_number"] == "7.1.4"
    fragment = hit["fragment"]
    assert fragment["text"] == "7.1.4 Лестницы жилых зданий"
    assert [fragment["text"][h["char_start"]:h["char_end"]] for h in fragment["highlights"]] == [
        "зданий"
    ]
    cursor = body["page"]["next_cursor"]
    assert cursor
    assert surface.get(f"/norms/search?q=здания&limit=2&cursor={cursor}").status_code == 200
    status, code, details = _envelope(
        surface.get(f"/norms/search?q=зданий&limit=2&cursor={cursor}")
    )
    assert (status, code, details) == (
        422, "validation_failed", {"field": "cursor", "constraint": "format"}
    )


def test_a_cursor_does_not_survive_a_new_designation() -> None:
    database = _searchable()
    surface = Surface(database)
    cursor = surface.get("/norms/search?q=здания&limit=2").json()["page"]["next_cursor"]
    database.designate(OTHER)
    status, code, _ = _envelope(surface.get(f"/norms/search?q=здания&limit=2&cursor={cursor}"))
    assert (status, code) == (422, "validation_failed")


def test_the_last_page_has_no_cursor() -> None:
    body = Surface(_searchable()).get("/norms/search?q=здания&limit=3").json()
    assert len(body["items"]) == 3 and body["page"]["next_cursor"] is None


# --- one document --------------------------------------------------------------------------


def _with_documents() -> FakeNorms:
    database = _searchable()
    database.documents = {
        NDOC: Document(NDOC, SNAPSHOT, pdf=(BLOB_ID, DIGEST, len(DATA))),
        BARE: Document(BARE, SNAPSHOT, pdf=None),
    }
    return database


def test_a_document_says_whether_its_pdf_is_served() -> None:
    surface = Surface(_with_documents())
    served = surface.get(f"/norm-documents/{NDOC}").json()
    assert served["content_available"] is True
    assert served["unreliable_paragraph_count"] == 1
    assert served["designation"] == "СП 54 13330 2022"
    assert surface.get(f"/norm-documents/{BARE}").json()["content_available"] is False
    status, code, details = _envelope(surface.get(f"/norm-documents/{ABSENT}"))
    assert (status, code, details) == (404, "not_found", {"aggregate_type": "NormDocument"})


# --- the PDF -------------------------------------------------------------------------------


def test_the_pdf_streams_through_its_confirmed_binding() -> None:
    surface = Surface(_with_documents())
    response = surface.get(f"/norm-documents/{NDOC}/content")
    assert response.status_code == 200
    assert response.content == DATA
    assert response.headers["Content-Type"] == "application/pdf"
    assert response.headers["Content-Length"] == str(len(DATA))
    assert [request.get("Range") for request in surface.s3.requests] == [None]


def test_a_window_is_asked_of_the_store_and_nothing_else() -> None:
    surface = Surface(_with_documents())
    response = surface.get(f"/norm-documents/{NDOC}/content", Range="bytes=100-163")
    assert response.status_code == 206
    assert response.content == DATA[100:164]
    assert response.headers["Content-Range"] == f"bytes 100-163/{len(DATA)}"
    assert [request.get("Range") for request in surface.s3.requests] == ["bytes=100-163"]


def test_a_document_without_a_confirmed_binding_serves_no_pdf() -> None:
    surface = Surface(_with_documents())
    status, code, details = _envelope(surface.get(f"/norm-documents/{BARE}/content"))
    assert (status, code, details) == (
        422, "required_norm_unavailable", {"reference_kind": "norm_source"}
    )
    assert surface.s3.requests == []


def test_an_unknown_document_is_404_whatever_the_range_says() -> None:
    surface = Surface(_with_documents())
    for headers in ({}, {"Range": "bytes=abc"}, {"Range": "bytes=0-1"}):
        status, code, _ = _envelope(surface.get(f"/norm-documents/{ABSENT}/content", **headers))
        assert (status, code) == (404, "not_found"), headers
    status, code, details = _envelope(
        surface.get(f"/norm-documents/{NDOC}/content", Range="bytes=abc")
    )
    assert (status, code, details["constraint"]) == (422, "validation_failed", "format")
    assert surface.s3.requests == []


def test_an_unsatisfiable_range_is_refused_before_the_store_is_touched() -> None:
    surface = Surface(_with_documents())
    status, code, details = _envelope(
        surface.get(f"/norm-documents/{NDOC}/content", Range=f"bytes={len(DATA)}-")
    )
    assert (status, code, details["constraint"]) == (422, "validation_failed", "unsatisfiable")
    assert surface.s3.requests == []


def test_an_absent_object_is_a_typed_integrity_failure() -> None:
    surface = Surface(_with_documents())
    surface.s3.missing = True
    status, code, details = _envelope(surface.get(f"/norm-documents/{NDOC}/content"))
    assert (status, code) == (422, "storage_integrity_error")
    assert details["role"] == "norm_source" and details["blob_id"] == BLOB_ID


def _drive(app: Any, path: str) -> list[dict[str, Any]]:
    sent: list[dict[str, Any]] = []
    delivered = False

    async def receive() -> dict[str, Any]:
        nonlocal delivered
        if not delivered:
            delivered = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await asyncio.sleep(3600)
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    scope = {
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1", "method": "GET", "scheme": "http", "path": path,
        "raw_path": path.encode(), "query_string": b"", "root_path": "",
        "headers": [(b"host", b"testserver")], "client": ("127.0.0.1", 1),
        "server": ("testserver", 80),
    }

    async def run() -> None:
        try:
            await app(scope, receive, send)
        except BaseException:  # noqa: BLE001 - the abort is what is observed
            pass

    asyncio.run(run())
    return sent


def test_a_tampered_pdf_stops_short_of_its_declared_length() -> None:
    tampered = bytearray(DATA)
    tampered[-1] ^= 0xFF
    surface = Surface(_with_documents(), stored=bytes(tampered))
    sent = _drive(surface.app, f"/norm-documents/{NDOC}/content")
    start = next(message for message in sent if message["type"] == "http.response.start")
    assert start["status"] == 200
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    assert len(body) < len(DATA)
    assert len(DATA) - len(body) == (len(DATA) % CONTENT_CHUNK_BYTES or CONTENT_CHUNK_BYTES)


# --- the designation, at the adapter -------------------------------------------------------


def _designation_db() -> FakeNorms:
    database = FakeNorms()
    database.snapshots = {
        SNAPSHOT: (True, True),
        OTHER: (True, True),
        "ns_01M2545JSD15ETSNNV904X994N": (False, True),
        "ns_01M2545JSD15ETSNNV904X995N": (True, False),
        "ns_01M2545JSD15ETSNNV904X996N": (False, False),
    }
    return database


def _refused(call) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call()
    return caught.value


def test_the_first_designation_writes_one_history_row() -> None:
    database = _designation_db()
    adapter = NormsSearchAdapter(database, timeout_ms=3000)  # type: ignore[arg-type]
    current = adapter.set_current_snapshot(
        norms_snapshot_id=SNAPSHOT, expected_current=None, user_uid=ADMIN
    )
    assert (current.norms_snapshot_id, current.designated_by) == (SNAPSHOT, ADMIN)
    assert current.designated_at == AT
    assert [(e.from_snapshot_id, e.to_snapshot_id) for e in database.events] == [(None, SNAPSHOT)]
    assert database.sent.index("lock") < database.sent.index("append_event")
    assert database.sent.index("append_event") < database.sent.index("insert_current")
    assert database.commits == 1


def test_an_already_current_target_is_a_replay_whatever_expected_says() -> None:
    database = _designation_db()
    database.designate(SNAPSHOT)
    adapter = NormsSearchAdapter(database, timeout_ms=3000)  # type: ignore[arg-type]
    for expected in (SNAPSHOT, None, OTHER):
        current = adapter.set_current_snapshot(
            norms_snapshot_id=SNAPSHOT, expected_current=expected, user_uid=ADMIN
        )
        assert current.norms_snapshot_id == SNAPSHOT
    assert len(database.events) == 1
    assert "append_event" not in database.sent


def test_a_stale_expected_current_is_a_conflict_and_writes_nothing() -> None:
    database = _designation_db()
    database.designate(SNAPSHOT)
    adapter = NormsSearchAdapter(database, timeout_ms=3000)  # type: ignore[arg-type]
    for stale in (None, "ns_01M2545JSD15ETSNNV904X994N"):
        error = _refused(lambda: adapter.set_current_snapshot(
            norms_snapshot_id=OTHER, expected_current=stale, user_uid=ADMIN
        ))
        assert (error.code, dict(error.detail_fields)) == (
            ErrorCode.CONFLICT, {"conflict_reason": "stale_current_snapshot"}
        )
    assert len(database.events) == 1
    current = adapter.set_current_snapshot(
        norms_snapshot_id=OTHER, expected_current=SNAPSHOT, user_uid=ADMIN
    )
    assert current.norms_snapshot_id == OTHER
    assert [(e.from_snapshot_id, e.to_snapshot_id) for e in database.events] == [
        (None, SNAPSHOT), (SNAPSHOT, OTHER)
    ]
    assert "update_current" in database.sent


@pytest.mark.parametrize(
    ("target", "kind"),
    [
        ("ns_01M2545JSD15ETSNNV904X994N", "norm_embedding_build"),
        ("ns_01M2545JSD15ETSNNV904X996N", "norm_embedding_build"),
        ("ns_01M2545JSD15ETSNNV904X995N", "norm_source"),
    ],
)
def test_a_target_that_does_not_qualify_is_refused_naming_the_missing_half(
    target: str, kind: str
) -> None:
    database = _designation_db()
    adapter = NormsSearchAdapter(database, timeout_ms=3000)  # type: ignore[arg-type]
    error = _refused(lambda: adapter.set_current_snapshot(
        norms_snapshot_id=target, expected_current=None, user_uid=ADMIN
    ))
    assert (error.code, dict(error.detail_fields)) == (
        ErrorCode.REQUIRED_NORM_UNAVAILABLE,
        {"reference_kind": kind, "norms_snapshot_id": target},
    )
    assert database.events == []


def test_an_unknown_target_is_not_found() -> None:
    database = _designation_db()
    adapter = NormsSearchAdapter(database, timeout_ms=3000)  # type: ignore[arg-type]
    error = _refused(lambda: adapter.set_current_snapshot(
        norms_snapshot_id=NEVER, expected_current=None, user_uid=ADMIN
    ))
    assert (error.code, dict(error.detail_fields)) == (
        ErrorCode.NOT_FOUND, {"aggregate_type": "NormsSnapshot"}
    )


def test_the_listing_the_setter_and_the_pdf_read_share_one_predicate() -> None:
    """`listNormSnapshots.qualified`, the setter's refusal, ``content_available`` and the PDF
    read are one SQL text each, not four restatements that could drift apart. The window
    suite (``test_current_snapshot_window.py``) proves what that text selects."""
    from auditmanager.norms import current_snapshot as current_module
    from auditmanager.norms.search import service as service_module

    for statement in (current_module._QUALIFICATION, service_module._SNAPSHOTS):
        assert current_module.BUILD_COMPLETE_SQL in statement.text
        assert current_module.SOURCES_CONFIRMED_SQL in statement.text
    for statement in (service_module._DOCUMENT, service_module._PDF_BINDING):
        assert current_module.PDF_BINDING_SQL in statement.text
    assert current_module.PDF_BINDING_SQL in current_module.SOURCES_CONFIRMED_SQL
    assert current_module.QUALIFICATION_PARAMETERS == {
        "q_embedding_profile": "bge-m3-dense-v1",
        "q_reliable_chunking": "characters-v2:%",
        "q_role": "norm_source",
        "q_target_kind": "norm_document",
        "q_anchor_kind": "pdf",
    }
    # Every search statement names the reliability literal the partial indexes need.
    from auditmanager.norms.search.query import ParsedQuery

    for parsed in (ParsedQuery("СП 54", "7.1", "здания"), ParsedQuery("СП 54", None, None)):
        for sql in (service_module._ranked_sql(parsed), service_module._ordered_sql(parsed)):
            assert "p.text_reliability = 'reliable'" in sql
            assert "LIMIT :search_window" in sql
    assert service_module.SEARCH_WINDOW == 1000
