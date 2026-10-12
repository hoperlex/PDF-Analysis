"""``streamDocumentVersionContent`` streams, without a container (`W55A-CONTENT-01`).

Plan section A3.5, owner ruling ``R-115``. The operation is driven through FastAPI -- the
document routes, the exception handlers, ``FailureEnvelopeMiddleware`` and the correlation
middleware -- over the **shipped** ``DocumentAdapter`` and ``IngestService`` and the real
``S3BlobStore``. Only the two edges are stood in for: the manifest lookup (one published
version, or ``not_found``) and the S3 client (one ``GetObject``, counting every body byte it
hands over). The database- and MinIO-backed half is ``test_document_content_window.py``.

Each case fails without the change it names:

* a ranged read asks the store for the window and receives only the window -- the object
  is never loaded, which slicing ``read_content`` did;
* an unsatisfiable range is ``422`` before the store is touched, and a malformed one on an
  unknown version is still ``404``;
* a storage failure is a typed envelope (``500`` for a refused credential, record 31's
  shape; ``422 storage_integrity_error`` for an absent object), because the object is
  opened before the status line;
* a tampered object's whole read answers ``200`` with the declared ``Content-Length`` and a
  **short body** -- the last chunk held back -- and logs ``storage_integrity_error``;
* the header lists are records 14's and 15's, in their order.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import logging
from datetime import datetime, timezone
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
from auditmanager.api.routers.documents import build_document_routes
from auditmanager.api.schemas.content import CONTENT_CHUNK_BYTES
from auditmanager.bootstrap.adapters import DocumentAdapter
from auditmanager.documents.models import (
    MANIFEST_ROLE_SOURCE_DOCUMENT,
    DocumentVersionRecord,
    ManifestEntry,
)
from auditmanager.ingest.service import IngestService
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid
from auditmanager.storage import S3BlobStore, S3StorageSettings, derive_blob_id

VERSION_UID = "ver_01M2545JSD15ETSNNV904X991J"
UNKNOWN_UID = "ver_01M2545JSD15ETSNNV904X991K"

#: Three chunks and a short fourth at 256 KiB, so the held-back chunk is not the whole body.
DATA = b"%PDF-1.7\n" + bytes(range(256)) * 3500
DIGEST = hashlib.sha256(DATA).hexdigest()
BLOB_ID = derive_blob_id(sha256=DIGEST, size=len(DATA))
LAST_CHUNK = len(DATA) % CONTENT_CHUNK_BYTES or CONTENT_CHUNK_BYTES


class CountingBody(io.BytesIO):
    def __init__(self, data: bytes) -> None:
        super().__init__(data)
        self.reads: list[int] = []

    def read(self, size: int | None = -1) -> bytes:  # type: ignore[override]
        chunk = super().read(size)
        self.reads.append(len(chunk))
        return chunk


class StreamingS3:
    """The ``GetObject`` S3 answers for one canonical object."""

    def __init__(self, stored: bytes = DATA) -> None:
        self.stored = stored
        # The metadata publication wrote, for the *declared* bytes: a body replaced under
        # intact metadata is the fault only a hash of the body can see.
        self.metadata = {"content-sha256": DIGEST, "content-size": str(len(DATA))}
        self.requests: list[dict[str, Any]] = []
        self.bodies: list[CountingBody] = []
        self.refuse: str | None = None

    def get_object(self, **request: Any) -> dict[str, Any]:
        self.requests.append(request)
        if self.refuse is not None:
            status = {"NoSuchKey": 404, "AccessDenied": 403}[self.refuse]
            raise ClientError(
                {"Error": {"Code": self.refuse}, "ResponseMetadata": {"HTTPStatusCode": status}},
                "GetObject",
            )
        response: dict[str, Any] = {"Metadata": dict(self.metadata)}
        header = request.get("Range")
        if header is None:
            payload = self.stored
        else:
            first, last = (int(part) for part in header.removeprefix("bytes=").split("-"))
            payload = self.stored[first : last + 1]
            response["ContentRange"] = f"bytes {first}-{last}/{len(self.stored)}"
        response["ContentLength"] = len(payload)
        body = CountingBody(payload)
        self.bodies.append(body)
        response["Body"] = body
        return response


class _Session:
    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def close(self) -> None: ...


class _OneVersion:
    """The manifest lookup: one published version, ``not_found`` for anything else."""

    def __init__(self) -> None:
        self.record = DocumentVersionRecord(
            version_uid=VersionUid(VERSION_UID),
            document_uid=DocumentUid("doc_01M2545JSD15ETSNNV904X991D"),
            project_uid=ProjectUid("prj_01M2545JSD15ETSNNV904X991F"),
            version_ordinal=1,
            display_title="baseline.pdf",
            section=None,
            media_type="application/pdf",
            byte_size=len(DATA),
            sha256=DIGEST,
            page_count=1,
            published_at=datetime(2026, 10, 12, tzinfo=timezone.utc),
            manifest=(
                ManifestEntry(
                    role=MANIFEST_ROLE_SOURCE_DOCUMENT,
                    blob_id=BLOB_ID,
                    sha256=DIGEST,
                    size_bytes=len(DATA),
                    media_type="application/pdf",
                ),
            ),
        )
        self.lookups = 0

    def get_version(self, session: Any, version_uid: VersionUid) -> DocumentVersionRecord:
        self.lookups += 1
        if str(version_uid) != VERSION_UID:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="DocumentVersion")
        return self.record


class Surface:
    def __init__(self, stored: bytes = DATA) -> None:
        self.s3 = StreamingS3(stored)
        settings = S3StorageSettings(
            endpoint_url="http://127.0.0.1:1",
            region="us-east-1",
            bucket="offline-bucket",
            access_key_id="offline",
            secret_access_key="offline",
        )
        service = IngestService(
            S3BlobStore(settings, client=self.s3), session_factory=_Session  # type: ignore[arg-type]
        )
        self.versions = _OneVersion()
        service._documents = self.versions  # type: ignore[assignment]
        router = APIRouter()
        build_document_routes(router, DocumentAdapter(service))
        app = FastAPI()
        install_exception_handlers(app)
        app.include_router(router)
        app.add_middleware(FailureEnvelopeMiddleware)
        app.add_middleware(CorrelationMiddleware)
        self.app = app
        self.client = TestClient(app, raise_server_exceptions=False)

    def get(self, version_uid: str = VERSION_UID, range_header: str | None = None) -> Any:
        headers = {} if range_header is None else {"Range": range_header}
        return self.client.get(f"/versions/{version_uid}/content", headers=headers)


def _drive(app: Any, path: str) -> tuple[list[dict[str, Any]], BaseException | None]:
    """One request through the ASGI app with a recording ``send``.

    ``TestClient`` drops a body whose stream raised, so a response that stopped short is
    observed here, message by message, as a server would send it.
    """
    sent: list[dict[str, Any]] = []
    failure: BaseException | None = None
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
        nonlocal failure
        try:
            await app(scope, receive, send)
        except BaseException as exc:  # noqa: BLE001 - the abort is what is observed
            failure = exc

    asyncio.run(run())
    return sent, failure


def _names(response: Any) -> list[str]:
    return [name.decode("latin-1") for name, _ in response.headers.raw]


# --- the whole object: record 14 ----------------------------------------------------------


def test_the_whole_document_streams_in_bounded_chunks_with_record_14s_headers() -> None:
    surface = Surface()
    response = surface.get()
    assert response.status_code == 200
    assert response.content == DATA
    assert _names(response)[:3] == ["Content-Type", "Content-Length", "Accept-Ranges"]
    assert _names(response)[-1].lower() == "x-correlation-id" and len(_names(response)) == 4
    assert response.headers["Content-Type"] == "application/pdf"
    assert response.headers["Content-Length"] == str(len(DATA))
    assert response.headers["Accept-Ranges"] == "bytes"
    assert [request.get("Range") for request in surface.s3.requests] == [None]
    assert max(surface.s3.bodies[0].reads) <= CONTENT_CHUNK_BYTES


# --- a window: record 15 -----------------------------------------------------------------


def test_a_ranged_read_never_loads_the_object() -> None:
    surface = Surface()
    response = surface.get(range_header="bytes=100-163")
    assert response.status_code == 206
    assert response.content == DATA[100:164]
    assert _names(response)[:4] == [
        "Content-Type", "Content-Length", "Content-Range", "Accept-Ranges",
    ]
    assert response.headers["Content-Length"] == "64"
    assert response.headers["Content-Range"] == f"bytes 100-163/{len(DATA)}"
    # The store was asked for the window, once, and handed over exactly 64 bytes.
    assert [request.get("Range") for request in surface.s3.requests] == ["bytes=100-163"]
    assert sum(surface.s3.bodies[0].reads) == 64


@pytest.mark.parametrize(
    ("header", "window"),
    (
        ("bytes=-50", (len(DATA) - 50, len(DATA) - 1)),
        (f"bytes={len(DATA) - 10}-", (len(DATA) - 10, len(DATA) - 1)),
        ("bytes=0-99999999", (0, len(DATA) - 1)),
    ),
    ids=("suffix", "open-end", "clamped"),
)
def test_suffix_and_open_ranges_are_resolved_before_the_store_is_asked(header, window) -> None:
    surface = Surface()
    response = surface.get(range_header=header)
    first, last = window
    assert response.status_code == 206
    assert response.content == DATA[first : last + 1]
    assert surface.s3.requests[0]["Range"] == f"bytes={first}-{last}"


def test_a_window_relies_on_recorded_verification() -> None:
    """``R-115``: a window does not read the bytes it would have to hash, so a tampered
    object under intact metadata is served as stored. The whole read catches it."""
    tampered = bytes([DATA[0] ^ 0xFF]) + DATA[1:]
    response = Surface(tampered).get(range_header="bytes=0-9")
    assert response.status_code == 206
    assert response.content == tampered[:10]


# --- refusals before the status line -----------------------------------------------------


@pytest.mark.parametrize("header", ("bytes=99999999-", "bytes=50-10", "bytes=-0"))
def test_an_unsatisfiable_range_is_422_and_the_store_is_never_asked(header) -> None:
    surface = Surface()
    response = surface.get(range_header=header)
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_failed"
    assert body["details"] == {"field": "Range", "constraint": "unsatisfiable"}
    assert surface.s3.requests == []


@pytest.mark.parametrize("header", ("bytes=abc", "bytes=-", "bytes=0-9,20-29", "items=0-9"))
def test_a_malformed_range_is_422_format_without_touching_the_store(header) -> None:
    surface = Surface()
    response = surface.get(range_header=header)
    assert response.status_code == 422
    assert response.json()["details"] == {"field": "Range", "constraint": "format"}
    assert surface.s3.requests == []


@pytest.mark.parametrize("header", (None, "bytes=abc", "bytes=99999999-"))
def test_an_unknown_version_is_404_whatever_the_range_says(header) -> None:
    """The precedence the operation had when it read the version first."""
    surface = Surface()
    response = surface.get(UNKNOWN_UID, range_header=header)
    assert response.status_code == 404
    assert response.json()["error_code"] == "not_found"
    assert surface.s3.requests == []


def test_an_absent_object_is_a_typed_refusal_before_the_status_line() -> None:
    """The answer :meth:`IngestService.read_source_bytes` gives over the same row."""
    surface = Surface()
    surface.s3.refuse = "NoSuchKey"
    response = surface.get()
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "storage_integrity_error"
    assert body["details"] == {
        "blob_id": str(BLOB_ID),
        "role": MANIFEST_ROLE_SOURCE_DOCUMENT,
        "expected_sha256": DIGEST,
    }


def test_a_refused_storage_credential_keeps_record_31s_answer() -> None:
    surface = Surface()
    surface.s3.refuse = "AccessDenied"
    response = surface.get()
    assert response.status_code == 500
    assert _names(response)[:2] == ["Content-Type", "Content-Length"]
    assert _names(response)[-1].lower() == "x-correlation-id" and len(_names(response)) == 3
    assert response.headers["Content-Length"] == str(len(response.content))
    body = response.json()
    assert body["error_code"] == "dependency_credential_refused"
    assert body["retryable"] is False
    assert body["details"] == {"dependency": "blob_storage"}


# --- the held-back last chunk ------------------------------------------------------------


def test_a_tampered_whole_read_answers_a_short_body_and_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Same length, intact metadata, one byte different in the last chunk. The status
    line and ``Content-Length`` are already sent; every chunk but the last arrives, the
    last is withheld, and the response ends short of what it declared -- never closed as
    complete."""
    tampered = DATA[:-1] + bytes([DATA[-1] ^ 0xFF])
    surface = Surface(tampered)
    with caplog.at_level(logging.ERROR, logger="auditmanager.storage.s3"):
        sent, failure = _drive(surface.app, f"/versions/{VERSION_UID}/content")
    start = sent[0]
    assert start["type"] == "http.response.start" and start["status"] == 200
    assert (b"Content-Length", str(len(DATA)).encode()) in start["headers"]
    bodies = [m for m in sent if m["type"] == "http.response.body"]
    delivered = b"".join(m["body"] for m in bodies)
    assert delivered == tampered[: len(DATA) - LAST_CHUNK]
    assert len(delivered) < len(DATA)
    assert not any(m.get("more_body") is False for m in bodies), "closed as complete"
    assert failure is not None, "the stream must abort, not end"
    assert any("storage_integrity_error" in r.getMessage() for r in caplog.records)


def test_an_honest_whole_read_is_closed_as_complete() -> None:
    """The control for the case above: the same drive, untampered, ends cleanly."""
    sent, failure = _drive(Surface().app, f"/versions/{VERSION_UID}/content")
    bodies = [m for m in sent if m["type"] == "http.response.body"]
    assert failure is None
    assert b"".join(m["body"] for m in bodies) == DATA
    assert bodies[-1].get("more_body") is False


def test_a_tampered_first_chunk_still_withholds_the_last() -> None:
    """The digest is only known at the end, so earlier chunks have already gone; what
    the rule guarantees is that the client never holds the complete wrong document."""
    tampered = bytes([DATA[0] ^ 0xFF]) + DATA[1:]
    sent, failure = _drive(Surface(tampered).app, f"/versions/{VERSION_UID}/content")
    delivered = b"".join(m["body"] for m in sent if m["type"] == "http.response.body")
    assert sent[0]["status"] == 200 and failure is not None
    assert len(delivered) == len(DATA) - LAST_CHUNK
