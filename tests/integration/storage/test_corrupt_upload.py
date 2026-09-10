"""The central invariant: a mismatch leaves NOTHING canonical.

Every test here provokes a real failure against the real service and then
proves the guard fired, using an independent boto3 client rather than the
adapter's own inspection path. A guard with no test showing it can fire is not
a guard, so the assertions are about the *bucket*, not about the exception.
"""

from __future__ import annotations

import traceback
from typing import Any

import pytest

from auditmanager.storage import (
    ROLE_SOURCE_DOCUMENT,
    BlobIntegrityError,
    BlobNotFoundError,
    ChecksumMismatchError,
    S3BlobStore,
    S3StorageSettings,
    SizeMismatchError,
    derive_blob_id,
    sha256_of,
)

CORRUPT = b"%PDF-1.7\ncontent that does not match what the caller declared\n"
OTHER = b"the bytes whose checksum the caller wrongly declared"


def test_a_wrong_checksum_publishes_nothing(
    store: S3BlobStore, bucket_keys: Any
) -> None:
    before = bucket_keys()
    wrong = sha256_of(OTHER)

    with pytest.raises(ChecksumMismatchError) as raised:
        store.put_blob(
            CORRUPT,
            declared_sha256=wrong,
            declared_size=len(CORRUPT),
            role=ROLE_SOURCE_DOCUMENT,
            media_type="application/pdf",
        )

    # The error says what was expected and what was actually stored.
    assert raised.value.details["expected_sha256"] == wrong
    assert raised.value.details["actual_sha256"] == sha256_of(CORRUPT)

    # Nothing canonical, and no temporary residue either: the bucket is
    # byte-for-byte the set of keys it held before the attempt.
    assert bucket_keys() == before


def test_the_blob_id_corrupt_content_would_have_taken_is_absent(
    store: S3BlobStore,
) -> None:
    """Prove the negative by name, not only by counting keys."""
    would_be = derive_blob_id(sha256=sha256_of(OTHER), size=len(CORRUPT))
    with pytest.raises(ChecksumMismatchError):
        store.put_blob(
            CORRUPT,
            declared_sha256=sha256_of(OTHER),
            declared_size=len(CORRUPT),
            role=ROLE_SOURCE_DOCUMENT,
            media_type="application/pdf",
        )
    with pytest.raises(BlobNotFoundError):
        store.inspect(would_be)
    # The honestly-declared identity is absent too: the attempt created
    # nothing under any name.
    with pytest.raises(BlobNotFoundError):
        store.inspect(derive_blob_id(sha256=sha256_of(CORRUPT), size=len(CORRUPT)))


def test_a_wrong_size_publishes_nothing(store: S3BlobStore, bucket_keys: Any) -> None:
    before = bucket_keys()

    with pytest.raises(SizeMismatchError) as raised:
        store.put_blob(
            CORRUPT,
            declared_sha256=sha256_of(CORRUPT),
            declared_size=len(CORRUPT) + 17,
            role=ROLE_SOURCE_DOCUMENT,
            media_type="application/pdf",
        )

    assert raised.value.details["expected_size"] == len(CORRUPT) + 17
    assert raised.value.details["actual_size"] == len(CORRUPT)
    assert bucket_keys() == before


def test_a_truncated_upload_publishes_nothing(
    store: S3BlobStore, bucket_keys: Any
) -> None:
    """The realistic corruption: fewer bytes arrive than the caller sent.

    Staging the truncated body while declaring the full content's size and
    checksum is exactly what a dropped connection looks like from the store's
    side, and it must be caught by reading the stored object back.
    """
    before = bucket_keys()
    full = CORRUPT
    truncated = CORRUPT[: len(CORRUPT) // 2]

    temporary = store.stage_temporary(
        truncated,
        declared_sha256=sha256_of(full),
        declared_size=len(full),
        role=ROLE_SOURCE_DOCUMENT,
        media_type="application/pdf",
    )
    with pytest.raises(SizeMismatchError):
        store.verify_temporary(temporary)

    assert bucket_keys() == before


def test_a_refused_upload_leaves_no_temporary_object(
    store: S3BlobStore, bucket_keys: Any
) -> None:
    temporary = store.stage_temporary(
        CORRUPT,
        declared_sha256=sha256_of(OTHER),
        declared_size=len(CORRUPT),
        role=ROLE_SOURCE_DOCUMENT,
        media_type="application/pdf",
    )
    staged = bucket_keys()
    assert temporary.upload_token in "".join(staged), "staging did not store anything"

    with pytest.raises(ChecksumMismatchError):
        store.verify_temporary(temporary)

    assert temporary.upload_token not in "".join(bucket_keys())


def test_integrity_failure_text_never_names_the_bucket_or_a_key(
    store: S3BlobStore, settings: S3StorageSettings
) -> None:
    """The privacy rule, asserted against the rendered failure, not the model."""
    with pytest.raises(BlobIntegrityError) as raised:
        store.put_blob(
            CORRUPT,
            declared_sha256=sha256_of(OTHER),
            declared_size=len(CORRUPT),
            role=ROLE_SOURCE_DOCUMENT,
            media_type="application/pdf",
        )
    error = raised.value
    rendered = "\n".join(
        [
            str(error),
            repr(error),
            "".join(traceback.format_exception(type(error), error, error.__traceback__)),
        ]
    )
    assert settings.bucket not in rendered
    assert "blobs/" not in rendered
    assert "temporary/" not in rendered
    for name in error.details:
        assert name not in {"bucket", "key", "prefix", "uri", "url", "path"}


def test_an_integrity_error_cannot_be_built_carrying_a_key() -> None:
    """The guard that makes the privacy rule structural rather than reviewed."""
    with pytest.raises(TypeError):
        ChecksumMismatchError(key="blobs/AA/BB/AABB")
    with pytest.raises(TypeError):
        ChecksumMismatchError(bucket="audit-a3")
