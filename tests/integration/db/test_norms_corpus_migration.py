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
        # `0018_norm_custody` (W54): custody and the paid repair journal.
        "norm_custody_admission",
        "norm_custody_binding",
        "norm_document",
        "norm_embedding",
        "norm_embedding_build",
        "norm_embedding_profile",
        "norm_paragraph",
        "norm_repair_call",
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


# --- `F-4`: the repaired key and `ck_norms_snapshot_raw_key` (`W54-REPAIR-01`) -----------------


def _snapshot_row(connection, *, content_key: str, repair_count: int, unreliable_count: int) -> None:
    from auditmanager.shared.identity import NormsSnapshotId

    connection.execute(
        text(
            """
            INSERT INTO norms_snapshot (
                norms_snapshot_id, content_key, base_content_key, content_digest,
                drawn_from, drawn_to, undated_documents, document_count,
                repair_count, unreliable_count, segmentation_profile
            ) VALUES (
                :snapshot, :content_key, :base, :digest,
                DATE '2026-07-23', DATE '2026-07-23', 0, 1, :repairs, :unreliable, 'markdown-v1'
            )
            """
        ),
        {
            "snapshot": str(NormsSnapshotId.new()),
            "content_key": content_key,
            "base": CONTENT_KEY,
            "digest": "2" * 64,
            "repairs": repair_count,
            "unreliable": unreliable_count,
        },
    )


def _key_of(ledger_outcomes: list[str]) -> str:
    """The key ``repaired_snapshot`` mints for a ledger of these outcomes over a fixed base."""
    from auditmanager.norms import (
        CorpusSnapshot,
        PageRepair,
        RepairOutcome,
        ledger_of,
        repaired_snapshot,
    )

    base = CorpusSnapshot(
        snapshot_id=CONTENT_KEY, drawn_from="2026-07-23", drawn_to="2026-07-23",
        undated_documents=0, document_count=1, content_digest=CONTENT_DIGEST,
    )
    repairs = []
    for index, outcome in enumerate(ledger_outcomes):
        repaired = outcome == "repaired"
        repairs.append(
            PageRepair(
                document_slug="СП_000_13330_2026", block_id=f"blk_{index:032x}", page_label=1,
                original_sha256="0" * 64, original_characters=1, crop_sha256="3" * 64,
                outcome=RepairOutcome(outcome),
                replacement="Исправленный текст страницы." if repaired else None, attempts=(),
            )
        )
    return repaired_snapshot(base, ledger_of(CONTENT_KEY, "2026-10-12T00:00:00+00:00", repairs)).snapshot_id


@pytest.mark.parametrize(
    ("outcomes", "repairs", "unreliable"),
    [
        (["repaired"], 1, 0),
        (["repaired", "still_degenerate"], 1, 1),
        (["call_failed", "not_attempted"], 0, 2),
    ],
)
def test_every_repaired_key_form_is_accepted_with_its_counts(
    migrated_engine: Engine, outcomes: list[str], repairs: int, unreliable: int
) -> None:
    key = _key_of(outcomes)
    assert key != CONTENT_KEY
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        _snapshot_row(connection, content_key=key, repair_count=repairs, unreliable_count=unreliable)
        transaction.rollback()


@pytest.mark.parametrize(
    ("content_key", "repairs", "unreliable"),
    [
        # Unreliable blocks under the base key: the W39 "applied nothing returns the base" rule,
        # which `F-4` inverts, is refused by the database too.
        (CONTENT_KEY, 0, 1),
        # A moved key with nothing repaired and nothing unreliable is a record of effort.
        ("2026-07-23..2026-07-23+0d+0r+0u." + "9" * 12, 0, 0),
    ],
)
def test_the_raw_key_check_refuses_a_key_that_disagrees_with_its_counts(
    migrated_engine: Engine, content_key: str, repairs: int, unreliable: int
) -> None:
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(IntegrityError) as refused:
            _snapshot_row(
                connection, content_key=content_key, repair_count=repairs,
                unreliable_count=unreliable,
            )
        transaction.rollback()
    assert "ck_norms_snapshot_raw_key" in str(refused.value)


# --- `W54-SNAPSHOT-01`: reliability-aware loads, `D-126`, and import with ids ------------------

THREE_BLOCK_SLUG = "СП_003_13330_2026"
THREE_BLOCK_IDS = tuple(f"blk_{letter * 32}" for letter in "def")
THREE_BLOCK_MARKDOWN = f"""# Document: {THREE_BLOCK_SLUG}.pdf

Path: normative/{THREE_BLOCK_SLUG}.pdf

Generated: 2026-08-25 09:47:54 UTC

## Page 1

### BLOCK #1 [TEXT]: {THREE_BLOCK_IDS[0]}

> **Created:** 2026-08-25 09:22:54 UTC
> **Crop:** [Crop](https://example.invalid/crop/1)

1.1. Первый пункт устанавливает требования к проектированию зданий и сооружений.

1.2. Второй пункт уточняет порядок приёмки выполненных строительных работ.

Дата сохранения: 23.07.2026

## Page 2

### BLOCK #2 [TEXT]: {THREE_BLOCK_IDS[1]}

> **Created:** 2026-08-25 09:22:54 UTC
> **Crop:** [Crop](https://example.invalid/crop/2)

Модель распознавания рассуждает о таблице вместо того чтобы её переписать.

Вторая строка того же нечитаемого блока, которую нельзя показывать эксперту.

## Page 3

### BLOCK #3 [TEXT]: {THREE_BLOCK_IDS[2]}

> **Created:** 2026-08-25 09:22:54 UTC
> **Crop:** [Crop](https://example.invalid/crop/3)

3.1. Третий пункт описывает испытания конструкций при приёмке.

3.2. Четвёртый пункт завершает раздел о контроле качества работ.
"""


def _write_three_block_corpus(root: Path) -> Path:
    document = root / THREE_BLOCK_SLUG
    document.mkdir(parents=True)
    (document / "results.md").write_text(THREE_BLOCK_MARKDOWN, encoding="utf-8")
    (document / "blocks.json").write_text(
        json.dumps({"document_id": "doc_source_0003"}), encoding="utf-8"
    )
    (root / "MANIFEST.json").write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "slug": THREE_BLOCK_SLUG,
                        "document_id": "doc_source_0003",
                        "document_name": f"{THREE_BLOCK_SLUG}.pdf",
                        "doc_type": "СП",
                        "pdf_pages": 3,
                        "blocks_count": 3,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return root


def _three_block_ledger(corpus: Path, *, repaired: bool = True, unreliable: bool = True):
    """Block 1 repaired, block 2 left unreliable — the shape operator step (3) loads."""
    import hashlib

    from auditmanager.norms import PageRepair, RepairOutcome, ledger_of
    from auditmanager.norms.corpus_source import snapshot_of
    from auditmanager.norms.segmentation import blocks

    parsed = blocks(THREE_BLOCK_MARKDOWN)
    entries = []
    for index, outcome, replacement in (
        (0, RepairOutcome.REPAIRED, "1.1. Исправленный первый пункт, прочитанный повторно."),
        (1, RepairOutcome.STILL_DEGENERATE, None),
    ):
        if (index == 0 and not repaired) or (index == 1 and not unreliable):
            continue
        block = parsed[index]
        entries.append(
            PageRepair(
                document_slug=THREE_BLOCK_SLUG,
                block_id=block.block_id,
                page_label=block.page_label,
                original_sha256=hashlib.sha256(block.text.encode("utf-8")).hexdigest(),
                original_characters=len(block.text),
                crop_sha256="3" * 64,
                outcome=outcome,
                replacement=replacement,
                attempts=(),
            )
        )
    return ledger_of(snapshot_of(corpus).content_key, "2026-10-12T00:00:00+00:00", entries)


def _chunk_spans(connection, snapshot: str, profile: str) -> list[tuple[int, int, int]]:
    return [
        tuple(row)
        for row in connection.execute(
            text(
                "SELECT ordinal, paragraph_ordinal_first, paragraph_ordinal_last FROM norm_chunk "
                "WHERE norms_snapshot_id = :snapshot AND chunking_profile = :profile "
                "ORDER BY norm_document_pk, ordinal"
            ),
            {"snapshot": snapshot, "profile": profile},
        )
    ]


_COVERAGE = text(
    """
    -- Every reliable paragraph covered exactly once; no unreliable paragraph covered.
    SELECT p.ordinal, p.text_reliability, count(c.norm_chunk_pk) AS covering
    FROM norm_paragraph p
    LEFT JOIN norm_chunk c
      ON c.norms_snapshot_id = p.norms_snapshot_id
     AND c.norm_document_pk = p.norm_document_pk
     AND c.chunking_profile = :profile
     AND p.ordinal BETWEEN c.paragraph_ordinal_first AND c.paragraph_ordinal_last
    WHERE p.norms_snapshot_id = :snapshot
    GROUP BY p.norm_paragraph_pk, p.ordinal, p.text_reliability
    ORDER BY p.ordinal
    """
)


def test_the_repaired_snapshot_loads_with_its_unreliable_count_and_marks(
    migrated_engine: Engine, tmp_path: Path
) -> None:
    """REPAIR's hand-back: before this lane the load broke `ck_norms_snapshot_raw_key`."""
    corpus = _write_three_block_corpus(tmp_path / "corpus")
    ledger = _three_block_ledger(corpus)

    with Session(migrated_engine) as session:
        with session.begin():
            result = load_corpus(session, corpus, repair_ledger=ledger)

    assert "+1r+1u." in result.content_key
    assert result.chunking_profile == "characters-v2:1200"
    assert result.unreliable_count == 1
    with migrated_engine.connect() as connection:
        snapshot = connection.execute(
            text(
                "SELECT repair_count, unreliable_count, base_content_key <> content_key "
                "FROM norms_snapshot WHERE norms_snapshot_id = :snapshot"
            ),
            {"snapshot": str(result.norms_snapshot_id)},
        ).one()
        marks = connection.execute(
            text(
                "SELECT block_ref, text_reliability FROM norm_paragraph "
                "WHERE norms_snapshot_id = :snapshot ORDER BY ordinal"
            ),
            {"snapshot": str(result.norms_snapshot_id)},
        ).all()
        coverage = connection.execute(
            _COVERAGE,
            {"snapshot": str(result.norms_snapshot_id), "profile": result.chunking_profile},
        ).all()
    assert tuple(snapshot) == (1, 1, True)
    assert [tuple(row) for row in marks] == [
        (THREE_BLOCK_IDS[0], "reliable"),
        (THREE_BLOCK_IDS[1], "unreliable"),
        (THREE_BLOCK_IDS[1], "unreliable"),
        (THREE_BLOCK_IDS[2], "reliable"),
        (THREE_BLOCK_IDS[2], "reliable"),
    ]
    assert [(row.text_reliability, row.covering) for row in coverage] == [
        ("reliable", 1),
        ("unreliable", 0),
        ("unreliable", 0),
        ("reliable", 1),
        ("reliable", 1),
    ]


def test_a_characters_v1_load_over_unreliable_text_is_refused_and_leaves_nothing(
    migrated_engine: Engine, tmp_path: Path
) -> None:
    from auditmanager.norms.chunking import ChunkingRefused

    corpus = _write_three_block_corpus(tmp_path / "corpus")
    ledger = _three_block_ledger(corpus)
    with Session(migrated_engine) as session:
        with session.begin():
            with pytest.raises(ChunkingRefused, match="1 unreliable block"):
                load_corpus(
                    session, corpus, repair_ledger=ledger, chunking_version="characters-v1"
                )
    with migrated_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM norms_snapshot")).scalar_one() == 0


def test_the_database_refuses_a_characters_v1_build_by_the_stored_count(
    migrated_engine: Engine, tmp_path: Path
) -> None:
    """A rebuild that bypasses the projection is refused on ``unreliable_count`` itself."""
    from auditmanager.norms.chunking import ChunkingRefused
    from auditmanager.norms.repository import NormsRepository

    corpus = _write_three_block_corpus(tmp_path / "corpus")
    with Session(migrated_engine) as session:
        with session.begin():
            result = load_corpus(session, corpus, repair_ledger=_three_block_ledger(corpus))
        with session.begin():
            repository = NormsRepository(session)
            with pytest.raises(ChunkingRefused, match="1 unreliable block"):
                repository.build_chunks_from_stored(
                    result.norms_snapshot_id, result.content_key, "characters-v1:1200"
                )
            with pytest.raises(ChunkingRefused):
                repository.finish_chunk_build(
                    result.norms_snapshot_id, "characters-v1:600", 600, 0
                )


def test_a_replay_naming_another_profile_builds_it_from_the_stored_paragraphs(
    migrated_engine: Engine, tmp_path: Path
) -> None:
    corpus = _write_three_block_corpus(tmp_path / "corpus")
    with Session(migrated_engine) as session:
        with session.begin():
            first = load_corpus(session, corpus, target_characters=150)
        with session.begin():
            second = load_corpus(
                session, corpus, target_characters=150, chunking_version="characters-v1"
            )
        with session.begin():
            again = load_corpus(session, corpus, target_characters=150)

    assert first.created and not second.created and not again.created
    assert {first.norms_snapshot_id, second.norms_snapshot_id, again.norms_snapshot_id} == {
        first.norms_snapshot_id
    }
    assert first.row_digest == second.row_digest == again.row_digest
    with migrated_engine.connect() as connection:
        v1 = _chunk_spans(connection, str(first.norms_snapshot_id), "characters-v1:150")
        v2 = _chunk_spans(connection, str(first.norms_snapshot_id), "characters-v2:150")
        texts = connection.execute(
            text(
                "SELECT chunking_profile, array_agg(text ORDER BY ordinal) FROM norm_chunk "
                "GROUP BY chunking_profile ORDER BY chunking_profile"
            )
        ).all()
    # Nothing is unreliable here, so the two profiles agree chunk for chunk.
    assert v1 == v2 and len(v1) > 1
    assert texts[0][1] == texts[1][1]
    assert second.counts == again.counts


def test_raising_the_segmentation_profile_loads_a_second_snapshot_beside_the_first(
    migrated_engine: Engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`D-126`: before this lane the second load raised `NormsProjectionConflict`."""
    from auditmanager.norms import segmentation

    corpus = _write_three_block_corpus(tmp_path / "corpus")
    with Session(migrated_engine) as session:
        with session.begin():
            first = load_corpus(session, corpus)
        monkeypatch.setattr(segmentation, "SEGMENTATION_PROFILE_VERSION", "markdown-v2")
        with session.begin():
            second = load_corpus(session, corpus)
        with session.begin():
            replay = load_corpus(session, corpus)

    assert second.created and not replay.created
    assert second.norms_snapshot_id != first.norms_snapshot_id
    assert replay.norms_snapshot_id == second.norms_snapshot_id
    assert second.content_key == f"{first.content_key}+seg-markdown-v2"
    with migrated_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT content_key, base_content_key, segmentation_profile FROM norms_snapshot "
                "ORDER BY segmentation_profile"
            )
        ).all()
    assert [tuple(row) for row in rows] == [
        (first.content_key, first.content_key, "markdown-v1"),
        (second.content_key, second.content_key, "markdown-v2"),
    ]


def test_the_row_digest_read_back_equals_the_digest_of_the_rows_read_back(
    migrated_engine: Engine, tmp_path: Path
) -> None:
    from auditmanager.norms import row_digest
    from auditmanager.norms.repository import NormsRepository

    corpus = _write_three_block_corpus(tmp_path / "corpus")
    with Session(migrated_engine) as session:
        with session.begin():
            result = load_corpus(session, corpus, repair_ledger=_three_block_ledger(corpus))
            rows = NormsRepository(session).read_snapshot_rows(result.norms_snapshot_id)
    assert row_digest(rows) == result.row_digest
    assert rows.snapshot.unreliable_count == 1
    assert [p.text_reliability for p in rows.paragraphs].count("unreliable") == 2
    assert all(p.norm_paragraph_id.startswith("npar_") for p in rows.paragraphs)


def _exported(engine: Engine, corpus: Path, **load):
    from auditmanager.norms.repository import NormsRepository

    with Session(engine) as session:
        with session.begin():
            result = load_corpus(session, corpus, **load)
            rows = NormsRepository(session).read_snapshot_rows(result.norms_snapshot_id)
    return result, rows


def _chunk_rows(engine: Engine) -> list[tuple]:
    with engine.connect() as connection:
        return [
            tuple(row)
            for row in connection.execute(
                text(
                    """
                    SELECT d.norm_document_id, c.chunking_profile, c.ordinal, c.page_first,
                           c.page_last, c.char_offset, c.char_length,
                           c.paragraph_ordinal_first, c.paragraph_ordinal_last,
                           c.paragraph_count, c.clause_numbers, c.contains_clause, c.text,
                           c.content_sha256
                    FROM norm_chunk c JOIN norm_document d USING (norms_snapshot_id, norm_document_pk)
                    ORDER BY d.norm_document_id, c.chunking_profile, c.ordinal
                    """
                )
            )
        ]


def _table_counts(engine: Engine) -> tuple[int, ...]:
    with engine.connect() as connection:
        return tuple(
            connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in ("norms_snapshot", "norm_document", "norm_paragraph", "norm_chunk", "norm_chunk_build")
        )


def test_an_import_carries_every_id_and_rebuilds_identical_chunks_in_another_database(
    migrated_database_factory, tmp_path: Path
) -> None:
    from auditmanager.norms.loader import import_snapshot
    from auditmanager.shared.db.engine import create_database_engine

    origin = create_database_engine(migrated_database_factory())
    target = create_database_engine(migrated_database_factory())
    try:
        corpus = _write_three_block_corpus(tmp_path / "corpus")
        loaded, rows = _exported(origin, corpus, repair_ledger=_three_block_ledger(corpus))

        with Session(target) as session:
            with session.begin():
                imported = import_snapshot(
                    session, rows, chunking_profiles=["characters-v2:1200"],
                    expected_row_digest=loaded.row_digest,
                )
        assert imported.created is True
        assert imported.norms_snapshot_id == loaded.norms_snapshot_id
        assert imported.row_digest == loaded.row_digest
        assert dict(imported.counts)["characters-v2:1200"] == loaded.counts
        assert _chunk_rows(target) == _chunk_rows(origin)

        before = _table_counts(target)
        with Session(target) as session:
            with session.begin():
                replay = import_snapshot(
                    session, rows, chunking_profiles=["characters-v2:1200"],
                    expected_row_digest=loaded.row_digest,
                )
        assert replay.created is False
        assert replay.row_digest == loaded.row_digest
        assert _table_counts(target) == before
    finally:
        origin.dispose()
        target.dispose()


def test_import_conflicts_are_refused_and_write_nothing(
    migrated_database_factory, tmp_path: Path
) -> None:
    import dataclasses

    from auditmanager.norms.loader import import_snapshot
    from auditmanager.norms.repository import SnapshotImportConflict
    from auditmanager.shared.db.engine import create_database_engine
    from auditmanager.shared.identity import NormParagraphId, NormsSnapshotId

    origin = create_database_engine(migrated_database_factory())
    target = create_database_engine(migrated_database_factory())
    try:
        corpus = _write_three_block_corpus(tmp_path / "corpus")
        _loaded, rows = _exported(origin, corpus, repair_ledger=_three_block_ledger(corpus))
        with Session(target) as session:
            with session.begin():
                import_snapshot(session, rows, chunking_profiles=["characters-v2:1200"])
        before = _table_counts(target)

        other_id = str(NormsSnapshotId.new())
        other_key = rows.snapshot.content_key.replace("+1r+1u.", "+1r+2u.")
        changed_text = dataclasses.replace(
            rows,
            paragraphs=(dataclasses.replace(rows.paragraphs[0], text=rows.paragraphs[0].text + " ."),
                        *rows.paragraphs[1:]),
        )
        changed_text = dataclasses.replace(
            changed_text,
            paragraphs=(
                dataclasses.replace(
                    changed_text.paragraphs[0], char_length=len(changed_text.paragraphs[0].text)
                ),
                *changed_text.paragraphs[1:],
            ),
        )

        def other_snapshot(snapshot_id: str, key: str, *, keep_children: bool):
            snapshot = dataclasses.replace(rows.snapshot, norms_snapshot_id=snapshot_id, content_key=key)
            if keep_children:
                return dataclasses.replace(rows, snapshot=snapshot)
            from auditmanager.shared.identity import NormDocumentId

            documents = {d.norm_document_id: str(NormDocumentId.new()) for d in rows.documents}
            return dataclasses.replace(
                rows,
                snapshot=snapshot,
                documents=tuple(
                    dataclasses.replace(d, norm_document_id=documents[d.norm_document_id])
                    for d in rows.documents
                ),
                paragraphs=tuple(
                    dataclasses.replace(
                        p,
                        norm_document_id=documents[p.norm_document_id],
                        norm_paragraph_id=str(NormParagraphId.new()),
                    )
                    for p in rows.paragraphs
                ),
            )

        fresh_children = other_snapshot(other_id, other_key, keep_children=False)
        one_reused = dataclasses.replace(
            fresh_children,
            paragraphs=(
                dataclasses.replace(
                    fresh_children.paragraphs[0], norm_paragraph_id=rows.paragraphs[0].norm_paragraph_id
                ),
                *fresh_children.paragraphs[1:],
            ),
        )
        cases = {
            "the same key under another id": (
                other_snapshot(other_id, rows.snapshot.content_key, keep_children=False),
                "the key is held by",
            ),
            "the same id under another key": (
                other_snapshot(rows.snapshot.norms_snapshot_id, other_key, keep_children=True),
                "the id names key",
            ),
            "equal ids with other rows": (changed_text, "is stored with row digest"),
            "a child id held by another snapshot": (one_reused, "belong to another snapshot"),
            "a replay naming an unbuilt profile": (rows, "is not built"),
        }
        for name, (candidate, message) in cases.items():
            profiles = (
                ["characters-v2:600"] if name == "a replay naming an unbuilt profile"
                else ["characters-v2:1200"]
            )
            with Session(target) as session:
                with session.begin():
                    with pytest.raises(SnapshotImportConflict, match=message):
                        import_snapshot(session, candidate, chunking_profiles=profiles)
            assert _table_counts(target) == before, name
    finally:
        origin.dispose()
        target.dispose()


def test_an_import_the_database_refuses_midway_leaves_nothing_behind(
    migrated_engine: Engine, tmp_path: Path
) -> None:
    """`ck_norms_snapshot_raw_key` refuses after the checks pass; the SAVEPOINT takes it all back."""
    import dataclasses

    from auditmanager.norms.loader import import_snapshot
    from auditmanager.shared.identity import (
        NormDocumentId,
        NormParagraphId,
        NormsSnapshotId,
    )

    corpus = _write_three_block_corpus(tmp_path / "corpus")
    loaded, rows = _exported(migrated_engine, corpus)
    documents = {d.norm_document_id: str(NormDocumentId.new()) for d in rows.documents}
    contradictory = dataclasses.replace(
        rows,
        snapshot=dataclasses.replace(
            rows.snapshot,
            norms_snapshot_id=str(NormsSnapshotId.new()),
            content_key="+0r+1u.".join(rows.snapshot.content_key.rsplit(".", 1)),
            unreliable_count=0,  # a moved key with nothing unreliable: refused by the CHECK
        ),
        documents=tuple(
            dataclasses.replace(d, norm_document_id=documents[d.norm_document_id])
            for d in rows.documents
        ),
        paragraphs=tuple(
            dataclasses.replace(
                p,
                norm_document_id=documents[p.norm_document_id],
                norm_paragraph_id=str(NormParagraphId.new()),
            )
            for p in rows.paragraphs
        ),
    )
    before = _table_counts(migrated_engine)
    with Session(migrated_engine) as session:
        with session.begin():
            with pytest.raises(IntegrityError, match="ck_norms_snapshot_raw_key"):
                import_snapshot(session, contradictory, chunking_profiles=["characters-v2:1200"])
    assert loaded.created
    assert _table_counts(migrated_engine) == before
