"""Read exact W57b catalogue bytes from a current Run's verified set custody.

This unserved, read-only boundary returns independently pinned facts for the
pure catalogue validator. The caller owns authorization and a short transaction
across both Attempt checks and both SQL reads; this read grants no later
publication authority and makes no corpus-qualification assertion.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.norms.references.catalogue_query import CatalogueExpectation
from auditmanager.storage.public import BlobStore, StorageError, parse_blob_id


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class CatalogueInputRefused(ValueError):
    """The Run pin, confirmed custody or saved catalogue bytes are untrusted."""


@dataclass(frozen=True, slots=True)
class VerifiedCatalogueInput:
    run_id: str
    norm_retrieval_set_id: str
    catalogue_blob_id: str
    data: bytes
    expectation: CatalogueExpectation


_PIN = text("""
    SELECT r.state AS run_state, r.norms_snapshot_id,
           s.norm_retrieval_set_id, s.map_sha256, s.reviewed_content_key,
           s.set_blob_id, s.observed_set_sha256 AS set_sha256, s.set_size_bytes,
           s.catalogue_blob_id,
           s.observed_catalogue_sha256 AS catalogue_sha256,
           s.catalogue_size_bytes, ns.content_key, ns.content_digest,
           ns.document_count,
           (SELECT count(*) FROM norm_document d
             WHERE d.norms_snapshot_id = ns.norms_snapshot_id) AS stored_document_count,
           (SELECT count(*) FROM norm_custody_binding b
             WHERE b.target_kind = 'norm_retrieval_set'
               AND b.target_id = s.norm_retrieval_set_id) AS binding_count
      FROM audit_run r
      JOIN norm_retrieval_set s
        ON s.norm_retrieval_set_id = r.norm_retrieval_set_id
       AND s.norms_snapshot_id = r.norms_snapshot_id
      JOIN norms_snapshot ns ON ns.norms_snapshot_id = r.norms_snapshot_id
      JOIN norm_custody_binding set_binding
        ON set_binding.target_kind = 'norm_retrieval_set'
       AND set_binding.target_id = s.norm_retrieval_set_id
       AND set_binding.role = 'norm_retrieval_set'
       AND set_binding.anchor_kind = 'artifact'
       AND set_binding.blob_id = s.set_blob_id
      JOIN norm_custody_admission set_admission
        ON set_admission.norm_custody_admission_id = set_binding.norm_custody_admission_id
       AND set_admission.state = 'confirmed'
       AND set_admission.blob_id = set_binding.blob_id
       AND set_admission.declared_sha256 = s.observed_set_sha256
       AND set_admission.declared_size_bytes = s.set_size_bytes
      JOIN blob set_blob ON set_blob.blob_id = set_binding.blob_id
       AND set_blob.state = 'available'
       AND set_blob.sha256 = s.observed_set_sha256
       AND set_blob.size_bytes = s.set_size_bytes
       AND set_blob.media_type = set_admission.media_type
      JOIN norm_custody_binding cat_binding
        ON cat_binding.target_kind = 'norm_retrieval_set'
       AND cat_binding.target_id = s.norm_retrieval_set_id
       AND cat_binding.role = 'norm_catalogue'
       AND cat_binding.anchor_kind = 'artifact'
       AND cat_binding.blob_id = s.catalogue_blob_id
      JOIN norm_custody_admission cat_admission
        ON cat_admission.norm_custody_admission_id = cat_binding.norm_custody_admission_id
       AND cat_admission.state = 'confirmed'
       AND cat_admission.blob_id = cat_binding.blob_id
       AND cat_admission.declared_sha256 = s.observed_catalogue_sha256
       AND cat_admission.declared_size_bytes = s.catalogue_size_bytes
      JOIN blob cat_blob ON cat_blob.blob_id = cat_binding.blob_id
       AND cat_blob.state = 'available'
       AND cat_blob.sha256 = s.observed_catalogue_sha256
       AND cat_blob.size_bytes = s.catalogue_size_bytes
       AND cat_blob.media_type = cat_admission.media_type
     WHERE r.run_id = :run_id
       AND s.state = 'verified'
       AND s.expected_set_sha256 = s.observed_set_sha256
       AND s.expected_catalogue_sha256 = s.observed_catalogue_sha256
       AND s.reviewed_content_key = ns.content_key
""")


def _read_exact(store: BlobStore, *, blob_id: str, sha256: str, size: int) -> bytes:
    try:
        chunks = store.open_stream(
            parse_blob_id(blob_id), expected_sha256=sha256, expected_size=size,
        )
        try:
            payload = bytearray()
            for chunk in chunks:
                if type(chunk) is not bytes or len(payload) + len(chunk) > size:
                    raise CatalogueInputRefused("catalogue_blob_size_invalid")
                payload.extend(chunk)
        finally:
            chunks.close()
    except StorageError as exc:
        raise CatalogueInputRefused("catalogue_blob_unreadable") from exc
    if len(payload) != size or hashlib.sha256(payload).hexdigest() != sha256:
        raise CatalogueInputRefused("catalogue_blob_integrity_invalid")
    return bytes(payload)


def load_verified_catalogue(
    session: Session, *, authority: AttemptAuthority, blob_store: BlobStore,
    max_catalogue_bytes: int = 10_000_000, jobs: JobRepository | None = None,
) -> VerifiedCatalogueInput:
    """Return a bounded saved catalogue and its independent snapshot facts.

    The caller must authorize the Run before this call and use a separate
    reviewed unparsed-slug list with ``load_pinned_catalogue`` afterwards.
    """
    if (type(max_catalogue_bytes) is not int
            or not 1 <= max_catalogue_bytes <= 10_000_000):
        raise CatalogueInputRefused("invalid_catalogue_byte_ceiling")
    job_repo = jobs or JobRepository()
    job_repo.require_current(session, authority)
    rows = session.execute(_PIN, {"run_id": authority.run_id}).mappings().all()
    if len(rows) != 1:
        raise CatalogueInputRefused("verified_catalogue_custody_missing_or_duplicate")
    row = dict(rows[0])
    size = row["catalogue_size_bytes"]
    count = row["document_count"]
    if (
        row["run_state"] not in {"running", "validating"}
        or type(size) is not int or not 1 <= size <= max_catalogue_bytes
        or type(count) is not int or count <= 0
        or row["stored_document_count"] != count
        or row["binding_count"] != 2
        or not isinstance(row["content_key"], str) or not row["content_key"]
        or not isinstance(row["catalogue_sha256"], str)
        or _SHA256.fullmatch(row["catalogue_sha256"]) is None
        or not isinstance(row["content_digest"], str)
        or _SHA256.fullmatch(row["content_digest"]) is None
    ):
        raise CatalogueInputRefused("verified_catalogue_pin_invalid")
    payload = _read_exact(
        blob_store, blob_id=row["catalogue_blob_id"],
        sha256=row["catalogue_sha256"], size=size,
    )
    job_repo.require_current(session, authority)
    after = session.execute(_PIN, {"run_id": authority.run_id}).mappings().all()
    if len(after) != 1 or dict(after[0]) != row:
        raise CatalogueInputRefused("verified_catalogue_pin_changed_during_read")
    return VerifiedCatalogueInput(
        run_id=authority.run_id,
        norm_retrieval_set_id=row["norm_retrieval_set_id"],
        catalogue_blob_id=row["catalogue_blob_id"],
        data=payload,
        expectation=CatalogueExpectation(
            snapshot_id=row["norms_snapshot_id"],
            content_key=row["content_key"],
            snapshot_content_digest=row["content_digest"],
            document_count=count,
            catalogue_sha256=row["catalogue_sha256"],
        ),
    )


__all__ = [
    "CatalogueInputRefused", "VerifiedCatalogueInput", "load_verified_catalogue",
]
