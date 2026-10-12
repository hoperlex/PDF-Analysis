"""``S3BlobStore.open_stream`` against a real S3-compatible service (`W55A-CONTENT-01`).

Runs in the owner's window with the rest of this directory (``R-102``, ``R-111``). The
decision table is proved offline in ``test_streamed_read_offline.py``; these cases prove
what only the real service can say: that MinIO answers a ranged ``GetObject`` with the
``ContentRange`` the adapter checks, ``InvalidRange`` past the end, and that a body
replaced under intact metadata is stopped short on a whole read.
"""

from __future__ import annotations

import hashlib
from typing import Any

import pytest

from auditmanager.storage import (
    BlobNotFoundError,
    ChecksumMismatchError,
    S3BlobStore,
    S3StorageSettings,
    SizeMismatchError,
    derive_blob_id,
    sha256_of,
)
from auditmanager.storage._object_layout import canonical_key

CHUNK = 64 * 1024
#: Three whole chunks and a short fourth.
CONTENT = b"%PDF-1.7\n" + bytes(range(256)) * 800


def _open(store: S3BlobStore, blob_id: Any, data: bytes = CONTENT, **kwargs: Any):
    return store.open_stream(
        blob_id,
        expected_sha256=sha256_of(data),
        expected_size=len(data),
        chunk_size=CHUNK,
        **kwargs,
    )


def test_a_whole_read_streams_the_published_bytes(store: S3BlobStore, publish: Any) -> None:
    published = publish(CONTENT)
    chunks = list(_open(store, published.blob_id))
    assert b"".join(chunks) == CONTENT
    assert max(len(chunk) for chunk in chunks) <= CHUNK


@pytest.mark.parametrize("window", ((0, 0), (100, 163), (CHUNK - 1, CHUNK + 1)))
def test_a_window_is_served_from_a_ranged_get(
    store: S3BlobStore, publish: Any, window: tuple[int, int]
) -> None:
    published = publish(CONTENT)
    first, last = window
    assert b"".join(_open(store, published.blob_id, window=window)) == CONTENT[first : last + 1]


def test_an_absent_object_is_refused_at_open(store: S3BlobStore) -> None:
    absent = derive_blob_id(sha256=hashlib.sha256(b"never published").hexdigest(), size=15)
    with pytest.raises(BlobNotFoundError):
        store.open_stream(
            absent,
            expected_sha256=hashlib.sha256(b"never published").hexdigest(),
            expected_size=15,
        )


def _replace_body(
    raw_s3: Any, settings: S3StorageSettings, blob_id: Any, body: bytes
) -> None:
    """New bytes under the canonical key, the recorded metadata copied verbatim."""
    key = canonical_key(blob_id)
    head = raw_s3.head_object(Bucket=settings.bucket, Key=key)
    raw_s3.put_object(
        Bucket=settings.bucket, Key=key, Body=body,
        ContentType=head["ContentType"], Metadata=head["Metadata"],
    )


def test_a_tampered_body_stops_a_whole_read_short(
    store: S3BlobStore, publish: Any, raw_s3: Any, settings: S3StorageSettings
) -> None:
    published = publish(CONTENT)
    tampered = CONTENT[:-1] + bytes([CONTENT[-1] ^ 0xFF])
    _replace_body(raw_s3, settings, published.blob_id, tampered)
    delivered = bytearray()
    with pytest.raises(ChecksumMismatchError):
        for chunk in _open(store, published.blob_id):
            delivered.extend(chunk)
    # Every chunk but the last: a strict prefix, short by at most one chunk.
    assert tampered.startswith(bytes(delivered))
    assert len(CONTENT) - CHUNK <= len(delivered) < len(CONTENT)
    # The window of the same object relies on recorded verification (R-115).
    window = (len(CONTENT) - 10, len(CONTENT) - 1)
    assert b"".join(_open(store, published.blob_id, window=window)) == tampered[-10:]


def test_a_shorter_body_is_a_size_mismatch_at_open(
    store: S3BlobStore, publish: Any, raw_s3: Any, settings: S3StorageSettings
) -> None:
    published = publish(CONTENT)
    _replace_body(raw_s3, settings, published.blob_id, CONTENT[:1000])
    with pytest.raises(SizeMismatchError):
        _open(store, published.blob_id)
    with pytest.raises(SizeMismatchError):
        _open(store, published.blob_id, window=(10, 19))  # total after the slash
    with pytest.raises(SizeMismatchError):
        _open(store, published.blob_id, window=(2000, 2009))  # InvalidRange
