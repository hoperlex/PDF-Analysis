"""Custody blobs belong to custody: the ingest sweep neither lists nor rejects them (`R-76`).

A norm-corpus custody admission is a durable owner of its ``blob_id``, exactly as a manifest
entry or an analysis publication intent is. Before `W54-CUSTODY-01` the sweep knew only the
latter two, so a confirmed corpus PDF was reported as an unattributed blob, and a custody
blob interrupted at ``temporary`` was refused for the wrong reason (``legacy_unattributed``).
Both are asserted here against real PostgreSQL and MinIO.
"""

from __future__ import annotations

import uuid

import pytest

from auditmanager.ingest import Reconciler
from auditmanager.norms.public import (
    NORM_SOURCE,
    AdmissionRequest,
    CustodyDispatcher,
    CustodySlot,
    DeclaredContent,
    DispatchResult,
    ManifestIndex,
    admit,
)
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import NormDocumentId
from auditmanager.storage import sha256_of
from sqlalchemy import text


class _Source:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files

    def open(self, admission):
        return self.files[admission.anchor]


class _Lost(BaseException):
    pass


def _admit(session_factory, files: dict[str, bytes], anchor: str) -> tuple[str, str]:
    data = files[anchor]
    content = DeclaredContent(sha256=sha256_of(data), size=len(data), media_type="application/pdf")
    document = str(NormDocumentId.new())
    slot = CustodySlot(NORM_SOURCE, "norm_document", document, "pdf", anchor)
    request = AdmissionRequest(
        role=NORM_SOURCE, target_id=document, anchor_kind="pdf", anchor=anchor,
        sha256=content.sha256, size=content.size, media_type=content.media_type,
    )
    with session_scope(session_factory) as session:
        outcome = admit(session, request, manifest=ManifestIndex({slot: content}))
    return outcome.admission.admission_id, outcome.admission.blob_id


def test_custody_blobs_are_neither_unattributed_nor_rejectable(
    store, session_factory, engine, reconciler: Reconciler, track
) -> None:
    files = {
        "doc_confirmed": f"%PDF-1.7\ncustody confirmed {uuid.uuid4().hex}\n".encode(),
        "doc_interrupted": f"%PDF-1.7\ncustody interrupted {uuid.uuid4().hex}\n".encode(),
    }
    confirmed_id, confirmed_blob = _admit(session_factory, files, "doc_confirmed")
    dispatcher = CustodyDispatcher(store, source=_Source(files), session_factory=session_factory)
    assert dispatcher.dispatch().ids(DispatchResult.CONFIRMED) == (confirmed_id,)
    track(confirmed_blob)

    _interrupted_id, interrupted_blob = _admit(session_factory, files, "doc_interrupted")

    def lose(point: str) -> None:
        if point == "blob_declared":
            raise _Lost(point)

    with pytest.raises(_Lost):
        CustodyDispatcher(
            store, source=_Source(files), session_factory=session_factory, checkpoint=lose
        ).dispatch()
    with engine.connect() as connection:
        states = dict(
            connection.execute(
                text("SELECT blob_id, state FROM blob WHERE blob_id IN (:a, :b)"),
                {"a": confirmed_blob, "b": interrupted_blob},
            ).all()
        )
    assert states == {confirmed_blob: "available", interrupted_blob: "temporary"}

    report = reconciler.report()
    unattributed = {str(item.blob_id) for item in report.unattributed_blobs}
    assert confirmed_blob not in unattributed, "a confirmed corpus PDF was reported as an orphan"
    assert interrupted_blob not in unattributed

    with pytest.raises(DomainError) as refusal:
        reconciler.reject_unpublished(interrupted_blob)  # type: ignore[arg-type]
    assert refusal.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    assert refusal.value.detail_fields == {
        "machine": "norm_custody_admission",
        "current_state": "custody_admission_declares_blob",
        "requested_state": "reject_blob",
    }
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT state FROM blob WHERE blob_id = :b"), {"b": interrupted_blob}
        ).scalar_one() == "temporary"
