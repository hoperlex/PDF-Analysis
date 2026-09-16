"""Four reconciliation rules that no test could redden before this file.

``auditmanager.ingest.reconciliation`` was swept by nobody before wave 10.
``test_reconciliation.py`` beside this file is thorough about the *interrupted
publication* — it breaks the real sequence at the real point and reads the resulting
state out of PostgreSQL and MinIO — but it reaches one of the four things ``Reconciler``
claims to establish, and three of the module's own stated decisions had nothing asking
about them at all.

``W10-RUN`` mutated each rule below away on a copy of ``src/`` (imported under
``pythonpath``, with ``auditmanager.__file__`` printed and checked to resolve under the
copy) and ran ``tests/integration/runs``, ``tests/integration/ingest``,
``tests/integration/api``, ``tests/e2e``, ``tests/integration/composition``,
``tests/integration/p02_journey``, ``tests/integration/storage``,
``tests/integration/exports`` and ``tests/integration/db`` against each. Nothing failed:

* ``verify_version``'s ``if published.sha256 != entry.sha256 or published.size !=
  entry.size_bytes:`` → ``if False:``. The docstring's second sentence — "and also when
  the store's recorded checksum disagrees with the manifest's" — was unchecked. Only the
  *absent* object was covered, by ``_purge_published``.
* ``_AVAILABLE_WITHOUT_MANIFEST``'s ``WHERE b.state = 'available'`` → ``WHERE false AND
  …``. The whole ``detached`` half of ``report()`` — an ``available`` blob that no
  manifest references — produced nothing and no assertion noticed.
* ``_object_exists``'s ``raise domain_error_from_storage(exc)`` → ``return False``. The
  comment says an unreachable store "must not be reported as 'the object is gone': that
  would turn a transient outage into a permanent integrity verdict". It could be.
* ``report()``'s default ``stale_command_age="1 hour"`` → ``"9999 hours"``. Every call in
  the suite passed the argument explicitly, so the default was a number nobody read.

Everything asserted here is a literal, or a value this test computed from bytes it built
itself, or a constant the production code exports as the contract's own spelling. Nothing
imports a value from ``auditmanager.ingest.reconciliation`` and compares it to itself.

Which rule refused, not merely that one did
-------------------------------------------
``storage_integrity_error`` is the answer to *three* different faults in this tree — an
absent object, a stored/manifest disagreement, and a manifest with no source entry.
Asserting the code alone would pass whichever fired, which is exactly how wave 9's
``details["field"]`` assertion let a deleted check survive. Each case below asserts the
**details** that distinguish it, and the two halves of the disagreement guard's single
``or`` are reached one at a time so that deleting either one reddens something.

Nothing is added to a corpus
----------------------------
``fixtures/synthetic/ar/`` is frozen evidence. Every byte these tests need beyond the
baseline is built in the process and never written to disk.
"""

from __future__ import annotations

import secrets
from dataclasses import replace

import pytest
from sqlalchemy import text

from auditmanager.documents import MANIFEST_ROLE_SOURCE_DOCUMENT, ROLE_SOURCE_DOCUMENT
from auditmanager.ingest import Reconciler
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode, screen_message
from auditmanager.storage import (
    StorageUnavailableError,
    derive_blob_id,
    parse_blob_role,
    sha256_of,
)
from auditmanager.storage.blob_repository import BlobMetadataRepository

DISPLAY_TITLE = "Annual report 2026"
SOURCE_FILENAME = "annual_report_2026.pdf"


class _Delegating:
    """Everything the real adapter does, except what a subclass overrides."""

    def __init__(self, inner) -> None:
        self._inner = inner

    def __getattr__(self, name):
        return getattr(self._inner, name)


class UnreachableStore(_Delegating):
    """The store is up-and-down, not empty: every inspection fails at the transport.

    ``StorageUnavailableError`` is the adapter's own transport failure and carries
    ``dependency_unavailable`` as a class constant, so nothing here invents a code.
    """

    def inspect(self, blob_id):
        raise StorageUnavailableError()


def _unique_pdf(baseline: bytes) -> bytes:
    """The corpus baseline with a unique comment appended: content nobody has published.

    ``blob_id`` is derived from ``(sha256, size)`` and publication is idempotent by that
    identity, so a test that uploaded the shared baseline would find the canonical object
    already there from an earlier run and could not control what it holds. A comment after
    ``%%EOF`` does not move ``startxref``, so the document still parses and still reports
    its real page count to the admission probe.
    """
    return baseline + b"\n% " + secrets.token_hex(16).encode("ascii") + b"\n"


def _publish_impostor_at(store, *, blob_id, content: bytes, record_sha256=None):
    """Put ``content`` at the canonical location of ``blob_id``, through the real adapter.

    Every step is the port's own public surface — ``stage_temporary``,
    ``verify_temporary``, ``publish``. The bytes really are staged and really are verified
    against their own declared digest; the one thing forced is the *identity* they are
    published under, which is a :func:`dataclasses.replace` on the ``VerifiedBlob`` the
    adapter handed back. Nothing here touches the private object layout and nothing writes
    an object behind the adapter's back.

    ``record_sha256`` overrides the digest written into the object's metadata. That is how
    the two halves of the guard's single ``or`` are reached one at a time: leave it alone
    and the digest disagrees with the manifest, set it to the manifest's own digest and
    only the size does.
    """
    digest = sha256_of(content)
    temporary = store.stage_temporary(
        content,
        declared_sha256=digest,
        declared_size=len(content),
        role=parse_blob_role(ROLE_SOURCE_DOCUMENT),
        media_type="application/pdf",
    )
    verified = store.verify_temporary(temporary)
    return store.publish(
        replace(
            verified,
            blob_id=blob_id,
            sha256=digest if record_sha256 is None else record_sha256,
        )
    )


# --- a published version whose bytes are present and are the wrong bytes -------


def test_a_version_whose_stored_checksum_disagrees_with_its_manifest_is_refused(
    store, service, project, baseline_pdf, key, track, reconciler
) -> None:
    """The *other* integrity failure: the object is there, and it is not the right object.

    ``test_reconciliation.py`` proves the absent-object case by deleting the object. This
    one leaves an object at the canonical location and changes what it is — the shape a
    restored-from-the-wrong-backup bucket produces, and the one this module's docstring
    claims to answer while nothing asked about it.

    The impostor is **the same length** as the document, so the size half of the guard's
    ``or`` cannot fire and the digest comparison is the only thing that can refuse. The
    next test is the mirror image.
    """
    content = _unique_pdf(baseline_pdf)
    honest_sha256 = sha256_of(content)
    blob_id = track(derive_blob_id(sha256=honest_sha256, size=len(content)))

    impostor_bytes = content[:-1] + bytes([content[-1] ^ 0xFF])
    assert len(impostor_bytes) == len(content)
    impostor_sha256 = sha256_of(impostor_bytes)
    assert impostor_sha256 != honest_sha256
    # Published under the document's identity *before* the document is uploaded:
    # publication is idempotent by (sha256, size), so the upload that follows adopts this
    # object instead of writing its own, exactly as a re-upload adopts an orphan.
    _publish_impostor_at(store, blob_id=blob_id, content=impostor_bytes)

    outcome = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=content,
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=key("wrong-bytes"),
    )

    # The precondition: the manifest froze the honest digest and the honest length, and
    # the store holds something else of the same length under that identity.
    entry = outcome.version.source
    assert entry.blob_id == blob_id
    assert entry.sha256 == honest_sha256
    assert entry.size_bytes == len(content)

    with pytest.raises(DomainError) as raised:
        reconciler.verify_version(outcome.version.version_uid)

    failure = raised.value
    envelope = failure.envelope("corr_disagree")
    assert failure.code is ErrorCode.STORAGE_INTEGRITY_ERROR
    assert envelope.retryable is False
    # The details say *which* integrity failure this is. An absent object reports no
    # ``actual_sha256`` — there is nothing to have hashed. A disagreement reports both
    # digests, and it is the only one of the three that does.
    assert envelope.details["blob_id"] == str(blob_id)
    assert envelope.details["role"] == MANIFEST_ROLE_SOURCE_DOCUMENT
    assert envelope.details["expected_sha256"] == honest_sha256
    assert envelope.details["actual_sha256"] == impostor_sha256
    screen_message(envelope.message)

    # The immutable rows are untouched: a version is never repaired, and a corrected
    # source file is a new ``version_uid``.
    assert service.get_version(outcome.version.version_uid).source.sha256 == honest_sha256

    # ``read_source_bytes`` does **not** answer this one, and that is recorded as a
    # product defect in ``docs/program/reviews/W10-RUN.md`` rather than asserted here as
    # if it were the contract. The adapter re-hashes what it read and compares it to the
    # object's *own* recorded digest, which agrees; the manifest's digest is never
    # consulted on the read path. So a caller receives the impostor bytes with no error,
    # while reconciliation over the same version refuses. This assertion pins the
    # behaviour that exists so the defect cannot be closed silently: the day the read
    # path starts consulting the manifest, this line fails and points at the note.
    returned = service.read_source_bytes(outcome.version.version_uid)
    assert sha256_of(returned) == impostor_sha256, (
        "read_source_bytes returns whatever the store holds under the blob_id; see "
        "W10-RUN's defect note. If this line fails because the read now refuses, the "
        "defect has been fixed and this expectation should become a pytest.raises"
    )


def test_a_version_whose_stored_size_disagrees_with_its_manifest_is_refused(
    store, service, project, baseline_pdf, key, track, reconciler
) -> None:
    """The same clause's other half, reached with the digests left agreeing.

    The guard is one ``or``, and a suite that only ever moved the digest would stay green
    if the size comparison were deleted. Here the object records the manifest's own digest
    and a different length, which is the shape a truncated restore leaves: the bytes look
    right by name and are not all there.
    """
    content = _unique_pdf(baseline_pdf)
    honest_sha256 = sha256_of(content)
    blob_id = track(derive_blob_id(sha256=honest_sha256, size=len(content)))

    truncated = content[: len(content) // 2]
    assert len(truncated) != len(content)
    _publish_impostor_at(
        store, blob_id=blob_id, content=truncated, record_sha256=honest_sha256
    )

    outcome = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=content,
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=key("wrong-size"),
    )
    entry = outcome.version.source
    assert entry.sha256 == honest_sha256
    assert entry.size_bytes == len(content)

    with pytest.raises(DomainError) as raised:
        reconciler.verify_version(outcome.version.version_uid)

    failure = raised.value
    envelope = failure.envelope("corr_short")
    assert failure.code is ErrorCode.STORAGE_INTEGRITY_ERROR
    assert envelope.details["blob_id"] == str(blob_id)
    # The digests agree, so this refusal came from the size comparison and nothing else.
    # Asserting that is the difference between guarding one ``or`` and guarding two.
    assert envelope.details["expected_sha256"] == honest_sha256
    assert envelope.details["actual_sha256"] == honest_sha256


# --- an available blob no manifest references ---------------------------------


def test_an_available_blob_that_no_manifest_references_is_reported_as_an_orphan(
    store, session_factory, reconciler, track, engine
) -> None:
    """The ``detached`` half of ``report()``, which nothing reached.

    ``test_reconciliation.py``'s orphan is a blob stuck in ``verifying`` — the crash
    between publish and commit — and that path goes through ``unsettled()``. This is the
    other shape the query exists for: a blob that completed its own lifecycle to
    ``available`` and whose version transaction is not there. Those bytes are reachable by
    nothing, and an operator who cannot see them cannot decide about them.

    Built by performing the publication's steps 2 to 6 **without** the version and
    manifest, through the same public repository and store the service uses. No SQL writes
    a state the machine would not permit: ``temporary -> verifying -> available`` are all
    declared edges and the ``AM001`` trigger checks every one.
    """
    blobs = BlobMetadataRepository()
    content = b"%PDF-1.7\n" + secrets.token_hex(16).encode("ascii") + b"\n%%EOF\n"
    digest = sha256_of(content)

    temporary = store.stage_temporary(
        content,
        declared_sha256=digest,
        declared_size=len(content),
        role=parse_blob_role(ROLE_SOURCE_DOCUMENT),
        media_type="application/pdf",
    )
    verified = store.verify_temporary(temporary)
    track(verified.blob_id)
    with session_scope(session_factory) as session:
        blobs.record_verified(session, verified)
    store.publish(verified)
    with session_scope(session_factory) as session:
        blobs.mark_available(session, verified.blob_id)

    # The precondition, read straight out of PostgreSQL: available, and referenced by no
    # manifest entry at all.
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT state FROM blob WHERE blob_id = :b"),
                {"b": str(verified.blob_id)},
            ).scalar_one()
            == "available"
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM input_manifest_entry WHERE blob_id = :b"),
                {"b": str(verified.blob_id)},
            ).scalar_one()
            == 0
        )

    report = reconciler.report()

    assert [item.blob_id for item in report.orphan_objects] == [verified.blob_id]
    orphan = report.orphan_objects[0]
    # ``recorded_state`` is what tells an operator which of the two orphan shapes this is.
    # ``verifying`` is the interrupted publication; ``available`` is this one. A report
    # that flattened them would not distinguish "finish it" from "look at it".
    assert orphan.recorded_state == "available"
    assert orphan.sha256 == digest
    assert orphan.size_bytes == len(content)
    assert report.unpublished_records == ()
    assert report.missing_objects == ()
    assert not report.is_clean
    assert report.describe() == (
        "orphan_objects=1 unpublished_records=0 missing_objects=0 stale_commands=0"
    )


# --- an unreachable store is not an integrity verdict --------------------------


def test_an_unreachable_store_is_reported_as_an_outage_not_as_missing_bytes(
    service, project, baseline_pdf, key, track, store, session_factory
) -> None:
    """A transient outage must not be recorded as "the bytes are gone".

    ``missing_objects`` means a published version is no longer reproducible, which is this
    module's own "serious one" and is not repairable. Deriving it from a store that merely
    could not be reached would manufacture that verdict out of a network blip.

    The two answers are told apart by **code**, not by the shape of the result: an outage
    is ``dependency_unavailable`` and is retryable, a missing object is
    ``storage_integrity_error`` and is not. Both come off the envelope, which reads them
    from the frozen catalog rather than from anything restated here.
    """
    outcome = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=baseline_pdf,
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=key("outage"),
    )
    track(outcome.version.source.blob_id)

    blind = Reconciler(UnreachableStore(store), session_factory=session_factory)

    with pytest.raises(DomainError) as raised:
        blind.report()
    envelope = raised.value.envelope("corr_outage")
    assert raised.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert envelope.retryable is True, (
        "an outage is worth retrying; an integrity verdict never is, and that difference "
        "is the whole of what this rule protects"
    )
    screen_message(envelope.message)

    with pytest.raises(DomainError) as verify_failure:
        blind.verify_version(outcome.version.version_uid)
    assert verify_failure.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE

    # The control: with a reachable store the same instance is clean, so the assertions
    # above cannot be passing because the reconciler fails at everything.
    healthy = Reconciler(store, session_factory=session_factory)
    assert healthy.report().is_clean
    healthy.verify_version(outcome.version.version_uid)


# --- the default staleness threshold -------------------------------------------


def _insert_aged_command(engine, command_id: str, key_value: str, age: str) -> None:
    """One ``in_progress`` command record, aged by rewriting its clock.

    The state guard permits no move back into ``in_progress``, so a stranded record is
    produced by inserting a fresh one in the declared initial state and backdating it —
    the same technique ``test_reconciliation.py`` uses for its own stale-command case.
    """
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO command_record "
                "(command_id, command_type, idempotency_key, payload_fingerprint, "
                " state, created_at, updated_at) "
                "VALUES (:c, 'upload_source_document', :k, :f, 'in_progress', "
                f"        now() - interval '{age}', now() - interval '{age}')"
            ),
            {"c": command_id, "k": key_value, "f": "0" * 64},
        )


def test_the_default_staleness_threshold_is_one_hour(engine, reconciler) -> None:
    """``report()`` called with no argument uses one hour, and that number is the rule.

    Every existing call passes ``stale_command_age=`` explicitly, so the default could be
    anything and the suite would not notice — it was raised to ``"9999 hours"`` and
    nothing failed. An operator running a bare ``report()`` is the case the default exists
    for, and a default nobody reads is a decision nobody made.

    Both sides of the boundary are written out: fifty-nine minutes is not stale,
    sixty-one minutes is.
    """
    _insert_aged_command(
        engine, "cmd_00000000000000000000000001", "fresh-executor", "59 minutes"
    )
    _insert_aged_command(
        engine, "cmd_00000000000000000000000002", "stranded-executor", "61 minutes"
    )

    assert [str(item) for item in reconciler.report().stale_commands] == [
        "cmd_00000000000000000000000002"
    ], (
        "the bare default must be one hour: the 61-minute record is stranded and the "
        "59-minute one is still somebody's running command"
    )

    # The same boundary through the explicit argument, so the default is shown to be the
    # one-hour behaviour rather than merely *a* behaviour that splits these two records.
    assert [
        str(i) for i in reconciler.report(stale_command_age="1 hour").stale_commands
    ] == ["cmd_00000000000000000000000002"]
    assert reconciler.report(stale_command_age="2 hours").stale_commands == ()
    assert {
        str(i) for i in reconciler.report(stale_command_age="30 minutes").stale_commands
    } == {"cmd_00000000000000000000000001", "cmd_00000000000000000000000002"}


def test_abandoning_stale_commands_also_defaults_to_one_hour(engine, reconciler) -> None:
    """The repair half of the same threshold, which shares no default with the report half.

    ``report`` and ``abandon_stale_commands`` each carry their own. A change that moved
    one and not the other would leave an operator a report and a repair that disagree
    about which records they are talking about.
    """
    _insert_aged_command(
        engine, "cmd_00000000000000000000000003", "fresh-two", "59 minutes"
    )
    _insert_aged_command(
        engine, "cmd_00000000000000000000000004", "stranded-two", "61 minutes"
    )

    assert [str(item) for item in reconciler.abandon_stale_commands()] == [
        "cmd_00000000000000000000000004"
    ]

    with engine.connect() as connection:
        states = dict(
            connection.execute(
                text(
                    "SELECT command_id, state FROM command_record "
                    "WHERE command_id IN (:a, :b)"
                ),
                {
                    "a": "cmd_00000000000000000000000003",
                    "b": "cmd_00000000000000000000000004",
                },
            ).all()
        )
    assert states == {
        "cmd_00000000000000000000000003": "in_progress",
        "cmd_00000000000000000000000004": "abandoned",
    }
