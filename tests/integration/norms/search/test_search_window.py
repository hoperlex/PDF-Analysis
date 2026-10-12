"""Text search against PostgreSQL (`W55A-SEARCH-01`; window: PostgreSQL ``57230``).

`W55-PLAN.md` section A3.4, through the shipped ``NormsSearchAdapter`` over one throwaway
database at the migration head (``0020``), the rows written by plain SQL (``conftest.Corpus``):

* Russian morphology: ``здание`` finds ``зданий`` and ``зданиях``;
* designation lookup by whole leading tokens: ``СП 54`` never finds ``СП 542``; homoglyphs
  and case fold; a clause is a dotted-segment prefix (``7.1`` is not ``7.10``);
* unreliable paragraphs are never a hit;
* a cursor is refused with another query, and paging neither repeats nor skips;
* the window is capped at 1 000;
* a search the statement timeout cancels is ``norms_search_too_broad``, and the timeout is
  local to the search's transaction;
* the scope: none current, or a never-current snapshot, is refused; a once-current one is
  searched.
"""

from __future__ import annotations

import threading

import pytest
from sqlalchemy import text

from auditmanager.bootstrap.adapters import NormsSearchAdapter
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.norms.search.conftest import Corpus

SP54 = "СП_54_13330_2022__Свод_правил__Здания_жилые_многоквартирные"
SP542 = "СП_542_1325800_2024__Свод_правил__Защитные_сооружения"
GOST = "ГОСТ_10140-2003__Межгосударственный_стандарт__Плиты"


class Seeded:
    def __init__(self, corpus: Corpus) -> None:
        self.corpus = corpus
        self.snapshot = corpus.snapshot(unreliable=1, documents=3)
        self.sp54 = corpus.document(self.snapshot, SP54)
        self.sp542 = corpus.document(self.snapshot, SP542)
        self.gost = corpus.document(self.snapshot, GOST)
        p = corpus.paragraph
        self.general = p(self.sp54, "7.1 Общие требования к лестницам", ordinal=0, clause="7.1")
        self.stairs = p(self.sp54, "7.1.4 Лестницы жилых зданий должны иметь ограждения",
                        ordinal=1, page=12, clause="7.1.4")
        self.roof = p(self.sp54, "7.10 Требования к кровле", ordinal=2, clause="7.10")
        self.garbage = p(self.sp54, "Здания жилые мусорный распознанный текст", ordinal=3,
                         reliable=False)
        self.shelter = p(self.sp542, "5.1 Защитные сооружения в зданиях", ordinal=0,
                         clause="5.1")
        self.slab = p(self.gost, "4.2 Плиты перекрытий для здания", ordinal=0, clause="4.2")
        corpus.designate(self.snapshot)
        self.adapter = NormsSearchAdapter(corpus.session_factory, timeout_ms=3000)

    def ids(self, q: str, **kwargs) -> list[str]:
        page = self.adapter.search(
            q=q, norms_snapshot_id=kwargs.get("snapshot"), cursor=None,
            limit=kwargs.get("limit", 50),
        )
        return [item.norm_paragraph_id for item in page.items]


@pytest.fixture
def seeded(corpus: Corpus) -> Seeded:
    return Seeded(corpus)


def _refusal(call) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call()
    return caught.value


def test_russian_morphology_finds_every_form(seeded: Seeded) -> None:
    found = set(seeded.ids("здание"))
    assert {seeded.stairs, seeded.shelter, seeded.slab} <= found
    assert seeded.garbage not in found


def test_unreliable_paragraphs_are_never_a_hit(seeded: Seeded) -> None:
    assert seeded.corpus.scalar(
        "SELECT count(*) FROM norm_paragraph WHERE text_reliability = 'unreliable' "
        "AND text_tsv @@ websearch_to_tsquery('russian', 'мусорный')"
    ) == 1
    assert seeded.ids("мусорный") == []
    assert seeded.garbage not in seeded.ids("СП 54")


def test_sp_54_finds_sp_54_and_never_sp_542(seeded: Seeded) -> None:
    assert seeded.ids("СП 54") == [seeded.general, seeded.stairs, seeded.roof]
    assert seeded.ids("СП 542") == [seeded.shelter]
    assert seeded.ids("ГОСТ 10140") == [seeded.slab]
    assert seeded.ids("ГОСТ 1014") == []


def test_homoglyphs_and_case_find_the_same_designation(seeded: Seeded) -> None:
    expected = seeded.ids("СП 54")
    for typed in ("CП 54", "сп 54", "Cп 54", "СП_54", "СП 54.13330"):
        assert seeded.ids(typed) == expected, typed


def test_a_clause_is_a_dotted_segment_prefix(seeded: Seeded) -> None:
    assert seeded.ids("СП 54 п. 7.1") == [seeded.general, seeded.stairs]
    assert seeded.ids("п. 7.10") == [seeded.roof]
    assert seeded.ids("п. 7.1.4") == [seeded.stairs]


def test_a_designation_narrows_ranked_words(seeded: Seeded) -> None:
    assert seeded.ids("СП 54 здания") == [seeded.stairs]
    page = seeded.adapter.search(q="СП 54 здания", norms_snapshot_id=None, cursor=None, limit=5)
    hit = page.items[0]
    assert (hit.designation, hit.page_label, hit.clause_number) == ("СП 54 13330 2022", 12, "7.1.4")
    spans = [hit.fragment.text[h.char_start:h.char_end] for h in hit.fragment.highlights]
    assert spans and all(span.lower().startswith("здан") for span in spans)
    assert hit.source_attribution.value == "consultant_plus"


def test_paging_neither_repeats_nor_skips_and_a_cursor_is_bound(seeded: Seeded) -> None:
    whole = seeded.ids("здание")
    collected: list[str] = []
    cursor = None
    while True:
        page = seeded.adapter.search(q="здание", norms_snapshot_id=None, cursor=cursor, limit=1)
        collected += [item.norm_paragraph_id for item in page.items]
        cursor = page.page.next_cursor
        if cursor is None:
            break
        error = _refusal(lambda: seeded.adapter.search(
            q="зданий", norms_snapshot_id=None, cursor=cursor, limit=1
        ))
        assert (error.code, dict(error.detail_fields)) == (
            ErrorCode.VALIDATION_FAILED, {"field": "cursor", "constraint": "format"}
        )
    assert collected == whole

    ordered = seeded.adapter.search(q="СП 54", norms_snapshot_id=None, cursor=None, limit=2)
    rest = seeded.adapter.search(
        q="СП 54", norms_snapshot_id=None, cursor=ordered.page.next_cursor, limit=2
    )
    assert [i.norm_paragraph_id for i in ordered.items + rest.items] == seeded.ids("СП 54")


def test_the_window_is_capped_at_one_thousand(corpus: Corpus) -> None:
    snapshot = corpus.snapshot()
    document = corpus.document(snapshot, SP54)
    corpus.run(
        "INSERT INTO norm_paragraph (norm_paragraph_id, norms_snapshot_id, norm_document_pk, "
        "ordinal, page_label, block_ref, char_offset, char_length, kind, clause_number, text, "
        "text_reliability) "
        "SELECT 'npar_' || lpad(n::text, 26, '0'), d.norms_snapshot_id, d.norm_document_pk, "
        "n, 1, 'blk_' || n, 0, char_length('Кровля здания номер ' || n), 'body', NULL, "
        "'Кровля здания номер ' || n, 'reliable' "
        "FROM norm_document d, generate_series(0, 1004) AS n WHERE d.norm_document_id = :d",
        d=document,
    )
    corpus.designate(snapshot)
    adapter = NormsSearchAdapter(corpus.session_factory, timeout_ms=30000)
    for q in ("кровля", "СП 54"):
        seen: list[str] = []
        cursor = None
        while True:
            page = adapter.search(q=q, norms_snapshot_id=None, cursor=cursor, limit=200)
            seen += [item.norm_paragraph_id for item in page.items]
            cursor = page.page.next_cursor
            if cursor is None:
                break
        assert len(seen) == 1000 and len(set(seen)) == 1000, q


def test_a_cancelled_search_is_too_broad_and_the_timeout_is_local(seeded: Seeded) -> None:
    corpus = seeded.corpus
    adapter = NormsSearchAdapter(corpus.session_factory, timeout_ms=300)
    locked = threading.Event()
    release = threading.Event()

    def hold_lock() -> None:
        with corpus.engine.begin() as connection:
            connection.execute(text("LOCK TABLE norm_paragraph IN ACCESS EXCLUSIVE MODE"))
            locked.set()
            release.wait(30)

    holder = threading.Thread(target=hold_lock)
    holder.start()
    try:
        assert locked.wait(30)
        error = _refusal(lambda: adapter.search(
            q="здание", norms_snapshot_id=None, cursor=None, limit=10
        ))
        assert (error.code, dict(error.detail_fields)) == (
            ErrorCode.VALIDATION_FAILED, {"field": "q", "constraint": "norms_search_too_broad"}
        )
    finally:
        release.set()
        holder.join(30)
    # The timeout was `SET LOCAL`: a later session of the same factory does not carry it.
    with corpus.session_factory() as session:
        assert session.execute(text("SHOW statement_timeout")).scalar() != "300ms"
    assert seeded.ids("здание")


def test_the_scope_rule(corpus: Corpus) -> None:
    adapter = NormsSearchAdapter(corpus.session_factory, timeout_ms=3000)
    first = corpus.snapshot()
    corpus.paragraph(corpus.document(first, SP54), "Лестницы зданий", ordinal=0)
    second = corpus.snapshot()
    corpus.paragraph(corpus.document(second, SP54), "Лестницы зданий", ordinal=0)
    never = corpus.snapshot()

    error = _refusal(lambda: adapter.search(q="здание", norms_snapshot_id=None, cursor=None,
                                            limit=10))
    assert (error.code, dict(error.detail_fields)) == (
        ErrorCode.REQUIRED_NORM_UNAVAILABLE, {"reference_kind": "norms_snapshot"}
    )
    corpus.designate(first)
    corpus.designate(second)
    current = adapter.search(q="здание", norms_snapshot_id=None, cursor=None, limit=10)
    assert {item.norms_snapshot_id for item in current.items} == {second}
    earlier = adapter.search(q="здание", norms_snapshot_id=first, cursor=None, limit=10)
    assert {item.norms_snapshot_id for item in earlier.items} == {first}
    error = _refusal(lambda: adapter.search(q="здание", norms_snapshot_id=never, cursor=None,
                                            limit=10))
    assert (error.code, dict(error.detail_fields)) == (
        ErrorCode.REQUIRED_NORM_UNAVAILABLE,
        {"reference_kind": "norms_snapshot", "norms_snapshot_id": never},
    )
