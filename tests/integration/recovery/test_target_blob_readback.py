"""The restored target must yield the full bytes of every available DB Blob."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import Iterator

import pytest

from auditmanager.storage.public import BlobId, BlobNotFoundError, canonical_object_key_for_recovery, derive_blob_id
from scripts.recovery.blob_object_binding import BoundBlobObject
from scripts.recovery.blob_reference_audit import BlobFact, BlobReferenceAudit
from scripts.recovery.offline_restore_audit import OfflineRestoreEvidence
from scripts.recovery.target_blob_readback import TargetBlobReadbackRefused, audit_target_blob_readback


def _evidence(payloads: tuple[bytes, ...]) -> OfflineRestoreEvidence:
    facts = []
    objects = []
    for payload in payloads:
        sha = hashlib.sha256(payload).hexdigest()
        blob_id = str(derive_blob_id(sha256=sha, size=len(payload)))
        facts.append(BlobFact(blob_id, sha, len(payload), "application/pdf"))
        objects.append(BoundBlobObject(blob_id, canonical_object_key_for_recovery(BlobId(blob_id)), sha, len(payload)))
    return OfflineRestoreEvidence(BlobReferenceAudit((), tuple(facts)), tuple(objects))


class FakeTarget:
    def __init__(self, bodies: dict[str, bytes]) -> None:
        self.bodies = bodies
        self.calls: list[tuple[str, str, int, object]] = []
        self.closed: list[str] = []

    def open_stream(self, blob_id: BlobId, *, expected_sha256: str,
                    expected_size: int, window: object = None) -> Iterator[bytes]:
        self.calls.append((blob_id, expected_sha256, expected_size, window))
        if blob_id not in self.bodies:
            raise BlobNotFoundError(blob_id=str(blob_id))

        def chunks() -> Iterator[bytes]:
            try:
                body = self.bodies[blob_id]
                if body:
                    yield body[:3]
                    if len(body) > 3:
                        yield body[3:]
            finally:
                self.closed.append(blob_id)

        return chunks()


def test_full_readback_is_stable_and_uses_ids_not_keys() -> None:
    evidence = _evidence((b"canonical payload", b""))
    bodies = {item.blob_id: payload for item, payload in zip(evidence.bound_objects, (b"canonical payload", b""))}
    target = FakeTarget(bodies)
    first = audit_target_blob_readback(evidence, target)  # type: ignore[arg-type]
    second = audit_target_blob_readback(evidence, target)  # type: ignore[arg-type]
    assert first == second
    assert (first.count, first.bytes_read) == (2, len(b"canonical payload"))
    assert [call[0] for call in target.calls] == sorted(bodies) * 2
    assert all(call[3] is None for call in target.calls)
    assert sorted(target.closed) == sorted(list(bodies) * 2)


@pytest.mark.parametrize("body", (b"wrong", b"canonical payloa", b"canonical payloadx"))
def test_readback_refuses_changed_short_or_long_bytes_and_closes(body: bytes) -> None:
    evidence = _evidence((b"canonical payload",))
    blob_id = evidence.bound_objects[0].blob_id
    target = FakeTarget({blob_id: body})
    with pytest.raises(TargetBlobReadbackRefused):
        audit_target_blob_readback(evidence, target)  # type: ignore[arg-type]
    assert target.closed == [blob_id]


def test_missing_target_blob_propagates_typed_refusal() -> None:
    evidence = _evidence((b"payload",))
    target = FakeTarget({})
    with pytest.raises(BlobNotFoundError):
        audit_target_blob_readback(evidence, target)  # type: ignore[arg-type]
    assert len(target.calls) == 1


@pytest.mark.parametrize("change", ("unbound", "duplicate", "wrong_key", "wrong_digest"))
def test_invalid_db_to_mirror_evidence_refuses_before_target_io(change: str) -> None:
    evidence = _evidence((b"payload",))
    item = evidence.bound_objects[0]
    if change == "unbound":
        evidence = replace(evidence, bound_objects=())
    elif change == "duplicate":
        evidence = replace(evidence, bound_objects=(item, item))
    elif change == "wrong_key":
        evidence = replace(evidence, bound_objects=(replace(item, key="blobs/other"),))
    else:
        evidence = replace(evidence, bound_objects=(replace(item, sha256="0" * 64),))
    target = FakeTarget({})
    with pytest.raises(TargetBlobReadbackRefused):
        audit_target_blob_readback(evidence, target)  # type: ignore[arg-type]
    assert target.calls == []


def test_refusal_after_first_blob_never_returns_partial_success() -> None:
    evidence = _evidence((b"first", b"second"))
    bodies = {item.blob_id: payload for item, payload in zip(evidence.bound_objects, (b"first", b"second"))}
    wrong_id = sorted(bodies)[-1]
    bodies[wrong_id] = b"broken"
    target = FakeTarget(bodies)
    with pytest.raises(TargetBlobReadbackRefused):
        audit_target_blob_readback(evidence, target)  # type: ignore[arg-type]
    assert len(target.calls) == 2
