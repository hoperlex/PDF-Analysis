"""The success path: temporary -> verify -> publish, then inspect and read."""

from __future__ import annotations

import dataclasses
import io
from typing import Any

from auditmanager.storage import (
    BLOB_ID_PATTERN,
    ROLE_SOURCE_DOCUMENT,
    BlobState,
    BlobStore,
    PublishedBlob,
    S3BlobStore,
    derive_blob_id,
    sha256_of,
)

PDF_LIKE = b"%PDF-1.7\n" + b"gate a3 publication path\n" * 64


def test_adapter_satisfies_the_port(store: S3BlobStore) -> None:
    assert isinstance(store, BlobStore)


def test_publication_records_role_media_type_size_and_sha256(publish: Any) -> None:
    published = publish(PDF_LIKE)

    assert published.role == ROLE_SOURCE_DOCUMENT
    assert published.media_type == "application/pdf"
    assert published.size == len(PDF_LIKE)
    assert published.sha256 == sha256_of(PDF_LIKE)
    assert published.state is BlobState.AVAILABLE
    assert published.published_at is not None


def test_blob_id_matches_the_frozen_identifier_pattern(publish: Any) -> None:
    published = publish(PDF_LIKE)
    assert BLOB_ID_PATTERN.match(published.blob_id), published.blob_id
    assert published.blob_id == derive_blob_id(
        sha256=sha256_of(PDF_LIKE), size=len(PDF_LIKE)
    )


def test_published_bytes_read_back_identically(store: S3BlobStore, publish: Any) -> None:
    published = publish(PDF_LIKE)
    assert store.read(published.blob_id) == PDF_LIKE


def test_inspection_agrees_with_publication_without_reading_bytes(
    store: S3BlobStore, publish: Any
) -> None:
    published = publish(PDF_LIKE)
    assert store.inspect(published.blob_id) == published


def test_a_file_object_can_be_staged(store: S3BlobStore, blobs: list) -> None:
    """Large artifacts must not have to be held in memory to be published."""
    payload = b"streamed " * 4096
    published = store.put_blob(
        io.BytesIO(payload),
        declared_sha256=sha256_of(payload),
        declared_size=len(payload),
        role=ROLE_SOURCE_DOCUMENT,
        media_type="application/pdf",
    )
    blobs.append(published.blob_id)
    assert store.read(published.blob_id) == payload


def test_publication_leaves_no_temporary_object(
    publish: Any, bucket_keys: Any
) -> None:
    publish(PDF_LIKE)
    assert [key for key in bucket_keys() if key.startswith("temporary/")] == []


def test_the_explicit_three_step_sequence_is_available(
    store: S3BlobStore, blobs: list, bucket_keys: Any
) -> None:
    """Each phase is separately callable, and only the third one is canonical."""
    payload = b"three step sequence"
    temporary = store.stage_temporary(
        payload,
        declared_sha256=sha256_of(payload),
        declared_size=len(payload),
        role=ROLE_SOURCE_DOCUMENT,
        media_type="application/pdf",
    )
    assert temporary.state is BlobState.TEMPORARY
    expected_id = derive_blob_id(sha256=sha256_of(payload), size=len(payload))
    # Staged bytes exist, but nothing canonical does.
    assert not [key for key in bucket_keys() if expected_id[len("blob_") :] in key]

    verified = store.verify_temporary(temporary)
    assert verified.state is BlobState.VERIFYING
    assert verified.blob_id == expected_id
    # Verification alone still publishes nothing.
    assert not [key for key in bucket_keys() if expected_id[len("blob_") :] in key]

    published = store.publish(verified)
    blobs.append(published.blob_id)
    assert published.blob_id == expected_id
    assert store.read(published.blob_id) == payload


def test_discarding_a_staged_upload_is_idempotent(
    store: S3BlobStore, bucket_keys: Any
) -> None:
    payload = b"discard me"
    temporary = store.stage_temporary(
        payload,
        declared_sha256=sha256_of(payload),
        declared_size=len(payload),
        role=ROLE_SOURCE_DOCUMENT,
        media_type="application/pdf",
    )
    store.discard_temporary(temporary)
    store.discard_temporary(temporary)  # a second discard is not an error
    assert temporary.upload_token not in "".join(bucket_keys())


def test_an_empty_blob_is_publishable(store: S3BlobStore, blobs: list) -> None:
    """Zero bytes are content, not a failure. The size check must allow 0."""
    published = store.put_blob(
        b"",
        declared_sha256=sha256_of(b""),
        declared_size=0,
        role=ROLE_SOURCE_DOCUMENT,
        media_type="application/pdf",
    )
    blobs.append(published.blob_id)
    assert published.size == 0
    assert store.read(published.blob_id) == b""


def test_the_published_record_exposes_no_location(publish: Any) -> None:
    """A consumer cannot observe bucket, key, endpoint or path. Ever."""
    published = publish(PDF_LIKE)
    field_names = {field.name for field in dataclasses.fields(PublishedBlob)}
    assert field_names == {
        "blob_id",
        "role",
        "media_type",
        "size",
        "sha256",
        "published_at",
        "state",
    }
    forbidden = ("bucket", "key", "uri", "url", "path", "endpoint", "prefix")
    assert not [name for name in field_names if any(f in name for f in forbidden)]
    assert not [
        attribute
        for attribute in dir(published)
        if not attribute.startswith("_") and any(f in attribute for f in forbidden)
    ]


def test_the_port_offers_no_way_to_name_or_delete_an_object() -> None:
    """The port's shape is part of the invariant, so it is asserted.

    A ``delete`` or ``key_for`` on the port would let a consumer bypass
    ``temporary -> verify -> publish`` or observe the layout. Erasure is an
    ``erasure_pending -> erased`` transition under an approved request, which
    P01 does not implement and must not approximate.
    """
    members = {name for name in dir(BlobStore) if not name.startswith("_")}
    assert members == {
        "check_access",
        "discard_temporary",
        "inspect",
        "publish",
        "put_blob",
        "read",
        "stage_temporary",
        "verify_temporary",
    }
