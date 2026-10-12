"""``S3BlobStore.open_stream`` without a container (`W55A-CONTENT-01`, ``R-115``).

The real-service half is ``test_streamed_read.py`` and runs in the owner's window. These
drive the same adapter code through an in-memory stand-in for the one S3 call a streamed
read makes -- ``GetObject``, with or without ``Range`` -- which answers the way S3 answers
(``ContentLength``, ``ContentRange``, the recorded metadata, ``404`` and ``416``) and counts
every body byte it hands over. It has no opinion; the counting is the evidence.

What is proved, each by a case that fails without the behaviour:

* a windowed read asks the store for the window and transfers nothing else -- the object
  is never loaded;
* a whole read holds its last chunk back until the digest matches, and on a tampered
  object (same length, intact metadata) stops short and logs ``storage_integrity_error``;
* every refusal that can be made from the response's headers is raised by ``open_stream``
  itself, before a body byte is consumed;
* a body that ends early or runs long stops the stream rather than finishing it.
"""

from __future__ import annotations

import hashlib
import io
import logging
from typing import Any

import pytest
from botocore.exceptions import ClientError

from auditmanager.storage import (
    BlobMetadataInvalidError,
    BlobNotFoundError,
    ChecksumMismatchError,
    DurablePublicationStore,
    S3BlobStore,
    S3StorageSettings,
    SizeMismatchError,
    StorageCredentialRefusedError,
    StorageUnavailableError,
    derive_blob_id,
)
from auditmanager.storage._object_layout import canonical_key

CHUNK = 16
#: Five chunks and a short sixth, so "the last chunk" is distinguishable from "a chunk".
DATA = bytes(range(256))[:90]
DIGEST = hashlib.sha256(DATA).hexdigest()


class CountingBody(io.BytesIO):
    """A ``StreamingBody`` stand-in that records how many bytes were handed over."""

    def __init__(self, data: bytes, *, short_by: int = 0, extra: bytes = b"") -> None:
        super().__init__(data[: len(data) - short_by] + extra)
        self.handed_over = 0
        self.closed_by_reader = False

    def read(self, size: int | None = -1) -> bytes:  # type: ignore[override]
        chunk = super().read(size)
        self.handed_over += len(chunk)
        return chunk

    def close(self) -> None:
        self.closed_by_reader = True
        super().close()


class StreamingS3:
    """One canonical object and the ``GetObject`` S3 answers for it."""

    def __init__(self, data: bytes = DATA, *, metadata: dict[str, str] | None = None) -> None:
        self.data = data
        self.metadata = (
            {"content-sha256": hashlib.sha256(data).hexdigest(), "content-size": str(len(data))}
            if metadata is None
            else metadata
        )
        self.requests: list[dict[str, Any]] = []
        self.bodies: list[CountingBody] = []
        self.refuse: str | None = None
        self.ignore_range = False
        self.short_by = 0
        self.extra = b""

    def get_object(self, **request: Any) -> dict[str, Any]:
        self.requests.append(request)
        if self.refuse is not None:
            status = {"NoSuchKey": 404, "AccessDenied": 403, "InvalidRange": 416}[self.refuse]
            raise ClientError(
                {"Error": {"Code": self.refuse}, "ResponseMetadata": {"HTTPStatusCode": status}},
                "GetObject",
            )
        header = request.get("Range")
        response: dict[str, Any] = {"Metadata": dict(self.metadata)}
        if header is None or self.ignore_range:
            payload = self.data
            response["ContentLength"] = len(payload)
        else:
            first, last = (int(part) for part in header.removeprefix("bytes=").split("-"))
            if first >= len(self.data):
                raise ClientError(
                    {"Error": {"Code": "InvalidRange"},
                     "ResponseMetadata": {"HTTPStatusCode": 416}},
                    "GetObject",
                )
            last = min(last, len(self.data) - 1)
            payload = self.data[first : last + 1]
            response["ContentLength"] = len(payload)
            response["ContentRange"] = f"bytes {first}-{last}/{len(self.data)}"
        body = CountingBody(payload, short_by=self.short_by, extra=self.extra)
        self.bodies.append(body)
        response["Body"] = body
        return response


def _store(client: StreamingS3) -> S3BlobStore:
    settings = S3StorageSettings(
        endpoint_url="http://127.0.0.1:1",
        region="us-east-1",
        bucket="offline-bucket",
        access_key_id="offline",
        secret_access_key="offline",
    )
    return S3BlobStore(settings, client=client)


BLOB_ID = derive_blob_id(sha256=DIGEST, size=len(DATA))


def _open(store: Any, *, window: tuple[int, int] | None = None, **overrides: Any):
    arguments: dict[str, Any] = {
        "expected_sha256": DIGEST,
        "expected_size": len(DATA),
        "window": window,
        "chunk_size": CHUNK,
    }
    arguments.update(overrides)
    return store.open_stream(BLOB_ID, **arguments)


# --- a window is the only thing transferred ---------------------------------------------


def test_a_windowed_read_requests_the_window_and_transfers_nothing_else() -> None:
    client = StreamingS3()
    chunks = list(_open(_store(client), window=(20, 59)))
    assert b"".join(chunks) == DATA[20:60]
    assert all(len(chunk) <= CHUNK for chunk in chunks)
    assert [request.get("Range") for request in client.requests] == ["bytes=20-59"]
    assert client.requests[0]["Key"] == canonical_key(BLOB_ID)
    # The evidence that the object was never loaded: the store handed over the window.
    assert [body.handed_over for body in client.bodies] == [40]


def test_a_windowed_read_of_a_tampered_object_relies_on_recorded_verification() -> None:
    """``R-115``: a window cannot hash an object it does not read. Same length, intact
    metadata, different bytes: the window is served as stored. The whole read below is
    the one that catches it."""
    tampered = bytes(reversed(DATA))
    client = StreamingS3(tampered, metadata=StreamingS3().metadata)
    assert b"".join(_open(_store(client), window=(0, 9))) == tampered[:10]


def test_nothing_is_requested_before_open_and_nothing_read_until_iterated() -> None:
    client = StreamingS3()
    stream = _open(_store(client))
    assert len(client.requests) == 1, "open_stream issues exactly the one GetObject"
    assert client.bodies[0].handed_over == 0, "the body was read before it was asked for"
    assert next(stream) == DATA[:CHUNK]
    stream.close()
    assert client.bodies[0].closed_by_reader


# --- the whole read holds its last chunk back -------------------------------------------


def test_a_whole_read_streams_every_byte_in_bounded_chunks() -> None:
    client = StreamingS3()
    chunks = list(_open(_store(client)))
    assert b"".join(chunks) == DATA
    assert [len(chunk) for chunk in chunks] == [16, 16, 16, 16, 16, 10]
    assert client.requests[0].get("Range") is None
    assert client.bodies[0].closed_by_reader


def test_the_last_chunk_is_yielded_only_after_the_whole_body_was_hashed() -> None:
    client = StreamingS3()
    stream = _open(_store(client))
    seen: list[bytes] = []
    for chunk in stream:
        seen.append(chunk)
        if len(seen) == 5:
            # Five chunks out; the sixth was already read (it is what released the
            # fifth), so the store has handed over everything while the client lacks it.
            assert client.bodies[0].handed_over == len(DATA)
            assert b"".join(seen) == DATA[:80]
    assert b"".join(seen) == DATA


def test_a_tampered_object_stops_short_and_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    """The fault two declarations cannot see: the body replaced, its length and recorded
    metadata intact. Every chunk but the last reaches the consumer; the last is withheld
    and the stream raises, so a consumer that declared ``len(DATA)`` delivers less."""
    tampered = DATA[:-1] + bytes([DATA[-1] ^ 0xFF])
    client = StreamingS3(tampered, metadata=StreamingS3().metadata)
    delivered = bytearray()
    with caplog.at_level(logging.ERROR, logger="auditmanager.storage.s3"):
        with pytest.raises(ChecksumMismatchError) as raised:
            for chunk in _open(_store(client)):
                delivered.extend(chunk)
    assert bytes(delivered) == tampered[:80]
    assert len(delivered) < len(DATA)
    assert raised.value.details == {
        "expected_sha256": DIGEST,
        "actual_sha256": hashlib.sha256(tampered).hexdigest(),
    }
    records = [r for r in caplog.records if "storage_integrity_error" in r.getMessage()]
    assert len(records) == 1
    message = records[0].getMessage()
    assert "stopped after 80 of 90 declared bytes" in message
    assert "offline-bucket" not in message and canonical_key(BLOB_ID) not in message
    assert client.bodies[0].closed_by_reader


def test_a_single_chunk_object_that_is_tampered_delivers_nothing() -> None:
    tampered = b"%PDF-short but wrong"
    honest = b"%PDF-short and right"
    client = StreamingS3(tampered, metadata=StreamingS3(honest).metadata)
    delivered = bytearray()
    with pytest.raises(ChecksumMismatchError):
        for chunk in _open(
            _store(client),
            expected_sha256=hashlib.sha256(honest).hexdigest(),
            expected_size=len(honest),
            chunk_size=1024,
        ):
            delivered.extend(chunk)
    assert delivered == b""


# --- refusals happen at open -------------------------------------------------------------


@pytest.mark.parametrize(
    ("refusal", "raised"),
    (
        ("NoSuchKey", BlobNotFoundError),
        ("AccessDenied", StorageCredentialRefusedError),
    ),
)
def test_a_store_refusal_is_raised_by_open_not_by_the_iterator(refusal, raised) -> None:
    client = StreamingS3()
    client.refuse = refusal
    with pytest.raises(raised):
        _open(_store(client))


def test_an_object_with_no_recorded_digest_is_refused_at_open() -> None:
    client = StreamingS3(metadata={})
    with pytest.raises(BlobMetadataInvalidError):
        _open(_store(client))
    assert client.bodies[0].handed_over == 0 and client.bodies[0].closed_by_reader


@pytest.mark.parametrize("window", (None, (0, 9)), ids=("whole", "window"))
def test_a_recorded_digest_other_than_the_declared_one_is_refused_at_open(window) -> None:
    other = "0" * 64
    client = StreamingS3(metadata={"content-sha256": other})
    with pytest.raises(ChecksumMismatchError) as raised:
        _open(_store(client), window=window)
    assert raised.value.details == {"expected_sha256": DIGEST, "actual_sha256": other}
    assert client.bodies[0].handed_over == 0


def test_a_stored_size_other_than_the_declared_one_is_refused_at_open() -> None:
    longer = DATA + b"!"
    client = StreamingS3(longer, metadata=StreamingS3().metadata)
    with pytest.raises(SizeMismatchError):
        _open(_store(client))
    with pytest.raises(SizeMismatchError):
        _open(_store(client), window=(0, 9))  # the total after the slash disagrees


def test_a_window_past_the_end_of_a_shorter_object_is_a_size_mismatch() -> None:
    shorter = DATA[:50]
    client = StreamingS3(shorter, metadata=StreamingS3().metadata)
    with pytest.raises(SizeMismatchError):
        _open(_store(client), window=(60, 89))


def test_a_store_that_ignores_the_range_is_refused_rather_than_sliced() -> None:
    client = StreamingS3()
    client.ignore_range = True
    with pytest.raises(StorageUnavailableError):
        _open(_store(client), window=(10, 19))
    assert client.bodies[0].handed_over == 0


def test_a_window_outside_the_declared_size_is_a_caller_error() -> None:
    client = StreamingS3()
    for window in ((0, 90), (10, 9), (-1, 5)):
        with pytest.raises(ValueError):
            _open(_store(client), window=window)
    assert client.requests == [], "nothing may be requested for an unresolved window"


# --- a body that ends early or runs long stops the stream --------------------------------


@pytest.mark.parametrize("window", (None, (0, 49)), ids=("whole", "window"))
def test_a_body_that_ends_early_stops_the_stream(window) -> None:
    client = StreamingS3()
    client.short_by = 5
    with pytest.raises(SizeMismatchError):
        list(_open(_store(client), window=window))


def test_a_window_body_that_runs_long_stops_the_stream() -> None:
    client = StreamingS3()
    client.extra = b"x" * 3
    delivered = bytearray()
    with pytest.raises(SizeMismatchError):
        for chunk in _open(_store(client), window=(0, 31)):
            delivered.extend(chunk)
    assert bytes(delivered) == DATA[:32]


# --- the decorator delegates -------------------------------------------------------------


def test_the_durable_publication_store_delegates_the_streamed_read() -> None:
    client = StreamingS3()

    def refuse(*_: Any) -> Any:  # pragma: no cover - a read never journals
        raise AssertionError("a streamed read must not journal anything")

    durable = DurablePublicationStore(
        _store(client), before_stage=refuse, before_publish=refuse
    )
    assert b"".join(_open(durable, window=(5, 14))) == DATA[5:15]
    assert client.requests[0]["Range"] == "bytes=5-14"
