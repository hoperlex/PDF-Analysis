"""The blob-metadata repository records lifecycle and never becomes the allocator.

The repository is the one addition ``B1`` makes to the Gate A storage tree. The property
that keeps it an addition rather than a takeover is that it cannot mint a ``blob_id``:
every write re-derives the identifier from ``(sha256, size)`` and refuses anything it
cannot reproduce. These tests attempt to hand it an identity it did not derive, and walk
the declared lifecycle a row actually takes.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage import BlobState, VerifiedBlob, derive_blob_id, sha256_of
from auditmanager.storage.blob_repository import (
    BlobMetadataRecord,
    BlobMetadataRepository,
)

CONTENT = b"%PDF-1.7\nnot a real document, but real bytes\n"

#: Any instant. The refusal below is about the digest and never reads these.
_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


def verified_for(content: bytes) -> VerifiedBlob:
    digest = sha256_of(content)
    return VerifiedBlob(
        blob_id=derive_blob_id(sha256=digest, size=len(content)),
        upload_token="tok_" + digest[:16],
        sha256=digest,
        size=len(content),
        role="source_document",  # type: ignore[arg-type]
        media_type="application/pdf",
    )


def test_the_row_walks_the_declared_lifecycle(session_factory, engine) -> None:
    repository = BlobMetadataRepository()
    verified = verified_for(CONTENT)

    with session_scope(session_factory) as session:
        recorded = repository.record_verified(session, verified)
    assert recorded.state is BlobState.VERIFYING
    assert recorded.sha256 == verified.sha256
    assert recorded.size_bytes == verified.size
    assert recorded.media_type == "application/pdf"

    with session_scope(session_factory) as session:
        available = repository.mark_available(session, verified.blob_id)
    assert available.state is BlobState.AVAILABLE
    assert available.is_available and available.is_settled

    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT state FROM blob WHERE blob_id = :b"),
            {"b": str(verified.blob_id)},
        ).scalar_one() == "available"


def test_an_identifier_the_repository_cannot_re_derive_is_refused(
    session_factory, engine
) -> None:
    """The guard that keeps this a lifecycle record instead of an identity authority."""
    repository = BlobMetadataRepository()
    honest = verified_for(CONTENT)
    forged = dataclasses.replace(
        honest, blob_id=derive_blob_id(sha256="c" * 64, size=999)
    )

    with pytest.raises(DomainError) as raised:
        with session_scope(session_factory) as session:
            repository.record_verified(session, forged)

    assert raised.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM blob")).scalar_one() == 0


def test_recording_the_same_content_twice_is_idempotent(session_factory, engine) -> None:
    repository = BlobMetadataRepository()
    verified = verified_for(CONTENT)

    with session_scope(session_factory) as session:
        repository.record_verified(session, verified)
        repository.mark_available(session, verified.blob_id)
    with session_scope(session_factory) as session:
        again = repository.record_verified(session, verified)
        # Marking an already-available blob available is a no-op, not a refusal: the
        # adapter is idempotent by (sha256, size) and the repository agrees with it.
        settled = repository.mark_available(session, verified.blob_id)

    assert again.state is BlobState.AVAILABLE
    assert settled.state is BlobState.AVAILABLE
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM blob")).scalar_one() == 1


def test_an_unsettled_row_is_what_reconciliation_starts_from(session_factory) -> None:
    repository = BlobMetadataRepository()
    verified = verified_for(CONTENT)

    with session_scope(session_factory) as session:
        assert repository.unsettled(session) == ()
        repository.record_verified(session, verified)
    with session_scope(session_factory) as session:
        unsettled = repository.unsettled(session)
    assert [item.blob_id for item in unsettled] == [verified.blob_id]

    with session_scope(session_factory) as session:
        repository.mark_available(session, verified.blob_id)
    with session_scope(session_factory) as session:
        assert repository.unsettled(session) == ()


def test_a_rejected_record_refuses_to_go_back_to_verifying(session_factory) -> None:
    """``rejected`` is terminal in the declared topology, and the guard reads it."""
    repository = BlobMetadataRepository()
    verified = verified_for(CONTENT)

    with session_scope(session_factory) as session:
        repository.record_verified(session, verified)
        repository.mark_rejected(session, verified.blob_id)

    with pytest.raises(DomainError) as raised:
        with session_scope(session_factory) as session:
            repository.record_verified(session, verified)
    assert raised.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED


def test_the_blob_table_has_no_location_column(engine) -> None:
    """The schema carries no bucket and no key, so the record cannot expose one."""
    with engine.connect() as connection:
        columns = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'blob'"
                )
            )
        }
    assert columns == {
        "blob_id",
        "state",
        "sha256",
        "size_bytes",
        "media_type",
        "created_at",
        "updated_at",
    }


# --- D-4, the second site: an empty digest must never reach an envelope ---------------

#: Read from the schema rather than spelled here, so the assertion below is about what
#: PostgreSQL enforces and not about what this file remembers.
_AVAILABLE_IS_VERIFIED = "ck_blob_available_is_verified"


def test_no_row_the_writer_can_create_reaches_the_comparison_without_a_digest(
    session_factory, engine
) -> None:
    """The discriminator, and the reason the test below is not itself the repair.

    `_assert_same_content` runs only on an `available` or `verifying` row. Two
    independent facts stop either carrying a NULL digest, and both are asserted because
    either alone would leave the other free to change silently:

    * the schema forbids it on an `available` row;
    * `_INSERT` is the only statement in the tree that creates a `blob` row, and it
      always supplies `verified.sha256`, so a `verifying` row never acquires one either.

    If either stops being true this reddens, and the branch below stops being unreachable.
    """
    repository = BlobMetadataRepository()
    verified = verified_for(CONTENT)
    with session_scope(session_factory) as session:
        repository.record_verified(session, verified)

    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT state, sha256 FROM blob "
                "WHERE state = ANY(ARRAY['available', 'verifying'])"
            )
        ).all()
    assert rows, "nothing reached a verified state; the discriminator proved nothing"
    assert all(sha is not None for _, sha in rows)

    with engine.connect() as connection:
        definition = connection.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = :name"
            ),
            {"name": _AVAILABLE_IS_VERIFIED},
        ).scalar_one()
    assert "sha256 IS NOT NULL" in definition, definition


def test_a_digestless_row_is_refused_as_an_invariant_not_reported_as_empty_bytes() -> None:
    """`DEBT_REGISTER.md` D-4, second site.

    This branch is unreachable through the writer -- the test above establishes that --
    so the record is constructed directly. That is legitimate precisely because the point
    is what the code says about a state it cannot produce.

    Before the repair it emitted `actual_sha256=""`: an empty string where a digest is
    expected, in an operator-facing envelope, claiming something about bytes nothing had
    looked at. An unreachable branch that invents a plausible value is worse than one
    that refuses, because the empty string reaches a reader looking exactly like a digest
    of nothing. The repair names the invariant instead.
    """
    verified = verified_for(CONTENT)
    digestless = BlobMetadataRecord(
        blob_id=verified.blob_id,
        state=BlobState.VERIFYING,
        sha256=None,
        size_bytes=verified.size,
        media_type=verified.media_type,
        created_at=_EPOCH,
        updated_at=_EPOCH,
    )

    with pytest.raises(DomainError) as raised:
        BlobMetadataRepository._assert_same_content(digestless, verified)

    assert raised.value.code is ErrorCode.INTERNAL_ERROR
    # The whole of the row: nothing in the envelope claims anything about the bytes.
    assert "actual_sha256" not in raised.value.detail_fields
    assert "" not in raised.value.detail_fields.values()
    assert raised.value.envelope("cid-d4").details == {}
