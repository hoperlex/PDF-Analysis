"""The pgvector extension and normative embedding projection are exact and rebuildable."""

from __future__ import annotations

import hashlib

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from auditmanager.norms.embedding_repository import (
    EMBEDDING_DIMENSIONS,
    EmbeddingWindow,
    NormEmbeddingConflict,
    NormEmbeddingRepository,
    input_digest,
)
from auditmanager.shared.identity import NormsSnapshotId
from tests.integration.db.conftest import (  # type: ignore[import-not-found]
    clear_the_role_backfill,
)

SNAPSHOT_ID = NormsSnapshotId.parse("ns_" + "0" * 26)
CHUNKING_PROFILE = "characters-v1-12000"
CONTENT_KEY = "2026-07-23..2026-07-23+0d." + "1" * 12


def _unit_vector(index: int) -> tuple[float, ...]:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[index] = 1.0
    return tuple(values)


def _seed_chunks(engine: Engine) -> tuple[int, int]:
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
                    DATE '2026-07-23', DATE '2026-07-23', 0, 1, 0, 'markdown-v1'
                )
                """
            ),
            {
                "snapshot": str(SNAPSHOT_ID),
                "content_key": CONTENT_KEY,
                "digest": "1" * 64,
            },
        )
        document_pk = int(
            connection.execute(
                text(
                    """
                    INSERT INTO norm_document (
                        norm_document_id, norms_snapshot_id, source_document_ref, slug,
                        title, doc_type, source_attribution, pdf_page_count, block_count,
                        page_heading_count, recognised_characters, paragraph_count
                    ) VALUES (
                        :identity, :snapshot, 'source-1', 'slug', 'title.pdf', 'СП',
                        'unattributed', 1, 1, 0, 20, 2
                    ) RETURNING norm_document_pk
                    """
                ),
                {"identity": "ndoc_" + "1" * 26, "snapshot": str(SNAPSHOT_ID)},
            ).scalar_one()
        )
        for ordinal, identity, value in (
            (0, "npar_" + "2" * 26, "0123456789"),
            (1, "npar_" + "3" * 26, "abcdefghij"),
        ):
            connection.execute(
                text(
                    """
                    INSERT INTO norm_paragraph (
                        norm_paragraph_id, norms_snapshot_id, norm_document_pk, ordinal,
                        page_label, block_ref, char_offset, char_length, kind, text
                    ) VALUES (
                        :identity, :snapshot, :document, :ordinal,
                        1, :block, :offset, 10, 'body', :text
                    )
                    """
                ),
                {
                    "identity": identity,
                    "snapshot": str(SNAPSHOT_ID),
                    "document": document_pk,
                    "ordinal": ordinal,
                    "block": f"block-{ordinal}",
                    "offset": ordinal * 10,
                    "text": value,
                },
            )
        connection.execute(
            text(
                """
                INSERT INTO norm_chunk_build (
                    norms_snapshot_id, chunking_profile, target_characters, chunk_count
                ) VALUES (:snapshot, :profile, 10, 2)
                """
            ),
            {"snapshot": str(SNAPSHOT_ID), "profile": CHUNKING_PROFILE},
        )
        chunk_pks: list[int] = []
        for ordinal, value in ((0, "0123456789"), (1, "abcdefghij")):
            chunk_pks.append(
                int(
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
                                :ordinal, 1, 1, :offset, 10,
                                :ordinal, :ordinal, 1, '{}', false,
                                :text, :digest
                            ) RETURNING norm_chunk_pk
                            """
                        ),
                        {
                            "snapshot": str(SNAPSHOT_ID),
                            "document": document_pk,
                            "profile": CHUNKING_PROFILE,
                            "ordinal": ordinal,
                            "offset": ordinal * 10,
                            "text": value,
                            "digest": hashlib.sha256(value.encode()).hexdigest(),
                        },
                    ).scalar_one()
                )
            )
    return chunk_pks[0], chunk_pks[1]


def _windows(chunk_pks: tuple[int, int]) -> tuple[EmbeddingWindow, ...]:
    return tuple(
        EmbeddingWindow(
            chunk_pk=chunk_pk,
            window_ordinal=0,
            token_count=5,
            char_offset=0,
            char_length=10,
            paragraph_ordinal_first=ordinal,
            paragraph_ordinal_last=ordinal,
            input_sha256=input_digest(value),
            embedding=_unit_vector(ordinal),
        )
        for ordinal, (chunk_pk, value) in enumerate(
            zip(chunk_pks, ("0123456789", "abcdefghij"), strict=True)
        )
    )


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


def test_complete_build_is_idempotent_and_inner_product_ordered(
    migrated_engine: Engine,
) -> None:
    chunk_pks = _seed_chunks(migrated_engine)
    windows = _windows(chunk_pks)

    with Session(migrated_engine) as session, session.begin():
        created = NormEmbeddingRepository(session).ensure_build(
            snapshot_id=SNAPSHOT_ID,
            chunking_profile=CHUNKING_PROFILE,
            windows=windows,
        )
    assert created.created is True
    assert created.chunk_count == 2
    assert created.window_count == 2

    with Session(migrated_engine) as session, session.begin():
        repository = NormEmbeddingRepository(session)
        replay = repository.ensure_build(
            snapshot_id=SNAPSHOT_ID,
            chunking_profile=CHUNKING_PROFILE,
            windows=windows,
        )
        nearest = repository.nearest(
            snapshot_id=SNAPSHOT_ID,
            chunking_profile=CHUNKING_PROFILE,
            query=_unit_vector(0),
            limit=2,
        )

    assert replay.created is False
    assert [row.chunk_pk for row in nearest] == [chunk_pks[0], chunk_pks[1]]
    assert nearest[0].inner_product == pytest.approx(1.0)
    assert nearest[1].inner_product == pytest.approx(0.0)


def test_invalid_or_conflicting_build_writes_nothing(migrated_engine: Engine) -> None:
    chunk_pks = _seed_chunks(migrated_engine)
    windows = _windows(chunk_pks)

    invalid = windows[:-1] + (
        EmbeddingWindow(
            chunk_pk=windows[-1].chunk_pk,
            window_ordinal=windows[-1].window_ordinal,
            token_count=windows[-1].token_count,
            char_offset=windows[-1].char_offset,
            char_length=windows[-1].char_length,
            paragraph_ordinal_first=windows[-1].paragraph_ordinal_first,
            paragraph_ordinal_last=windows[-1].paragraph_ordinal_last,
            input_sha256=windows[-1].input_sha256,
            embedding=tuple(0.0 for _ in range(EMBEDDING_DIMENSIONS)),
        ),
    )
    with Session(migrated_engine) as session, pytest.raises(NormEmbeddingConflict):
        NormEmbeddingRepository(session).ensure_build(
            snapshot_id=SNAPSHOT_ID,
            chunking_profile=CHUNKING_PROFILE,
            windows=invalid,
        )
    with migrated_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM norm_embedding")).scalar_one() == 0

    with Session(migrated_engine) as session, session.begin():
        NormEmbeddingRepository(session).ensure_build(
            snapshot_id=SNAPSHOT_ID,
            chunking_profile=CHUNKING_PROFILE,
            windows=windows,
        )
    conflicting = windows[:-1] + (
        EmbeddingWindow(
            chunk_pk=windows[-1].chunk_pk,
            window_ordinal=0,
            token_count=5,
            char_offset=0,
            char_length=9,
            paragraph_ordinal_first=1,
            paragraph_ordinal_last=1,
            input_sha256=input_digest("abcdefghi"),
            embedding=windows[-1].embedding,
        ),
    )
    with Session(migrated_engine) as session, pytest.raises(NormEmbeddingConflict):
        NormEmbeddingRepository(session).ensure_build(
            snapshot_id=SNAPSHOT_ID,
            chunking_profile=CHUNKING_PROFILE,
            windows=conflicting,
        )


def test_downgrade_refuses_to_drop_a_complete_retained_build(
    migrated_database,
    migrated_engine: Engine,
    foundation_command,
) -> None:
    chunk_pks = _seed_chunks(migrated_engine)
    with Session(migrated_engine) as session, session.begin():
        NormEmbeddingRepository(session).ensure_build(
            snapshot_id=SNAPSHOT_ID,
            chunking_profile=CHUNKING_PROFILE,
            windows=_windows(chunk_pks),
        )

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
