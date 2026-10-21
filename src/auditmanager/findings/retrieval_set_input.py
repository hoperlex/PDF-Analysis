"""Read the exact verified retrieval-set Blob for one current Attempt.

This unserved boundary supplies bytes to the citation transaction writer.  It
does not establish model provenance or reserve authority for a later call.
The caller owns the transaction and must finish it promptly: current Attempt
locks are held while the object is read.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.storage.public import BlobStore, StorageError, parse_blob_id


class RetrievalSetInputRefused(ValueError):
    """The Run pin, confirmed custody or saved set bytes cannot be trusted."""


@dataclass(frozen=True, slots=True)
class VerifiedRetrievalSetInput:
    run_id: str
    norms_snapshot_id: str
    norm_retrieval_set_id: str
    set_blob_id: str
    set_sha256: str
    data: bytes


_PIN = text("""
    SELECT r.state AS run_state, r.norms_snapshot_id,
           s.norm_retrieval_set_id, s.set_blob_id,
           s.observed_set_sha256 AS set_sha256, s.set_size_bytes,
           s.map_sha256, s.reviewed_content_key
      FROM audit_run r
      JOIN norm_retrieval_set s
        ON s.norm_retrieval_set_id = r.norm_retrieval_set_id
       AND s.norms_snapshot_id = r.norms_snapshot_id
      JOIN norms_snapshot ns ON ns.norms_snapshot_id = r.norms_snapshot_id
      JOIN norm_custody_binding cb
        ON cb.target_kind = 'norm_retrieval_set'
       AND cb.target_id = s.norm_retrieval_set_id
       AND cb.role = 'norm_retrieval_set'
       AND cb.anchor_kind = 'artifact'
       AND cb.blob_id = s.set_blob_id
      JOIN norm_custody_admission ca
        ON ca.norm_custody_admission_id = cb.norm_custody_admission_id
       AND ca.state = 'confirmed'
       AND ca.blob_id = cb.blob_id
       AND ca.declared_sha256 = s.observed_set_sha256
       AND ca.declared_size_bytes = s.set_size_bytes
      JOIN blob b ON b.blob_id = cb.blob_id
       AND b.state = 'available'
       AND b.sha256 = s.observed_set_sha256
       AND b.size_bytes = s.set_size_bytes
       AND b.media_type = ca.media_type
     WHERE r.run_id = :run_id
       AND s.state = 'verified'
       AND s.expected_set_sha256 = s.observed_set_sha256
       AND ns.content_key = s.reviewed_content_key
       AND EXISTS (
           SELECT 1 FROM norm_custody_binding cat
           JOIN norm_custody_admission cat_a
             ON cat_a.norm_custody_admission_id = cat.norm_custody_admission_id
            AND cat_a.state = 'confirmed'
            AND cat_a.blob_id = cat.blob_id
            AND cat_a.declared_sha256 = s.observed_catalogue_sha256
            AND cat_a.declared_size_bytes = s.catalogue_size_bytes
           JOIN blob cat_b ON cat_b.blob_id = cat.blob_id
            AND cat_b.state = 'available'
            AND cat_b.sha256 = s.observed_catalogue_sha256
            AND cat_b.size_bytes = s.catalogue_size_bytes
            AND cat_b.media_type = cat_a.media_type
           WHERE cat.target_kind = 'norm_retrieval_set'
             AND cat.target_id = s.norm_retrieval_set_id
             AND cat.role = 'norm_catalogue'
             AND cat.anchor_kind = 'artifact'
             AND cat.blob_id = s.catalogue_blob_id
       )
""")


def _read_exact(
    store: BlobStore, *, blob_id: str, sha256: str, size: int,
) -> bytes:
    try:
        chunks = store.open_stream(
            parse_blob_id(blob_id), expected_sha256=sha256, expected_size=size,
        )
        try:
            payload = bytearray()
            for chunk in chunks:
                if type(chunk) is not bytes or len(payload) + len(chunk) > size:
                    raise RetrievalSetInputRefused("set_blob_size_invalid")
                payload.extend(chunk)
        finally:
            chunks.close()
    except StorageError as exc:
        raise RetrievalSetInputRefused("set_blob_unreadable") from exc
    if len(payload) != size or hashlib.sha256(payload).hexdigest() != sha256:
        raise RetrievalSetInputRefused("set_blob_integrity_invalid")
    return bytes(payload)


def load_verified_retrieval_set(
    session: Session, *, authority: AttemptAuthority, blob_store: BlobStore,
    max_set_bytes: int = 10_000_000, jobs: JobRepository | None = None,
) -> VerifiedRetrievalSetInput:
    """Bind a current Attempt to confirmed set custody and exact saved bytes.

    The caller must have authorized the Run and must later recheck publication
    authority. This operation is read-only and never calls a model.
    """
    if type(max_set_bytes) is not int or not 1 <= max_set_bytes <= 10_000_000:
        raise RetrievalSetInputRefused("invalid_set_byte_ceiling")
    job_repo = jobs or JobRepository()
    job_repo.require_current(session, authority)
    rows = session.execute(_PIN, {"run_id": authority.run_id}).mappings().all()
    if len(rows) != 1:
        raise RetrievalSetInputRefused("verified_set_custody_missing_or_duplicate")
    row = dict(rows[0])
    size = row["set_size_bytes"]
    if (row["run_state"] not in {"running", "validating"}
            or type(size) is not int or not 1 <= size <= max_set_bytes
            or not isinstance(row["set_sha256"], str)
            or len(row["set_sha256"]) != 64):
        raise RetrievalSetInputRefused("verified_set_pin_invalid")
    payload = _read_exact(
        blob_store, blob_id=row["set_blob_id"],
        sha256=row["set_sha256"], size=size,
    )
    job_repo.require_current(session, authority)
    after = session.execute(_PIN, {"run_id": authority.run_id}).mappings().all()
    if len(after) != 1 or dict(after[0]) != row:
        raise RetrievalSetInputRefused("verified_set_pin_changed_during_read")
    return VerifiedRetrievalSetInput(
        run_id=authority.run_id,
        norms_snapshot_id=row["norms_snapshot_id"],
        norm_retrieval_set_id=row["norm_retrieval_set_id"],
        set_blob_id=row["set_blob_id"],
        set_sha256=row["set_sha256"],
        data=payload,
    )


__all__ = [
    "RetrievalSetInputRefused", "VerifiedRetrievalSetInput",
    "load_verified_retrieval_set",
]
