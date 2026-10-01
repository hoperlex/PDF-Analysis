"""Transaction-local persistence for rebuildable normative embedding windows.

No model is loaded here. The future embedding worker owns inference and hands this boundary
validated window metadata plus vectors. This module owns the persistence invariants and exact
replay behavior; the caller owns commit/rollback.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from auditmanager.shared.identity import NormsSnapshotId

EMBEDDING_PROFILE = "bge-m3-dense-v1"
EMBEDDING_DIMENSIONS = 1024
MAX_TOKENS = 512
UNIT_NORM_TOLERANCE = 0.0001

_LOCK_BUILD = text(
    """
    SELECT pg_advisory_xact_lock(
        hashtextextended(
            :snapshot || chr(31) || :chunking_profile || chr(31) || :embedding_profile,
            0
        )
    )
    """
)
_SELECT_BUILD = text(
    """
    SELECT chunk_count, window_count, embedding_set_sha256
    FROM norm_embedding_build
    WHERE norms_snapshot_id = :snapshot
      AND chunking_profile = :chunking_profile
      AND embedding_profile = :embedding_profile
    """
)
_SELECT_CHUNKS = text(
    """
    SELECT norm_chunk_pk, char_length,
           paragraph_ordinal_first, paragraph_ordinal_last
    FROM norm_chunk
    WHERE norms_snapshot_id = :snapshot
      AND chunking_profile = :chunking_profile
      AND norm_chunk_pk IN :chunk_pks
    """
).bindparams(bindparam("chunk_pks", expanding=True))
_COUNT_CHUNKS = text(
    """
    SELECT count(*)
    FROM norm_chunk
    WHERE norms_snapshot_id = :snapshot
      AND chunking_profile = :chunking_profile
    """
)
_INSERT_WINDOW = text(
    """
    INSERT INTO norm_embedding (
        norms_snapshot_id, norm_chunk_pk, chunking_profile, embedding_profile,
        window_ordinal, token_count, char_offset, char_length,
        paragraph_ordinal_first, paragraph_ordinal_last,
        input_sha256, embedding_sha256, embedding
    ) VALUES (
        :snapshot, :chunk_pk, :chunking_profile, :embedding_profile,
        :window_ordinal, :token_count, :char_offset, :char_length,
        :paragraph_first, :paragraph_last,
        :input_sha256, :embedding_sha256, CAST(:embedding AS vector(1024))
    )
    """
)
_INSERT_BUILD = text(
    """
    INSERT INTO norm_embedding_build (
        norms_snapshot_id, chunking_profile, embedding_profile,
        chunk_count, window_count, embedding_set_sha256
    ) VALUES (
        :snapshot, :chunking_profile, :embedding_profile,
        :chunk_count, :window_count, :embedding_set_sha256
    )
    """
)
_NEAREST = text(
    """
    SELECT norm_chunk_pk, window_ordinal,
           -(embedding <#> CAST(:query AS vector(1024))) AS inner_product
    FROM norm_embedding
    WHERE norms_snapshot_id = :snapshot
      AND chunking_profile = :chunking_profile
      AND embedding_profile = :embedding_profile
    ORDER BY embedding <#> CAST(:query AS vector(1024))
    LIMIT :limit
    """
)


class NormEmbeddingConflict(RuntimeError):
    """The requested build is incomplete, malformed or conflicts with stored rows."""


@dataclass(frozen=True, slots=True)
class EmbeddingWindow:
    chunk_pk: int
    window_ordinal: int
    token_count: int
    char_offset: int
    char_length: int
    paragraph_ordinal_first: int
    paragraph_ordinal_last: int
    input_sha256: str
    embedding: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class StoredEmbeddingBuild:
    snapshot_id: NormsSnapshotId
    chunking_profile: str
    embedding_profile: str
    chunk_count: int
    window_count: int
    embedding_set_sha256: str
    created: bool


@dataclass(frozen=True, slots=True)
class NearestEmbedding:
    chunk_pk: int
    window_ordinal: int
    inner_product: float


@dataclass(frozen=True, slots=True)
class _PreparedWindow:
    source: EmbeddingWindow
    float32: tuple[float, ...]
    embedding_sha256: str
    vector_literal: str


def input_digest(text_value: str) -> str:
    """Digest the exact inference input without storing or logging it here."""
    return hashlib.sha256(text_value.encode("utf-8")).hexdigest()


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _to_float32(value: float) -> float:
    try:
        return struct.unpack("!f", struct.pack("!f", float(value)))[0]
    except (OverflowError, TypeError, ValueError, struct.error) as exc:
        raise NormEmbeddingConflict("embedding contains a value that is not finite float32") from exc


def _prepare_vector(values: Sequence[float]) -> tuple[tuple[float, ...], str, str]:
    if len(values) != EMBEDDING_DIMENSIONS:
        raise NormEmbeddingConflict(
            f"{EMBEDDING_PROFILE} requires {EMBEDDING_DIMENSIONS} dimensions, got {len(values)}"
        )
    converted = tuple(_to_float32(value) for value in values)
    if not all(math.isfinite(value) for value in converted):
        raise NormEmbeddingConflict("embedding contains NaN or infinity")
    norm = math.sqrt(math.fsum(value * value for value in converted))
    if abs(norm - 1.0) > UNIT_NORM_TOLERANCE:
        raise NormEmbeddingConflict(
            f"embedding must be L2-normalized within {UNIT_NORM_TOLERANCE}, got {norm:.8f}"
        )
    packed = struct.pack(f"!{EMBEDDING_DIMENSIONS}f", *converted)
    digest = hashlib.sha256(packed).hexdigest()
    literal = "[" + ",".join(format(value, ".9g") for value in converted) + "]"
    return converted, digest, literal


def _prepare_windows(windows: Sequence[EmbeddingWindow]) -> list[_PreparedWindow]:
    if not windows:
        raise NormEmbeddingConflict("a complete embedding build cannot contain zero windows")
    prepared: list[_PreparedWindow] = []
    for window in windows:
        if window.chunk_pk <= 0:
            raise NormEmbeddingConflict("chunk_pk must name a persisted private chunk key")
        if window.window_ordinal < 0:
            raise NormEmbeddingConflict("window ordinal cannot be negative")
        if not 1 <= window.token_count <= MAX_TOKENS:
            raise NormEmbeddingConflict(
                f"window token count must be between 1 and {MAX_TOKENS}"
            )
        if window.char_offset < 0 or window.char_length <= 0:
            raise NormEmbeddingConflict("window character span must be non-empty and non-negative")
        if (
            window.paragraph_ordinal_first < 0
            or window.paragraph_ordinal_last < window.paragraph_ordinal_first
        ):
            raise NormEmbeddingConflict("window paragraph span is invalid")
        if not _is_sha256(window.input_sha256):
            raise NormEmbeddingConflict("window input_sha256 is not a lowercase SHA-256")
        converted, digest, literal = _prepare_vector(window.embedding)
        prepared.append(
            _PreparedWindow(
                source=window,
                float32=converted,
                embedding_sha256=digest,
                vector_literal=literal,
            )
        )
    return prepared


def _set_digest(prepared: Sequence[_PreparedWindow]) -> str:
    digest = hashlib.sha256()
    for item in sorted(
        prepared, key=lambda value: (value.source.chunk_pk, value.source.window_ordinal)
    ):
        source = item.source
        document = {
            "char_length": source.char_length,
            "char_offset": source.char_offset,
            "chunk_pk": source.chunk_pk,
            "embedding_sha256": item.embedding_sha256,
            "input_sha256": source.input_sha256,
            "paragraph_ordinal_first": source.paragraph_ordinal_first,
            "paragraph_ordinal_last": source.paragraph_ordinal_last,
            "token_count": source.token_count,
            "window_ordinal": source.window_ordinal,
        }
        digest.update(json.dumps(document, sort_keys=True, separators=(",", ":")).encode())
        digest.update(b"\n")
    return digest.hexdigest()


def _batches(rows: list[dict[str, object]], size: int = 500) -> Iterable[list[dict[str, object]]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


class NormEmbeddingRepository:
    """Persist and query one exact, complete embedding profile build."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def ensure_build(
        self,
        *,
        snapshot_id: NormsSnapshotId,
        chunking_profile: str,
        windows: Sequence[EmbeddingWindow],
        embedding_profile: str = EMBEDDING_PROFILE,
    ) -> StoredEmbeddingBuild:
        if embedding_profile != EMBEDDING_PROFILE:
            raise NormEmbeddingConflict(
                f"this repository slot is frozen to {EMBEDDING_PROFILE!r}, got {embedding_profile!r}"
            )
        prepared = _prepare_windows(windows)
        grouped: dict[int, list[_PreparedWindow]] = defaultdict(list)
        for item in prepared:
            grouped[item.source.chunk_pk].append(item)
        for chunk_pk, items in grouped.items():
            ordinals = sorted(item.source.window_ordinal for item in items)
            if ordinals != list(range(len(ordinals))):
                raise NormEmbeddingConflict(
                    f"chunk {chunk_pk} window ordinals must be contiguous from zero, got {ordinals}"
                )

        parameters = {
            "snapshot": str(snapshot_id),
            "chunking_profile": chunking_profile,
            "embedding_profile": embedding_profile,
        }
        expected_digest = _set_digest(prepared)
        expected = (len(grouped), len(prepared), expected_digest)
        # The lock is transaction-scoped and key-local: two workers racing the same complete
        # projection serialize before observing/inserting it, while unrelated snapshots and
        # profiles remain concurrent. The caller still owns the transaction boundary.
        self._session.execute(_LOCK_BUILD, parameters)
        stored = self._session.execute(_SELECT_BUILD, parameters).one_or_none()
        if stored is not None:
            actual = (int(stored.chunk_count), int(stored.window_count), stored.embedding_set_sha256)
            if actual != expected:
                raise NormEmbeddingConflict(
                    f"embedding build {snapshot_id}/{chunking_profile}/{embedding_profile} "
                    f"already exists with {actual!r}, requested {expected!r}"
                )
            return StoredEmbeddingBuild(
                snapshot_id=snapshot_id,
                chunking_profile=chunking_profile,
                embedding_profile=embedding_profile,
                chunk_count=expected[0],
                window_count=expected[1],
                embedding_set_sha256=expected_digest,
                created=False,
            )

        chunk_rows = self._session.execute(
            _SELECT_CHUNKS,
            parameters | {"chunk_pks": sorted(grouped)},
        ).mappings()
        chunks = {int(row["norm_chunk_pk"]): row for row in chunk_rows}
        total_chunks = int(self._session.execute(_COUNT_CHUNKS, parameters).scalar_one())
        if set(chunks) != set(grouped) or total_chunks != len(grouped):
            missing = sorted(set(grouped) - set(chunks))
            raise NormEmbeddingConflict(
                "a complete build must cover every chunk of the selected snapshot/profile; "
                f"stored={total_chunks}, supplied={len(grouped)}, unknown={missing}"
            )
        for chunk_pk, items in grouped.items():
            chunk = chunks[chunk_pk]
            for item in items:
                source = item.source
                if source.char_offset + source.char_length > int(chunk["char_length"]):
                    raise NormEmbeddingConflict(f"chunk {chunk_pk} window exceeds its text span")
                if (
                    source.paragraph_ordinal_first < int(chunk["paragraph_ordinal_first"])
                    or source.paragraph_ordinal_last > int(chunk["paragraph_ordinal_last"])
                ):
                    raise NormEmbeddingConflict(
                        f"chunk {chunk_pk} window exceeds its canonical paragraph span"
                    )

        insert_rows = []
        for item in prepared:
            source = item.source
            insert_rows.append(
                parameters
                | {
                    "chunk_pk": source.chunk_pk,
                    "window_ordinal": source.window_ordinal,
                    "token_count": source.token_count,
                    "char_offset": source.char_offset,
                    "char_length": source.char_length,
                    "paragraph_first": source.paragraph_ordinal_first,
                    "paragraph_last": source.paragraph_ordinal_last,
                    "input_sha256": source.input_sha256,
                    "embedding_sha256": item.embedding_sha256,
                    "embedding": item.vector_literal,
                }
            )
        for batch in _batches(insert_rows):
            self._session.execute(_INSERT_WINDOW, batch)
        self._session.execute(
            _INSERT_BUILD,
            parameters
            | {
                "chunk_count": expected[0],
                "window_count": expected[1],
                "embedding_set_sha256": expected_digest,
            },
        )
        return StoredEmbeddingBuild(
            snapshot_id=snapshot_id,
            chunking_profile=chunking_profile,
            embedding_profile=embedding_profile,
            chunk_count=expected[0],
            window_count=expected[1],
            embedding_set_sha256=expected_digest,
            created=True,
        )

    def nearest(
        self,
        *,
        snapshot_id: NormsSnapshotId,
        chunking_profile: str,
        query: Sequence[float],
        limit: int,
        embedding_profile: str = EMBEDDING_PROFILE,
    ) -> tuple[NearestEmbedding, ...]:
        if not 1 <= limit <= 100:
            raise NormEmbeddingConflict("nearest limit must be between 1 and 100")
        _, _, literal = _prepare_vector(query)
        rows = self._session.execute(
            _NEAREST,
            {
                "snapshot": str(snapshot_id),
                "chunking_profile": chunking_profile,
                "embedding_profile": embedding_profile,
                "query": literal,
                "limit": limit,
            },
        )
        return tuple(
            NearestEmbedding(
                chunk_pk=int(row.norm_chunk_pk),
                window_ordinal=int(row.window_ordinal),
                inner_product=float(row.inner_product),
            )
            for row in rows
        )
