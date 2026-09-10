"""A published version and its manifest are frozen, and the refusal is read on SQLSTATE.

``docs/program/P02_SEAMS.md`` section 3.2: three custom SQLSTATEs, all mapping to
``state_transition_not_allowed``, and "map on the SQLSTATE, never on the message text".
These tests attempt the writes the schema forbids and assert both halves: that the
database refuses, and that the refusal carries the SQLSTATE the mapping is keyed on.

The attempts are made with raw SQL on purpose. Proving that the *repository* does not
issue an UPDATE would prove nothing about the guard; the guard's job is to refuse every
caller, including one that bypasses the repository entirely.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from auditmanager.documents import (
    SQLSTATE_IMMUTABLE_ROW_VIOLATION,
    SQLSTATE_UNDECLARED_TRANSITION,
    sqlstate_of,
    translate_database_refusal,
)
from auditmanager.shared.db.schema import SQLSTATE_TO_CATALOG_CODE
from auditmanager.shared.errors import ErrorCode

DISPLAY_TITLE = "Annual report 2026"
SOURCE_FILENAME = "annual_report_2026.pdf"


@pytest.fixture
def published(service, project, baseline_pdf, key, track):
    outcome = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=baseline_pdf,
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=key("immutable"),
    )
    track(outcome.version.source.blob_id)
    return outcome.version


def refuse(engine, statement: str, parameters: dict) -> DBAPIError:
    with pytest.raises(DBAPIError) as raised:
        with engine.begin() as connection:
            connection.execute(text(statement), parameters)
    return raised.value


@pytest.mark.parametrize(
    ("what", "statement"),
    [
        (
            "update a published version",
            "UPDATE document_version SET page_count = 3 WHERE version_uid = :v",
        ),
        (
            "delete a published version",
            "DELETE FROM document_version WHERE version_uid = :v",
        ),
        (
            "update a manifest entry",
            "UPDATE input_manifest_entry SET sha256 = "
            "'0000000000000000000000000000000000000000000000000000000000000000' "
            "WHERE version_uid = :v",
        ),
        (
            "delete a manifest entry",
            "DELETE FROM input_manifest_entry WHERE version_uid = :v",
        ),
    ],
)
def test_published_input_state_refuses_every_later_write(
    engine, published, what, statement
) -> None:
    exc = refuse(engine, statement, {"v": str(published.version_uid)})

    assert sqlstate_of(exc) == SQLSTATE_IMMUTABLE_ROW_VIOLATION, what
    failure = translate_database_refusal(exc, machine="document_version")
    assert failure is not None
    assert failure.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED

    # The row survived the attempt.
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM document_version WHERE version_uid = :v"),
            {"v": str(published.version_uid)},
        ).scalar_one() == 1
        assert connection.execute(
            text("SELECT count(*) FROM input_manifest_entry WHERE version_uid = :v"),
            {"v": str(published.version_uid)},
        ).scalar_one() == 1


def test_verified_blob_metadata_is_write_once(engine, published) -> None:
    """``AM003`` again, from the write-once guard rather than the immutable-row one."""
    exc = refuse(
        engine,
        "UPDATE blob SET sha256 = "
        "'1111111111111111111111111111111111111111111111111111111111111111' "
        "WHERE blob_id = :b",
        {"b": str(published.source.blob_id)},
    )
    assert sqlstate_of(exc) == SQLSTATE_IMMUTABLE_ROW_VIOLATION
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT sha256 FROM blob WHERE blob_id = :b"),
            {"b": str(published.source.blob_id)},
        ).scalar_one() == published.sha256


def test_an_undeclared_blob_transition_is_refused(engine, published) -> None:
    """``available -> temporary`` is not an edge the contract declares: ``AM001``."""
    exc = refuse(
        engine,
        "UPDATE blob SET state = 'temporary' WHERE blob_id = :b",
        {"b": str(published.source.blob_id)},
    )
    assert sqlstate_of(exc) == SQLSTATE_UNDECLARED_TRANSITION
    failure = translate_database_refusal(
        exc, machine="blob", current_state="available", requested_state="temporary"
    )
    assert failure is not None
    assert failure.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    assert failure.envelope("corr_blob").details == {
        "machine": "blob",
        "current_state": "available",
        "requested_state": "temporary",
    }


def test_every_custom_sqlstate_maps_to_the_frozen_catalog_code() -> None:
    """The mapping is the shared kernel's, not a copy. All three land on one code."""
    assert set(SQLSTATE_TO_CATALOG_CODE) == {"AM001", "AM002", "AM003"}
    assert set(SQLSTATE_TO_CATALOG_CODE.values()) == {"state_transition_not_allowed"}


def test_a_refusal_is_not_translated_from_its_message(engine, published) -> None:
    """A driver error with no custom SQLSTATE is left alone rather than guessed at.

    This is the other half of "map on the SQLSTATE": the translator must decline a
    refusal that is not one of the three, instead of pattern-matching prose and
    reporting a state conflict for an unrelated fault.
    """
    exc = refuse(
        engine,
        "INSERT INTO input_manifest_entry "
        "(version_uid, role, blob_id, sha256, size_bytes, media_type) "
        "VALUES (:v, 'source_document', :b, :s, 1, 'application/pdf')",
        {
            "v": str(published.version_uid),
            "b": str(published.source.blob_id),
            "s": published.sha256,
        },
    )
    # A primary-key collision: real, but not one of the immutability guards.
    assert sqlstate_of(exc) == "23505"
    assert translate_database_refusal(exc) is None
