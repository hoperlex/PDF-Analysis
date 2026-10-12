"""Two-phase custody against a real PostgreSQL and a real S3-compatible store (`R-76`).

Plan §4 Stage B item 1 names what this file proves: the five interruption points, and eight
cases -- admission before the target with binding in the target's transaction; an orphaned
admission that stays unbound; double admission as a no-op; equal bytes under two roles; a
media-type conflict; D-143's report and refusal (here) -- plus the two that live with their
own code: two concurrent declarers (D-146, ``tests/integration/ingest/test_blob_metadata.py``)
and D-142's settlement and event (``tests/integration/runs/test_durable_effect_boundaries.py``
and ``tests/integration/qa_w53/test_queue_and_effect_journal.py``).

Every case observes the database through its own connection and the bucket through a plain
``boto3`` client, never through the code under test.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from auditmanager.norms.public import (
    D143_REASON,
    NORM_SOURCE,
    AdmissionState,
    BindingDigestEntry,
    CustodyDispatcher,
    CustodyReconciler,
    CustodyRefused,
    DispatchResult,
    IncidentKind,
    admit,
    binding_digest,
    publish_bindings,
    report,
    requeue,
)
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import ErrorCode
from auditmanager.storage import (
    ROLE_SOURCE_DOCUMENT,
    StorageUnavailableError,
    VerifiedBlob,
    derive_blob_id,
    sha256_of,
)
from auditmanager.storage.public import BlobMetadataRepository
from auditmanager.storage._object_layout import canonical_key

from .conftest import CustodyKit, insert_target, new_document_id


class ProcessLost(BaseException):
    """A killed process: no ``except Exception`` in the dispatcher can turn it into state."""


def _pdf(label: str) -> bytes:
    return f"%PDF-1.7\nnorm corpus source {label} {uuid.uuid4().hex}\n".encode()


def _admit(kit: CustodyKit, request: Any):
    with session_scope(kit.session_factory) as session:
        return admit(session, request, manifest=kit.manifest)


def _dispatcher(kit: CustodyKit, *, checkpoint=None, store=None) -> CustodyDispatcher:
    return CustodyDispatcher(
        store or kit.store,
        source=kit.source,
        session_factory=kit.session_factory,
        checkpoint=checkpoint,
    )


def _bind(kit: CustodyKit, documents: list[str], *, create: bool = True):
    with session_scope(kit.session_factory) as session:
        if create:
            for document in documents:
                insert_target(session, document)
        return publish_bindings(session, NORM_SOURCE, documents)


def _report(kit: CustodyKit, **scope: Any):
    with session_scope(kit.session_factory) as session:
        return report(session, **scope)


def _admission_state(kit: CustodyKit, admission_id: str) -> str:
    return kit.scalar(
        "SELECT state FROM norm_custody_admission WHERE norm_custody_admission_id = :a",
        a=admission_id,
    )


def _blob_state(kit: CustodyKit, blob_id: str) -> str | None:
    return kit.scalar("SELECT state FROM blob WHERE blob_id = :b", b=blob_id)


def _events(kit: CustodyKit, event_type: str, aggregate_id: str | None = None) -> int:
    if aggregate_id is None:
        return kit.scalar("SELECT count(*) FROM audit_event WHERE event_type = :t", t=event_type)
    return kit.scalar(
        "SELECT count(*) FROM audit_event WHERE event_type = :t AND aggregate_id = :a",
        t=event_type,
        a=aggregate_id,
    )


def _canonical(kit: CustodyKit) -> list[str]:
    return [key for key in kit.bucket_keys() if key.startswith("blobs/")]


def _temporary(kit: CustodyKit) -> list[str]:
    return [key for key in kit.bucket_keys() if key.startswith("temporary/")]


def _available_project_blob(kit: CustodyKit, data: bytes, *, media_type: str = "application/pdf"):
    """Bytes a project upload already holds: a canonical object and an ``available`` row."""
    published = kit.store.put_blob(
        data,
        declared_sha256=sha256_of(data),
        declared_size=len(data),
        role=ROLE_SOURCE_DOCUMENT,
        media_type=media_type,
    )
    blobs = BlobMetadataRepository()
    with session_scope(kit.session_factory) as session:
        blobs.record_verified(
            session,
            VerifiedBlob(
                blob_id=published.blob_id,
                upload_token="project-upload",
                sha256=published.sha256,
                size=published.size,
                role=ROLE_SOURCE_DOCUMENT,
                media_type=media_type,
            ),
        )
        blobs.mark_available(session, published.blob_id)
    return published


# --- the five interruption points ---------------------------------------------------------

#: point -> (blob row state, canonical object present, temporary object present)
_AT_THE_POINT = {
    "admitted": (None, False, False),
    "blob_declared": ("temporary", False, False),
    "temporary_staged": ("temporary", False, True),
    "blob_verifying": ("verifying", False, True),
    "object_published": ("verifying", True, False),
}


@pytest.mark.parametrize("point", tuple(_AT_THE_POINT))
def test_a_process_lost_at_each_interruption_point_converges(custody: CustodyKit, point: str) -> None:
    document = new_document_id()
    data = _pdf(point)
    outcome = _admit(custody, custody.request(document, f"doc_{point}", data))
    admission_id, blob_id = outcome.admission.admission_id, outcome.admission.blob_id

    if point != "admitted":
        def lose(reached: str) -> None:
            if reached == point:
                raise ProcessLost(reached)

        with pytest.raises(ProcessLost, match=point):
            _dispatcher(custody, checkpoint=lose).dispatch()

    blob_state, canonical, temporary = _AT_THE_POINT[point]
    assert _admission_state(custody, admission_id) == "pending"
    assert _blob_state(custody, blob_id) == blob_state
    assert bool(_canonical(custody)) is canonical
    assert bool(_temporary(custody)) is temporary
    assert custody.scalar("SELECT count(*) FROM norm_custody_binding") == 0

    redriven = _dispatcher(custody).dispatch()
    assert redriven.ids(DispatchResult.CONFIRMED) == (admission_id,)
    assert redriven.is_idle_and_complete
    assert _admission_state(custody, admission_id) == "confirmed"
    assert _blob_state(custody, blob_id) == "available"
    assert custody.scalar("SELECT count(*) FROM blob") == 1
    assert _canonical(custody) == [canonical_key(derive_blob_id(sha256=sha256_of(data), size=len(data)))]
    assert _temporary(custody) == [], "a re-drive left a staged object behind"
    # Phase one never makes a binding visible.
    assert custody.scalar("SELECT count(*) FROM norm_custody_binding") == 0
    assert _dispatcher(custody).dispatch().steps == ()

    publication = _bind(custody, [document])
    assert [binding.blob_id for binding in publication.bound] == [blob_id]
    assert custody.store.read(publication.bound[0].blob_id) == data  # type: ignore[arg-type]


# --- case 1: admission before the target, binding with it ---------------------------------


def test_admission_precedes_its_target_and_binds_in_the_targets_transaction(
    custody: CustodyKit,
) -> None:
    document = new_document_id()
    data = _pdf("before-target")
    admission = _admit(custody, custody.request(document, "doc_before", data)).admission
    assert custody.scalar(
        "SELECT count(*) FROM norm_document WHERE norm_document_id = :d", d=document
    ) == 0, "the target exists already, so this case proves nothing"

    assert _dispatcher(custody).dispatch().ids(DispatchResult.CONFIRMED) == (admission.admission_id,)
    waiting = _report(custody)
    assert [item.admission_id for item in waiting.unbound_confirmed] == [admission.admission_id]
    assert waiting.binding_count == 0

    publication = _bind(custody, [document])
    assert len(publication.bound) == 1 and publication.already_bound == 0
    binding = publication.bound[0]
    assert (binding.role, binding.target_kind, binding.target_id, binding.anchor_kind, binding.anchor) == (
        NORM_SOURCE, "norm_document", document, "pdf", "doc_before",
    )
    assert binding.admission_id == admission.admission_id
    assert _events(custody, "norm_custody.bound", binding.binding_id) == 1

    bound = _report(custody)
    assert bound.unbound_confirmed == ()
    assert bound.binding_count == 1
    assert bound.binding_digest == binding_digest(
        [BindingDigestEntry(NORM_SOURCE, "norm_document", document, admission.blob_id, "pdf", "doc_before")]
    )


# --- case 2: an orphaned admission stays unbound -------------------------------------------


def test_an_orphaned_admission_stays_unbound_and_reported(custody: CustodyKit) -> None:
    orphan = new_document_id()
    admission = _admit(custody, custody.request(orphan, "doc_orphan", _pdf("orphan"))).admission
    _dispatcher(custody).dispatch()

    with pytest.raises(CustodyRefused) as refused:
        _bind(custody, [orphan], create=False)
    assert refused.value.reason == "target_absent"
    assert refused.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    assert custody.scalar("SELECT count(*) FROM norm_custody_binding") == 0

    # The database refuses the same binding on its own, at publication time (invariant 4).
    with pytest.raises(DBAPIError, match="target does not exist"):
        with custody.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO norm_custody_binding (norm_custody_binding_id, "
                    "norm_custody_admission_id, role, target_kind, target_id, anchor_kind, "
                    "anchor, blob_id) VALUES ('nbd_01J00000000000000000000000', :a, "
                    "'norm_source', 'norm_document', :d, 'pdf', 'doc_orphan', :b)"
                ),
                {"a": admission.admission_id, "d": orphan, "b": admission.blob_id},
            )

    unbound = _report(custody).unbound_confirmed
    assert [item.admission_id for item in unbound] == [admission.admission_id]
    assert _admission_state(custody, admission.admission_id) == "confirmed"


def test_a_binding_is_refused_while_an_admission_of_the_target_is_not_confirmed(
    custody: CustodyKit,
) -> None:
    document = new_document_id()
    _admit(custody, custody.request(document, "doc_pending", _pdf("pending")))
    with pytest.raises(CustodyRefused) as refused:
        _bind(custody, [document])
    assert refused.value.reason == "admission_not_confirmed"
    # The refusal rolled the target transaction back with it: nothing was written.
    assert custody.scalar("SELECT count(*) FROM norm_document") == 0
    assert custody.scalar("SELECT count(*) FROM norm_custody_binding") == 0


# --- case 3: double admission is a no-op ----------------------------------------------------


def test_double_admission_dispatch_and_publication_are_no_ops(custody: CustodyKit) -> None:
    document = new_document_id()
    data = _pdf("twice")
    request = custody.request(document, "doc_twice", data)
    first = _admit(custody, request)
    second = _admit(custody, request)
    assert (first.replayed, second.replayed) == (False, True)
    assert second.admission.admission_id == first.admission.admission_id
    assert custody.scalar("SELECT count(*) FROM norm_custody_admission") == 1
    assert _events(custody, "norm_custody.admitted") == 1

    assert len(_dispatcher(custody).dispatch().steps) == 1
    assert _dispatcher(custody).dispatch().steps == ()
    assert custody.scalar("SELECT count(*) FROM blob") == 1
    assert len(_canonical(custody)) == 1

    once = _bind(custody, [document])
    with session_scope(custody.session_factory) as session:
        again = publish_bindings(session, NORM_SOURCE, [document])
    assert (len(once.bound), once.already_bound) == (1, 0)
    assert (len(again.bound), again.already_bound) == (0, 1)
    assert custody.scalar("SELECT count(*) FROM norm_custody_binding") == 1
    assert _events(custody, "norm_custody.bound") == 1

    # The same slot with other bytes is a reused key, and writes nothing.
    other = custody.request(document, "doc_twice", _pdf("other"))
    with pytest.raises(CustodyRefused) as refused:
        _admit(custody, other)
    assert refused.value.reason == "slot_reuse"
    assert refused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
    assert custody.scalar("SELECT count(*) FROM norm_custody_admission") == 1


# --- case 4: equal bytes under two roles -------------------------------------------------------


def test_a_project_upload_reuses_bytes_custody_published_under_its_own_role(
    custody: CustodyKit,
) -> None:
    document = new_document_id()
    data = _pdf("custody-first")
    admission = _admit(custody, custody.request(document, "doc_shared", data)).admission
    _dispatcher(custody).dispatch()

    # Before R-76 this was `BlobAttributeConflictError`: the object recorded `norm_source`.
    project = custody.store.put_blob(
        data,
        declared_sha256=sha256_of(data),
        declared_size=len(data),
        role=ROLE_SOURCE_DOCUMENT,
        media_type="application/pdf",
    )
    assert str(project.blob_id) == admission.blob_id
    assert project.role == NORM_SOURCE, "the first publisher's role is the recorded history"
    assert len(_canonical(custody)) == 1 and _temporary(custody) == []

    binding = _bind(custody, [document]).bound[0]
    assert (binding.role, binding.blob_id) == (NORM_SOURCE, admission.blob_id)


def test_custody_reuses_bytes_a_project_upload_holds_without_rewriting_them(
    custody: CustodyKit,
) -> None:
    data = _pdf("project-first")
    published = _available_project_blob(custody, data)
    key = canonical_key(published.blob_id)
    head = custody.raw_s3.head_object(Bucket=custody.bucket, Key=key)
    witness = dict(head["Metadata"]) | {"w54-witness": "not-written-by-the-adapter"}
    custody.raw_s3.copy_object(
        Bucket=custody.bucket, Key=key, CopySource={"Bucket": custody.bucket, "Key": key},
        MetadataDirective="REPLACE", ContentType=head["ContentType"], Metadata=witness,
    )

    document = new_document_id()
    admission = _admit(custody, custody.request(document, "doc_reuse", data)).admission
    assert admission.blob_id == str(published.blob_id)
    assert _dispatcher(custody).dispatch().ids(DispatchResult.CONFIRMED) == (admission.admission_id,)
    assert custody.source.reads == 0, "an available, matching object was uploaded again"
    after = custody.raw_s3.head_object(Bucket=custody.bucket, Key=key)
    assert after["Metadata"].get("w54-witness") == "not-written-by-the-adapter"
    assert custody.store.inspect(published.blob_id).role == ROLE_SOURCE_DOCUMENT

    binding = _bind(custody, [document]).bound[0]
    assert (binding.role, binding.blob_id) == (NORM_SOURCE, str(published.blob_id))


def test_equal_bytes_at_two_anchors_share_one_blob(custody: CustodyKit) -> None:
    first, second = new_document_id(), new_document_id()
    data = _pdf("two-anchors")
    a = _admit(custody, custody.request(first, "doc_first", data)).admission
    b = _admit(custody, custody.request(second, "doc_second", data)).admission
    assert a.blob_id == b.blob_id and a.admission_id != b.admission_id
    confirmed = _dispatcher(custody).dispatch().ids(DispatchResult.CONFIRMED)
    assert set(confirmed) == {a.admission_id, b.admission_id}
    assert custody.scalar("SELECT count(*) FROM blob") == 1
    assert len(_canonical(custody)) == 1
    bound = _bind(custody, [first, second]).bound
    assert {binding.blob_id for binding in bound} == {a.blob_id}
    assert len(bound) == 2


# --- case 5: a media-type conflict ---------------------------------------------------------------


def test_a_media_type_conflict_is_refused_at_admission(custody: CustodyKit) -> None:
    data = _pdf("media-admit")
    _available_project_blob(custody, data, media_type="application/pdf")
    with pytest.raises(CustodyRefused) as refused:
        _admit(custody, custody.request(new_document_id(), "doc_png", data, media_type="image/png"))
    assert refused.value.reason == "media_type_conflict"
    assert refused.value.code is ErrorCode.CONFLICT
    assert refused.value.detail_fields == {"aggregate_type": "Blob", "conflict_reason": "media_type_conflict"}
    assert custody.scalar("SELECT count(*) FROM norm_custody_admission") == 0


def test_a_media_type_conflict_found_at_dispatch_rejects_the_admission_not_the_blob(
    custody: CustodyKit,
) -> None:
    document = new_document_id()
    data = _pdf("media-dispatch")
    admission = _admit(
        custody, custody.request(document, "doc_late", data, media_type="image/png")
    ).admission
    # Another writer stores the same bytes as a PDF before the dispatcher gets there.
    _available_project_blob(custody, data, media_type="application/pdf")

    step = _dispatcher(custody).dispatch().steps[0]
    assert (step.result, step.failure) == (DispatchResult.REJECTED, "media_type_conflict")
    assert _admission_state(custody, admission.admission_id) == "rejected"
    assert _blob_state(custody, admission.blob_id) == "available"
    assert custody.scalar("SELECT media_type FROM blob WHERE blob_id = :b", b=admission.blob_id) == "application/pdf"

    # The slot is free again: a corrected admission takes a new identity and confirms.
    corrected = _admit(custody, custody.request(document, "doc_late", data)).admission
    assert corrected.admission_id != admission.admission_id
    assert _dispatcher(custody).dispatch().ids(DispatchResult.CONFIRMED) == (corrected.admission_id,)


# --- byte mismatch: the admission is rejected, never the shared Blob row --------------------------


def test_bytes_that_differ_from_the_admission_reject_the_admission_only(custody: CustodyKit) -> None:
    document = new_document_id()
    declared = _pdf("declared")
    admission = _admit(
        custody, custody.request(document, "doc_mismatch", _pdf("served"), declared=declared)
    ).admission

    step = _dispatcher(custody).dispatch().steps[0]
    assert (step.result, step.failure) == (DispatchResult.REJECTED, "storage_integrity_error")
    assert _admission_state(custody, admission.admission_id) == "rejected"
    assert _blob_state(custody, admission.blob_id) == "temporary", "the shared Blob row was rejected"
    assert custody.bucket_keys() == []
    assert _events(custody, "norm_custody.rejected", admission.admission_id) == 1

    corrected = _admit(custody, custody.request(document, "doc_mismatch", declared)).admission
    assert corrected.blob_id == admission.blob_id
    assert _dispatcher(custody).dispatch().ids(DispatchResult.CONFIRMED) == (corrected.admission_id,)


# --- case 8: D-143 report and refusal -------------------------------------------------------------


def _rejected_blob(kit: CustodyKit, data: bytes) -> str:
    blobs = BlobMetadataRepository()
    verified = VerifiedBlob(
        blob_id=derive_blob_id(sha256=sha256_of(data), size=len(data)),
        upload_token="pre-w53-close",
        sha256=sha256_of(data),
        size=len(data),
        role=ROLE_SOURCE_DOCUMENT,
        media_type="application/pdf",
    )
    with session_scope(kit.session_factory) as session:
        blobs.record_verified(session, verified)
        blobs.mark_rejected(session, verified.blob_id)
    return str(verified.blob_id)


def test_d143_bytes_of_a_rejected_blob_are_refused_at_admission_and_reported(
    custody: CustodyKit,
) -> None:
    data = _pdf("d143-admit")
    blob_id = _rejected_blob(custody, data)

    with pytest.raises(CustodyRefused) as refused:
        _admit(custody, custody.request(new_document_id(), "doc_banned", data))
    assert refused.value.reason == D143_REASON
    assert refused.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    assert "D-143" in str(refused.value)
    assert custody.scalar("SELECT count(*) FROM norm_custody_admission") == 0

    listed = _report(custody)
    assert [(item.blob_id, item.named_by_custody) for item in listed.rejected_blobs] == [(blob_id, False)]
    assert listed.rejected_blob_count == 1
    assert _blob_state(custody, blob_id) == "rejected", "D-143 has no re-entry edge"


def test_d143_a_blob_rejected_after_admission_rejects_the_admission_at_dispatch(
    custody: CustodyKit,
) -> None:
    data = _pdf("d143-dispatch")
    admission = _admit(custody, custody.request(new_document_id(), "doc_late_ban", data)).admission
    _rejected_blob(custody, data)

    step = _dispatcher(custody).dispatch().steps[0]
    assert (step.result, step.failure) == (DispatchResult.REJECTED, D143_REASON)
    assert _blob_state(custody, admission.blob_id) == "rejected"
    listed = _report(custody)
    assert [(item.blob_id, item.named_by_custody) for item in listed.rejected_blobs] == [
        (admission.blob_id, True)
    ]
    assert [item.admission_id for item in listed.rejected_admissions] == [admission.admission_id]
    assert custody.bucket_keys() == []


# --- five tries, poisoned, requeue ----------------------------------------------------------------


class _UnreachableStore:
    """The real store, except that staging always finds the endpoint unreachable."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def stage_temporary(self, *args: Any, **kwargs: Any) -> Any:
        raise StorageUnavailableError()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def test_five_failed_tries_poison_an_admission_and_requeue_returns_it(custody: CustodyKit) -> None:
    admission = _admit(custody, custody.request(new_document_id(), "doc_flaky", _pdf("flaky"))).admission
    unreachable = _dispatcher(custody, store=_UnreachableStore(custody.store))
    results = []
    delays = []
    for _try in range(5):
        with custody.engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE norm_custody_admission SET available_at = clock_timestamp() "
                    "WHERE norm_custody_admission_id = :a"
                ),
                {"a": admission.admission_id},
            )
        step = unreachable.dispatch(until_idle=False).steps[0]
        results.append(step.result)
        delays.append(
            custody.scalar(
                "SELECT round(extract(epoch FROM available_at - updated_at)) "
                "FROM norm_custody_admission WHERE norm_custody_admission_id = :a",
                a=admission.admission_id,
            )
        )
    assert results == [DispatchResult.RETRY_SCHEDULED] * 4 + [DispatchResult.POISONED]
    assert [int(delay) for delay in delays[:4]] == [30, 300, 1800, 7200]
    assert _admission_state(custody, admission.admission_id) == "poisoned"
    assert custody.scalar(
        "SELECT last_failure FROM norm_custody_admission WHERE norm_custody_admission_id = :a",
        a=admission.admission_id,
    ) == "dependency_unavailable"
    assert [item.admission_id for item in _report(custody).poisoned] == [admission.admission_id]
    assert custody.bucket_keys() == []

    with session_scope(custody.session_factory) as session:
        assert requeue(session, [admission.admission_id]) == (admission.admission_id,)
    assert custody.scalar(
        "SELECT attempt_count FROM norm_custody_admission WHERE norm_custody_admission_id = :a",
        a=admission.admission_id,
    ) == 0
    assert _dispatcher(custody).dispatch().ids(DispatchResult.CONFIRMED) == (admission.admission_id,)

    with pytest.raises(CustodyRefused) as refused:
        with session_scope(custody.session_factory) as session:
            requeue(session, [admission.admission_id])
    assert refused.value.reason == "admission_terminal"


# --- reconcile -----------------------------------------------------------------------------------


def test_reconcile_reports_a_bound_admission_whose_object_vanished(custody: CustodyKit) -> None:
    document = new_document_id()
    admission = _admit(custody, custody.request(document, "doc_gone", _pdf("gone"))).admission
    _dispatcher(custody).dispatch()
    binding = _bind(custody, [document]).bound[0]
    reconciler = CustodyReconciler(custody.store, session_factory=custody.session_factory)
    assert reconciler.reconcile().is_clean

    custody.store._purge_published(derive_blob_id(sha256=admission.declared_sha256, size=admission.declared_size_bytes))
    found = reconciler.reconcile()
    assert [(item.kind, item.admission_id, item.binding_id) for item in found.incidents] == [
        (IncidentKind.OBJECT_MISSING, admission.admission_id, binding.binding_id)
    ]
    # Reported, never repaired: the binding and the admission stand.
    assert custody.scalar("SELECT count(*) FROM norm_custody_binding") == 1
    assert _admission_state(custody, admission.admission_id) == AdmissionState.CONFIRMED.value
