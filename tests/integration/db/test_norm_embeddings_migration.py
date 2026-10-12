"""The pgvector extension and normative embedding projection are exact and rebuildable.

`W54-EMBED-01` repository cases, against the real tables (the owner's window):

* `D-127` — a build is complete only with every chunk's full window set, and its digest is
  keyed by computed keys: the same content in a database whose private chunk keys differ has
  the same digest;
* rows are invisible to every other transaction until the completion row commits, and a load
  that dies midway leaves nothing;
* `D-124` — two snapshots with synthetic vectors in the one HNSW index: without the scan
  settings the filtered scan returns nothing for the far snapshot (shown here, on purpose), with
  them it returns ``limit`` rows of that snapshot;
* prepare → build (fake encoder) → load, end to end through the checkpoint files.
"""

from __future__ import annotations

import hashlib
import math
import struct
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from auditmanager.norms.chunking import JOIN
from auditmanager.norms.embedding import vectors
from auditmanager.norms.embedding.builder import embed_batch, run_build
from auditmanager.norms.embedding.checkpoint import checkpoint_digest, read_plan
from auditmanager.norms.embedding.model import ChunkEmbedding, EmbeddedWindow
from auditmanager.norms.embedding.operations import load, prepare
from auditmanager.norms.embedding_repository import (
    EMBEDDING_DIMENSIONS,
    NormEmbeddingConflict,
    NormEmbeddingRepository,
    NormEmbeddingScanShort,
    input_digest,
)
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import NormsSnapshotId
from tests.integration.db.conftest import (  # type: ignore[import-not-found]
    clear_the_role_backfill,
)
from tests.integration.norms.embedding.support import FakeEncoder, paragraph

SNAPSHOT_ID = NormsSnapshotId.parse("ns_" + "0" * 26)
OTHER_SNAPSHOT_ID = NormsSnapshotId.parse("ns_" + "1" * 26)
CHUNKING_PROFILE = "characters-v2:1200"
CONTENT_KEY = "2026-07-23..2026-07-23+0d." + "1" * 12
OTHER_CONTENT_KEY = "2026-07-23..2026-07-23+0d." + "2" * 12

TWO_CHUNKS = {"source-1": [["0123456789"], ["abcdefghij"]]}


def _unit_vector(index: int) -> tuple[float, ...]:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[index] = 1.0
    return tuple(values)


def _seed(
    engine: Engine,
    documents: dict[str, list[list[str]]],
    *,
    snapshot_id: NormsSnapshotId = SNAPSHOT_ID,
    content_key: str = CONTENT_KEY,
    number: int = 0,
) -> None:
    """One snapshot whose documents hold chunks of paragraphs, and its chunk build."""
    chunk_count = sum(len(chunks) for chunks in documents.values())
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO norms_snapshot (
                    norms_snapshot_id, content_key, base_content_key, content_digest,
                    drawn_from, drawn_to, undated_documents, document_count,
                    repair_count, segmentation_profile
                ) VALUES (
                    :snapshot, :content_key, :content_key, :digest,
                    DATE '2026-07-23', DATE '2026-07-23', 0, :documents, 0, 'markdown-v1'
                )
                """
            ),
            {
                "snapshot": str(snapshot_id),
                "content_key": content_key,
                "digest": hashlib.sha256(content_key.encode()).hexdigest(),
                "documents": len(documents),
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO norm_chunk_build (
                    norms_snapshot_id, chunking_profile, target_characters, chunk_count
                ) VALUES (:snapshot, :profile, 1200, :count)
                """
            ),
            {"snapshot": str(snapshot_id), "profile": CHUNKING_PROFILE, "count": chunk_count},
        )
        for document_index, (reference, chunks) in enumerate(documents.items()):
            paragraphs = [value for chunk in chunks for value in chunk]
            document_pk = int(
                connection.execute(
                    text(
                        """
                        INSERT INTO norm_document (
                            norm_document_id, norms_snapshot_id, source_document_ref, slug,
                            title, doc_type, source_attribution, pdf_page_count, block_count,
                            page_heading_count, recognised_characters, paragraph_count
                        ) VALUES (
                            :identity, :snapshot, :reference, :slug, 'title.pdf', 'СП',
                            'unattributed', 1, :paragraphs, 0, :characters, :paragraphs
                        ) RETURNING norm_document_pk
                        """
                    ),
                    {
                        "identity": f"ndoc_{number}{document_index:025d}",
                        "snapshot": str(snapshot_id),
                        "reference": reference,
                        "slug": f"slug-{document_index}",
                        "paragraphs": len(paragraphs),
                        "characters": sum(len(value) for value in paragraphs),
                    },
                ).scalar_one()
            )
            ordinal = offset = 0
            for chunk_ordinal, chunk in enumerate(chunks):
                first = ordinal
                chunk_offset = offset
                for value in chunk:
                    connection.execute(
                        text(
                            """
                            INSERT INTO norm_paragraph (
                                norm_paragraph_id, norms_snapshot_id, norm_document_pk, ordinal,
                                page_label, block_ref, char_offset, char_length, kind, text
                            ) VALUES (
                                :identity, :snapshot, :document, :ordinal,
                                1, :block, :offset, :length, 'body', :text
                            )
                            """
                        ),
                        {
                            "identity": f"npar_{number}{document_index:05d}{ordinal:020d}",
                            "snapshot": str(snapshot_id),
                            "document": document_pk,
                            "ordinal": ordinal,
                            "block": f"block-{ordinal}",
                            "offset": offset,
                            "length": len(value),
                            "text": value,
                        },
                    )
                    ordinal += 1
                    offset += len(value) + len(JOIN)
                joined = JOIN.join(chunk)
                connection.execute(
                    text(
                        """
                        INSERT INTO norm_chunk (
                            norms_snapshot_id, norm_document_pk, chunking_profile,
                            ordinal, page_first, page_last, char_offset, char_length,
                            paragraph_ordinal_first, paragraph_ordinal_last,
                            paragraph_count, clause_numbers, contains_clause,
                            text, content_sha256
                        ) VALUES (
                            :snapshot, :document, :profile,
                            :ordinal, 1, 1, :offset, :length,
                            :first, :last, :count, '{}', false,
                            :text, :digest
                        )
                        """
                    ),
                    {
                        "snapshot": str(snapshot_id),
                        "document": document_pk,
                        "profile": CHUNKING_PROFILE,
                        "ordinal": chunk_ordinal,
                        "offset": chunk_offset,
                        "length": len(joined),
                        "first": first,
                        "last": ordinal - 1,
                        "count": len(chunk),
                        "text": joined,
                        "digest": hashlib.sha256(joined.encode()).hexdigest(),
                    },
                )


def _whole(reference: str, ordinal: int, value: str, vector: tuple[float, ...], first: int) -> ChunkEmbedding:
    """One chunk of one paragraph, embedded as one window covering all of it."""
    return ChunkEmbedding(
        reference,
        ordinal,
        (
            EmbeddedWindow(
                window_ordinal=0,
                char_offset=0,
                char_length=len(value),
                token_count=5,
                paragraph_ordinal_first=first,
                paragraph_ordinal_last=first,
                input_sha256=input_digest(value),
                vector=vectors.pack(vector),
            ),
        ),
    )


def _two_windows() -> list[ChunkEmbedding]:
    return [
        _whole("source-1", 0, "0123456789", _unit_vector(0), 0),
        _whole("source-1", 1, "abcdefghij", _unit_vector(1), 1),
    ]


def _ensure(session: Session, chunks, snapshot_id: NormsSnapshotId = SNAPSHOT_ID):
    return NormEmbeddingRepository(session).ensure_build(
        snapshot_id=snapshot_id, chunking_profile=CHUNKING_PROFILE, chunks=chunks
    )


def _count(engine: Engine, table: str) -> int:
    with engine.connect() as connection:
        return int(connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())


def test_extension_profile_type_and_hnsw_index_are_exact(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        version = connection.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        ).scalar_one()
        profile = connection.execute(
            text(
                """
                SELECT model_repository, model_revision, pooling, dimensions,
                       normalized, distance_metric, max_tokens, overlap_tokens
                FROM norm_embedding_profile
                WHERE embedding_profile = 'bge-m3-dense-v1'
                """
            )
        ).one()
        vector_type = connection.execute(
            text(
                """
                SELECT format_type(a.atttypid, a.atttypmod)
                FROM pg_attribute a
                JOIN pg_class c ON c.oid = a.attrelid
                WHERE c.relname = 'norm_embedding' AND a.attname = 'embedding'
                """
            )
        ).scalar_one()
        index_definition = connection.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE indexname = 'ix_norm_embedding_hnsw_ip'"
            )
        ).scalar_one()

    assert version == "0.8.6"
    assert profile == (
        "BAAI/bge-m3",
        "5617a9f61b028005a4858fdac845db406aefb181",
        "cls",
        1024,
        True,
        "inner_product",
        512,
        64,
    )
    assert vector_type == "vector(1024)"
    assert "USING hnsw" in index_definition
    assert "vector_ip_ops" in index_definition


def test_complete_build_is_idempotent_and_inner_product_ordered(migrated_engine: Engine) -> None:
    _seed(migrated_engine, TWO_CHUNKS)

    with Session(migrated_engine) as session, session.begin():
        created = _ensure(session, _two_windows())
    assert created.created is True
    assert (created.chunk_count, created.window_count) == (2, 2)

    with Session(migrated_engine) as session, session.begin():
        repository = NormEmbeddingRepository(session)
        replay = _ensure(session, _two_windows())
        nearest = repository.nearest(
            snapshot_id=SNAPSHOT_ID,
            chunking_profile=CHUNKING_PROFILE,
            query=_unit_vector(0),
            limit=2,
        )
        stored = repository.stored_build_digest(SNAPSHOT_ID, CHUNKING_PROFILE)

    assert replay.created is False
    assert replay.embedding_set_sha256 == created.embedding_set_sha256
    assert stored == (created.embedding_set_sha256, 2, 2)
    assert [row.window_ordinal for row in nearest] == [0, 0]
    assert nearest[0].inner_product == pytest.approx(1.0)
    assert nearest[1].inner_product == pytest.approx(0.0)


def test_invalid_incomplete_or_conflicting_build_writes_nothing(migrated_engine: Engine) -> None:
    _seed(migrated_engine, TWO_CHUNKS)
    good = _two_windows()
    zero = good[:-1] + [
        ChunkEmbedding(
            good[-1].document_ref,
            good[-1].chunk_ordinal,
            (EmbeddedWindow(**{
                **{name: getattr(good[-1].windows[0], name) for name in (
                    "window_ordinal", "char_offset", "char_length", "token_count",
                    "paragraph_ordinal_first", "paragraph_ordinal_last", "input_sha256")},
                "vector": struct.pack("!1024f", *([0.0] * 1024)),
            }),),
        )
    ]
    one_character = good[:-1] + [
        ChunkEmbedding(
            "source-1",
            1,
            (
                EmbeddedWindow(0, 0, 1, 1, 1, 1, input_digest("a"), vectors.pack(_unit_vector(1))),
            ),
        )
    ]
    for invalid, match in ((zero, "normalized"), (one_character, "last window ends"), (good[:-1], "every chunk")):
        with (
            Session(migrated_engine) as session,
            pytest.raises(NormEmbeddingConflict, match=match),
            session.begin(),
        ):
            _ensure(session, invalid)
        assert _count(migrated_engine, "norm_embedding") == 0
        assert _count(migrated_engine, "norm_embedding_build") == 0

    with Session(migrated_engine) as session, session.begin():
        _ensure(session, good)
    conflicting = good[:-1] + [_whole("source-1", 1, "abcdefghij", _unit_vector(2), 1)]
    with (
        Session(migrated_engine) as session,
        pytest.raises(NormEmbeddingConflict, match="already exists"),
        session.begin(),
    ):
        _ensure(session, conflicting)
    assert _count(migrated_engine, "norm_embedding") == 2


def test_chunk_inputs_stream_in_code_point_order_with_their_paragraph_layout(migrated_engine: Engine) -> None:
    _seed(migrated_engine, {"doc-é": [["е" * 7]], "doc-a": [["a" * 3, "b" * 4], ["c" * 5]]})
    with Session(migrated_engine) as session:
        repository = NormEmbeddingRepository(session)
        inputs = list(repository.iter_chunk_inputs(SNAPSHOT_ID, CHUNKING_PROFILE))
        subject = repository.build_subject(SNAPSHOT_ID, CHUNKING_PROFILE)
    assert [item.key for item in inputs] == [("doc-a", 0), ("doc-a", 1), ("doc-é", 0)]
    assert inputs[0].text == "aaa\n\nbbbb" and inputs[0].paragraph_lengths == (3, 4)
    assert (inputs[1].paragraph_ordinal_first, inputs[1].paragraph_ordinal_last) == (2, 2)
    assert (subject.content_key, subject.chunk_count) == (CONTENT_KEY, 3)


def test_the_digest_is_the_same_in_a_database_whose_private_keys_differ(
    migrated_database_factory, migrated_engine: Engine
) -> None:
    """`D-127`: the old digest hashed ``norm_chunk_pk``; this one hashes computed keys."""
    other = create_database_engine(migrated_database_factory())
    try:
        with other.begin() as connection:
            connection.execute(
                text("SELECT setval(pg_get_serial_sequence('norm_chunk', 'norm_chunk_pk'), 7000)")
            )
        digests, pks = [], []
        for engine in (migrated_engine, other):
            _seed(engine, TWO_CHUNKS)
            with Session(engine) as session, session.begin():
                digests.append(_ensure(session, _two_windows()).embedding_set_sha256)
            with engine.connect() as connection:
                pks.append(connection.execute(text("SELECT min(norm_chunk_pk) FROM norm_embedding")).scalar_one())
    finally:
        other.dispose()
    assert pks[0] != pks[1]
    assert digests[0] == digests[1]


def test_rows_are_invisible_until_the_completion_row_commits_and_a_dead_load_leaves_nothing(
    migrated_engine: Engine,
) -> None:
    _seed(migrated_engine, TWO_CHUNKS)

    def dying() -> Iterator[ChunkEmbedding]:
        yield _two_windows()[0]
        raise RuntimeError("killed mid-load")

    with (
        Session(migrated_engine) as session,
        pytest.raises(RuntimeError, match="mid-load"),
        session.begin(),
    ):
        _ensure(session, dying())
    assert _count(migrated_engine, "norm_embedding") == 0

    with Session(migrated_engine) as session, session.begin():
        _ensure(session, _two_windows())
        own = session.execute(text("SELECT count(*) FROM norm_embedding")).scalar_one()
        assert own == 2
        assert _count(migrated_engine, "norm_embedding") == 0
        assert _count(migrated_engine, "norm_embedding_build") == 0
        with (
            pytest.raises(NormEmbeddingConflict, match="no complete embedding build"),
            Session(migrated_engine) as reader,
        ):
            NormEmbeddingRepository(reader).nearest(
                snapshot_id=SNAPSHOT_ID, chunking_profile=CHUNKING_PROFILE,
                query=_unit_vector(0), limit=1,
            )
    assert _count(migrated_engine, "norm_embedding") == 2
    assert _count(migrated_engine, "norm_embedding_build") == 1


def _near(index: int, weight: float) -> tuple[float, ...]:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[0] = 1.0
    values[index] = weight
    norm = math.sqrt(1.0 + weight * weight)
    return tuple(value / norm for value in values)


def _far(index: int) -> tuple[float, ...]:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[0] = 0.1
    values[index] = 1.0
    norm = math.sqrt(1.01)
    return tuple(value / norm for value in values)


def _seed_snapshot_with_vectors(engine, snapshot_id, content_key, number, count, vector) -> None:
    values = [f"{number}-{index:04d}" for index in range(count)]
    _seed(engine, {"doc": [[value] for value in values]}, snapshot_id=snapshot_id, content_key=content_key, number=number)
    with Session(engine) as session, session.begin():
        _ensure(
            session,
            [_whole("doc", index, value, vector(index), index) for index, value in enumerate(values)],
            snapshot_id,
        )


_FORCE_THE_INDEX = (
    "SET LOCAL enable_seqscan = off",
    "SET LOCAL enable_bitmapscan = off",
    "SET LOCAL enable_sort = off",
)


def test_d124_a_second_snapshot_no_longer_shrinks_nearest(migrated_engine: Engine) -> None:
    """The near snapshot fills the default 40-candidate scan; the far one is filtered out of it."""
    _seed_snapshot_with_vectors(migrated_engine, SNAPSHOT_ID, CONTENT_KEY, 0, 150, lambda i: _near(i + 1, 0.01))
    _seed_snapshot_with_vectors(migrated_engine, OTHER_SNAPSHOT_ID, OTHER_CONTENT_KEY, 1, 30, lambda i: _far(i + 500))
    from auditmanager.norms import embedding_repository as module

    literal = vectors.pgvector_literal(vectors.pack(_unit_vector(0)))
    parameters = {
        "snapshot": str(OTHER_SNAPSHOT_ID),
        "chunking_profile": CHUNKING_PROFILE,
        "embedding_profile": "bge-m3-dense-v1",
        "query": literal,
        "limit": 10,
    }
    with Session(migrated_engine) as session, session.begin():
        for statement in _FORCE_THE_INDEX:
            session.execute(text(statement))
        plan = "\n".join(
            row[0] for row in session.execute(text("EXPLAIN " + str(module._NEAREST)), parameters)
        )
        assert "ix_norm_embedding_hnsw_ip" in plan, plan
        # The defect, reproduced on purpose: the pre-fix query, without the scan settings.
        assert session.execute(module._NEAREST, parameters).all() == []

    with Session(migrated_engine) as session, session.begin():
        for statement in _FORCE_THE_INDEX:
            session.execute(text(statement))
        rows = NormEmbeddingRepository(session).nearest(
            snapshot_id=OTHER_SNAPSHOT_ID, chunking_profile=CHUNKING_PROFILE, query=_unit_vector(0), limit=10
        )
        far_pks = set(
            session.execute(
                text("SELECT norm_chunk_pk FROM norm_chunk WHERE norms_snapshot_id = :snapshot"),
                {"snapshot": str(OTHER_SNAPSHOT_ID)},
            ).scalars()
        )
        settings = session.execute(
            text("SELECT current_setting('hnsw.iterative_scan'), current_setting('hnsw.ef_search')")
        ).one()
    assert len(rows) == 10 and {row.chunk_pk for row in rows} <= far_pks
    assert settings == ("strict_order", str(module.HNSW_EF_SEARCH))

    # And the guard: with the settings reverted, the repository refuses rather than shrinks.
    original = NormEmbeddingRepository.SCAN_SETTINGS
    NormEmbeddingRepository.SCAN_SETTINGS = ()
    try:
        with Session(migrated_engine) as session, session.begin():
            for statement in _FORCE_THE_INDEX:
                session.execute(text(statement))
            with pytest.raises(NormEmbeddingScanShort):
                NormEmbeddingRepository(session).nearest(
                    snapshot_id=OTHER_SNAPSHOT_ID, chunking_profile=CHUNKING_PROFILE,
                    query=_unit_vector(0), limit=10,
                )
    finally:
        NormEmbeddingRepository.SCAN_SETTINGS = original


def test_prepare_build_load_end_to_end_through_the_checkpoint_files(migrated_engine: Engine, tmp_path: Path) -> None:
    documents = {
        f"doc-{index}": [[paragraph(index * 10 + chunk, 30), paragraph(index * 10 + chunk + 5, 60)] for chunk in range(3)]
        for index in range(3)
    }
    documents["doc-long"] = [[paragraph(99, 700)]]
    _seed(migrated_engine, documents)
    directory = tmp_path / "build"
    with Session(migrated_engine) as session:
        plan, created = prepare(session, directory, snapshot_id=SNAPSHOT_ID, chunking_profile=CHUNKING_PROFILE, batch_chunks=4)
        session.rollback()
    assert created and plan.chunk_count == 10 and plan.identity.content_key == CONTENT_KEY
    progress = run_build(
        directory, FakeEncoder(), norms_snapshot_id=str(SNAPSHOT_ID), chunking_profile=CHUNKING_PROFILE,
        report=lambda _line: None,
    )
    assert progress.complete
    expected, _, windows = checkpoint_digest(directory, read_plan(directory))
    assert windows > 10

    with Session(migrated_engine) as session, session.begin():
        result = load(session, directory, snapshot_id=SNAPSHOT_ID, chunking_profile=CHUNKING_PROFILE)
    assert result.build.created and result.build.embedding_set_sha256 == expected == progress.digest
    with Session(migrated_engine) as session, session.begin():
        replay = load(session, directory, snapshot_id=SNAPSHOT_ID, chunking_profile=CHUNKING_PROFILE)
        stored = NormEmbeddingRepository(session).stored_build_digest(SNAPSHOT_ID, CHUNKING_PROFILE)
    assert replay.build.created is False and stored == (expected, 10, windows)
    assert _count(migrated_engine, "norm_embedding") == windows

    # The same chunks embedded directly agree with what the files carried.
    with Session(migrated_engine) as session:
        inputs = list(NormEmbeddingRepository(session).iter_chunk_inputs(SNAPSHOT_ID, CHUNKING_PROFILE))
    assert sum(len(item.windows) for item in embed_batch(FakeEncoder(), inputs)) == windows


def test_downgrade_refuses_to_drop_a_complete_retained_build(
    migrated_database,
    migrated_engine: Engine,
    foundation_command,
) -> None:
    _seed(migrated_engine, TWO_CHUNKS)
    with Session(migrated_engine) as session, session.begin():
        _ensure(session, _two_windows())

    # `0015` refuses its own downgrade while its role backfill is there; this test is about an
    # earlier revision, so that backfill is removed first (conftest.clear_the_role_backfill).
    clear_the_role_backfill(migrated_database.url.render_as_string(hide_password=False))
    result = foundation_command(
        [
            ".venv/bin/python",
            "-m",
            "alembic",
            "--config",
            "db/migrations/alembic.ini",
            "downgrade",
            "0012_norms_corpus",
        ],
        migrated_database.url.render_as_string(hide_password=False),
    )
    assert result.returncode != 0
    assert "downgrade refused" in result.stderr
