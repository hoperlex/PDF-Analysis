"""`NORM-REFS-RUN-01` on real PostgreSQL: the pinned catalogue read from the snapshot's rows.

Rows are written by plain SQL (``tests/integration/norms/search/conftest.py``), never by the
code under test. What this proves that the container-free tests cannot: the keyset statement
selects exactly one snapshot's documents in the byte order the catalogue uses at every page
boundary; the database's generated ``designation_tokens`` equal the Python twin (the resolver
refuses a difference, so a catalogue read here is also resolved here); the declared document
count is checked against what is stored; and the whole read runs in a READ ONLY transaction.

HEAVY by the repository's classification: it needs the lane's PostgreSQL (a throwaway database
at the migration head). It needs no S3.
"""

from __future__ import annotations

import pytest
from sqlalchemy import event, text

from auditmanager.norms.references.read_model import build_reference_read_model
from auditmanager.norms.references.resolution import (
    ReferenceRefused,
    extract_references,
    resolve_references,
    TextPage,
)
from auditmanager.norms.references.snapshot_catalogue import read_snapshot_catalogue
from auditmanager.norms.references.tokens import sql_designation_tokens
from auditmanager.shared.identity import NormDocumentId, NormsSnapshotId
from tests.integration.norms.search.conftest import (  # noqa: F401  (fixtures)
    Corpus,
    corpus,
    search_database,
    search_engine,
)

SP_2022 = "СП_54_13330_2022__Свод_правил__Здания_жилые_многоквартирные"
SP_2024 = "СП_54_13330_2024__Свод_правил__Здания_жилые_многоквартирные"
GOST = "ГОСТ_21_101-2020__Система_проектной_документации"
LAW = "Федеральный_закон_от_22_07_2008_N_123-ФЗ_(ред__от_25_12_2023)"
SNIP = "СНиП_31-01-2003__Здания_жилые"
MDS = "МДС_12-24_2006__Устройство_обычных"
ORDER = "Приказ_МЧС_России_от_19_03_2020_N_194"
# A Latin ``C`` and ``P`` in a Cyrillic word, and an en dash: the fold the database applies.
HOMOGLYPH = "CП_1_13130_2020__Системы_противопожарной_защиты"
OTHER_SNAPSHOT_ONLY = "СП_99_13330_2020__Только_в_другом_снимке"

SLUGS = (SP_2022, SP_2024, GOST, LAW, SNIP, MDS, ORDER, HOMOGLYPH)


def _seed(corpus: Corpus, *slugs: str, declared: int | None = None) -> tuple[str, dict[str, str]]:
    """One snapshot with these documents, inserted in the REVERSE of their identity order.

    ``NormDocumentId.new()`` is time-ordered, so inserting in call order would make the
    physical order the identity order and an ``ORDER BY`` mutation invisible.
    """
    snapshot = corpus.snapshot(documents=len(slugs) if declared is None else declared)
    ids = {slug: str(NormDocumentId.new()) for slug in slugs}
    for slug in reversed(slugs):
        corpus.run(
            "INSERT INTO norm_document (norm_document_id, norms_snapshot_id, source_document_ref, "
            "slug, title, doc_type, source_attribution, pdf_page_count, block_count, "
            "page_heading_count, recognised_characters, paragraph_count) "
            "VALUES (:d, :s, :ref, :slug, :title, :doc_type, 'consultant_plus', 50, 1, 0, 10, 0)",
            d=ids[slug], s=snapshot, ref=f"ref-{ids[slug][-8:]}", slug=slug,
            title=slug.split("__", 1)[-1].replace("_", " ") or slug, doc_type=slug.split("_", 1)[0],
        )
    return snapshot, ids


def _read(corpus: Corpus, snapshot: str, **keywords):
    with corpus.session_factory() as session:
        return read_snapshot_catalogue(session, snapshot_id=snapshot, **keywords)


@pytest.mark.parametrize("page_size", [1, 2, 3, 7, 8, 9, 500])
def test_every_page_size_reads_the_same_snapshot_in_catalogue_order(corpus: Corpus, page_size) -> None:
    snapshot, ids = _seed(corpus, *SLUGS)
    other, _ = _seed(corpus, OTHER_SNAPSHOT_ONLY, SP_2022)

    catalogue = _read(corpus, snapshot, page_size=page_size)

    assert catalogue.snapshot_id == snapshot != other
    assert [d.document_id for d in catalogue.documents] == sorted(ids.values())
    assert {d.slug: d.document_id for d in catalogue.documents} == ids
    assert OTHER_SNAPSHOT_ONLY not in {d.slug for d in catalogue.documents}


def test_the_unparsed_slugs_are_the_ones_the_parser_cannot_read(corpus: Corpus) -> None:
    snapshot, ids = _seed(corpus, *SLUGS)

    catalogue = _read(corpus, snapshot)

    by_id = {v: k for k, v in ids.items()}
    assert set(catalogue.listed_unparsed_slugs) == {MDS, ORDER}
    assert list(catalogue.listed_unparsed_slugs) == [
        by_id[d.document_id] for d in catalogue.documents if by_id[d.document_id] in {MDS, ORDER}
    ]


def test_the_stored_tokens_equal_the_python_twin_and_the_resolver_accepts_them(corpus: Corpus) -> None:
    snapshot, ids = _seed(corpus, *SLUGS)

    catalogue = _read(corpus, snapshot)

    for document in catalogue.documents:
        assert document.designation_tokens == sql_designation_tokens(document.slug), document.slug
    # The Latin look-alikes were folded by the database exactly as the twin folds them.
    homoglyph = next(d for d in catalogue.documents if d.slug == HOMOGLYPH)
    assert homoglyph.designation_tokens[0] == "сп"
    report = resolve_references(
        extraction=extract_references((TextPage("1", "по СП 1.13130.2020 и СП 54.13330.2022"),)),
        catalogue=catalogue,
        pinned_snapshot_id=snapshot,
    )
    assert [(r.cited, r.outcome) for r in report.references] == [
        ("СП 1.13130.2020", "есть в корпусе"),
        ("СП 54.13330.2022", "в корпусе есть более новая редакция"),
    ]
    assert report.references[0].matched_document_id == ids[HOMOGLYPH]


def test_the_read_model_over_the_seeded_snapshot(corpus: Corpus) -> None:
    snapshot, ids = _seed(corpus, *SLUGS)
    pages = {
        1: "Здания по СП 54.13330.2022, ГОСТ 21.101-2020 и ГОСТ 21.101-2021.",
        2: "",
        3: "Пожарная безопасность по ФЗ-123; СНиП 31-01-2012; ГОСТ Р 99999-2020.",
    }

    model = build_reference_read_model(
        pages=pages, catalogue=_read(corpus, snapshot), pinned_snapshot_id=snapshot
    )

    assert [(i.cited, i.outcome) for i in model.items] == [
        ("СП 54.13330.2022", "newer_edition"),
        ("ГОСТ 21.101-2020", "in_corpus"),
        ("ГОСТ 21.101-2021", "older_edition_only"),
        ("ФЗ-123", "in_corpus"),
        ("СНиП 31-01-2012", "older_edition_only"),
        ("ГОСТ Р 99999-2020", "not_in_corpus"),
    ]
    assert model.items[0].matched_document_id == ids[SP_2024]
    assert model.items[0].matched_designation == "СП 54.13330.2024"
    assert model.items[3].matched_designation == "Федеральный закон от 22.07.2008 N 123-ФЗ (ред. от 25.12.2023)"
    assert model.unread_pages == (2,)
    assert sorted(u.slug for u in model.unrecognised) == sorted([MDS, ORDER])
    assert model.snapshot_document_count == len(SLUGS)


def test_the_read_runs_in_a_read_only_transaction_and_sends_selects_only(corpus: Corpus, search_engine) -> None:
    snapshot, _ = _seed(corpus, *SLUGS)
    sent: list[str] = []

    @event.listens_for(search_engine, "before_cursor_execute")
    def record(connection, cursor, statement, parameters, context, executemany):  # noqa: ARG001
        sent.append(" ".join(statement.split()))

    try:
        with corpus.session_factory() as session:
            session.execute(text("SET TRANSACTION READ ONLY"))
            catalogue = read_snapshot_catalogue(session, snapshot_id=snapshot, page_size=3)
    finally:
        event.remove(search_engine, "before_cursor_execute", record)

    assert catalogue.snapshot_id == snapshot
    reads = [s for s in sent if "norm_document" in s or "norms_snapshot" in s]
    assert len(reads) == 1 + 3  # the declared count, then three pages: 3 + 3 + 2 documents
    assert all(s.upper().startswith("SELECT") for s in reads)


def test_a_snapshot_that_declares_more_than_it_stores_is_refused(corpus: Corpus) -> None:
    snapshot, _ = _seed(corpus, SP_2022, SP_2024, declared=3)

    with pytest.raises(ReferenceRefused, match="fewer documents"):
        _read(corpus, snapshot)


def test_a_snapshot_that_declares_less_than_it_stores_is_refused(corpus: Corpus) -> None:
    snapshot, _ = _seed(corpus, SP_2022, SP_2024, declared=1)

    with pytest.raises(ReferenceRefused, match="more documents"):
        _read(corpus, snapshot)


def test_an_absent_snapshot_is_refused(corpus: Corpus) -> None:
    _seed(corpus, SP_2022)

    with pytest.raises(ReferenceRefused, match="absent"):
        _read(corpus, str(NormsSnapshotId.new()))
