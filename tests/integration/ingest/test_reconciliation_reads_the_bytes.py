"""What ``verify_version`` establishes once it stops comparing two declarations.

``DEBT_REGISTER.md`` D-2 and D-4. Before wave 12 this method asked the store one
question -- ``inspect``, a ``head_object`` -- and compared the *record it got back*
against the manifest. Both sides of that comparison are declarations, and an object
replaced out of band with its recorded metadata and its length left intact satisfies it.
``W11-RD`` measured exactly that on real MinIO: ``inspect().sha256`` equalled the
manifest digest, ``verify_version`` returned, and ``read_source_bytes`` refused the same
row. Reconciliation -- the tool an operator uses to decide a version is fine -- was the
permissive one.

The three cases below are the three things that changed, and each is reachable only from
behind the adapter. That is the point and not a weakness: no sequence of the twelve
operations rewrites a canonical object's body or strips its metadata, so every case here
is written with the independent ``raw_s3`` client, and what they guard is defence in
depth rather than a hole a caller can walk through.

Every expected value is a literal, or is computed from bytes this test built. Nothing is
imported from ``auditmanager.ingest.reconciliation`` and compared to itself.
"""

from __future__ import annotations

import secrets
from typing import Any

import pytest

from auditmanager.documents import MANIFEST_ROLE_SOURCE_DOCUMENT
from auditmanager.ingest import Reconciler
from auditmanager.shared.errors import DomainError, ErrorCode, screen_message
from auditmanager.storage import sha256_of
from auditmanager.storage._object_layout import canonical_key  # noqa: PLC2701

DISPLAY_TITLE = "Annual report 2026"
SOURCE_FILENAME = "annual_report_2026.pdf"

#: The user-metadata name S3 lower-cases to `x-amz-meta-content-sha256`, as a literal.
RECORDED_DIGEST_NAME = "content-sha256"


def _unique_pdf(baseline: bytes) -> bytes:
    """The corpus baseline with a unique comment appended.

    ``blob_id`` is derived from ``(sha256, size)`` and publication is idempotent by that
    identity, so a test uploading the shared baseline would adopt whatever an earlier run
    left at that canonical key. A comment after ``%%EOF`` does not move ``startxref``, so
    the document still parses. Nothing is written to ``fixtures/`` -- the corpus is frozen
    evidence and this builds its bytes in the process.
    """
    return baseline + b"\n% " + secrets.token_hex(16).encode("ascii") + b"\n"


def _publish_one(service, project, key, label: str, content: bytes):
    return service.upload_single_pdf(
        project_uid=project.project_uid,
        content=content,
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=key(label),
    )


class _Delegating:
    """Everything the real adapter does, except what a subclass overrides."""

    def __init__(self, inner) -> None:
        self._inner = inner

    def __getattr__(self, name):
        return getattr(self._inner, name)


class CountingReads(_Delegating):
    """The real adapter, with every body transfer recorded.

    Not a double: the bytes really are fetched from MinIO. Only the fact that a fetch
    happened is remembered, which is the one thing an assertion about *cost* needs.
    """

    def __init__(self, inner) -> None:
        super().__init__(inner)
        self.reads: list[str] = []

    def read(self, blob_id, **kwargs):
        self.reads.append(str(blob_id))
        return self._inner.read(blob_id, **kwargs)


# --- D-2: the bytes, not the declaration about them ----------------------------


def test_a_version_whose_bytes_were_replaced_under_intact_metadata_is_refused(
    service, project, baseline_pdf, key, track, reconciler, raw_s3: Any, s3_settings
) -> None:
    """The fault two declarations cannot see, built the way ``W11-RD`` measured it.

    The canonical object's body is replaced while its recorded metadata is copied
    verbatim and its length is unchanged. Afterwards the store's record still says the
    manifest's digest and the manifest's size, so **neither half of the declaration
    comparison can fire** -- that precondition is asserted below rather than assumed.
    Only a comparison that hashes the body can refuse this row.
    """
    content = _unique_pdf(baseline_pdf)
    honest_sha256 = sha256_of(content)
    outcome = _publish_one(service, project, key, "intact-metadata", content)
    blob_id = track(outcome.version.source.blob_id)
    entry = outcome.version.source
    assert entry.sha256 == honest_sha256
    assert entry.size_bytes == len(content)

    # It verifies and reads correctly first: the replacement below is the only thing
    # that changes, so nothing here can be green for an unrelated reason.
    reconciler.verify_version(outcome.version.version_uid)
    assert service.read_source_bytes(outcome.version.version_uid) == content

    impostor = content[:-1] + bytes([content[-1] ^ 0xFF])
    assert len(impostor) == len(content)
    impostor_sha256 = sha256_of(impostor)
    assert impostor_sha256 != honest_sha256

    key_name = canonical_key(blob_id)
    before = raw_s3.head_object(Bucket=s3_settings.bucket, Key=key_name)
    raw_s3.put_object(
        Bucket=s3_settings.bucket,
        Key=key_name,
        Body=impostor,
        ContentType=before.get("ContentType", "application/pdf"),
        Metadata=dict(before.get("Metadata") or {}),
    )

    # The precondition, read back through the independent client: the object records the
    # manifest's own digest and the manifest's own length, and holds neither.
    after = raw_s3.head_object(Bucket=s3_settings.bucket, Key=key_name)
    recorded = {k.lower(): v for k, v in (after.get("Metadata") or {}).items()}
    assert recorded[RECORDED_DIGEST_NAME] == honest_sha256
    assert int(after["ContentLength"]) == len(content)

    with pytest.raises(DomainError) as raised:
        reconciler.verify_version(outcome.version.version_uid)

    failure = raised.value
    envelope = failure.envelope("corr_replaced")
    assert failure.code is ErrorCode.STORAGE_INTEGRITY_ERROR
    assert envelope.retryable is False
    # ``actual_sha256`` is the digest of the bytes the store actually holds. The record
    # says ``honest_sha256``; asserting the impostor's digest is what distinguishes a
    # refusal that hashed the body from one that merely re-read the declaration.
    assert envelope.details["actual_sha256"] == impostor_sha256
    assert envelope.details["expected_sha256"] == honest_sha256
    # ``blob_id`` and the manifest ``role`` are reported by this method and are not
    # carried by any error the adapter raises, so they also witness that the comparison
    # was made here, against the manifest, rather than delegated to ``read(verify=True)``.
    assert envelope.details["blob_id"] == str(blob_id)
    assert envelope.details["role"] == MANIFEST_ROLE_SOURCE_DOCUMENT
    assert s3_settings.bucket not in envelope.message
    assert key_name not in envelope.message
    screen_message(envelope.message)

    # One fault, one answer, whichever path reaches it: the read path already refused
    # this row before wave 12, and it still does, with the same code and the same digests.
    with pytest.raises(DomainError) as read_raised:
        service.read_source_bytes(outcome.version.version_uid)
    read_envelope = read_raised.value.envelope("corr_replaced_read")
    assert read_raised.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR
    assert read_envelope.details["expected_sha256"] == honest_sha256
    assert read_envelope.details["actual_sha256"] == impostor_sha256

    # The version row is untouched. A version is never repaired.
    assert service.get_version(outcome.version.version_uid).source.sha256 == honest_sha256


# --- D-4: an empty digest never reaches an operator ----------------------------


def test_a_version_whose_object_records_no_digest_is_not_an_integrity_verdict(
    service, project, baseline_pdf, key, track, reconciler, raw_s3: Any, s3_settings
) -> None:
    """``inspect`` yields ``sha256=""`` for an unstamped object, and that is not a digest.

    Before wave 12 the declaration comparison fired on it and emitted
    ``actual_sha256=""`` -- an empty string where an operator reads a digest, and a claim
    about bytes nothing had looked at. The store has compared nothing to anything here;
    the honest statement is that it cannot vouch for the object, which is
    ``validation_failed``. That is the same answer ``BlobStore.read`` gives over the same
    row, decided in wave 11 for exactly this reason: telling an operator the document is
    corrupt would send them to restore a backup they may not need. The bytes, in this
    test, are in fact the right bytes.
    """
    content = _unique_pdf(baseline_pdf)
    outcome = _publish_one(service, project, key, "no-recorded-digest", content)
    blob_id = track(outcome.version.source.blob_id)
    reconciler.verify_version(outcome.version.version_uid)  # healthy first

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
    # The bytes are untouched: this case is about the store's evidence, not the document.
    assert raw_s3.get_object(Bucket=s3_settings.bucket, Key=key_name)["Body"].read() == (
        content
    )

    with pytest.raises(DomainError) as raised:
        reconciler.verify_version(outcome.version.version_uid)

    failure = raised.value
    envelope = failure.envelope("corr_unstamped")
    assert failure.code is ErrorCode.VALIDATION_FAILED
    # *Not* the integrity code, and that is the whole of what this case establishes.
    assert failure.code is not ErrorCode.STORAGE_INTEGRITY_ERROR
    assert envelope.retryable is False
    assert envelope.details["field"] == "sha256"
    assert envelope.details["aggregate_type"] == "Blob"
    # The defect, stated as an assertion: no empty string anywhere a digest is read.
    assert "actual_sha256" not in envelope.details
    assert "" not in set(envelope.details.values())
    assert s3_settings.bucket not in str(envelope.details)
    assert key_name not in str(envelope.details)
    screen_message(envelope.message)


# --- what the change costs, and what it does not -------------------------------


def test_the_body_is_read_once_per_entry_and_not_at_all_when_the_record_already_fails(
    service, project, baseline_pdf, key, track, session_factory, store, raw_s3: Any,
    s3_settings,
) -> None:
    """The cost of the repair, pinned on both sides.

    A healthy version now costs one ``head`` **and one full body transfer per manifest
    entry**, where it used to cost one ``head``. That is the price of a verdict that
    means anything, and it is asserted here so that it is a decision on the record rather
    than a surprise in an operator's timing.

    The other side is the ordering, and it is the reason the declaration comparison was
    kept in front of the read rather than replaced by it: a row the store's own record
    already fails is refused **without** fetching a body. Reordering the two -- reading
    first and comparing the declarations afterwards -- would give the same verdicts and
    reddens nothing else in the suite.

    ``report()`` is deliberately not in this test's scope: it is the sweep, it asks
    through ``_object_exists``, and it still never reads a byte. That is asserted below
    on the same instance, so the two entrypoints are shown to be priced differently.
    """
    content = _unique_pdf(baseline_pdf)
    honest_sha256 = sha256_of(content)
    outcome = _publish_one(service, project, key, "cost", content)
    blob_id = track(outcome.version.source.blob_id)
    assert len(outcome.version.manifest) == 1

    counting = CountingReads(store)
    reconciler = Reconciler(counting, session_factory=session_factory)

    reconciler.verify_version(outcome.version.version_uid)
    assert counting.reads == [str(blob_id)], (
        "a healthy version must cost one body transfer per manifest entry: that is the "
        "whole of what the wave-12 repair buys and the whole of what it costs"
    )

    # The sweep is untouched and stays head-only.
    counting.reads.clear()
    assert reconciler.report().is_clean
    assert counting.reads == [], (
        "report() is the sweep and must stay proportional to the number of rows, never "
        "to how large the objects are"
    )

    # Now a row whose recorded digest already disagrees with the manifest. The record is
    # rewritten and the body left alone, so the object is internally inconsistent and the
    # declaration comparison is what refuses it.
    key_name = canonical_key(blob_id)
    before = raw_s3.head_object(Bucket=s3_settings.bucket, Key=key_name)
    metadata = {k.lower(): v for k, v in (before.get("Metadata") or {}).items()}
    wrong_digest = sha256_of(content + b"x")
    assert wrong_digest != honest_sha256
    metadata[RECORDED_DIGEST_NAME] = wrong_digest
    raw_s3.copy_object(
        Bucket=s3_settings.bucket,
        Key=key_name,
        CopySource={"Bucket": s3_settings.bucket, "Key": key_name},
        MetadataDirective="REPLACE",
        ContentType=before.get("ContentType", "application/pdf"),
        Metadata=metadata,
    )

    counting.reads.clear()
    with pytest.raises(DomainError) as raised:
        reconciler.verify_version(outcome.version.version_uid)

    envelope = raised.value.envelope("corr_record_disagrees")
    assert raised.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR
    # ``actual_sha256`` is the store's own record here, because nothing was read. That is
    # the strongest fact this refusal established, and it is deliberately a different
    # fact from the one the previous test asserts.
    assert envelope.details["expected_sha256"] == honest_sha256
    assert envelope.details["actual_sha256"] == wrong_digest
    assert envelope.details["blob_id"] == str(blob_id)
    assert counting.reads == [], (
        "a record that already disagrees with the manifest settles the verdict; pulling "
        "the body afterwards would buy nothing and cost a full transfer"
    )
    screen_message(envelope.message)
