"""Repeated publication of identical verified content.

``machines.blob.retry`` in the frozen domain contract: "Re-uploading identical
content is idempotent by ``(sha256, size)`` and never mutates an available
blob." This package satisfies that by deriving ``blob_id`` from those two
values, so the second publication resolves to the same identity, finds the
canonical object already present and returns it without rewriting anything.

Documented consequences, each asserted below:

* identical bytes published twice produce one object and one ``blob_id``;
* the second publication does not touch the stored object at all, proved with
  an out-of-band witness rather than with a one-second-resolution timestamp;
* the temporary object of the second attempt is still cleaned up;
* re-publishing identical bytes under a *different* role or media type is a
  typed conflict, not a silent reinterpretation of an immutable blob.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.storage import (
    ROLE_SOURCE_DOCUMENT,
    BlobAttributeConflictError,
    BlobState,
    S3BlobStore,
    derive_blob_id,
    parse_blob_role,
    sha256_of,
)

# Reaching into the adapter's private layout is deliberate and confined to this
# one assertion: it is the only way to stamp the canonical object out-of-band,
# and importing the module beats copying the layout into a test.
from auditmanager.storage._object_layout import canonical_key

REPEATED = b"%PDF-1.7\nidentical verified content, published more than once\n"


def test_identical_content_publishes_once(
    store: S3BlobStore, blobs: list, bucket_keys: Any
) -> None:
    first = store.put_blob(
        REPEATED,
        declared_sha256=sha256_of(REPEATED),
        declared_size=len(REPEATED),
        role=ROLE_SOURCE_DOCUMENT,
        media_type="application/pdf",
    )
    blobs.append(first.blob_id)
    after_first = bucket_keys()

    second = store.put_blob(
        REPEATED,
        declared_sha256=sha256_of(REPEATED),
        declared_size=len(REPEATED),
        role=ROLE_SOURCE_DOCUMENT,
        media_type="application/pdf",
    )

    assert second.blob_id == first.blob_id
    assert second == first
    assert bucket_keys() == after_first, "the second publication changed the bucket"


def test_the_second_publication_does_not_rewrite_available_bytes(
    store: S3BlobStore, blobs: list, raw_s3: Any, settings: Any
) -> None:
    """Available bytes are immutable. Re-publishing must not touch them.

    Proved with a witness rather than with a timestamp. ``LastModified`` has
    one-second resolution, so two publications inside the same second look
    identical even when the second one really did rewrite the object. Instead
    the canonical object is stamped out-of-band with a marker the adapter never
    writes; if the second publication rewrites the object, the marker is gone.
    """
    payload = REPEATED + b"immutability\n"
    first = store.put_blob(
        payload,
        declared_sha256=sha256_of(payload),
        declared_size=len(payload),
        role=ROLE_SOURCE_DOCUMENT,
        media_type="application/pdf",
    )
    blobs.append(first.blob_id)

    canonical = canonical_key(first.blob_id)
    head = raw_s3.head_object(Bucket=settings.bucket, Key=canonical)
    witness = dict(head["Metadata"])
    witness["a3-witness"] = "not-written-by-the-adapter"
    raw_s3.copy_object(
        Bucket=settings.bucket,
        Key=canonical,
        CopySource={"Bucket": settings.bucket, "Key": canonical},
        MetadataDirective="REPLACE",
        ContentType=head["ContentType"],
        Metadata=witness,
    )

    second = store.put_blob(
        payload,
        declared_sha256=sha256_of(payload),
        declared_size=len(payload),
        role=ROLE_SOURCE_DOCUMENT,
        media_type="application/pdf",
    )

    after = raw_s3.head_object(Bucket=settings.bucket, Key=canonical)
    assert after["Metadata"].get("a3-witness") == "not-written-by-the-adapter", (
        "the second publication rewrote an available object"
    )
    assert second.blob_id == first.blob_id
    assert store.read(first.blob_id) == payload
    assert store.inspect(first.blob_id).state is BlobState.AVAILABLE


def test_repeated_publication_leaves_no_temporary_object(
    store: S3BlobStore, blobs: list, bucket_keys: Any
) -> None:
    payload = REPEATED + b"no residue\n"
    for _ in range(3):
        published = store.put_blob(
            payload,
            declared_sha256=sha256_of(payload),
            declared_size=len(payload),
            role=ROLE_SOURCE_DOCUMENT,
            media_type="application/pdf",
        )
    blobs.append(published.blob_id)
    assert [key for key in bucket_keys() if key.startswith("temporary/")] == []


def test_identity_is_a_pure_function_of_sha256_and_size(
    store: S3BlobStore, blobs: list
) -> None:
    published = store.put_blob(
        REPEATED,
        declared_sha256=sha256_of(REPEATED),
        declared_size=len(REPEATED),
        role=ROLE_SOURCE_DOCUMENT,
        media_type="application/pdf",
    )
    blobs.append(published.blob_id)
    assert published.blob_id == derive_blob_id(
        sha256=sha256_of(REPEATED), size=len(REPEATED)
    )
    # Different content, different identity.
    assert published.blob_id != derive_blob_id(
        sha256=sha256_of(REPEATED + b"x"), size=len(REPEATED) + 1
    )


def test_republishing_under_a_different_role_is_refused(
    store: S3BlobStore, blobs: list, bucket_keys: Any
) -> None:
    payload = REPEATED + b"role conflict\n"
    published = store.put_blob(
        payload,
        declared_sha256=sha256_of(payload),
        declared_size=len(payload),
        role=ROLE_SOURCE_DOCUMENT,
        media_type="application/pdf",
    )
    blobs.append(published.blob_id)
    after_first = bucket_keys()

    with pytest.raises(BlobAttributeConflictError):
        store.put_blob(
            payload,
            declared_sha256=sha256_of(payload),
            declared_size=len(payload),
            role=parse_blob_role("extracted_text"),
            media_type="application/pdf",
        )

    # The refusal changed nothing: the original record and bytes stand, and
    # the conflicting attempt left no temporary object behind.
    assert bucket_keys() == after_first
    assert store.inspect(published.blob_id) == published


def test_republishing_under_a_different_media_type_is_refused(
    store: S3BlobStore, blobs: list
) -> None:
    payload = REPEATED + b"media type conflict\n"
    published = store.put_blob(
        payload,
        declared_sha256=sha256_of(payload),
        declared_size=len(payload),
        role=ROLE_SOURCE_DOCUMENT,
        media_type="application/pdf",
    )
    blobs.append(published.blob_id)

    with pytest.raises(BlobAttributeConflictError):
        store.put_blob(
            payload,
            declared_sha256=sha256_of(payload),
            declared_size=len(payload),
            role=ROLE_SOURCE_DOCUMENT,
            media_type="text/plain",
        )
    assert store.inspect(published.blob_id).media_type == "application/pdf"
