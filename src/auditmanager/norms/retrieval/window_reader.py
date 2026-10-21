"""SELECT-only, bounded W57a reader of canonical embedding windows.

The caller owns one consistent read transaction, reviewed map/document set and
independent qualification of the embedding build. This reader checks stored
build metadata and selected vector bytes; it never activates or publishes a set.
"""

from __future__ import annotations

import json
import re
import unicodedata
from array import array
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.norms.chunking import parse_chunking_profile
from auditmanager.norms.embedding import vectors
from auditmanager.norms.embedding.digest import EmbeddingSetDigest
from auditmanager.norms.embedding.profile import EMBEDDING_PROFILE, require_snapshot_id
from auditmanager.norms.retrieval.ranking import MAX_CANDIDATE_WINDOWS, RetrievalWindow


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_DOCUMENT = re.compile(r"ndoc_[0-9A-HJKMNP-TV-Z]{26}\Z")
_MAX_BUILD_WINDOWS = 1_000_000

_BUILD = text("""
    SELECT s.content_key, cb.chunk_count AS canonical_chunk_count,
           b.chunk_count, b.window_count, b.embedding_set_sha256,
           (SELECT count(*) FROM norm_chunk c
            WHERE c.norms_snapshot_id = s.norms_snapshot_id
              AND c.chunking_profile = :chunking_profile) AS stored_chunk_count
    FROM norms_snapshot s
    JOIN norm_chunk_build cb
      ON cb.norms_snapshot_id = s.norms_snapshot_id
     AND cb.chunking_profile = :chunking_profile
    JOIN norm_embedding_build b
      ON b.norms_snapshot_id = s.norms_snapshot_id
     AND b.chunking_profile = cb.chunking_profile
     AND b.embedding_profile = :embedding_profile
    WHERE s.norms_snapshot_id = :snapshot_id
""")
_METADATA = text("""
    SELECT d.norm_document_id, d.source_document_ref,
           c.ordinal AS chunk_ordinal, e.window_ordinal, e.token_count,
           e.char_offset, e.char_length,
           e.paragraph_ordinal_first, e.paragraph_ordinal_last,
           e.input_sha256, e.embedding_sha256
    FROM norm_embedding e
    JOIN norm_chunk c
      ON c.norm_chunk_pk = e.norm_chunk_pk
     AND c.norms_snapshot_id = e.norms_snapshot_id
     AND c.chunking_profile = e.chunking_profile
    JOIN norm_document d
      ON d.norms_snapshot_id = c.norms_snapshot_id
     AND d.norm_document_pk = c.norm_document_pk
    WHERE e.norms_snapshot_id = :snapshot_id
      AND e.chunking_profile = :chunking_profile
      AND e.embedding_profile = :embedding_profile
    ORDER BY d.source_document_ref COLLATE "C", c.ordinal, e.window_ordinal
""")
_MAPPED_VECTORS = text("""
    SELECT d.norm_document_id, c.ordinal AS chunk_ordinal,
           e.window_ordinal, e.token_count, e.char_offset, e.char_length,
           e.paragraph_ordinal_first, e.paragraph_ordinal_last,
           e.input_sha256, e.embedding_sha256, e.embedding::text AS embedding_text
    FROM norm_embedding e
    JOIN norm_chunk c
      ON c.norm_chunk_pk = e.norm_chunk_pk
     AND c.norms_snapshot_id = e.norms_snapshot_id
     AND c.chunking_profile = e.chunking_profile
    JOIN norm_document d
      ON d.norms_snapshot_id = c.norms_snapshot_id
     AND d.norm_document_pk = c.norm_document_pk
    WHERE e.norms_snapshot_id = :snapshot_id
      AND e.chunking_profile = :chunking_profile
      AND e.embedding_profile = :embedding_profile
      AND d.norm_document_id = ANY(CAST(:mapped_ids AS text[]))
    ORDER BY d.norm_document_id COLLATE "C", c.ordinal, e.window_ordinal
""")


class WindowReadRefused(ValueError):
    """Stored build or selected windows do not match exact caller inputs."""


@dataclass(frozen=True, slots=True)
class WindowEvidence:
    snapshot_id: str
    embedding_build: str
    embedding_set_sha256: str
    build_chunk_count: int
    build_window_count: int
    windows: tuple[RetrievalWindow, ...]


def _integer(value: object, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise WindowReadRefused(f"{label} must be an integer >= {minimum}")
    return value


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise WindowReadRefused(f"invalid {label}")
    return value


def _build_profiles(embedding_build: str) -> tuple[str, str]:
    if not isinstance(embedding_build, str):
        raise WindowReadRefused("invalid embedding build identity")
    profile, separator, chunking = embedding_build.partition(":")
    if not separator or profile != EMBEDDING_PROFILE:
        raise WindowReadRefused("unknown embedding build identity")
    try:
        parse_chunking_profile(chunking)
    except ValueError as exc:
        raise WindowReadRefused("invalid chunking profile") from exc
    return profile, chunking


def _metadata_values(row: object) -> tuple[int, int, int, int, int, int, int, str, str]:
    return (
        _integer(row["chunk_ordinal"], "chunk ordinal"),
        _integer(row["window_ordinal"], "window ordinal"),
        _integer(row["token_count"], "token count", minimum=1),
        _integer(row["char_offset"], "character offset"),
        _integer(row["char_length"], "character length", minimum=1),
        _integer(row["paragraph_ordinal_first"], "first paragraph ordinal"),
        _integer(row["paragraph_ordinal_last"], "last paragraph ordinal"),
        _digest(row["input_sha256"], "window input digest"),
        _digest(row["embedding_sha256"], "vector digest"),
    )


def _vector(value: object, expected_sha256: str) -> array:
    if not isinstance(value, str) or len(value) > 25_000:
        raise WindowReadRefused("invalid vector text")
    try:
        raw = json.loads(value)
        if not isinstance(raw, list):
            raise ValueError("vector is not a list")
        packed = vectors.pack(raw)
    except (ValueError, TypeError, vectors.VectorRefused) as exc:
        raise WindowReadRefused("invalid stored vector") from exc
    if vectors.sha256(packed) != expected_sha256:
        raise WindowReadRefused("stored vector digest mismatch")
    return array("f", vectors.unpack(packed))


def read_retrieval_windows(
    session: Session,
    *,
    snapshot_id: str,
    expected_content_key: str,
    embedding_build: str,
    expected_embedding_set_sha256: str,
    mapped_document_ids: tuple[str, ...],
) -> WindowEvidence:
    """Read every mapped window under a caller-owned consistent transaction.

    The full build's ordered metadata is replayed against its recorded digest
    and counts before mapped vectors are materialized. The independent expected
    digest must come from the caller's build qualification. No HNSW query runs.
    """
    try:
        require_snapshot_id(snapshot_id)
    except (TypeError, ValueError) as exc:
        raise WindowReadRefused("invalid snapshot id") from exc
    if (
        not isinstance(expected_content_key, str)
        or not expected_content_key
        or unicodedata.normalize("NFC", expected_content_key) != expected_content_key
    ):
        raise WindowReadRefused("invalid expected content key")
    embedding_profile, chunking_profile = _build_profiles(embedding_build)
    _digest(expected_embedding_set_sha256, "expected embedding set digest")
    if not isinstance(mapped_document_ids, tuple) or not mapped_document_ids:
        raise WindowReadRefused("mapped document ids must be a unique nonempty tuple")
    if any(
        not isinstance(doc, str) or _DOCUMENT.fullmatch(doc) is None
        for doc in mapped_document_ids
    ):
        raise WindowReadRefused("invalid mapped document id")
    if len(set(mapped_document_ids)) != len(mapped_document_ids):
        raise WindowReadRefused("duplicate mapped document id")
    parameters = {
        "snapshot_id": snapshot_id,
        "chunking_profile": chunking_profile,
        "embedding_profile": embedding_profile,
    }
    build = session.execute(_BUILD, parameters).mappings().one_or_none()
    if build is None:
        raise WindowReadRefused("complete embedding build is absent")
    if build["content_key"] != expected_content_key:
        raise WindowReadRefused("snapshot content key mismatch")
    chunk_count = _integer(build["chunk_count"], "build chunk count", minimum=1)
    window_count = _integer(build["window_count"], "build window count", minimum=1)
    if (
        chunk_count != _integer(build["canonical_chunk_count"], "canonical chunk count")
        or chunk_count != _integer(build["stored_chunk_count"], "stored chunk count")
        or window_count < chunk_count
        or window_count > _MAX_BUILD_WINDOWS
    ):
        raise WindowReadRefused("embedding build count mismatch or capacity exceeded")
    stored_digest = _digest(build["embedding_set_sha256"], "stored embedding set digest")
    if stored_digest != expected_embedding_set_sha256:
        raise WindowReadRefused("embedding set digest differs from expected")

    digest = EmbeddingSetDigest(
        content_key=expected_content_key,
        chunking_profile=chunking_profile,
        embedding_profile=embedding_profile,
    )
    mapped = set(mapped_document_ids)
    selected: dict[tuple[str, int, int], tuple[int, int, int, int, int, int, int, str, str]] = {}
    seen_docs: set[str] = set()
    last_chunk: tuple[str, int] | None = None
    chunks_seen = 0
    next_window_ordinal = 0
    for row in session.execute(
        _METADATA, parameters, execution_options={"stream_results": True, "yield_per": 2000},
    ).mappings():
        source_ref = row["source_document_ref"]
        if not isinstance(source_ref, str) or not source_ref:
            raise WindowReadRefused("invalid source document reference")
        values = _metadata_values(row)
        chunk_ordinal, window_ordinal = values[:2]
        if values[6] < values[5]:
            raise WindowReadRefused("reversed paragraph span")
        chunk_key = (source_ref, chunk_ordinal)
        if chunk_key != last_chunk:
            if last_chunk is not None and chunk_key <= last_chunk:
                raise WindowReadRefused("embedding chunks out of canonical order")
            chunks_seen += 1
            last_chunk = chunk_key
            next_window_ordinal = 0
        if window_ordinal != next_window_ordinal:
            raise WindowReadRefused("embedding window ordinals are incomplete")
        next_window_ordinal += 1
        try:
            digest.add_values(
                source_ref, chunk_ordinal,
                window_ordinal=window_ordinal,
                token_count=values[2], char_offset=values[3], char_length=values[4],
                paragraph_ordinal_first=values[5], paragraph_ordinal_last=values[6],
                input_sha256=values[7], embedding_sha256=values[8],
            )
        except ValueError as exc:
            raise WindowReadRefused("embedding windows out of canonical order") from exc
        document_id = row["norm_document_id"]
        if document_id in mapped:
            key = (document_id, chunk_ordinal, window_ordinal)
            if key in selected:
                raise WindowReadRefused("duplicate mapped embedding window")
            selected[key] = values
            seen_docs.add(document_id)
            if len(selected) > MAX_CANDIDATE_WINDOWS:
                raise WindowReadRefused("too many mapped candidate windows")
    if (
        chunks_seen != chunk_count
        or digest.windows != window_count
        or digest.hexdigest() != stored_digest
    ):
        raise WindowReadRefused("stored embedding rows differ from build digest or counts")
    if seen_docs != mapped:
        raise WindowReadRefused("mapped document has no embedding windows")

    windows: list[RetrievalWindow] = []
    last_key: tuple[str, int, int] | None = None
    for row in session.execute(
        _MAPPED_VECTORS,
        parameters | {"mapped_ids": list(mapped_document_ids)},
        execution_options={"stream_results": True, "yield_per": 250},
    ).mappings():
        document_id = row["norm_document_id"]
        if document_id not in mapped:
            raise WindowReadRefused("foreign mapped vector row")
        values = _metadata_values(row)
        key = (document_id, values[0], values[1])
        if last_key is not None and key <= last_key:
            raise WindowReadRefused("mapped vectors out of canonical order")
        if selected.get(key) != values:
            raise WindowReadRefused("mapped vector metadata differs from complete build")
        last_key = key
        windows.append(RetrievalWindow(
            document_id=document_id,
            chunk_ordinal=values[0],
            window_ordinal=values[1],
            paragraph_ordinal_first=values[5],
            paragraph_ordinal_last=values[6],
            vector=_vector(row["embedding_text"], values[8]),
        ))
        if len(windows) > len(selected):
            raise WindowReadRefused("mapped vector count exceeds build metadata")
    if len(windows) != len(selected):
        raise WindowReadRefused("mapped vector rows are incomplete")
    return WindowEvidence(
        snapshot_id=snapshot_id,
        embedding_build=embedding_build,
        embedding_set_sha256=stored_digest,
        build_chunk_count=chunk_count,
        build_window_count=window_count,
        windows=tuple(windows),
    )


__all__ = ["WindowEvidence", "WindowReadRefused", "read_retrieval_windows"]
