"""The repository's rules, against a scripted session: no PostgreSQL needed.

The same cases run against the real tables in ``tests/integration/db/test_norm_embeddings_migration.py``
(the owner's window); here the session answers each of the repository's statements from
memory, so the order of statements, what is inserted and when, and what is refused are exact.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.norms import embedding_repository as module
from auditmanager.norms.embedding.builder import embed_batch
from auditmanager.norms.embedding.digest import EmbeddingSetDigest
from auditmanager.norms.embedding.model import ChunkEmbedding
from auditmanager.norms.embedding.windowing import input_digest
from auditmanager.norms.embedding_repository import (
    HNSW_EF_SEARCH,
    HNSW_MAX_SCAN_TUPLES,
    NormEmbeddingConflict,
    NormEmbeddingRepository,
    NormEmbeddingScanShort,
)
from auditmanager.shared.identity import NormsSnapshotId
from tests.integration.norms.embedding.support import (
    CHUNKING_PROFILE,
    CONTENT_KEY,
    SNAPSHOT_ID,
    FakeEncoder,
    chunk_set,
)

SNAPSHOT = NormsSnapshotId.parse(SNAPSHOT_ID)


class _Result:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def one_or_none(self):
        return self._rows[0] if self._rows else None

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None

    def mappings(self):
        return iter(self._rows)

    def all(self):
        return list(self._rows)


class FakeSession:
    """Answers the repository's statements from in-memory chunks; records everything."""

    def __init__(self, chunks, *, unreliable: int = 0, nearest_rows: int | None = None) -> None:
        self.chunks = {item.key: (pk, item) for pk, item in enumerate(chunks, start=1)}
        self.unreliable = unreliable
        self.log: list[str] = []
        self.windows: list[dict[str, Any]] = []
        self.build: dict[str, Any] | None = None
        self.nearest_rows = nearest_rows
        self.commits = 0

    def commit(self) -> None:  # the repository must never call it
        self.commits += 1

    def execute(self, statement, parameters=None, execution_options=None):
        if statement is module._LOCK_BUILD:
            self.log.append("lock")
            return _Result([])
        if statement is module._SELECT_BUILD:
            self.log.append("select-build")
            row = None if self.build is None else SimpleNamespace(**self.build)
            return _Result([row] if row else [])
        if statement is module._SELECT_SUBJECT:
            self.log.append("select-subject")
            return _Result(
                [SimpleNamespace(content_key=CONTENT_KEY, unreliable_count=self.unreliable,
                                 chunk_count=len(self.chunks), stored_chunks=len(self.chunks))]
            )
        if statement is module._SELECT_GROUP:
            self.log.append(f"select-group:{len(parameters['refs'])}")
            rows = []
            for key in zip(parameters["refs"], parameters["ordinals"], strict=True):
                if key in self.chunks:
                    pk, item = self.chunks[key]
                    rows.append({
                        "norm_chunk_pk": pk, "source_document_ref": item.document_ref,
                        "ordinal": item.chunk_ordinal, "text": item.text,
                        "paragraph_ordinal_first": item.paragraph_ordinal_first,
                        "paragraph_ordinal_last": item.paragraph_ordinal_last,
                        "paragraph_lengths": list(item.paragraph_lengths),
                    })
            return _Result(rows)
        if statement is module._INSERT_WINDOW:
            self.log.append(f"insert-windows:{len(parameters)}")
            self.windows.extend(parameters)
            return _Result([])
        if statement is module._INSERT_BUILD:
            self.log.append("insert-build")
            self.build = {key: parameters[key] for key in ("chunk_count", "window_count", "embedding_set_sha256")}
            return _Result([])
        if statement is module._SELECT_CONTENT_KEY:
            return _Result([CONTENT_KEY])
        if statement is module._SELECT_STORED_WINDOWS:
            self.log.append("read-back")
            by_pk = {pk: item for pk, item in self.chunks.values()}
            rows = sorted(
                (
                    {
                        "source_document_ref": by_pk[row["chunk_pk"]].document_ref,
                        "chunk_ordinal": by_pk[row["chunk_pk"]].chunk_ordinal,
                        **{name: row[name] for name in ("window_ordinal", "token_count", "char_offset",
                                                         "char_length", "input_sha256", "embedding_sha256")},
                        "paragraph_ordinal_first": row["paragraph_first"],
                        "paragraph_ordinal_last": row["paragraph_last"],
                    }
                    for row in self.windows
                ),
                key=lambda row: (row["source_document_ref"], row["chunk_ordinal"], row["window_ordinal"]),
            )
            return _Result(rows)
        if statement in NormEmbeddingRepository.SCAN_SETTINGS:
            self.log.append("set:" + str(statement).split("SET LOCAL ", 1)[1])
            return _Result([])
        if statement is module._NEAREST:
            self.log.append("nearest")
            count = parameters["limit"] if self.nearest_rows is None else self.nearest_rows
            return _Result([SimpleNamespace(norm_chunk_pk=1, window_ordinal=0, inner_product=1.0)] * count)
        raise AssertionError(f"unexpected statement {statement}")


CHUNKS = chunk_set(300)


def _embeddings(chunks=CHUNKS) -> list[ChunkEmbedding]:
    return embed_batch(FakeEncoder(), chunks)


def _ensure(session: FakeSession, chunks) -> Any:
    return NormEmbeddingRepository(session).ensure_build(
        snapshot_id=SNAPSHOT, chunking_profile=CHUNKING_PROFILE, chunks=chunks
    )


def test_a_build_inserts_every_window_then_the_completion_row_last_and_never_commits() -> None:
    session = FakeSession(CHUNKS)
    embeddings = _embeddings()
    result = _ensure(session, iter(embeddings))
    assert result.created and result.chunk_count == 300
    assert result.window_count == sum(len(item.windows) for item in embeddings) == len(session.windows)
    inserts = [index for index, entry in enumerate(session.log) if entry.startswith("insert-windows")]
    assert session.log.index("insert-build") > max(inserts)
    assert session.log[-1] == "read-back" and session.commits == 0

    expected = EmbeddingSetDigest(content_key=CONTENT_KEY, chunking_profile=CHUNKING_PROFILE, embedding_profile="bge-m3-dense-v1")
    for item in embeddings:
        for window in item.windows:
            expected.add(item.document_ref, item.chunk_ordinal, window)
    assert result.embedding_set_sha256 == expected.hexdigest()


def test_the_build_is_consumed_group_by_group() -> None:
    """Memory is bounded by one group: chunks are pulled only as each group is written."""
    session = FakeSession(CHUNKS)
    pulled = 0
    high_water = 0

    def source() -> Iterator[ChunkEmbedding]:
        nonlocal pulled, high_water
        for item in _embeddings():
            pulled += 1
            written = len({(row["chunk_pk"]) for row in session.windows})
            high_water = max(high_water, pulled - written)
            yield item

    _ensure(session, source())
    assert high_water <= module._GROUP_CHUNKS
    groups = [entry for entry in session.log if entry.startswith("select-group")]
    assert groups == ["select-group:128", "select-group:128", "select-group:44"]


def test_a_replay_inserts_nothing_and_a_different_replay_is_a_conflict() -> None:
    session = FakeSession(CHUNKS)
    embeddings = _embeddings()
    _ensure(session, embeddings)
    stored = len(session.windows)
    replay = _ensure(session, embeddings)
    assert replay.created is False and len(session.windows) == stored

    changed = list(embeddings)
    first = changed[0]
    changed[0] = replace(first, windows=(replace(first.windows[0], vector=_embeddings(CHUNKS[1:2])[0].windows[0].vector),) + first.windows[1:])
    with pytest.raises(NormEmbeddingConflict, match="already exists"):
        _ensure(session, changed)
    assert len(session.windows) == stored


def test_a_replay_refuses_a_completion_row_with_a_missing_stored_window() -> None:
    session = FakeSession(CHUNKS[:2])
    embeddings = _embeddings(CHUNKS[:2])
    _ensure(session, embeddings)
    session.windows.pop()  # A row can be deleted while the completion row remains.

    with pytest.raises(NormEmbeddingConflict, match="stored rows digest/counts"):
        _ensure(session, embeddings)


def test_one_one_character_window_per_chunk_is_refused_before_anything_is_inserted() -> None:
    """`D-127`'s defect: the old check accepted any window inside the chunk's bounds."""
    session = FakeSession(CHUNKS)
    embeddings = _embeddings()
    degenerate = []
    for source, item in zip(CHUNKS, embeddings, strict=True):
        window = replace(
            item.windows[0],
            char_offset=0,
            char_length=1,
            paragraph_ordinal_last=source.paragraph_ordinal_first,
            input_sha256=input_digest(source.text[:1]),
        )
        degenerate.append(replace(item, windows=(window,)))
    with pytest.raises(NormEmbeddingConflict, match="last window ends"):
        _ensure(session, degenerate)
    assert session.windows == [] and session.build is None


@pytest.mark.parametrize("case", ["missing", "repeated", "unknown", "out-of-order"])
def test_anything_but_every_chunk_once_in_order_is_refused(case: str) -> None:
    session = FakeSession(CHUNKS)
    embeddings = _embeddings()
    if case == "missing":
        supplied, match = embeddings[:-1], "every chunk"
    elif case == "repeated":
        supplied, match = embeddings[:5] + embeddings[4:], "repeated or out of canonical order"
    elif case == "unknown":
        supplied, match = embeddings[:-1] + [replace(embeddings[-1], document_ref="doc-ü")], "not chunks of this"
    else:
        supplied, match = [embeddings[1], embeddings[0], *embeddings[2:]], "out of canonical order"
    with pytest.raises(NormEmbeddingConflict, match=match):
        _ensure(session, supplied)
    assert session.build is None


def test_characters_v1_over_an_unreliable_snapshot_is_refused() -> None:
    session = FakeSession(CHUNKS, unreliable=2)
    with pytest.raises(NormEmbeddingConflict, match="unreliable"):
        NormEmbeddingRepository(session).ensure_build(
            snapshot_id=SNAPSHOT, chunking_profile="characters-v1:1200", chunks=_embeddings()
        )
    with pytest.raises(NormEmbeddingConflict, match="malformed chunking profile"):
        NormEmbeddingRepository(session).ensure_build(
            snapshot_id=SNAPSHOT, chunking_profile="characters-v1-12000", chunks=_embeddings()
        )


QUERY = [1.0] + [0.0] * 1023


def test_nearest_scopes_the_d124_scan_settings_to_its_transaction_before_the_query() -> None:
    session = FakeSession(CHUNKS)
    _ensure(session, _embeddings())
    session.log.clear()
    rows = NormEmbeddingRepository(session).nearest(
        snapshot_id=SNAPSHOT, chunking_profile=CHUNKING_PROFILE, query=QUERY, limit=10
    )
    assert len(rows) == 10
    assert session.log == [
        "select-build",
        "set:hnsw.iterative_scan = strict_order",
        f"set:hnsw.ef_search = {HNSW_EF_SEARCH}",
        f"set:hnsw.max_scan_tuples = {HNSW_MAX_SCAN_TUPLES}",
        "nearest",
    ]
    assert HNSW_EF_SEARCH >= module.MAX_NEAREST_LIMIT


def test_nearest_refuses_a_short_scan_instead_of_returning_fewer_rows() -> None:
    session = FakeSession(CHUNKS, nearest_rows=3)
    _ensure(session, _embeddings())
    with pytest.raises(NormEmbeddingScanShort, match="3 of 10"):
        NormEmbeddingRepository(session).nearest(
            snapshot_id=SNAPSHOT, chunking_profile=CHUNKING_PROFILE, query=QUERY, limit=10
        )


def test_nearest_refuses_a_build_without_its_completion_row() -> None:
    session = FakeSession(CHUNKS)
    with pytest.raises(NormEmbeddingConflict, match="no complete embedding build"):
        NormEmbeddingRepository(session).nearest(
            snapshot_id=SNAPSHOT, chunking_profile=CHUNKING_PROFILE, query=QUERY, limit=10
        )
    assert "nearest" not in session.log
