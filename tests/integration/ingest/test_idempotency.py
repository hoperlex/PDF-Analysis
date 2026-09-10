"""The command record: a repeat replays, a reused key with a new payload conflicts.

``docs/program/P02_SEAMS.md`` section 3.5 forbids an automatic retry, because "a retry
that does not consult the command record writes duplicates". These tests are how we
know the record is actually consulted rather than merely written.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from auditmanager.ingest import COMMAND_TYPE_UPLOAD
from auditmanager.shared.errors import DomainError, ErrorCode, screen_message

DISPLAY_TITLE = "Annual report 2026"
SOURCE_FILENAME = "annual_report_2026.pdf"


def counts(engine, table: str) -> int:
    with engine.connect() as connection:
        return connection.execute(
            text(f"SELECT count(*) FROM {table}")  # noqa: S608 - fixed table names
        ).scalar_one()


def test_same_key_and_payload_replays_the_version_and_creates_nothing(
    service, project, baseline_pdf, key, engine, bucket_keys, track
) -> None:
    shared_key = key("repeat")
    first = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=baseline_pdf,
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=shared_key,
    )
    track(first.version.source.blob_id)
    keys_after_first = set(bucket_keys())

    second = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=baseline_pdf,
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=shared_key,
    )

    assert second.replayed is True
    assert first.replayed is False
    assert second.version == first.version
    assert counts(engine, "document_version") == 1
    assert counts(engine, "input_manifest_entry") == 1
    assert counts(engine, "document") == 1
    assert counts(engine, "blob") == 1
    assert counts(engine, "command_record") == 1
    assert set(bucket_keys()) == keys_after_first


def test_same_key_with_a_different_payload_is_idempotency_key_reuse(
    service, project, baseline_pdf, key, engine, bucket_keys, track
) -> None:
    shared_key = key("conflict")
    first = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=baseline_pdf,
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=shared_key,
    )
    track(first.version.source.blob_id)
    keys_after_first = set(bucket_keys())

    with pytest.raises(DomainError) as raised:
        service.upload_single_pdf(
            project_uid=project.project_uid,
            content=baseline_pdf + b"\n% different bytes\n",
            source_filename=SOURCE_FILENAME,
            display_title=DISPLAY_TITLE,
            idempotency_key=shared_key,
        )

    failure = raised.value
    envelope = failure.envelope("corr_reuse")
    assert failure.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
    assert envelope.http_status == 409
    assert envelope.retryable is False

    # The key is a forbidden envelope detail. Only `command_type` may travel.
    assert envelope.details == {"command_type": COMMAND_TYPE_UPLOAD}
    assert str(shared_key) not in envelope.message
    assert str(shared_key) not in str(envelope.details)
    screen_message(envelope.message)

    # Nothing was created by the refused attempt.
    assert counts(engine, "document_version") == 1
    assert counts(engine, "blob") == 1
    assert counts(engine, "command_record") == 1
    assert set(bucket_keys()) == keys_after_first


def test_the_file_name_is_part_of_the_payload_fingerprint(
    service, project, baseline_pdf, key, track
) -> None:
    """Same bytes, same key, a different declared name is still a different payload."""
    shared_key = key("renamed")
    first = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=baseline_pdf,
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=shared_key,
    )
    track(first.version.source.blob_id)

    with pytest.raises(DomainError) as raised:
        service.upload_single_pdf(
            project_uid=project.project_uid,
            content=baseline_pdf,
            source_filename="renamed.pdf",
            display_title=DISPLAY_TITLE,
            idempotency_key=shared_key,
        )
    assert raised.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE


def test_a_rejected_payload_never_claims_the_key(
    service, project, baseline_pdf, negative_pdf, key, engine, track
) -> None:
    """The envelope is answered first, so a refused upload leaves the key usable."""
    shared_key = key("reusable")

    with pytest.raises(DomainError) as raised:
        service.upload_single_pdf(
            project_uid=project.project_uid,
            content=negative_pdf("encrypted.pdf"),
            source_filename="encrypted.pdf",
            display_title=DISPLAY_TITLE,
            idempotency_key=shared_key,
        )
    assert raised.value.code is ErrorCode.VALIDATION_FAILED
    assert counts(engine, "command_record") == 0

    # The very same key now works, because the refusal claimed nothing.
    outcome = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=baseline_pdf,
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=shared_key,
    )
    track(outcome.version.source.blob_id)
    assert outcome.replayed is False
    assert counts(engine, "command_record") == 1


def test_the_command_record_ends_succeeded_with_a_replayable_outcome(
    service, project, baseline_pdf, key, engine, track
) -> None:
    outcome = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=baseline_pdf,
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=key("recorded"),
    )
    track(outcome.version.source.blob_id)

    with engine.connect() as connection:
        command_type, state, recorded, error_code = connection.execute(
            text(
                "SELECT command_type, state, outcome, error_code FROM command_record"
            )
        ).one()

    assert command_type == COMMAND_TYPE_UPLOAD
    assert state == "succeeded"
    assert error_code is None
    assert recorded["version_uid"] == str(outcome.version.version_uid)
    assert recorded["blob_id"] == str(outcome.version.source.blob_id)
