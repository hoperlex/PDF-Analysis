"""What the read path answers when the store cannot vouch for the object.

The companion to the repaired assertion in
``test_reconciliation_rules_with_no_guard.py``. That one covers the fault where the
object is internally consistent and is *not the document the manifest names*: the read
path hashes the bytes, compares them to ``entry.sha256`` and refuses with
``storage_integrity_error`` carrying both digests.

This one covers the neighbouring fault, and exists so that the two do not collapse into
one answer. An object with no recorded digest is not a document that disagrees with its
manifest -- the adapter has compared nothing to anything and has no evidence about these
bytes at all. It is refused as ``validation_failed``, and an operator reading the
envelope can tell the two apart without looking at a log.

The object is made by rewriting one canonical object's metadata through the independent
``raw_s3`` client. That is behind the adapter's back on purpose: this whole class of
fault is reachable only out of band -- no sequence of the twelve operations produces a
canonical object this adapter did not stamp -- which is why it is defence in depth and
not a hole a caller can walk through.

Every expected value below is a literal or is computed from bytes this test built.
"""

from __future__ import annotations

import secrets
from typing import Any

import pytest

from auditmanager.shared.errors import DomainError, ErrorCode, screen_message
from auditmanager.storage._object_layout import canonical_key  # noqa: PLC2701

DISPLAY_TITLE = "Annual report 2026"
SOURCE_FILENAME = "annual_report_2026.pdf"

#: The user-metadata name S3 lower-cases to `x-amz-meta-content-sha256`, as a literal.
RECORDED_DIGEST_NAME = "content-sha256"


def test_a_source_object_carrying_no_recorded_digest_is_not_read_as_the_document(
    service, project, baseline_pdf, key, track, raw_s3: Any, s3_settings
) -> None:
    content = baseline_pdf + b"\n% " + secrets.token_hex(16).encode("ascii") + b"\n"
    outcome = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=content,
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=key("no-recorded-digest"),
    )
    blob_id = track(outcome.version.source.blob_id)

    # It reads correctly first: the fault below is the *only* thing that changes.
    assert service.read_source_bytes(outcome.version.version_uid) == content

    key_name = canonical_key(blob_id)
    raw_s3.copy_object(
        Bucket=s3_settings.bucket,
        Key=key_name,
        CopySource={"Bucket": s3_settings.bucket, "Key": key_name},
        MetadataDirective="REPLACE",
        ContentType="application/pdf",
        Metadata={},
    )
    head = raw_s3.head_object(Bucket=s3_settings.bucket, Key=key_name)
    assert RECORDED_DIGEST_NAME not in {k.lower() for k in (head.get("Metadata") or {})}

    with pytest.raises(DomainError) as raised:
        service.read_source_bytes(outcome.version.version_uid)

    failure = raised.value
    envelope = failure.envelope("corr_unvouched")
    assert failure.code is ErrorCode.VALIDATION_FAILED
    # *Not* the integrity code. These bytes are in fact the right bytes; what is missing
    # is the store's evidence for them, and telling an operator the document is corrupt
    # would send them to restore a backup they do not need.
    assert failure.code is not ErrorCode.STORAGE_INTEGRITY_ERROR
    assert envelope.retryable is False
    assert envelope.details["field"] == RECORDED_DIGEST_NAME
    # No bucket, no key, anywhere in what a caller can see.
    assert s3_settings.bucket not in envelope.message
    assert key_name not in envelope.message
    assert s3_settings.bucket not in str(envelope.details)
    assert key_name not in str(envelope.details)
    screen_message(envelope.message)
