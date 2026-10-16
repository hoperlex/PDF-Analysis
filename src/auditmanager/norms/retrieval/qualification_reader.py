"""SELECT-only stored facts for a later W57a qualification decision.

The caller owns one consistent read transaction and independent corpus, map,
embedding-digest and custody evidence. Counts and a completion row are facts,
not a verified retrieval set or proof that source bytes match a manifest.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.norms.chunking import RELIABLE_CHUNKING_PROFILE_VERSION, parse_chunking_profile
from auditmanager.norms.embedding.profile import EMBEDDING_PROFILE, require_snapshot_id


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")

_SNAPSHOT = text("""
    SELECT s.norms_snapshot_id, s.content_key, s.content_digest,
           s.document_count, s.repair_count,
           (SELECT count(*) FROM norm_document d
             WHERE d.norms_snapshot_id = s.norms_snapshot_id) AS stored_document_count,
           (SELECT count(*) FROM norm_document d
             WHERE d.norms_snapshot_id = s.norms_snapshot_id
               AND EXISTS (
                   SELECT 1 FROM norm_custody_binding cb
                    WHERE cb.role = 'norm_source'
                      AND cb.target_kind = 'norm_document'
                      AND cb.target_id = d.norm_document_id
                      AND cb.anchor_kind = 'pdf'
                      AND cb.anchor = d.source_document_ref
               )) AS pdf_bound_document_count
      FROM norms_snapshot s
     WHERE s.norms_snapshot_id = :snapshot_id
""")

_BUILDS = text("""
    SELECT cb.target_characters, cb.chunk_count AS declared_chunk_count,
           (SELECT count(*) FROM norm_chunk c
             WHERE c.norms_snapshot_id = cb.norms_snapshot_id
               AND c.chunking_profile = cb.chunking_profile) AS stored_chunk_count,
           eb.chunk_count AS embedded_chunk_count,
           eb.window_count AS declared_window_count,
           eb.embedding_set_sha256,
           (SELECT count(*) FROM norm_embedding e
             WHERE e.norms_snapshot_id = cb.norms_snapshot_id
               AND e.chunking_profile = cb.chunking_profile
               AND e.embedding_profile = :embedding_profile) AS stored_window_count,
           (SELECT count(DISTINCT e.norm_chunk_pk) FROM norm_embedding e
             WHERE e.norms_snapshot_id = cb.norms_snapshot_id
               AND e.chunking_profile = cb.chunking_profile
               AND e.embedding_profile = :embedding_profile) AS stored_embedded_chunk_count
      FROM norm_chunk_build cb
      LEFT JOIN norm_embedding_build eb
        ON eb.norms_snapshot_id = cb.norms_snapshot_id
       AND eb.chunking_profile = cb.chunking_profile
       AND eb.embedding_profile = :embedding_profile
     WHERE cb.norms_snapshot_id = :snapshot_id
       AND cb.chunking_profile = :chunking_profile
""")


class QualificationReadRefused(ValueError):
    """Snapshot identity, profile or stored scalar facts cannot be read safely."""


@dataclass(frozen=True, slots=True)
class EmbeddingBuildFacts:
    declared_chunk_count: int
    declared_window_count: int
    embedding_set_sha256: str
    stored_window_count: int
    stored_embedded_chunk_count: int


@dataclass(frozen=True, slots=True)
class ChunkBuildFacts:
    target_characters: int
    declared_chunk_count: int
    stored_chunk_count: int
    embedding: EmbeddingBuildFacts | None


@dataclass(frozen=True, slots=True)
class SnapshotBuildFacts:
    snapshot_id: str
    content_key: str
    content_digest: str
    declared_document_count: int
    stored_document_count: int
    pdf_bound_document_count: int
    repair_count: int
    chunking_profile: str
    embedding_profile: str
    chunk: ChunkBuildFacts | None


def _count(value: object, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise QualificationReadRefused(f"invalid {label}")
    return value


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise QualificationReadRefused(f"invalid {label}")
    return value


def read_snapshot_build_facts(
    session: Session,
    *,
    snapshot_id: str,
    expected_content_key: str,
    chunking_profile: str,
) -> SnapshotBuildFacts:
    """Read exact-key stored facts; missing chunk/build rows remain explicit ``None``.

    A matching count or digest field does not attest the source PDF bytes, the
    full embedding stream, map approval, expected digest or custody of a set.
    """
    try:
        require_snapshot_id(snapshot_id)
    except (TypeError, ValueError) as exc:
        raise QualificationReadRefused("invalid snapshot id") from exc
    if (
        not isinstance(expected_content_key, str)
        or not expected_content_key
        or unicodedata.normalize("NFC", expected_content_key) != expected_content_key
    ):
        raise QualificationReadRefused("invalid expected content key")
    try:
        version, target_characters = parse_chunking_profile(chunking_profile)
    except (AttributeError, TypeError, ValueError) as exc:
        raise QualificationReadRefused("invalid chunking profile") from exc
    if version != RELIABLE_CHUNKING_PROFILE_VERSION:
        raise QualificationReadRefused("W57a requires the reliability-aware chunk profile")

    row = session.execute(_SNAPSHOT, {"snapshot_id": snapshot_id}).mappings().one_or_none()
    if row is None or row["norms_snapshot_id"] != snapshot_id:
        raise QualificationReadRefused("snapshot is absent")
    if row["content_key"] != expected_content_key:
        raise QualificationReadRefused("snapshot content key differs from reviewed input")
    content_digest = _digest(row["content_digest"], "snapshot content digest")
    declared_documents = _count(row["document_count"], "declared document count", minimum=1)
    stored_documents = _count(row["stored_document_count"], "stored document count")
    bound_documents = _count(row["pdf_bound_document_count"], "PDF-bound document count")
    if bound_documents > stored_documents:
        raise QualificationReadRefused("PDF-bound count exceeds stored documents")
    repair_count = _count(row["repair_count"], "repair count")

    parameters = {
        "snapshot_id": snapshot_id,
        "chunking_profile": chunking_profile,
        "embedding_profile": EMBEDDING_PROFILE,
    }
    build = session.execute(_BUILDS, parameters).mappings().one_or_none()
    chunk: ChunkBuildFacts | None = None
    if build is not None:
        target = _count(build["target_characters"], "target characters", minimum=1)
        if target != target_characters:
            raise QualificationReadRefused("chunk target differs from profile")
        embedding: EmbeddingBuildFacts | None = None
        if build["embedded_chunk_count"] is not None:
            embedding = EmbeddingBuildFacts(
                declared_chunk_count=_count(build["embedded_chunk_count"], "embedding chunk count"),
                declared_window_count=_count(build["declared_window_count"], "embedding window count"),
                embedding_set_sha256=_digest(build["embedding_set_sha256"], "embedding set digest"),
                stored_window_count=_count(build["stored_window_count"], "stored window count"),
                stored_embedded_chunk_count=_count(
                    build["stored_embedded_chunk_count"], "stored embedded chunk count"
                ),
            )
        elif build["declared_window_count"] is not None or build["embedding_set_sha256"] is not None:
            raise QualificationReadRefused("partial embedding completion row")
        chunk = ChunkBuildFacts(
            target_characters=target,
            declared_chunk_count=_count(build["declared_chunk_count"], "chunk count"),
            stored_chunk_count=_count(build["stored_chunk_count"], "stored chunk count"),
            embedding=embedding,
        )
    return SnapshotBuildFacts(
        snapshot_id=snapshot_id,
        content_key=expected_content_key,
        content_digest=content_digest,
        declared_document_count=declared_documents,
        stored_document_count=stored_documents,
        pdf_bound_document_count=bound_documents,
        repair_count=repair_count,
        chunking_profile=chunking_profile,
        embedding_profile=EMBEDDING_PROFILE,
        chunk=chunk,
    )
