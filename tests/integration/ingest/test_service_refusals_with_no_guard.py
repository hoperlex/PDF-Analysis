"""Five refusals `IngestService` makes that nothing in the tree could redden.

``auditmanager.ingest.service`` was swept by nobody before wave 10. Its happy path,
its idempotency and its interrupted publication are all well covered; what was not
covered is what it refuses. ``W10-RUN`` mutated each rule below away on a copy of
``src/`` — ``auditmanager.__file__`` printed and checked to resolve under the copy on
every run — and ran ``tests/integration/runs`` and ``tests/integration/ingest`` (123
tests) plus ``tests/integration/api``, ``tests/e2e``, ``tests/integration/composition``,
``tests/integration/p02_journey``, ``tests/integration/storage``,
``tests/integration/exports`` and ``tests/integration/db``. Nothing failed:

* ``if owner != project_uid: raise DomainError(NOT_FOUND, aggregate_type="Document")``
  → ``if False:``. A caller could add a version to a document belonging to **another
  project** by naming it, and the new version would then be reachable through the wrong
  project's listing.
* ``_replayed_version_uid``'s ``if not isinstance(raw, str):`` → ``if False:``. A
  succeeded upload command whose outcome cannot say what it created replayed as a
  ``TypeError`` from inside ``VersionUid`` instead of as ``idempotency_key_stale``.
* the same check in ``create_project_under_key``'s replay branch.
* ``require_source_entry``'s ``storage_integrity_error`` for a version whose manifest
  names no source document — the code was swapped for ``not_found`` and nothing noticed.
* ``if temporary is not None: self._discard_quietly(temporary)`` → ``if False:``. Staged
  bytes that will never be published were left in the bucket for ever. (This mutation
  leaves real residue: the object it stranded then failed
  ``tests/integration/storage``'s two "leaves no temporary object" tests on the *next*
  run, which is how it was noticed at all. It was deleted by identity afterwards.)

Which rule refused
------------------
``not_found`` is the answer to an unknown project *and* to a document owned by another
project, and ``storage_integrity_error`` is the answer to three separate faults. A test
asserting only the code would pass whichever fired. Every case below asserts the detail
that names the aggregate or the role, so a deleted check reddens rather than being
covered by its neighbour.
"""

from __future__ import annotations

import secrets

import pytest
from sqlalchemy import text

from auditmanager.documents import ROLE_SOURCE_DOCUMENT
from auditmanager.ingest import IngestService
from auditmanager.shared.errors import DomainError, ErrorCode, screen_message
from auditmanager.shared.identity import DocumentUid, VersionUid
from auditmanager.storage import StorageUnavailableError

DISPLAY_TITLE = "Annual report 2026"
SOURCE_FILENAME = "annual_report_2026.pdf"


class _Delegating:
    def __init__(self, inner) -> None:
        self._inner = inner

    def __getattr__(self, name):
        return getattr(self._inner, name)


class LoseTheStoreAfterStaging(_Delegating):
    """Stage for real, then fail before anything canonical exists.

    ``verify_temporary`` is the first call after staging, so this is the failure window in
    which ``temporary`` is still held and the staged object is still in the bucket. The
    adapter cleans up after *its own* verification mismatches; this failure is not one of
    those, so the discard has to come from the service.
    """

    def verify_temporary(self, temporary):
        raise StorageUnavailableError()


def _temporary_keys(bucket_keys) -> list[str]:
    """Every staged-but-unpublished object currently in the lane bucket.

    ``temporary/`` is the adapter's top-level prefix for staged uploads and is the same
    string ``tests/integration/storage`` asserts on. Using the prefix rather than a
    computed key is what makes "did this failure leave anything staged?" a question about
    the bucket rather than about a naming convention.
    """
    return [key for key in bucket_keys() if key.startswith("temporary/")]


# --- a document that belongs to somebody else ---------------------------------


def test_a_document_from_another_project_is_refused_and_names_the_document(
    service, baseline_pdf, key, track, engine
) -> None:
    """Naming another project's document must not add a version to it.

    ``document_uid`` is an optional argument to ``upload_single_pdf``: supplied, it says
    "this is a new version of that existing document" instead of "create a new document".
    Nothing but this check ties the named document to the project the caller also named,
    and the project is what every listing and every export scopes by. With the check gone
    a version lands under a document the caller has no business touching, and appears in
    the other project's listing.

    The refusal is asserted by the aggregate it names, not merely by its code: an unknown
    *project* is also ``not_found`` from three lines earlier, and a test that asserted the
    code alone would pass with this check deleted.
    """
    owner = service.create_project("owning project")
    stranger = service.create_project("some other project")

    first = service.upload_single_pdf(
        project_uid=owner.project_uid,
        content=baseline_pdf,
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=key("owned"),
    )
    track(first.version.source.blob_id)
    document_uid = first.version.document_uid

    with pytest.raises(DomainError) as raised:
        service.upload_single_pdf(
            project_uid=stranger.project_uid,
            content=baseline_pdf + b"\n% a second version\n",
            source_filename=SOURCE_FILENAME,
            display_title=DISPLAY_TITLE,
            idempotency_key=key("cross-project"),
            document_uid=document_uid,
        )

    failure = raised.value
    envelope = failure.envelope("corr_cross")
    assert failure.code is ErrorCode.NOT_FOUND
    assert envelope.details["aggregate_type"] == "Document", (
        "an unknown project is also not_found, from the check three lines above this "
        "one; the aggregate is what says which rule refused"
    )
    screen_message(envelope.message)

    # Nothing was added anywhere, and the owner's document still has exactly its one
    # version. Read out of PostgreSQL, not from the return value of the call that failed.
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM document_version WHERE document_uid = :d"),
                {"d": str(document_uid)},
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM document WHERE project_uid = :p"),
                {"p": str(stranger.project_uid)},
            ).scalar_one()
            == 0
        )


def test_a_document_from_the_same_project_is_accepted(
    service, project, baseline_pdf, key, track
) -> None:
    """The mirror image: the check refuses the wrong owner, not every named document.

    Without this the test above would pass against a service that refused ``document_uid``
    outright, which would be a different — and also wrong — behaviour.
    """
    first = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=baseline_pdf,
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=key("same-project-1"),
    )
    track(first.version.source.blob_id)

    second = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=baseline_pdf + b"\n% a second version\n",
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=key("same-project-2"),
        document_uid=first.version.document_uid,
    )
    track(second.version.source.blob_id)

    assert second.version.document_uid == first.version.document_uid
    assert second.version.version_uid != first.version.version_uid


def test_an_unknown_document_is_refused_and_also_names_the_document(
    service, project, baseline_pdf, key
) -> None:
    """A ``document_uid`` that resolves to nothing is the same answer from the same guard."""
    with pytest.raises(DomainError) as raised:
        service.upload_single_pdf(
            project_uid=project.project_uid,
            content=baseline_pdf,
            source_filename=SOURCE_FILENAME,
            display_title=DISPLAY_TITLE,
            idempotency_key=key("ghost-document"),
            document_uid=DocumentUid.new(),
        )
    envelope = raised.value.envelope("corr_ghost")
    assert raised.value.code is ErrorCode.NOT_FOUND
    assert envelope.details["aggregate_type"] == "Document"


# --- a replay that cannot say what it created ----------------------------------


def _blank_the_outcome(engine, idempotency_key: str) -> None:
    """Leave one succeeded command record with an outcome that names nothing.

    ``ck_command_record_succeeded_has_outcome`` refuses a NULL outcome on a succeeded
    row, so the empty object is the weakest thing the schema admits — and is exactly what
    a row written by an older or a partly-deployed version of this command would look
    like. The row's frozen columns and its state are untouched, so no trigger is bypassed:
    ``am_guard_frozen_columns`` covers ``command_id``, ``command_type``,
    ``idempotency_key`` and ``payload_fingerprint``, and none of them is written here.
    """
    with engine.begin() as connection:
        updated = connection.execute(
            text(
                "UPDATE command_record SET outcome = '{}'::jsonb "
                "WHERE idempotency_key = :k AND state = 'succeeded'"
            ),
            {"k": idempotency_key},
        ).rowcount
    assert updated == 1, "expected exactly one succeeded command record to blank"


def test_an_upload_replay_whose_outcome_names_no_version_is_stale(
    service, project, baseline_pdf, key, track, engine
) -> None:
    """A key whose outcome cannot be established is ``idempotency_key_stale``, not a crash.

    The catalog's own meaning of the code is that nothing can say what the command
    created. Unguarded, the missing value reached ``VersionUid(raw)`` and surfaced as a
    ``TypeError`` out of the identity kernel — an unclassified fault, which the service's
    own ``_as_domain_error`` would have turned into ``internal_error`` for a caller. The
    difference matters to the caller: ``idempotency_key_stale`` says "retry under a new
    key", and ``internal_error`` says nothing at all.
    """
    label = f"stale-outcome-{secrets.token_hex(6)}"
    upload_key = key(label)
    outcome = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=baseline_pdf,
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=upload_key,
    )
    track(outcome.version.source.blob_id)

    # The precondition: the same key replays cleanly while the outcome is intact.
    replayed = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=baseline_pdf,
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=upload_key,
    )
    assert replayed.replayed is True
    assert replayed.version.version_uid == outcome.version.version_uid

    _blank_the_outcome(engine, str(upload_key))

    with pytest.raises(DomainError) as raised:
        service.upload_single_pdf(
            project_uid=project.project_uid,
            content=baseline_pdf,
            source_filename=SOURCE_FILENAME,
            display_title=DISPLAY_TITLE,
            idempotency_key=upload_key,
        )

    failure = raised.value
    envelope = failure.envelope("corr_stale_upload")
    assert failure.code is ErrorCode.IDEMPOTENCY_KEY_STALE
    assert envelope.details["command_type"] == "upload_source_document", (
        "the same code answers a start_audit_run replay and a create_project replay; "
        "the command type is what says which one this is"
    )
    screen_message(envelope.message)


def test_a_create_project_replay_whose_outcome_names_no_project_is_stale(
    service, engine
) -> None:
    """The same rule on the other command, which carries its own copy of the check.

    ``createProject`` and ``uploadSourceDocument`` each derive their replay value
    separately. A wave that fixed one and not the other would leave two commands
    disagreeing about what an unreadable outcome means.
    """
    project_key = f"create-project-{secrets.token_hex(8)}"
    created, replayed_flag = service.create_project_under_key(
        name="a project under a key", idempotency_key=project_key
    )
    assert replayed_flag is False

    again, replayed_flag = service.create_project_under_key(
        name="a project under a key", idempotency_key=project_key
    )
    assert replayed_flag is True
    assert again.project_uid == created.project_uid

    _blank_the_outcome(engine, project_key)

    with pytest.raises(DomainError) as raised:
        service.create_project_under_key(
            name="a project under a key", idempotency_key=project_key
        )
    envelope = raised.value.envelope("corr_stale_project")
    assert raised.value.code is ErrorCode.IDEMPOTENCY_KEY_STALE
    assert envelope.details["command_type"] == "create_project"


# --- a version whose manifest names no source document -------------------------


def test_a_version_with_no_source_entry_is_an_integrity_failure_not_a_missing_version(
    service, project, engine
) -> None:
    """A version that exists and cannot be read is an integrity failure, and says so.

    ``not_found`` would be wrong and actively misleading: the version row is right there,
    and a caller told "no such version" would look for a lookup mistake rather than for
    the bytes a published manifest promised. This is the same distinction
    ``read_source_bytes`` already draws for an *absent object*, applied to the case where
    the manifest itself is the thing that is incomplete.

    The row is written with raw SQL because no code path can produce one:
    ``_commit_publication`` always writes the source entry, and manifest entries are
    immutable and undeletable (``AM003``). That the fault has to be built by hand is not a
    reason to leave the branch unguarded — it is a database that a partial restore, or an
    import written later, can present.
    """
    document_uid = str(DocumentUid.new())
    version_uid = str(VersionUid.new())
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO document (document_uid, project_uid, display_title) "
                "VALUES (:d, :p, 'a document whose manifest is incomplete')"
            ),
            {"d": document_uid, "p": str(project.project_uid)},
        )
        connection.execute(
            text(
                "INSERT INTO document_version (version_uid, document_uid, "
                "version_ordinal, media_type, byte_size, sha256, page_count) "
                "VALUES (:v, :d, 1, 'application/pdf', 1024, :s, 12)"
            ),
            {"v": version_uid, "d": document_uid, "s": "a" * 64},
        )

    parsed = VersionUid.parse(version_uid)
    # The version really is readable as a row; only its manifest is empty.
    assert str(service.get_version(parsed).version_uid) == version_uid
    assert service.manifest_for(parsed) == ()

    for call in (service.require_source_entry, service.read_source_bytes):
        with pytest.raises(DomainError) as raised:
            call(parsed)
        envelope = raised.value.envelope("corr_no_source")
        assert raised.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR, (
            "the version exists; reporting not_found would send the caller looking for "
            "the wrong problem"
        )
        # The blob role, not the manifest-entry role: there is no manifest entry to take
        # a role from, so this refusal reports the role that is *missing*. That spelling
        # is what distinguishes this integrity failure from the other two.
        assert envelope.details["role"] == ROLE_SOURCE_DOCUMENT
        assert "blob_id" not in envelope.details, (
            "nothing names a blob here; an absent object reports one and a checksum "
            "disagreement reports one, and this is neither"
        )
        screen_message(envelope.message)


# --- staged bytes that will never be published ---------------------------------


def test_a_failure_after_staging_leaves_no_temporary_object(
    store, session_factory, project, baseline_pdf, key, bucket_keys, engine
) -> None:
    """Every failure path discards what it staged, including ones the adapter does not.

    The adapter removes the staged bytes itself when *its own* verification finds a
    mismatch. It does not, and cannot, know about a failure that happens for any other
    reason, and the service's ``except`` block is the only thing that cleans up after
    those. Unguarded, that block was removed and the whole battery stayed green — the
    stranded object only surfaced one run later, as somebody else's failing test.

    Asserted against the ``temporary/`` prefix before and after, so this measures what the
    bucket holds rather than what the service believes it did.
    """
    assert _temporary_keys(bucket_keys) == [], (
        "this lane's bucket must start with nothing staged, or the assertion below "
        "would be about somebody else's residue"
    )

    service = IngestService(
        LoseTheStoreAfterStaging(store), session_factory=session_factory
    )
    content = baseline_pdf + b"\n% " + secrets.token_hex(16).encode("ascii") + b"\n"

    with pytest.raises(DomainError) as raised:
        service.upload_single_pdf(
            project_uid=project.project_uid,
            content=content,
            source_filename=SOURCE_FILENAME,
            display_title=DISPLAY_TITLE,
            idempotency_key=key("stranded-bytes"),
        )
    assert raised.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE

    assert _temporary_keys(bucket_keys) == [], (
        "the staged object was never published and never will be; leaving it costs "
        "storage for ever and no later run can identify it"
    )

    # And nothing canonical was written either, so the discard is not covering for a
    # half-finished publication.
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT count(*) FROM blob")).scalar_one() == 0
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM document_version")
            ).scalar_one()
            == 0
        )
        state, error_code = connection.execute(
            text("SELECT state, error_code FROM command_record")
        ).one()
    assert (state, error_code) == ("failed", "dependency_unavailable")
