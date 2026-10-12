"""`W55A-FIX` against PostgreSQL: the judges' search findings on a real database.

The offline half (``test_w55a_fix_offline.py``) proves the refusals happen in Python; this
half proves what each one prevents on PostgreSQL, through the shipped ``NormsSearchAdapter``
over the suite's throwaway database (``conftest.Corpus``):

* **Y-4** ``СП 54`` typed with a no-break space or a tab, and ``СНиП 2.01.07-85`` typed with
  an en or em dash, find exactly what the ASCII spelling finds -- before the fix the database
  received one token ``сп 54`` or ``07–85`` and answered an empty page;
* **X-M1** a forged ``s1d`` ordinal of 2^31 is ``422 cursor/format`` -- before the fix
  ``CAST(:after_ordinal AS integer)`` failed with SQLSTATE 22003 (an internal error);
* **X-M2** a NUL in ``q`` is ``422 q/format`` -- before the fix psycopg refused to bind it
  (an internal error);
* **X-M5** a blank ``q`` is ``422 q/format`` -- before the fix it answered a page of the
  whole snapshot, sorted.

HEAVY: the lane's private PostgreSQL.
"""

from __future__ import annotations

import pytest

from auditmanager.bootstrap.adapters import NormsSearchAdapter
from auditmanager.norms.search.cursor import (
    DesignationPosition,
    ParagraphPosition,
    encode_paragraph_cursor,
    encode_search_cursor,
    query_binding,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.norms.search.conftest import Corpus

SP54 = "СП_54_13330_2022__Свод_правил__Здания_жилые_многоквартирные"
SP542 = "СП_542_1325800_2024__Свод_правил__Защитные_сооружения"
SNIP = "СНиП_2_01_07-85__Нагрузки_и_воздействия"

FORMAT_CURSOR = {"field": "cursor", "constraint": "format"}
FORMAT_Q = {"field": "q", "constraint": "format"}


class Seeded:
    def __init__(self, corpus: Corpus) -> None:
        self.snapshot = corpus.snapshot(documents=3)
        self.sp54 = corpus.document(self.snapshot, SP54)
        self.sp542 = corpus.document(self.snapshot, SP542)
        self.snip = corpus.document(self.snapshot, SNIP)
        p = corpus.paragraph
        self.stairs = p(self.sp54, "7.1.4 Лестницы жилых зданий", ordinal=0, clause="7.1.4")
        self.roof = p(self.sp54, "7.10 Требования к кровле зданий", ordinal=1, clause="7.10")
        self.shelter = p(self.sp542, "5.1 Защитные сооружения в зданиях", ordinal=0)
        self.loads = p(self.snip, "Нагрузки на перекрытия зданий", ordinal=0)
        corpus.designate(self.snapshot)
        self.adapter = NormsSearchAdapter(corpus.session_factory, timeout_ms=3000)

    def ids(self, q: str, *, cursor: str | None = None) -> list[str]:
        page = self.adapter.search(q=q, norms_snapshot_id=None, cursor=cursor, limit=50)
        return [item.norm_paragraph_id for item in page.items]

    def refusal(self, q: str, *, cursor: str | None = None) -> DomainError:
        with pytest.raises(DomainError) as caught:
            self.adapter.search(q=q, norms_snapshot_id=None, cursor=cursor, limit=50)
        return caught.value


@pytest.fixture
def seeded(corpus: Corpus) -> Seeded:
    return Seeded(corpus)


@pytest.mark.parametrize(
    ("typed", "ascii"),
    [
        ("СП 54", "СП 54"),
        ("СП\t54", "СП 54"),
        ("сп  54 зданий", "СП 54 зданий"),
        ("СНиП 2.01.07–85", "СНиП 2.01.07-85"),
        ("СНиП 2.01.07—85", "СНиП 2.01.07-85"),
    ],
    ids=["nbsp", "tab", "em-space-nbsp-words", "en-dash", "nbsp-em-dash"],
)
def test_a_designation_with_unicode_separators_finds_what_ascii_finds(
    seeded: Seeded, typed: str, ascii: str,
) -> None:
    expected = seeded.ids(ascii)
    assert expected, f"the control {ascii!r} found nothing, so the case proves nothing"
    assert seeded.ids(typed) == expected


def test_the_designation_still_matches_whole_leading_tokens(seeded: Seeded) -> None:
    assert seeded.ids("СП 54") == [seeded.stairs, seeded.roof]
    assert seeded.ids("СП 542") == [seeded.shelter]
    assert seeded.ids("СНиП 2.01.07–85") == [seeded.loads]


def test_a_forged_ordinal_is_refused_not_a_database_error(seeded: Seeded) -> None:
    binding = query_binding("СП 54", seeded.snapshot)
    forged = encode_search_cursor(binding, DesignationPosition(seeded.sp54, 2**31, seeded.stairs))
    error = seeded.refusal("СП 54", cursor=forged)
    assert (error.code, dict(error.detail_fields)) == (ErrorCode.VALIDATION_FAILED, FORMAT_CURSOR)
    # The control: the largest integer resumes after every paragraph of that document.
    largest = encode_search_cursor(
        binding, DesignationPosition(seeded.sp54, 2**31 - 1, seeded.stairs)
    )
    assert seeded.ids("СП 54", cursor=largest) == []
    paragraph = encode_paragraph_cursor(ParagraphPosition(seeded.sp54, 2**31))
    with pytest.raises(DomainError) as caught:
        seeded.adapter.list_paragraphs(norm_document_id=seeded.sp54, cursor=paragraph, limit=10)
    assert dict(caught.value.detail_fields) == FORMAT_CURSOR


@pytest.mark.parametrize("q", ["здания\x00", "\x00", "СП 54\x00"], ids=["words", "alone", "designation"])
def test_a_nul_in_q_is_refused_not_a_database_error(seeded: Seeded, q: str) -> None:
    error = seeded.refusal(q)
    assert (error.code, dict(error.detail_fields)) == (ErrorCode.VALIDATION_FAILED, FORMAT_Q)
    assert seeded.ids(q.replace("\x00", "") or "здания")  # the control is searchable


@pytest.mark.parametrize("q", [" ", "   ", " \t"], ids=["space", "spaces", "nbsp-tab"])
def test_a_blank_q_is_refused_not_a_sort_of_the_snapshot(seeded: Seeded, q: str) -> None:
    error = seeded.refusal(q)
    assert (error.code, dict(error.detail_fields)) == (ErrorCode.VALIDATION_FAILED, FORMAT_Q)
