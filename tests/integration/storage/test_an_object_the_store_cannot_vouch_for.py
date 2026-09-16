"""Reading an object whose recorded digest is absent, and one whose digest disagrees.

``read(verify=True)`` re-hashes what it read. Before ``W11-RD`` it compared that hash to
the object's recorded ``content-sha256`` under ``if recorded is not None and recorded !=
actual``, so an object carrying **no** recorded digest went through the whole verified
read path and was returned unchecked, from a call whose parameter is named ``verify`` and
defaults to ``True``. Nothing asked about that: every object in the suite was published
through this adapter, and ``publish`` always writes the metadata.

Two faults, and the point of this file is that they stay two
--------------------------------------------------------------
* **the store cannot vouch for this object** -- there is no recorded digest to compare
  anything against. ``validation_failed``: a declaration is absent, and nothing was
  compared to any bytes.
* **the bytes are not the declared bytes** -- there is a recorded digest and the bytes
  disagree with it. ``storage_integrity_error``.

An operator who reads one envelope must be able to tell which happened, so both tests
assert the *code*, and each asserts the other code is not what came back. One code for
both would be the ``analysis_failed`` flattening again.

How the objects are made
------------------------
Both are built by rewriting the metadata of an object this adapter published, through
the independent ``raw_s3`` client -- deliberately behind the adapter's back, because
that is exactly the fault being modelled: no sequence of port calls can produce a
canonical object the adapter did not stamp. The bytes are never touched; only what the
object records about itself changes. Every published object is registered for scoped
per-key cleanup by the ``publish`` fixture.

Nothing here imports a value from ``auditmanager.storage.s3`` and compares it to itself:
the metadata name and the two error codes are written out as literals.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.storage import (
    BlobIntegrityError,
    BlobMetadataInvalidError,
    S3BlobStore,
    S3StorageSettings,
    sha256_of,
)

# Reached through the private module deliberately: `_object_layout` is not exported, and
# an out-of-band rewrite has to address the object by its real key.
from auditmanager.storage._object_layout import canonical_key  # noqa: PLC2701

CONTENT = b"%PDF-1.7\nthe bytes a manifest would name\n%%EOF\n"

#: The user-metadata name S3 lower-cases to `x-amz-meta-content-sha256`. A literal, so
#: renaming the module constant does not silently move this test with it.
RECORDED_DIGEST_NAME = "content-sha256"

#: Some other document's digest. Written out rather than computed from CONTENT, so that
#: nothing here can agree with the object by construction.
A_FOREIGN_DIGEST = "1f0c1d0a2b3c4d5e6f708192a3b4c5d6e7f8091a2b3c4d5e6f708192a3b4c5d6"


def _rewrite_metadata(
    raw_s3: Any, settings: S3StorageSettings, blob_id, metadata: dict[str, str]
) -> None:
    """Replace one canonical object's user metadata in place. The bytes are untouched."""
    key = canonical_key(blob_id)
    raw_s3.copy_object(
        Bucket=settings.bucket,
        Key=key,
        CopySource={"Bucket": settings.bucket, "Key": key},
        MetadataDirective="REPLACE",
        ContentType="application/pdf",
        Metadata=metadata,
    )


def test_an_object_with_no_recorded_digest_is_refused_rather_than_returned(
    store: S3BlobStore, publish: Any, raw_s3: Any, settings: S3StorageSettings
) -> None:
    published = publish(CONTENT)
    _rewrite_metadata(raw_s3, settings, published.blob_id, {})

    # The precondition, established through the independent client: the object is there,
    # it still holds the right bytes, and it records no digest.
    head = raw_s3.head_object(
        Bucket=settings.bucket, Key=canonical_key(published.blob_id)
    )
    assert RECORDED_DIGEST_NAME not in {k.lower() for k in (head.get("Metadata") or {})}

    with pytest.raises(BlobMetadataInvalidError) as raised:
        store.read(published.blob_id)

    failure = raised.value
    assert failure.code == "validation_failed"
    # Not the integrity answer: nothing was compared to any bytes, so reporting a
    # checksum failure here would tell an operator to look for corruption that this
    # adapter has no evidence of.
    assert failure.code != "storage_integrity_error"
    assert not isinstance(failure, BlobIntegrityError)
    # `field` names which declaration is absent, and carries no bucket, key or value.
    assert failure.details["field"] == RECORDED_DIGEST_NAME
    rendered = str(failure)
    assert settings.bucket not in rendered
    assert canonical_key(published.blob_id) not in rendered

    # The refusal is the *verification*, not the read. The explicit opt-out still hands
    # back the bytes, and they are the bytes that were published: this test moved
    # metadata only, so a green assertion here proves the refusal above came from the
    # absent declaration and not from a damaged object.
    assert store.read(published.blob_id, verify=False) == CONTENT


def test_an_object_whose_recorded_digest_disagrees_is_the_other_fault(
    store: S3BlobStore, publish: Any, raw_s3: Any, settings: S3StorageSettings
) -> None:
    """The neighbouring case, which must keep its own code.

    Same object, same bytes, and this time a digest *is* recorded and is wrong. If a
    later change answered both with one code, this test and the one above could not both
    pass.
    """
    published = publish(CONTENT)
    _rewrite_metadata(
        raw_s3,
        settings,
        published.blob_id,
        {RECORDED_DIGEST_NAME: A_FOREIGN_DIGEST},
    )

    with pytest.raises(BlobIntegrityError) as raised:
        store.read(published.blob_id)

    failure = raised.value
    assert failure.code == "storage_integrity_error"
    assert failure.code != "validation_failed"
    assert failure.details["expected_sha256"] == A_FOREIGN_DIGEST
    assert failure.details["actual_sha256"] == sha256_of(CONTENT)
