"""Transaction-local persistence for rebuildable normative embedding windows.

No model is loaded here. The embedder (``auditmanager.norms.embedding``) computes windows and
vectors inside the norms-worker image and hands this boundary verified checkpoints; this module
owns the persistence invariants and exact replay behaviour; the caller owns commit/rollback.

* **Completeness (`D-127`).** A build is accepted only with every chunk's *full* window set
  (``windowing.verify_window_set``, applied here against the stored chunk text and paragraph
  layout): windows from the first character to the last, overlapping pairwise, each input
  digest the digest of exactly its slice, each paragraph span the one its slice touches, and
  every chunk of the snapshot's profile present exactly once.
* **Digest (`D-127`).** ``embedding_set_sha256`` is ``norm-embedding-set/2``
  (``embedding/digest.py``): keyed by ``content_key ‖ source_document_ref ‖ chunking_profile ‖
  ordinal``, never by the private ``norm_chunk_pk``, so the same corpus in another database has
  the same digest. After inserting, the digest is recomputed from the stored rows and must agree.
* **Invisible until complete.** Window rows and the completion row are written in the caller's
  one transaction, the completion row last; ``fk_norm_embedding_build`` is deferred to commit,
  so no other transaction ever sees a window without its build, and :meth:`nearest` refuses a
  build that has no completion row.
* **Streaming.** :meth:`ensure_build` consumes its chunks group by group; memory is bounded by
  one group, not by the build.
* **Filtered search (`D-124`).** The one HNSW index spans every snapshot and profile and the
  filter runs after the index scan. :meth:`nearest` therefore sets, for its transaction only,
  ``hnsw.iterative_scan = strict_order`` (the scan continues past filtered-out tuples, in exact
  distance order), ``hnsw.ef_search`` and ``hnsw.max_scan_tuples``, and refuses a short answer
  rather than returning fewer rows than the build holds.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.identity import NormsSnapshotId

from .chunking import CHUNKING_PROFILE_VERSION, parse_chunking_profile
from .embedding import vectors
from .embedding.digest import EmbeddingSetDigest
from .embedding.model import ChunkEmbedding, ChunkInput
from .embedding.profile import DIMENSIONS, EMBEDDING_PROFILE, MAX_TOKENS
from .embedding.windowing import (
    WindowFacts,
    WindowingRefused,
    input_digest,
    verify_window_set,
)

EMBEDDING_DIMENSIONS = DIMENSIONS

#: `D-124`. ``ef_search`` bounds the candidate list of each scan step and must be at least the
#: largest ``limit``; ``max_scan_tuples`` bounds how far an iterative scan may walk past
#: filtered-out tuples (pgvector's default is 20 000). Real-vector recall and p95 latency are
#: measured in W55, which owns any retuning.
HNSW_EF_SEARCH = 200
HNSW_MAX_SCAN_TUPLES = 100_000
MAX_NEAREST_LIMIT = 100

#: Chunks per SELECT/INSERT round trip while a build streams in.
_GROUP_CHUNKS = 128
_INSERT_ROWS = 500

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
_SELECT_SUBJECT = text(
    """
    SELECT s.content_key, s.unreliable_count, b.chunk_count,
           (SELECT count(*) FROM norm_chunk c
            WHERE c.norms_snapshot_id = s.norms_snapshot_id
              AND c.chunking_profile = :chunking_profile) AS stored_chunks
    FROM norms_snapshot s
    LEFT JOIN norm_chunk_build b
      ON b.norms_snapshot_id = s.norms_snapshot_id AND b.chunking_profile = :chunking_profile
    WHERE s.norms_snapshot_id = :snapshot
    """
)
_PARAGRAPH_LENGTHS = """
    ARRAY(
        SELECT char_length(p.text) FROM norm_paragraph p
        WHERE p.norms_snapshot_id = c.norms_snapshot_id
          AND p.norm_document_pk = c.norm_document_pk
          AND p.ordinal BETWEEN c.paragraph_ordinal_first AND c.paragraph_ordinal_last
        ORDER BY p.ordinal
    ) AS paragraph_lengths
"""
_SELECT_CHUNK_INPUTS = text(
    f"""
    SELECT d.source_document_ref, c.ordinal, c.text,
           c.paragraph_ordinal_first, c.paragraph_ordinal_last,
           {_PARAGRAPH_LENGTHS}
    FROM norm_chunk c
    JOIN norm_document d
      ON d.norms_snapshot_id = c.norms_snapshot_id AND d.norm_document_pk = c.norm_document_pk
    WHERE c.norms_snapshot_id = :snapshot AND c.chunking_profile = :chunking_profile
    ORDER BY d.source_document_ref COLLATE "C", c.ordinal
    """
)
_SELECT_GROUP = text(
    f"""
    SELECT c.norm_chunk_pk, d.source_document_ref, c.ordinal, c.text,
           c.paragraph_ordinal_first, c.paragraph_ordinal_last,
           {_PARAGRAPH_LENGTHS}
    FROM unnest(CAST(:refs AS text[]), CAST(:ordinals AS integer[])) AS k(source_document_ref, ordinal)
    JOIN norm_document d
      ON d.norms_snapshot_id = :snapshot AND d.source_document_ref = k.source_document_ref
    JOIN norm_chunk c
      ON c.norms_snapshot_id = :snapshot
     AND c.chunking_profile = :chunking_profile
     AND c.norm_document_pk = d.norm_document_pk
     AND c.ordinal = k.ordinal
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
_SELECT_STORED_WINDOWS = text(
    """
    SELECT d.source_document_ref, c.ordinal AS chunk_ordinal, e.window_ordinal, e.token_count,
           e.char_offset, e.char_length, e.paragraph_ordinal_first, e.paragraph_ordinal_last,
           e.input_sha256, e.embedding_sha256
    FROM norm_embedding e
    JOIN norm_chunk c ON c.norm_chunk_pk = e.norm_chunk_pk
    JOIN norm_document d
      ON d.norms_snapshot_id = c.norms_snapshot_id AND d.norm_document_pk = c.norm_document_pk
    WHERE e.norms_snapshot_id = :snapshot
      AND e.chunking_profile = :chunking_profile
      AND e.embedding_profile = :embedding_profile
    ORDER BY d.source_document_ref COLLATE "C", c.ordinal, e.window_ordinal
    """
)
_SELECT_CONTENT_KEY = text(
    "SELECT content_key FROM norms_snapshot WHERE norms_snapshot_id = :snapshot"
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


class NormEmbeddingScanShort(NormEmbeddingConflict):
    """A filtered HNSW scan returned fewer rows than the build holds (`D-124`)."""


@dataclass(frozen=True, slots=True)
class BuildSubject:
    """What a build is of: the snapshot's content key and its chunk set."""

    content_key: str
    unreliable_count: int
    chunk_count: int


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


def _facts(chunk: ChunkEmbedding) -> list[WindowFacts]:
    return [
        WindowFacts(
            window_ordinal=window.window_ordinal,
            char_offset=window.char_offset,
            char_length=window.char_length,
            token_count=window.token_count,
            paragraph_ordinal_first=window.paragraph_ordinal_first,
            paragraph_ordinal_last=window.paragraph_ordinal_last,
            input_sha256=window.input_sha256,
        )
        for window in chunk.windows
    ]


def _groups(chunks: Iterable[ChunkEmbedding], size: int) -> Iterator[list[ChunkEmbedding]]:
    group: list[ChunkEmbedding] = []
    for chunk in chunks:
        group.append(chunk)
        if len(group) == size:
            yield group
            group = []
    if group:
        yield group


class NormEmbeddingRepository:
    """Persist and query one exact, complete embedding profile build."""

    #: `D-124`: statements :meth:`nearest` runs first, scoped to the caller's transaction.
    SCAN_SETTINGS: tuple = (
        text("SET LOCAL hnsw.iterative_scan = strict_order"),
        text(f"SET LOCAL hnsw.ef_search = {HNSW_EF_SEARCH}"),
        text(f"SET LOCAL hnsw.max_scan_tuples = {HNSW_MAX_SCAN_TUPLES}"),
    )

    def __init__(self, session: Session) -> None:
        self._session = session

    # --- reading what a build is of ------------------------------------------------------

    def build_subject(self, snapshot_id: NormsSnapshotId, chunking_profile: str) -> BuildSubject:
        """The snapshot's content key and complete chunk set, or a refusal naming what is missing."""
        version, _ = self._parse_profile(chunking_profile)
        row = self._session.execute(
            _SELECT_SUBJECT, {"snapshot": str(snapshot_id), "chunking_profile": chunking_profile}
        ).one_or_none()
        if row is None:
            raise NormEmbeddingConflict(f"snapshot {snapshot_id} is not stored")
        if row.chunk_count is None:
            raise NormEmbeddingConflict(
                f"snapshot {snapshot_id} has no complete {chunking_profile} chunk build; build it "
                "from the stored paragraphs first (NormsRepository.build_chunks_from_stored)"
            )
        if version == CHUNKING_PROFILE_VERSION and int(row.unreliable_count) > 0:
            raise NormEmbeddingConflict(
                f"{chunking_profile} over snapshot {snapshot_id} is refused: it carries "
                f"{int(row.unreliable_count)} unreliable block(s)"
            )
        if int(row.stored_chunks) != int(row.chunk_count):
            raise NormEmbeddingConflict(
                f"the {chunking_profile} build records {int(row.chunk_count)} chunks but "
                f"{int(row.stored_chunks)} are stored"
            )
        return BuildSubject(str(row.content_key), int(row.unreliable_count), int(row.chunk_count))

    def iter_chunk_inputs(
        self, snapshot_id: NormsSnapshotId, chunking_profile: str
    ) -> Iterator[ChunkInput]:
        """Every chunk of the profile, streamed in canonical ``(document ref, ordinal)`` order."""
        result = self._session.execute(
            _SELECT_CHUNK_INPUTS,
            {"snapshot": str(snapshot_id), "chunking_profile": chunking_profile},
            execution_options={"stream_results": True, "yield_per": 500},
        )
        for row in result.mappings():
            yield ChunkInput(
                document_ref=str(row["source_document_ref"]),
                chunk_ordinal=int(row["ordinal"]),
                text=str(row["text"]),
                paragraph_ordinal_first=int(row["paragraph_ordinal_first"]),
                paragraph_ordinal_last=int(row["paragraph_ordinal_last"]),
                paragraph_lengths=tuple(int(value) for value in row["paragraph_lengths"]),
            )

    # --- the build ---------------------------------------------------------------------

    def ensure_build(
        self,
        *,
        snapshot_id: NormsSnapshotId,
        chunking_profile: str,
        chunks: Iterable[ChunkEmbedding],
        embedding_profile: str = EMBEDDING_PROFILE,
    ) -> StoredEmbeddingBuild:
        """Insert one complete build with its completion row last, or confirm an equal one.

        ``chunks`` must come in canonical order and name every chunk of the profile once. On
        replay of an existing build nothing is inserted; any difference in the computed digest
        or counts is a conflict. Any refusal leaves the caller's transaction to roll back.
        """
        if embedding_profile != EMBEDDING_PROFILE:
            raise NormEmbeddingConflict(
                f"this repository slot is frozen to {EMBEDDING_PROFILE!r}, got {embedding_profile!r}"
            )
        parameters = {
            "snapshot": str(snapshot_id),
            "chunking_profile": chunking_profile,
            "embedding_profile": embedding_profile,
        }
        # The lock is transaction-scoped and key-local: two loaders racing the same build
        # serialise before observing/inserting it; unrelated builds remain concurrent.
        self._session.execute(_LOCK_BUILD, parameters)
        stored = self._session.execute(_SELECT_BUILD, parameters).one_or_none()
        subject = self.build_subject(snapshot_id, chunking_profile)
        digest = EmbeddingSetDigest(
            content_key=subject.content_key,
            chunking_profile=chunking_profile,
            embedding_profile=embedding_profile,
        )
        chunk_total = 0
        previous: tuple[str, int] | None = None
        for group in _groups(chunks, _GROUP_CHUNKS):
            for chunk in group:
                if previous is not None and not chunk.key > previous:
                    raise NormEmbeddingConflict(
                        f"chunk {chunk.key!r} is repeated or out of canonical order after {previous!r}"
                    )
                previous = chunk.key
            rows = self._insert_group(parameters, group, digest, insert=stored is None)
            chunk_total += rows
        if chunk_total == 0:
            raise NormEmbeddingConflict("a complete embedding build cannot contain zero windows")
        if chunk_total != subject.chunk_count:
            raise NormEmbeddingConflict(
                "a complete build must cover every chunk of the selected snapshot/profile; "
                f"stored={subject.chunk_count}, supplied={chunk_total}"
            )
        expected = (chunk_total, digest.windows, digest.hexdigest())
        if stored is not None:
            actual = (int(stored.chunk_count), int(stored.window_count), stored.embedding_set_sha256)
            if actual != expected:
                raise NormEmbeddingConflict(
                    f"embedding build {snapshot_id}/{chunking_profile}/{embedding_profile} "
                    f"already exists with {actual!r}, requested {expected!r}"
                )
            return self._result(snapshot_id, chunking_profile, embedding_profile, expected, False)

        self._session.execute(
            _INSERT_BUILD,
            parameters
            | {
                "chunk_count": expected[0],
                "window_count": expected[1],
                "embedding_set_sha256": expected[2],
            },
        )
        read_back = self.stored_build_digest(snapshot_id, chunking_profile, embedding_profile)
        if read_back != (expected[2], expected[0], expected[1]):
            raise NormEmbeddingConflict(
                f"the stored rows digest to {read_back!r}, the build computed {expected!r}"
            )
        return self._result(snapshot_id, chunking_profile, embedding_profile, expected, True)

    def _insert_group(
        self,
        parameters: dict[str, str],
        group: Sequence[ChunkEmbedding],
        digest: EmbeddingSetDigest,
        *,
        insert: bool,
    ) -> int:
        stored = {
            (str(row["source_document_ref"]), int(row["ordinal"])): row
            for row in self._session.execute(
                _SELECT_GROUP,
                parameters
                | {
                    "refs": [chunk.document_ref for chunk in group],
                    "ordinals": [chunk.chunk_ordinal for chunk in group],
                },
            ).mappings()
        }
        unknown = [chunk.key for chunk in group if chunk.key not in stored]
        if unknown:
            raise NormEmbeddingConflict(
                f"{len(unknown)} chunk(s) are not chunks of this snapshot/profile, first {unknown[0]!r}"
            )
        rows: list[dict[str, object]] = []
        for chunk in group:
            row = stored[chunk.key]
            try:
                verify_window_set(
                    label=f"chunk {chunk.key!r}",
                    text=str(row["text"]),
                    paragraph_ordinal_first=int(row["paragraph_ordinal_first"]),
                    paragraph_ordinal_last=int(row["paragraph_ordinal_last"]),
                    paragraph_lengths=tuple(int(value) for value in row["paragraph_lengths"]),
                    windows=_facts(chunk),
                    limit=MAX_TOKENS,
                )
            except WindowingRefused as exc:
                raise NormEmbeddingConflict(str(exc)) from exc
            for window in chunk.windows:
                try:
                    vectors.require_unit(window.vector)
                except vectors.VectorRefused as exc:
                    raise NormEmbeddingConflict(f"chunk {chunk.key!r}: {exc}") from exc
                digest.add(chunk.document_ref, chunk.chunk_ordinal, window)
                if insert:
                    rows.append(
                        parameters
                        | {
                            "chunk_pk": int(row["norm_chunk_pk"]),
                            "window_ordinal": window.window_ordinal,
                            "token_count": window.token_count,
                            "char_offset": window.char_offset,
                            "char_length": window.char_length,
                            "paragraph_first": window.paragraph_ordinal_first,
                            "paragraph_last": window.paragraph_ordinal_last,
                            "input_sha256": window.input_sha256,
                            "embedding_sha256": window.embedding_sha256,
                            "embedding": vectors.pgvector_literal(window.vector),
                        }
                    )
        for start in range(0, len(rows), _INSERT_ROWS):
            self._session.execute(_INSERT_WINDOW, rows[start : start + _INSERT_ROWS])
        return len(group)

    @staticmethod
    def _result(
        snapshot_id: NormsSnapshotId,
        chunking_profile: str,
        embedding_profile: str,
        expected: tuple[int, int, str],
        created: bool,
    ) -> StoredEmbeddingBuild:
        return StoredEmbeddingBuild(
            snapshot_id=snapshot_id,
            chunking_profile=chunking_profile,
            embedding_profile=embedding_profile,
            chunk_count=expected[0],
            window_count=expected[1],
            embedding_set_sha256=expected[2],
            created=created,
        )

    @staticmethod
    def _parse_profile(chunking_profile: str) -> tuple[str, int]:
        try:
            return parse_chunking_profile(chunking_profile)
        except ValueError as exc:
            raise NormEmbeddingConflict(str(exc)) from exc

    def stored_build_digest(
        self,
        snapshot_id: NormsSnapshotId,
        chunking_profile: str,
        embedding_profile: str = EMBEDDING_PROFILE,
    ) -> tuple[str, int, int]:
        """``(digest, chunk count, window count)`` recomputed from the stored rows, streamed."""
        content_key = self._session.execute(
            _SELECT_CONTENT_KEY, {"snapshot": str(snapshot_id)}
        ).scalar_one_or_none()
        if content_key is None:
            raise NormEmbeddingConflict(f"snapshot {snapshot_id} is not stored")
        digest = EmbeddingSetDigest(
            content_key=str(content_key),
            chunking_profile=chunking_profile,
            embedding_profile=embedding_profile,
        )
        result = self._session.execute(
            _SELECT_STORED_WINDOWS,
            {
                "snapshot": str(snapshot_id),
                "chunking_profile": chunking_profile,
                "embedding_profile": embedding_profile,
            },
            execution_options={"stream_results": True, "yield_per": 2000},
        )
        last_chunk: tuple[str, int] | None = None
        chunk_count = 0
        for row in result.mappings():
            key = (str(row["source_document_ref"]), int(row["chunk_ordinal"]))
            if key != last_chunk:
                chunk_count += 1
                last_chunk = key
            digest.add_values(
                key[0],
                key[1],
                window_ordinal=int(row["window_ordinal"]),
                token_count=int(row["token_count"]),
                char_offset=int(row["char_offset"]),
                char_length=int(row["char_length"]),
                paragraph_ordinal_first=int(row["paragraph_ordinal_first"]),
                paragraph_ordinal_last=int(row["paragraph_ordinal_last"]),
                input_sha256=str(row["input_sha256"]),
                embedding_sha256=str(row["embedding_sha256"]),
            )
        return digest.hexdigest(), chunk_count, digest.windows

    # --- search -------------------------------------------------------------------------

    def nearest(
        self,
        *,
        snapshot_id: NormsSnapshotId,
        chunking_profile: str,
        query: Sequence[float],
        limit: int,
        embedding_profile: str = EMBEDDING_PROFILE,
    ) -> tuple[NearestEmbedding, ...]:
        if not 1 <= limit <= MAX_NEAREST_LIMIT:
            raise NormEmbeddingConflict(f"nearest limit must be between 1 and {MAX_NEAREST_LIMIT}")
        try:
            literal = vectors.pgvector_literal(vectors.pack(query))
        except vectors.VectorRefused as exc:
            raise NormEmbeddingConflict(str(exc)) from exc
        parameters = {
            "snapshot": str(snapshot_id),
            "chunking_profile": chunking_profile,
            "embedding_profile": embedding_profile,
        }
        build = self._session.execute(_SELECT_BUILD, parameters).one_or_none()
        if build is None:
            raise NormEmbeddingConflict(
                f"no complete embedding build {snapshot_id}/{chunking_profile}/{embedding_profile}"
            )
        for statement in self.SCAN_SETTINGS:
            self._session.execute(statement)
        rows = self._session.execute(_NEAREST, parameters | {"query": literal, "limit": limit}).all()
        expected = min(limit, int(build.window_count))
        if len(rows) < expected:
            raise NormEmbeddingScanShort(
                f"the filtered HNSW scan returned {len(rows)} of {expected} rows for "
                f"{snapshot_id}/{chunking_profile}; raise hnsw.max_scan_tuples (D-124)"
            )
        return tuple(
            NearestEmbedding(
                chunk_pk=int(row.norm_chunk_pk),
                window_ordinal=int(row.window_ordinal),
                inner_product=float(row.inner_product),
            )
            for row in rows
        )


__all__ = [
    "EMBEDDING_DIMENSIONS",
    "EMBEDDING_PROFILE",
    "HNSW_EF_SEARCH",
    "HNSW_MAX_SCAN_TUPLES",
    "BuildSubject",
    "NearestEmbedding",
    "NormEmbeddingConflict",
    "NormEmbeddingRepository",
    "NormEmbeddingScanShort",
    "StoredEmbeddingBuild",
    "input_digest",
]
