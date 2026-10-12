"""``streamDocumentVersionContent`` over real PostgreSQL and real MinIO (`W55A-CONTENT-01`).

The container-free half is ``test_document_content_streaming.py``; this one runs in the
owner's window (``R-102``, ``R-111``), on the suite's own fixtures: a version published
through ``uploadDocument``, then read back through the application with the bearer
credential the suite presents.

* a ranged read is answered from a ranged ``GetObject``: MinIO's own ``ContentRange`` is
  what the adapter checks, so this is the case the in-memory stand-in cannot prove;
* the canonical object's body replaced under intact metadata and the same length -- the
  fault ``W11-RD`` measured -- answers ``200`` with the declared ``Content-Length`` and a
  short body (the source is one chunk, so nothing of it), and the stream aborts;
* a window of that same tampered object is served as stored: ``R-115`` lets a ``206`` rely
  on the recorded verification.

The PDF is made unique per test, so its content-addressed object is this test's alone and
can be tampered with and purged without touching another test's bytes.
"""

from __future__ import annotations

import asyncio
import json
import secrets
from typing import Any, Iterator

import boto3
import pytest
from botocore.client import Config

from auditmanager.storage import S3BlobStore, S3StorageSettings, derive_blob_id, sha256_of
from auditmanager.storage._object_layout import canonical_key
from w13_api_driver import TEST_TOKEN, Request, Surface, dispatch

BOUNDARY = "----w55acontent"


def _unique_pdf(baseline: bytes) -> bytes:
    """The baseline plus a comment after ``%%EOF``: still the same PDF to every reader."""
    return baseline + b"\n% " + secrets.token_hex(16).encode("ascii") + b"\n"


def _upload_body(content: bytes) -> bytes:
    return b"".join(
        (
            (
                f"--{BOUNDARY}\r\n"
                'Content-Disposition: form-data; name="file"; filename="content.pdf"\r\n'
                "Content-Type: application/pdf\r\n\r\n"
            ).encode("utf-8"),
            content,
            f"\r\n--{BOUNDARY}--\r\n".encode("utf-8"),
        )
    )


def _ok(answer: Any) -> dict[str, Any]:
    assert answer.status < 300, (answer.status, answer.body)
    return json.loads(answer.body)


@pytest.fixture
def raw_s3(store: S3BlobStore) -> Any:
    """A plain boto3 client on the suite's own bucket, independent of the adapter."""
    settings: S3StorageSettings = store._settings
    return boto3.client(
        "s3",
        endpoint_url=settings.endpoint_url,
        region_name=settings.region,
        aws_access_key_id=settings.access_key_id,
        aws_secret_access_key=settings.secret_access_key,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


@pytest.fixture
def published(
    router: Surface, store: S3BlobStore, corpus_pdf: bytes
) -> Iterator[tuple[dict[str, Any], bytes]]:
    content = _unique_pdf(corpus_pdf)
    project = _ok(
        dispatch(
            router,
            Request.build(
                "POST",
                "/projects",
                headers={"Idempotency-Key": f"w55a-content-{secrets.token_hex(4)}",
                         "Content-Type": "application/json"},
                body=json.dumps({"name": "Содержимое"}).encode("utf-8"),
            ),
        )
    )
    version = _ok(
        dispatch(
            router,
            Request.build(
                "POST",
                f"/projects/{project['project_uid']}/documents",
                headers={
                    "Idempotency-Key": f"w55a-content-{secrets.token_hex(4)}",
                    "Content-Type": f"multipart/form-data; boundary={BOUNDARY}",
                },
                body=_upload_body(content),
            ),
        )
    )
    try:
        yield version, content
    finally:
        store._purge_published(derive_blob_id(sha256=sha256_of(content), size=len(content)))


def _tamper(raw_s3: Any, store: S3BlobStore, content: bytes) -> bytes:
    """Replace the canonical body, same length, metadata copied verbatim."""
    key = canonical_key(derive_blob_id(sha256=sha256_of(content), size=len(content)))
    bucket = store._bucket
    head = raw_s3.head_object(Bucket=bucket, Key=key)
    tampered = content[:-2] + b"X\n"
    assert len(tampered) == len(content) and tampered != content
    raw_s3.put_object(
        Bucket=bucket, Key=key, Body=tampered,
        ContentType=head["ContentType"], Metadata=head["Metadata"],
    )
    after = raw_s3.head_object(Bucket=bucket, Key=key)
    assert after["Metadata"] == head["Metadata"] and after["ContentLength"] == len(content)
    return tampered


def _drive(surface: Surface, path: str) -> tuple[list[dict[str, Any]], BaseException | None]:
    """One authenticated GET through the ASGI app, every message recorded."""
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
        "headers": [
            (b"host", b"testserver"),
            (b"authorization", f"Bearer {TEST_TOKEN}".encode("latin-1")),
        ],
        "client": ("127.0.0.1", 1), "server": ("testserver", 80),
    }

    async def run() -> None:
        nonlocal failure
        try:
            await surface.app(scope, receive, send)
        except BaseException as exc:  # noqa: BLE001 - the abort is what is observed
            failure = exc

    asyncio.run(run())
    return sent, failure


def test_a_ranged_read_is_answered_from_a_ranged_get(
    router: Surface, published: tuple[dict[str, Any], bytes]
) -> None:
    version, content = published
    answer = dispatch(
        router,
        Request.build(
            "GET", f"/versions/{version['version_uid']}/content",
            headers={"Range": "bytes=100-163"},
        ),
    )
    assert answer.status == 206
    assert answer.body == content[100:164]
    assert answer.header("Content-Range") == f"bytes 100-163/{len(content)}"
    assert answer.header("Content-Length") == "64"


def test_a_tampered_object_answers_a_short_body(
    router: Surface,
    published: tuple[dict[str, Any], bytes],
    raw_s3: Any,
    store: S3BlobStore,
    caplog: pytest.LogCaptureFixture,
) -> None:
    version, content = published
    _tamper(raw_s3, store, content)
    with caplog.at_level("ERROR", logger="auditmanager.storage.s3"):
        sent, failure = _drive(router, f"/versions/{version['version_uid']}/content")
    start = sent[0]
    assert start["type"] == "http.response.start" and start["status"] == 200
    assert (b"Content-Length", str(len(content)).encode()) in start["headers"]
    bodies = [m for m in sent if m["type"] == "http.response.body"]
    delivered = b"".join(m["body"] for m in bodies)
    assert len(delivered) < len(content)
    assert not any(m.get("more_body") is False for m in bodies)
    assert failure is not None
    assert any("storage_integrity_error" in r.getMessage() for r in caplog.records)


def test_a_window_of_a_tampered_object_relies_on_recorded_verification(
    router: Surface,
    published: tuple[dict[str, Any], bytes],
    raw_s3: Any,
    store: S3BlobStore,
) -> None:
    version, content = published
    tampered = _tamper(raw_s3, store, content)
    last = len(content) - 1
    answer = dispatch(
        router,
        Request.build(
            "GET", f"/versions/{version['version_uid']}/content",
            headers={"Range": f"bytes={last - 9}-{last}"},
        ),
    )
    assert answer.status == 206
    assert answer.body == tampered[-10:]
