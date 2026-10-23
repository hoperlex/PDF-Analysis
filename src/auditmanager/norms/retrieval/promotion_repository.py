"""0023 persistence for a reviewed retrieval set; no Blob calls or commits.

The set row is immutable. A verified insert and both custody bindings belong to
one caller transaction, so a failed publication leaves no half-verified set.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from sqlalchemy import text
from sqlalchemy.orm import Session


_COLUMNS = (
    "norm_retrieval_set_id, norms_snapshot_id, map_sha256, reviewed_content_key, "
    "chunking_profile, embedding_profile, builder_version, state, "
    "expected_set_sha256, observed_set_sha256, expected_catalogue_sha256, "
    "observed_catalogue_sha256, set_blob_id, set_size_bytes, "
    "catalogue_blob_id, catalogue_size_bytes, prompt_part_characters"
)
_GET = text(f"SELECT {_COLUMNS} FROM norm_retrieval_set WHERE norm_retrieval_set_id = :set_id")
_INSERT = text(f"""
    INSERT INTO norm_retrieval_set ({_COLUMNS}) VALUES (
        :set_id, :snapshot_id, :map_sha256, :content_key, :chunking_profile,
        :embedding_profile, :builder_version, :state, :expected_set_sha256,
        :observed_set_sha256, :expected_catalogue_sha256,
        :observed_catalogue_sha256, :set_blob_id, :set_size_bytes,
        :catalogue_blob_id, :catalogue_size_bytes, :prompt_part_characters
    ) ON CONFLICT DO NOTHING
""")
_IDENTITY_HOLDER = text("""
    SELECT norm_retrieval_set_id FROM norm_retrieval_set
     WHERE state = 'verified' AND map_sha256 = :map_sha256
       AND norms_snapshot_id = :snapshot_id
       AND chunking_profile = :chunking_profile
       AND embedding_profile = :embedding_profile
       AND builder_version = :builder_version
""")
_VERIFIED = text("""
    SELECT s.norm_retrieval_set_id, s.norms_snapshot_id, s.map_sha256,
           s.reviewed_content_key, s.chunking_profile, s.embedding_profile,
           s.builder_version, s.observed_set_sha256, s.observed_catalogue_sha256,
           s.set_blob_id, s.set_size_bytes, s.catalogue_blob_id, s.catalogue_size_bytes
      FROM norm_retrieval_set s
      JOIN norms_snapshot ns ON ns.norms_snapshot_id = s.norms_snapshot_id
     WHERE s.state = 'verified'
       AND s.map_sha256 = :map_sha256
       AND s.norms_snapshot_id = :snapshot_id
       AND s.chunking_profile = :chunking_profile
       AND s.embedding_profile = :embedding_profile
       AND s.builder_version = :builder_version
       AND ns.content_key = s.reviewed_content_key
       AND s.expected_set_sha256 = s.observed_set_sha256
       AND s.expected_catalogue_sha256 = s.observed_catalogue_sha256
       AND (SELECT count(*) FROM norm_custody_binding b
             JOIN norm_custody_admission a
               ON a.norm_custody_admission_id = b.norm_custody_admission_id
             JOIN blob x ON x.blob_id = b.blob_id
            WHERE b.target_kind = 'norm_retrieval_set'
              AND b.target_id = s.norm_retrieval_set_id
              AND a.state = 'confirmed' AND x.state = 'available'
              AND b.anchor_kind = 'artifact'
              AND ((b.role = 'norm_retrieval_set' AND b.blob_id = s.set_blob_id
                    AND a.declared_sha256 = s.observed_set_sha256
                    AND a.declared_size_bytes = s.set_size_bytes
                    AND x.sha256 = s.observed_set_sha256
                    AND x.size_bytes = s.set_size_bytes)
                OR (b.role = 'norm_catalogue' AND b.blob_id = s.catalogue_blob_id
                    AND a.declared_sha256 = s.observed_catalogue_sha256
                    AND a.declared_size_bytes = s.catalogue_size_bytes
                    AND x.sha256 = s.observed_catalogue_sha256
                    AND x.size_bytes = s.catalogue_size_bytes))) = 2
       AND EXISTS (SELECT 1 FROM norm_custody_binding b
                    WHERE b.target_kind = 'norm_retrieval_set'
                      AND b.target_id = s.norm_retrieval_set_id
                      AND b.role = 'norm_retrieval_set'
                      AND b.blob_id = s.set_blob_id)
       AND EXISTS (SELECT 1 FROM norm_custody_binding b
                    WHERE b.target_kind = 'norm_retrieval_set'
                      AND b.target_id = s.norm_retrieval_set_id
                      AND b.role = 'norm_catalogue'
                      AND b.blob_id = s.catalogue_blob_id)
    LIMIT 2
""")


@dataclass(frozen=True, slots=True)
class VerifiedSetReference:
    set_id: str
    snapshot_id: str
    map_sha256: str
    reviewed_content_key: str
    chunking_profile: str
    embedding_profile: str
    builder_version: str
    set_sha256: str
    catalogue_sha256: str
    set_blob_id: str
    set_size_bytes: int
    catalogue_blob_id: str
    catalogue_size_bytes: int


def get_set(session: Session, set_id: str) -> Mapping[str, Any] | None:
    row = session.execute(_GET, {"set_id": set_id}).mappings().one_or_none()
    return None if row is None else dict(row)


def insert_set(session: Session, values: Mapping[str, Any]) -> bool:
    """Try an immutable insert. False means an existing ID or verified identity won."""
    return session.execute(_INSERT, dict(values)).rowcount == 1


def verified_identity_holder(session: Session, values: Mapping[str, Any]) -> str | None:
    """Preflight 0023's partial UNIQUE key before admitting or reading Blobs."""
    value = session.execute(_IDENTITY_HOLDER, dict(values)).scalar_one_or_none()
    return None if value is None else str(value)


def verified_for_identity(
    session: Session, *, map_sha256: str, snapshot_id: str,
    chunking_profile: str, embedding_profile: str, builder_version: str,
) -> VerifiedSetReference | None:
    rows = session.execute(_VERIFIED, {
        "map_sha256": map_sha256, "snapshot_id": snapshot_id,
        "chunking_profile": chunking_profile, "embedding_profile": embedding_profile,
        "builder_version": builder_version,
    }).mappings().all()
    if not rows:
        return None
    if len(rows) != 1:
        raise ValueError("multiple verified sets have one identity")
    row = rows[0]
    return VerifiedSetReference(
        set_id=str(row["norm_retrieval_set_id"]),
        snapshot_id=str(row["norms_snapshot_id"]),
        map_sha256=str(row["map_sha256"]),
        reviewed_content_key=str(row["reviewed_content_key"]),
        chunking_profile=str(row["chunking_profile"]),
        embedding_profile=str(row["embedding_profile"]),
        builder_version=str(row["builder_version"]),
        set_sha256=str(row["observed_set_sha256"]),
        catalogue_sha256=str(row["observed_catalogue_sha256"]),
        set_blob_id=str(row["set_blob_id"]),
        set_size_bytes=int(row["set_size_bytes"]),
        catalogue_blob_id=str(row["catalogue_blob_id"]),
        catalogue_size_bytes=int(row["catalogue_size_bytes"]),
    )


__all__ = [
    "VerifiedSetReference", "get_set", "insert_set", "verified_for_identity",
    "verified_identity_holder",
]
