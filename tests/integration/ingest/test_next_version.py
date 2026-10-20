"""The next version of an existing document (`W59-VERSION-UPLOAD-01`, phase A).

:meth:`IngestService.upload_next_version` admits a portal bundle into a document that
already exists. It is :meth:`IngestService.upload_bundle` with the document named, so the
envelope and custody suites of this directory cover its bytes; what is asserted here is
what is specific to a *further* version:

* it gets the next ordinal and the document's current pointer moves to it;
* it inherits nothing -- no classification row exists for it -- and every fact of the older
  version (its row, its manifest, its classification) is byte-for-byte what it was;
* an exact retry replays, a key spent elsewhere is ``idempotency_key_reuse``;
* a foreign or unknown document, or an unknown project, is refused before the key is
  claimed; an envelope refusal leaves the document as it was;
* two concurrent uploads into one document get consecutive ordinals, never a collision.

Every assertion about what was written is read out of PostgreSQL, never off the return
value of the call under test.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from sqlalchemy import Engine, text

from auditmanager.documents import DocumentRepository
from auditmanager.ingest import ACCEPTED_MEDIA_TYPE, IngestService
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode, screen_message
from auditmanager.shared.identity import DocumentUid, ProjectUid
from auditmanager.shared.identity.ids import UserUid
from tests.integration.ingest.bundle_support import bundle_around

SOURCE_FILENAME = "annual_report_2026.zip"
DISPLAY_TITLE = "Annual report 2026"


def _first(service: IngestService, project, baseline_pdf: bytes, key, track, **overrides):
    """Version 1 of a fresh document, through ``uploadDocument``'s entry."""
    arguments: dict[str, Any] = {
        "project_uid": project.project_uid,
        "content": bundle_around(baseline_pdf),
        "source_filename": SOURCE_FILENAME,
        "display_title": DISPLAY_TITLE,
        "idempotency_key": key("first"),
    }
    arguments.update(overrides)
    outcome = service.upload_bundle(**arguments)
    for entry in outcome.version.manifest:
        track(entry.blob_id)
    return outcome


def _revision(baseline_pdf: bytes, label: str) -> bytes:
    """A bundle whose every stored member differs from the baseline's and from another label's.

    The PDF differs by a trailing comment; the block list and the markdown embed the stem, so
    a stem per label gives them distinct bytes and distinct blob identities as well. That
    matters for the concurrency test: two bundles sharing a member blob would queue on that
    blob's row in the publishing transaction and never reach the ordinal at the same time.
    """
    stem = "revision_" + label.replace("-", "_")
    return bundle_around(baseline_pdf + f"\n% revision {label}\n".encode(), stem=stem)


def _next(service: IngestService, project_uid, document_uid, content: bytes, idempotency_key, track):
    outcome = service.upload_next_version(
        project_uid=project_uid,
        document_uid=document_uid,
        content=content,
        source_filename="annual_report_2026_rev.zip",
        idempotency_key=idempotency_key,
    )
    for entry in outcome.version.manifest:
        track(entry.blob_id)
    return outcome


def _ordinals(engine: Engine, document_uid) -> list[tuple[str, int]]:
    with engine.connect() as connection:
        return [
            (str(row[0]), int(row[1]))
            for row in connection.execute(
                text(
                    "SELECT version_uid, version_ordinal FROM document_version "
                    "WHERE document_uid = :d ORDER BY version_ordinal"
                ),
                {"d": str(document_uid)},
            )
        ]


def _current(engine: Engine, document_uid) -> str | None:
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT current_version_uid FROM document WHERE document_uid = :d"),
            {"d": str(document_uid)},
        ).scalar_one()


def _command_records(engine: Engine, idempotency_key) -> list[tuple[str, str]]:
    with engine.connect() as connection:
        return [
            (str(row[0]), str(row[1]))
            for row in connection.execute(
                text(
                    "SELECT command_type, state FROM command_record "
                    "WHERE idempotency_key = :k"
                ),
                {"k": str(idempotency_key)},
            )
        ]


# --- the next ordinal and the current pointer -------------------------------------------


def test_further_versions_take_the_next_ordinals_and_the_current_pointer(
    service, project, baseline_pdf, key, track, engine
) -> None:
    first = _first(service, project, baseline_pdf, key, track)
    document_uid = first.version.document_uid

    second = _next(service, project.project_uid, document_uid, _revision(baseline_pdf, "2"), key("v2"), track)
    assert _current(engine, document_uid) == str(second.version.version_uid)
    third = _next(service, project.project_uid, document_uid, _revision(baseline_pdf, "3"), key("v3"), track)

    assert not second.replayed and not third.replayed
    assert {second.version.document_uid, third.version.document_uid} == {document_uid}
    assert _ordinals(engine, document_uid) == [
        (str(first.version.version_uid), 1),
        (str(second.version.version_uid), 2),
        (str(third.version.version_uid), 3),
    ]
    assert _current(engine, document_uid) == str(third.version.version_uid)
    assert third.version.version_ordinal == 3

    # No second document was created, and the project still counts one.
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM document WHERE project_uid = :p"),
                {"p": str(project.project_uid)},
            ).scalar_one()
            == 1
        )
    # The reads the screens use: the version list newest first, the project's document
    # list naming the new head only, and the listing count unchanged.
    listed = service.list_versions(document_uid)
    assert [v.version_uid for v in listed] == [
        third.version.version_uid,
        second.version.version_uid,
        first.version.version_uid,
    ]
    documents = service.list_documents(project.project_uid)
    assert [v.version_uid for v in documents] == [third.version.version_uid]
    (row,) = [p for p in service.list_projects() if p.project_uid == project.project_uid]
    assert row.document_count == 1

    # The title is the document's: a further version takes none, whatever its member is named.
    assert third.version.display_title == DISPLAY_TITLE


# --- nothing is inherited, nothing older is touched -------------------------------------


def _test_user(engine: Engine) -> str:
    user = str(UserUid.new())
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO app_user (user_uid, login, password_algorithm, "
                "password_iterations, password_salt, password_hash) "
                "VALUES (:u, :login, 'pbkdf2_sha256', 100000, :salt, :hash)"
            ),
            {"u": user, "login": user.lower(), "salt": "0" * 32, "hash": "0" * 64},
        )
    return user


def _facts_of(engine: Engine, version_uid) -> dict[str, Any]:
    """Every stored fact of one version, as the database holds it."""
    with engine.connect() as connection:
        version = connection.execute(
            text("SELECT * FROM document_version WHERE version_uid = :v"),
            {"v": str(version_uid)},
        ).mappings().one()
        manifest = connection.execute(
            text(
                "SELECT * FROM input_manifest_entry WHERE version_uid = :v ORDER BY role"
            ),
            {"v": str(version_uid)},
        ).mappings().all()
        classification = connection.execute(
            text(
                "SELECT * FROM document_version_classification WHERE version_uid = :v"
            ),
            {"v": str(version_uid)},
        ).mappings().all()
    return {
        "version": dict(version),
        "manifest": [dict(row) for row in manifest],
        "classification": [dict(row) for row in classification],
    }


def test_the_new_version_inherits_nothing_and_the_older_one_keeps_every_fact(
    service, project, baseline_pdf, key, track, engine, session_factory
) -> None:
    first = _first(service, project, baseline_pdf, key, track, section="AR")
    older = first.version.version_uid
    expert = _test_user(engine)
    with session_scope(session_factory) as session:
        DocumentRepository().insert_classification(
            session,
            version_uid=older,
            project_stage="P",
            section_code="AR",
            confirmed_by_user_uid=expert,
        )
    before = _facts_of(engine, older)
    assert len(before["classification"]) == 1

    second = _next(
        service, project.project_uid, first.version.document_uid, _revision(baseline_pdf, "2"), key("v2"), track
    )

    # The older version: row, manifest and classification exactly as they were.
    assert _facts_of(engine, older) == before
    reread = service.get_version(older)
    assert reread.classification is not None
    assert (reread.classification.project_stage, reread.classification.section_code) == ("P", "AR")

    # The new version: no classification row at all, so no stage and no confirmed section.
    assert _facts_of(engine, second.version.version_uid)["classification"] == []
    assert second.version.classification is None
    assert service.get_version(second.version.version_uid).classification is None
    # `document.section` is the legacy document-level fact written at the first upload. A
    # further version neither rewrites it nor turns it into a version classification.
    assert second.version.section == "AR"
    assert second.version.media_type == ACCEPTED_MEDIA_TYPE
    assert second.version.source.blob_id != first.version.source.blob_id


# --- idempotency ------------------------------------------------------------------------


def test_an_exact_retry_replays_the_same_version(
    service, project, baseline_pdf, key, track, engine
) -> None:
    first = _first(service, project, baseline_pdf, key, track)
    document_uid = first.version.document_uid
    retried_key = key("retried")
    content = _revision(baseline_pdf, "2")

    created = _next(service, project.project_uid, document_uid, content, retried_key, track)
    replayed = _next(service, project.project_uid, document_uid, content, retried_key, track)

    assert not created.replayed
    assert replayed.replayed
    assert replayed.version.version_uid == created.version.version_uid
    assert _ordinals(engine, document_uid) == [
        (str(first.version.version_uid), 1),
        (str(created.version.version_uid), 2),
    ]
    assert _command_records(engine, retried_key) == [("upload_source_document", "succeeded")]


def test_the_same_key_for_another_document_is_refused_as_reuse(
    service, project, baseline_pdf, key, track, engine
) -> None:
    one = _first(service, project, baseline_pdf, key, track)
    other = _first(
        service, project, baseline_pdf + b"\n% another set\n", key, track, idempotency_key=key("other")
    )
    shared_key = key("shared")
    content = _revision(baseline_pdf, "2")
    _next(service, project.project_uid, one.version.document_uid, content, shared_key, track)

    with pytest.raises(DomainError) as raised:
        _next(service, project.project_uid, other.version.document_uid, content, shared_key, track)

    assert raised.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
    assert _ordinals(engine, other.version.document_uid) == [(str(other.version.version_uid), 1)]
    assert _current(engine, other.version.document_uid) == str(other.version.version_uid)


def test_a_key_spent_on_a_new_document_is_not_a_next_version(
    service, project, baseline_pdf, key, track, engine
) -> None:
    """``uploadDocument`` and the next-version upload share one command type; the
    fingerprint names the document, so a key cannot be replayed across the two."""
    spent = key("spent")
    first = _first(service, project, baseline_pdf, key, track, idempotency_key=spent)

    with pytest.raises(DomainError) as raised:
        _next(
            service,
            project.project_uid,
            first.version.document_uid,
            bundle_around(baseline_pdf),
            spent,
            track,
        )

    assert raised.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
    assert _ordinals(engine, first.version.document_uid) == [(str(first.version.version_uid), 1)]


# --- refusals ---------------------------------------------------------------------------


def test_a_document_of_another_project_is_refused_before_the_key_is_claimed(
    service, project, baseline_pdf, key, track, engine
) -> None:
    first = _first(service, project, baseline_pdf, key, track)
    stranger = service.create_project("another project")
    unclaimed = key("unclaimed")
    content = _revision(baseline_pdf, "2")

    with pytest.raises(DomainError) as raised:
        _next(service, stranger.project_uid, first.version.document_uid, content, unclaimed, track)

    envelope = raised.value.envelope("corr_foreign")
    assert raised.value.code is ErrorCode.NOT_FOUND
    assert envelope.details["aggregate_type"] == "Document"
    screen_message(envelope.message)
    assert _ordinals(engine, first.version.document_uid) == [(str(first.version.version_uid), 1)]
    # The refusal came before the claim: the key is still free and nothing was staged.
    assert _command_records(engine, unclaimed) == []
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM blob")).scalar_one() == len(
            first.version.manifest
        )

    # The same key then works for the right project.
    accepted = _next(service, project.project_uid, first.version.document_uid, content, unclaimed, track)
    assert accepted.version.version_ordinal == 2


@pytest.mark.parametrize(
    ("project_known", "aggregate"),
    [(True, "Document"), (False, "Project")],
    ids=["unknown-document", "unknown-project"],
)
def test_an_unknown_target_is_refused_naming_it(
    service, project, baseline_pdf, key, track, engine, project_known, aggregate
) -> None:
    first = _first(service, project, baseline_pdf, key, track)
    project_uid = project.project_uid if project_known else ProjectUid.new()
    document_uid = DocumentUid.new() if project_known else first.version.document_uid
    unclaimed = key("ghost")

    with pytest.raises(DomainError) as raised:
        _next(service, project_uid, document_uid, _revision(baseline_pdf, "2"), unclaimed, track)

    assert raised.value.code is ErrorCode.NOT_FOUND
    assert raised.value.envelope("corr_ghost").details["aggregate_type"] == aggregate
    assert _command_records(engine, unclaimed) == []
    assert _ordinals(engine, first.version.document_uid) == [(str(first.version.version_uid), 1)]


def test_an_envelope_refusal_leaves_the_document_as_it_was(
    service, project, baseline_pdf, key, track, engine
) -> None:
    """A bare PDF is refused exactly as ``uploadDocument`` refuses it."""
    first = _first(service, project, baseline_pdf, key, track)
    refused_key = key("bare-pdf")

    with pytest.raises(DomainError) as raised:
        _next(service, project.project_uid, first.version.document_uid, baseline_pdf, refused_key, track)

    envelope = raised.value.envelope("corr_bare")
    assert raised.value.code is ErrorCode.VALIDATION_FAILED
    assert envelope.details == {"field": "file", "constraint": "portal_bundle_required"}
    assert _ordinals(engine, first.version.document_uid) == [(str(first.version.version_uid), 1)]
    assert _current(engine, first.version.document_uid) == str(first.version.version_uid)
    assert _command_records(engine, refused_key) == []


def test_publishing_into_a_missing_document_is_refused_by_the_repository(
    session_factory,
) -> None:
    """The row lock doubles as the existence check: ``not_found``, not a foreign-key fault."""
    from auditmanager.documents import ManifestEntry
    from auditmanager.storage import derive_blob_id

    digest = "a" * 64
    with pytest.raises(DomainError) as raised:
        with session_scope(session_factory) as session:
            DocumentRepository().publish_version(
                session,
                document_uid=DocumentUid.new(),
                media_type=ACCEPTED_MEDIA_TYPE,
                byte_size=1,
                sha256=digest,
                page_count=1,
                source_filename=None,
                entries=(
                    ManifestEntry(
                        role="source_document",
                        blob_id=derive_blob_id(sha256=digest, size=1),
                        sha256=digest,
                        size_bytes=1,
                        media_type=ACCEPTED_MEDIA_TYPE,
                    ),
                ),
            )
    assert raised.value.code is ErrorCode.NOT_FOUND
    assert raised.value.envelope("corr_missing").details["aggregate_type"] == "Document"


# --- concurrency ------------------------------------------------------------------------


def _lock_waiters(engine: Engine) -> int:
    with engine.connect() as connection:
        return int(
            connection.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE datname = current_database() AND wait_event_type = 'Lock'"
                )
            ).scalar_one()
        )


def test_concurrent_next_versions_get_consecutive_ordinals(
    service, project, baseline_pdf, key, track, engine
) -> None:
    """Both uploads are held at their publishing transaction, then released together.

    The document row is locked from outside until **both** uploads are waiting on a lock
    (``pg_stat_activity``), so the two publishing transactions really overlap rather than
    happening to run one after the other. With the repository's row lock they queue on the
    document and read consecutive ordinals; without it both read ``max + 1`` and the second
    insert fails on ``uq_document_version_ordinal`` -- the mutation this test reddens.
    """
    first = _first(service, project, baseline_pdf, key, track)
    document_uid = first.version.document_uid
    contents = [_revision(baseline_pdf, f"concurrent-{index}") for index in (1, 2)]
    keys = [key(f"concurrent-{index}") for index in (1, 2)]

    blocker = engine.connect()
    held = blocker.begin()
    try:
        blocker.execute(
            text("SELECT 1 FROM document WHERE document_uid = :d FOR UPDATE"),
            {"d": str(document_uid)},
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(
                    service.upload_next_version,
                    project_uid=project.project_uid,
                    document_uid=document_uid,
                    content=content,
                    source_filename="concurrent.zip",
                    idempotency_key=idempotency_key,
                )
                for content, idempotency_key in zip(contents, keys, strict=True)
            ]
            deadline = time.monotonic() + 60
            while _lock_waiters(engine) < 2:
                if time.monotonic() > deadline or any(f.done() for f in futures):
                    break
                time.sleep(0.05)
            waiting = _lock_waiters(engine)
            held.rollback()
            outcomes = [future.result(timeout=120) for future in futures]
    finally:
        if held.is_active:
            held.rollback()
        blocker.close()

    for outcome in outcomes:
        for entry in outcome.version.manifest:
            track(entry.blob_id)
    assert waiting == 2, "both uploads must have been held at the same time"
    assert sorted(o.version.version_ordinal for o in outcomes) == [2, 3]
    stored = _ordinals(engine, document_uid)
    assert [ordinal for _uid, ordinal in stored] == [1, 2, 3]
    assert {uid for uid, _ordinal in stored[1:]} == {str(o.version.version_uid) for o in outcomes}
    # The pointer names the one that committed last, which is the one with ordinal 3.
    assert _current(engine, document_uid) == stored[-1][0]
