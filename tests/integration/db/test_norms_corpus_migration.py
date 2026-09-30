"""The durable norms projection is identity-safe, canonical and idempotent."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from auditmanager.norms.loader import load_corpus

SNAPSHOT_ID = "ns_" + "0" * 26
CONTENT_KEY = "2026-07-23..2026-07-23+0d." + "1" * 12
NORM_DOCUMENT_ID = "ndoc_" + "1" * 26
NORM_PARAGRAPH_ID = "npar_" + "2" * 26
CONTENT_DIGEST = "1" * 64

MARKDOWN = """# Document: СП_000_13330_2026.pdf

Path: normative/СП_000_13330_2026.pdf

Generated: 2026-08-25 09:47:54 UTC

## Page 1

### BLOCK #1 [TEXT]: blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa

> **Created:** 2026-08-25 09:22:54 UTC
> **Crop:** [Crop](https://example.invalid/crop)

##### 1. ОБЩИЕ ПОЛОЖЕНИЯ

1.1. Настоящий свод правил устанавливает проверяемые требования к проектированию.

Дата сохранения: 23.07.2026
"""


def _write_corpus(root: Path) -> Path:
    slug = "СП_000_13330_2026"
    document = root / slug
    document.mkdir(parents=True)
    (document / "results.md").write_text(MARKDOWN, encoding="utf-8")
    (document / "blocks.json").write_text(
        json.dumps({"document_id": "doc_source_0001"}), encoding="utf-8"
    )
    (root / "MANIFEST.json").write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "slug": slug,
                        "document_id": "doc_source_0001",
                        "document_name": "СП_000_13330_2026.pdf",
                        "doc_type": "СП",
                        "pdf_pages": 1,
                        "blocks_count": 1,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return root


def _insert_snapshot(connection) -> None:
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
        {"snapshot": SNAPSHOT_ID, "content_key": CONTENT_KEY, "digest": CONTENT_DIGEST},
    )


def test_the_migration_creates_the_canonical_and_rebuildable_topology(
    migrated_engine: Engine,
) -> None:
    with migrated_engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' AND tablename LIKE 'norm%'"
                )
            )
        }
        audit_fk = connection.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'fk_audit_run_norms_snapshot'"
            )
        ).scalar_one()
        chunk_build_fk = connection.execute(
            text(
                "SELECT condeferrable, condeferred, confdeltype FROM pg_constraint "
                "WHERE conname = 'fk_norm_chunk_build'"
            )
        ).one()

    assert tables == {
        "norm_chunk",
        "norm_chunk_build",
        "norm_document",
        "norm_paragraph",
        "norms_snapshot",
    }
    assert "FOREIGN KEY (norms_snapshot_id)" in audit_fk
    assert "REFERENCES norms_snapshot(norms_snapshot_id)" in audit_fk
    assert chunk_build_fk == (True, True, "c")


def test_a_content_key_cannot_be_used_as_the_opaque_snapshot_identity(
    migrated_engine: Engine,
) -> None:
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(IntegrityError):
            connection.execute(
                text(
                    """
                    INSERT INTO norms_snapshot (
                        norms_snapshot_id, content_key, base_content_key, content_digest,
                        undated_documents, document_count, repair_count, segmentation_profile
                    ) VALUES (:content_key, :content_key, :content_key, :digest, 1, 1, 0, 'markdown-v1')
                    """
                ),
                {"content_key": CONTENT_KEY, "digest": CONTENT_DIGEST},
            )
        transaction.rollback()


def test_source_anchors_cannot_substitute_for_public_child_ids(
    migrated_engine: Engine,
) -> None:
    with migrated_engine.begin() as connection:
        _insert_snapshot(connection)

    document_sql = text(
        """
        INSERT INTO norm_document (
            norm_document_id, norms_snapshot_id, source_document_ref, slug,
            title, doc_type, source_attribution, pdf_page_count, block_count,
            page_heading_count, recognised_characters, paragraph_count
        ) VALUES (
            :identity, :snapshot, 'source-1', 'slug', 'title.pdf', 'СП',
            'unattributed', 1, 1, 0, 10, 1
        ) RETURNING norm_document_pk
        """
    )
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(IntegrityError):
            connection.execute(
                document_sql,
                {"identity": "source-1", "snapshot": SNAPSHOT_ID},
            )
        transaction.rollback()

    with migrated_engine.begin() as connection:
        document_pk = connection.execute(
            document_sql,
            {"identity": NORM_DOCUMENT_ID, "snapshot": SNAPSHOT_ID},
        ).scalar_one()

    paragraph_sql = text(
        """
        INSERT INTO norm_paragraph (
            norm_paragraph_id, norms_snapshot_id, norm_document_pk, ordinal,
            page_label, block_ref, char_offset, char_length, kind, text
        ) VALUES (
            :identity, :snapshot, :document, :ordinal,
            1, 'block-1', 0, 10, 'body', '0123456789'
        )
        """
    )
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(IntegrityError):
            connection.execute(
                paragraph_sql,
                {
                    "identity": "block-1",
                    "snapshot": SNAPSHOT_ID,
                    "document": document_pk,
                    "ordinal": 0,
                },
            )
        transaction.rollback()

    with migrated_engine.begin() as connection:
        connection.execute(
            paragraph_sql,
            {
                "identity": NORM_PARAGRAPH_ID,
                "snapshot": SNAPSHOT_ID,
                "document": document_pk,
                "ordinal": 0,
            },
        )

    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(IntegrityError):
            connection.execute(
                paragraph_sql,
                {
                    "identity": NORM_PARAGRAPH_ID,
                    "snapshot": SNAPSHOT_ID,
                    "document": document_pk,
                    "ordinal": 1,
                },
            )
        transaction.rollback()


def test_canonical_rows_are_immutable_and_a_chunk_build_is_replaceable(
    migrated_engine: Engine,
) -> None:
    with migrated_engine.begin() as connection:
        _insert_snapshot(connection)
        document_pk = connection.execute(
            text(
                """
                INSERT INTO norm_document (
                    norm_document_id, norms_snapshot_id, source_document_ref, slug,
                    title, doc_type,
                    source_attribution, pdf_page_count, block_count, page_heading_count,
                    recognised_characters, paragraph_count
                ) VALUES (
                    :norm_document, :snapshot, 'source-1', 'slug', 'title.pdf', 'СП',
                    'unattributed', 1, 1, 1, 10, 1
                ) RETURNING norm_document_pk
                """
            ),
            {
                "norm_document": NORM_DOCUMENT_ID,
                "snapshot": SNAPSHOT_ID,
            },
        ).scalar_one()
        connection.execute(
            text(
                """
                INSERT INTO norm_paragraph (
                    norm_paragraph_id, norms_snapshot_id, norm_document_pk, ordinal,
                    page_label, block_ref,
                    char_offset, char_length, kind, text
                ) VALUES (
                    :norm_paragraph, :snapshot, :document, 0, 1, 'block-1',
                    0, 10, 'body', '0123456789'
                )
                """
            ),
            {
                "norm_paragraph": NORM_PARAGRAPH_ID,
                "snapshot": SNAPSHOT_ID,
                "document": document_pk,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO norm_chunk_build (
                    norms_snapshot_id, chunking_profile, target_characters, chunk_count
                ) VALUES (:snapshot, 'characters-v1:1200', 1200, 1)
                """
            ),
            {"snapshot": SNAPSHOT_ID},
        )
        connection.execute(
            text(
                """
                INSERT INTO norm_chunk (
                    norms_snapshot_id, norm_document_pk, chunking_profile, ordinal,
                    page_first, page_last, char_offset, char_length,
                    paragraph_ordinal_first, paragraph_ordinal_last, paragraph_count,
                    clause_numbers, contains_clause, text, content_sha256
                ) VALUES (
                    :snapshot, :document, 'characters-v1:1200', 0,
                    1, 1, 0, 10, 0, 0, 1, '{}', false, '0123456789', :digest
                )
                """
            ),
            {"snapshot": SNAPSHOT_ID, "document": document_pk, "digest": "2" * 64},
        )

    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(DBAPIError, match="immutable once written"):
            connection.execute(text("UPDATE norm_paragraph SET text = 'changed'"))
        transaction.rollback()

    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(DBAPIError, match="replace-only"):
            connection.execute(text("UPDATE norm_chunk SET text = 'changed'"))
        transaction.rollback()

    with migrated_engine.begin() as connection:
        connection.execute(
            text(
                "DELETE FROM norm_chunk_build "
                "WHERE norms_snapshot_id = :snapshot AND chunking_profile = 'characters-v1:1200'"
            ),
            {"snapshot": SNAPSHOT_ID},
        )
        assert connection.execute(text("SELECT count(*) FROM norm_chunk")).scalar_one() == 0


def test_the_loader_is_an_exact_repeat_idempotent_command(
    migrated_engine: Engine, tmp_path: Path
) -> None:
    corpus = _write_corpus(tmp_path / "corpus")

    with Session(migrated_engine) as session:
        with session.begin():
            first = load_corpus(session, corpus)
        with session.begin():
            repeated = load_corpus(session, corpus)

    assert first.created is True
    assert repeated.created is False
    assert repeated.norms_snapshot_id == first.norms_snapshot_id
    assert first.content_key != str(first.norms_snapshot_id)
    assert first.counts.documents == 1
    assert first.counts.paragraphs == 2
    assert first.counts.chunks == 1
    assert repeated.counts == first.counts

    with migrated_engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT s.norms_snapshot_id, s.content_key,
                       min(d.norm_document_id) AS norm_document_id,
                       count(DISTINCT d.norm_document_pk) AS documents,
                       array_agg(DISTINCT p.norm_paragraph_id) AS norm_paragraph_ids,
                       count(DISTINCT p.norm_paragraph_pk) AS paragraphs,
                       count(DISTINCT c.norm_chunk_pk) AS chunks
                FROM norms_snapshot s
                JOIN norm_document d USING (norms_snapshot_id)
                JOIN norm_paragraph p USING (norms_snapshot_id, norm_document_pk)
                JOIN norm_chunk c USING (norms_snapshot_id, norm_document_pk)
                GROUP BY s.norms_snapshot_id, s.content_key
                """
            )
        ).one()
    assert row[:2] == (str(first.norms_snapshot_id), first.content_key)
    assert row.norm_document_id.startswith("ndoc_")
    assert len(row.norm_document_id) == 31
    assert len(row.norm_paragraph_ids) == 2
    assert all(
        value.startswith("npar_") and len(value) == 31
        for value in row.norm_paragraph_ids
    )
    assert row.documents == 1
    assert row.paragraphs == 2
    assert row.chunks == 1


def test_a_validated_repair_is_the_text_persisted_under_a_new_content_key(
    migrated_engine: Engine, tmp_path: Path
) -> None:
    import hashlib

    from auditmanager.norms import PageRepair, RepairOutcome, ledger_of
    from auditmanager.norms.corpus_source import snapshot_of
    from auditmanager.norms.segmentation import blocks

    corpus = _write_corpus(tmp_path / "repaired-corpus")
    base = snapshot_of(corpus)
    raw = blocks(MARKDOWN)[0]
    replacement = (
        "##### 2. ИСПРАВЛЕННЫЙ РАЗДЕЛ\n\n"
        "2.1. Исправленный нормативный текст используется в канонической проекции."
    )
    ledger = ledger_of(
        base.content_key,
        "2026-09-30T00:00:00+00:00",
        [
            PageRepair(
                document_slug="СП_000_13330_2026",
                block_id=raw.block_id,
                page_label=raw.page_label,
                original_sha256=hashlib.sha256(raw.text.encode("utf-8")).hexdigest(),
                original_characters=len(raw.text),
                crop_sha256="3" * 64,
                outcome=RepairOutcome.REPAIRED,
                replacement=replacement,
                attempts=(),
            )
        ],
    )

    with Session(migrated_engine) as session:
        with session.begin():
            result = load_corpus(session, corpus, repair_ledger=ledger)

    assert "+1r." in result.content_key
    with migrated_engine.connect() as connection:
        snapshot = connection.execute(
            text(
                "SELECT base_content_key, content_key, repair_count "
                "FROM norms_snapshot WHERE norms_snapshot_id = :snapshot"
            ),
            {"snapshot": str(result.norms_snapshot_id)},
        ).one()
        persisted = connection.execute(
            text(
                "SELECT string_agg(text, E'\\n\\n' ORDER BY ordinal) "
                "FROM norm_paragraph WHERE norms_snapshot_id = :snapshot"
            ),
            {"snapshot": str(result.norms_snapshot_id)},
        ).scalar_one()
    assert snapshot == (base.content_key, result.content_key, 1)
    assert persisted == replacement
