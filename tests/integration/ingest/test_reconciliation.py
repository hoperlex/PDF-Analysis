"""The interrupted publication, produced by actually interrupting it.

Nothing here asserts a comment. Each case drives the real sequence and stops it with a
real failure at a real point, then reads the resulting state out of PostgreSQL and MinIO
directly.

The proxies below wrap the live adapter and delegate everything except the one call they
break. They are not test doubles for the store: the bytes really are staged, really are
verified and -- in :class:`PublishThenLoseTheStore` -- really do become canonical. Only
what happens *after* that is forced.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from auditmanager.ingest import IngestService, Reconciler
from auditmanager.shared.errors import DomainError, ErrorCode, screen_message
from auditmanager.documents import MANIFEST_ROLE_SOURCE_DOCUMENT
from auditmanager.storage import (
    BlobNotFoundError,
    StorageUnavailableError,
    derive_blob_id,
    sha256_of,
)

DISPLAY_TITLE = "Annual report 2026"
SOURCE_FILENAME = "annual_report_2026.pdf"


class _Delegating:
    """Everything the real adapter does, except what a subclass overrides."""

    def __init__(self, inner) -> None:
        self._inner = inner

    def __getattr__(self, name):
        return getattr(self._inner, name)


class CorruptOnTheWire(_Delegating):
    """The bytes that land differ from the bytes that were declared.

    Same length, one byte changed, so the size check passes and the *checksum* is what
    catches it -- which is the failure this proves the adapter refuses.
    """

    def stage_temporary(self, source, **kwargs):
        payload = bytes(source)
        flipped = bytes([payload[0] ^ 0xFF]) + payload[1:]
        return self._inner.stage_temporary(flipped, **kwargs)


class PublishThenLoseTheStore(_Delegating):
    """Publish for real, then lose the store before the version can be committed.

    This is the exact crash window ``P2-META-01`` names: "a crash between publish and
    commit leaves an orphan object rather than a half-version".
    """

    def publish(self, verified):
        self._inner.publish(verified)
        raise StorageUnavailableError()


def counts(engine, table: str) -> int:
    with engine.connect() as connection:
        return connection.execute(
            text(f"SELECT count(*) FROM {table}")  # noqa: S608 - fixed table names
        ).scalar_one()


def blob_state(engine, blob_id) -> str | None:
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT state FROM blob WHERE blob_id = :b"), {"b": str(blob_id)}
        ).scalar_one_or_none()


# --- a forced checksum mismatch ----------------------------------------------


def test_a_checksum_mismatch_leaves_no_available_blob_and_no_version(
    store, session_factory, project, baseline_pdf, key, engine, bucket_keys
) -> None:
    service = IngestService(CorruptOnTheWire(store), session_factory=session_factory)
    before = set(bucket_keys())

    with pytest.raises(DomainError) as raised:
        service.upload_single_pdf(
            project_uid=project.project_uid,
            content=baseline_pdf,
            source_filename=SOURCE_FILENAME,
            display_title=DISPLAY_TITLE,
            idempotency_key=key("corrupt"),
        )

    failure = raised.value
    assert failure.code is ErrorCode.STORAGE_INTEGRITY_ERROR
    screen_message(failure.envelope("corr_corrupt").message)

    # Nothing canonical, no temporary residue, and no metadata row at all: the blob row
    # is written only for content that has already been verified.
    assert set(bucket_keys()) == before
    assert counts(engine, "blob") == 0
    assert counts(engine, "document_version") == 0
    assert counts(engine, "input_manifest_entry") == 0
    assert counts(engine, "document") == 0

    # The command is terminal and carries the code that ended it.
    with engine.connect() as connection:
        state, error_code = connection.execute(
            text("SELECT state, error_code FROM command_record")
        ).one()
    assert state == "failed"
    assert error_code == "storage_integrity_error"


# --- published, then interrupted before the version could be committed --------


@pytest.fixture
def interrupted(store, session_factory, project, baseline_pdf, key, track):
    """Run the real sequence and lose the store immediately after publication."""
    service = IngestService(
        PublishThenLoseTheStore(store), session_factory=session_factory
    )
    blob_id = derive_blob_id(sha256=sha256_of(baseline_pdf), size=len(baseline_pdf))
    track(blob_id)
    with pytest.raises(DomainError) as raised:
        service.upload_single_pdf(
            project_uid=project.project_uid,
            content=baseline_pdf,
            source_filename=SOURCE_FILENAME,
            display_title=DISPLAY_TITLE,
            idempotency_key=key("interrupted"),
        )
    assert raised.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    return blob_id


def test_an_interruption_after_publish_leaves_an_orphan_not_a_half_version(
    interrupted, store, engine, reconciler: Reconciler, baseline_pdf
) -> None:
    blob_id = interrupted

    # The object really is canonical -- this is not a simulated publication.
    published = store.inspect(blob_id)
    assert published.sha256 == sha256_of(baseline_pdf)
    assert store.read(blob_id) == baseline_pdf

    # And the database has no version: the transaction that would have created one
    # never ran, so there is no half-written aggregate anywhere.
    assert counts(engine, "document_version") == 0
    assert counts(engine, "input_manifest_entry") == 0
    assert counts(engine, "document") == 0
    assert blob_state(engine, blob_id) == "verifying"

    report = reconciler.report()

    assert [item.blob_id for item in report.orphan_objects] == [blob_id]
    assert report.orphan_objects[0].recorded_state == "verifying"
    assert report.unpublished_records == ()
    assert report.missing_objects == ()
    assert not report.is_clean
    screen_message(report.describe())


def test_a_re_upload_adopts_the_orphan_instead_of_writing_a_second_object(
    interrupted, service, project, baseline_pdf, key, engine, bucket_keys, reconciler
) -> None:
    """The recovery is explicit and it is idempotent by content.

    ``blob_id`` is derived from ``(sha256, size)``, so the identical bytes resolve to
    the identifier the interrupted attempt already recorded. The publication finds the
    object present, the metadata row completes, and the orphan becomes the version's
    own blob.
    """
    blob_id = interrupted
    keys_before = set(bucket_keys())

    outcome = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=baseline_pdf,
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=key("recovery"),
    )

    assert outcome.version.source.blob_id == blob_id
    assert set(bucket_keys()) == keys_before, "the recovery wrote a second copy"
    assert blob_state(engine, blob_id) == "available"
    assert counts(engine, "blob") == 1
    assert counts(engine, "document_version") == 1
    assert service.read_source_bytes(outcome.version.version_uid) == baseline_pdf

    assert reconciler.report().is_clean


def test_a_record_with_no_object_is_reported_as_unpublished_not_as_an_orphan(
    session_factory, store, project, baseline_pdf, key, engine, reconciler
) -> None:
    """The other side of the window: the database is mid-publication, the store is empty.

    Produced by publishing for real, then removing the object -- which is exactly the
    state a crash between the metadata commit and the publication leaves behind.
    """
    blob_id = derive_blob_id(sha256=sha256_of(baseline_pdf), size=len(baseline_pdf))
    service = IngestService(
        PublishThenLoseTheStore(store), session_factory=session_factory
    )
    with pytest.raises(DomainError):
        service.upload_single_pdf(
            project_uid=project.project_uid,
            content=baseline_pdf,
            source_filename=SOURCE_FILENAME,
            display_title=DISPLAY_TITLE,
            idempotency_key=key("no-object"),
        )
    store._purge_published(blob_id)

    report = reconciler.report()

    assert report.orphan_objects == ()
    assert [item.blob_id for item in report.unpublished_records] == [blob_id]
    assert report.unpublished_records[0].recorded_state == "verifying"


# --- a published version whose bytes have gone -------------------------------


def test_a_version_whose_blob_is_missing_fails_with_storage_integrity_error(
    service, project, baseline_pdf, key, engine, store, reconciler
) -> None:
    outcome = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=baseline_pdf,
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=key("vanishing"),
    )
    blob_id = outcome.version.source.blob_id
    reconciler.verify_version(outcome.version.version_uid)  # healthy first

    store._purge_published(blob_id)

    with pytest.raises(DomainError) as raised:
        reconciler.verify_version(outcome.version.version_uid)

    failure = raised.value
    envelope = failure.envelope("corr_missing")
    assert failure.code is ErrorCode.STORAGE_INTEGRITY_ERROR
    assert envelope.details["blob_id"] == str(blob_id)
    # The reconciler walks manifest entries, so the role it reports is the manifest-entry
    # role, not the blob role. That is the useful one: it tells an operator which manifest
    # role is broken. The two spellings are deliberately different namespaces.
    assert envelope.details["role"] == MANIFEST_ROLE_SOURCE_DOCUMENT
    assert envelope.retryable is False
    screen_message(envelope.message)

    # Reading the version answers the same way, and the immutable rows are untouched:
    # a version is never repaired, a corrected source file is a new version_uid.
    with pytest.raises(DomainError) as read_failure:
        service.read_source_bytes(outcome.version.version_uid)
    assert read_failure.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR
    assert counts(engine, "document_version") == 1

    report = reconciler.report()
    assert [item.blob_id for item in report.missing_objects] == [blob_id]
    assert report.missing_objects[0].version_uid == outcome.version.version_uid


def test_report_is_clean_on_a_healthy_instance(
    service, project, baseline_pdf, key, track, reconciler
) -> None:
    outcome = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=baseline_pdf,
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=key("healthy"),
    )
    track(outcome.version.source.blob_id)

    report = reconciler.report()

    assert report.is_clean
    assert report.describe() == (
        "orphan_objects=0 unpublished_records=0 missing_objects=0 stale_commands=0"
    )


# --- stale commands -----------------------------------------------------------


def test_a_stale_in_progress_command_is_reported_and_can_be_abandoned(
    service, project, baseline_pdf, key, engine, reconciler, track
) -> None:
    """A command whose executor is gone. Abandonment is terminal, and deliberately so."""
    outcome = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=baseline_pdf,
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=key("stranded"),
    )
    track(outcome.version.source.blob_id)

    # Return the record to `in_progress` as a crash would have left it. The state guard
    # permits nothing of the kind, so this is done by rewriting the row's clock instead:
    # a fresh command is inserted in the initial state and aged.
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO command_record "
                "(command_id, command_type, idempotency_key, payload_fingerprint, "
                " state, created_at, updated_at) "
                "VALUES (:c, 'upload_source_document', :k, :f, 'in_progress', "
                "        now() - interval '3 hours', now() - interval '3 hours')"
            ),
            {
                "c": "cmd_00000000000000000000000000",
                "k": "stranded-executor",
                "f": "0" * 64,
            },
        )

    report = reconciler.report(stale_command_age="1 hour")
    assert [str(item) for item in report.stale_commands] == [
        "cmd_00000000000000000000000000"
    ]

    abandoned = reconciler.abandon_stale_commands(older_than="1 hour")
    assert [str(item) for item in abandoned] == ["cmd_00000000000000000000000000"]

    with engine.connect() as connection:
        state, error_code = connection.execute(
            text("SELECT state, error_code FROM command_record WHERE command_id = :c"),
            {"c": "cmd_00000000000000000000000000"},
        ).one()
    assert state == "abandoned"
    assert error_code == "idempotency_key_stale"
    assert reconciler.report(stale_command_age="1 hour").stale_commands == ()


def test_rejecting_a_never_published_record_is_explicit_and_permanent(
    interrupted, store, engine, reconciler, service, project, baseline_pdf, key
) -> None:
    """``reject_unpublished`` is opt-in, and its consequence is asserted, not implied.

    ``blob_id`` is content-derived, so rejecting a record permanently occupies the
    identity of those exact bytes. A later upload of identical content is then refused.
    That is why the ingest path never rejects on its own.
    """
    blob_id = interrupted
    store._purge_published(blob_id)

    reconciler.reject_unpublished(blob_id)
    assert blob_state(engine, blob_id) == "rejected"

    with pytest.raises(DomainError) as raised:
        service.upload_single_pdf(
            project_uid=project.project_uid,
            content=baseline_pdf,
            source_filename=SOURCE_FILENAME,
            display_title=DISPLAY_TITLE,
            idempotency_key=key("after-reject"),
        )
    assert raised.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    assert counts(engine, "document_version") == 0


def test_an_available_blob_is_never_rejected(
    service, project, baseline_pdf, key, track, reconciler
) -> None:
    outcome = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=baseline_pdf,
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=key("no-reject"),
    )
    track(outcome.version.source.blob_id)

    with pytest.raises(DomainError) as raised:
        reconciler.reject_unpublished(outcome.version.source.blob_id)
    assert raised.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED


def test_an_unknown_blob_is_not_found(reconciler) -> None:
    with pytest.raises(DomainError) as raised:
        reconciler.reject_unpublished(derive_blob_id(sha256="a" * 64, size=1))
    assert raised.value.code is ErrorCode.NOT_FOUND


def test_the_store_is_never_asked_to_list_the_bucket(store, reconciler) -> None:
    """Reconciliation works through a port that has no ``list``, and must keep doing so.

    Asserted against the port rather than by inspection: if a later change added a
    listing operation and reconciliation started depending on it, this fails.
    """
    from auditmanager.storage import BlobStore

    assert not hasattr(BlobStore, "list")
    assert not hasattr(BlobStore, "list_blobs")
    with pytest.raises(BlobNotFoundError):
        store.inspect(derive_blob_id(sha256="b" * 64, size=7))
