"""`CMP-VC-AIPAIR-01`: which cells of the effective matrix are doubtful, container-free (a port of ``questions``,
``sheet_match.py:124-166``, over the effective read model)."""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.comparison.ai_pairs.model import KIND_MEDIUM_PAIR, KIND_NO_PAIR, MAX_CANDIDATES_NO_PAIR, PageFacts
from auditmanager.comparison.ai_pairs.questions import derive_questions, is_multi_sheet_spec, is_spec_page

V1, V2, V3 = "ver_1", "ver_2", "ver_3"


def facts(version: str, number: int, *, title: str = "", designation: str = "", preview: bool = True) -> PageFacts:
    return PageFacts(
        page_profile_id=f"cpr_{version}_{number}", version_uid=version, page_number=number, content_key=f"k{version}{number}",
        title=title, designation=designation, preview_blob_id=f"blob_{version}_{number}" if preview else None,
        preview_sha256="ab" * 32 if preview else None, preview_size=500 if preview else 0,
    )


def pages(**special: PageFacts) -> dict[tuple[str, int], PageFacts]:
    out = {(v, n): facts(v, n) for v in (V1, V2, V3) for n in range(1, 13)}
    for (key, value) in special.items():
        out[(value.version_uid, value.page_number)] = value
    return out


def ref(version: str, number: int) -> dict[str, Any]:
    return {"version_uid": version, "page_number": number, "page_profile_id": f"cpr_{version}_{number}"}


def matched(version: str, number: int, confidence: str | None = None, flags: tuple[str, ...] = ()) -> dict[str, Any]:
    cell: dict[str, Any] = {"version_uid": version, "state": "matched", "page": ref(version, number), "flags": list(flags)}
    if confidence:
        cell["confidence"] = confidence
    return cell


def unmatched(version: str, candidates: list[int]) -> dict[str, Any]:
    return {
        "version_uid": version, "state": "unmatched", "reason": "candidates_left",
        "candidates": [{"page": ref(version, n), "score": 0.4} for n in candidates],
    }


def absent(version: str) -> dict[str, Any]:
    return {"version_uid": version, "state": "absent", "reason": "no_candidates"}


def row(*cells: dict[str, Any]) -> dict[str, Any]:
    return {"row_id": cells[0].get("page", {}).get("page_profile_id", "x"), "cells": list(cells)}


def derive(rows: list[dict[str, Any]], facts_map: dict[tuple[str, int], PageFacts] | None = None, order: tuple[str, ...] = (V1, V2)):
    return derive_questions(order=order, page_counts={v: 12 for v in order}, rows=rows, facts=facts_map or pages())


def test_an_unmatched_cell_with_candidates_is_a_no_pair_question() -> None:
    rows = [row(matched(V1, 2), unmatched(V2, [5, 3, 4]))]
    (q,) = derive(rows)
    assert (q.kind, q.a.page_number, q.b_version_uid) == (KIND_NO_PAIR, 2, V2)
    assert [c.page_number for c in q.candidates] == [3, 4, 5], "sorted by number"
    assert q.a.page_profile_id == "cpr_ver_1_2" and q.candidates[0].page_profile_id == "cpr_ver_2_3"


def test_a_pair_of_medium_confidence_is_a_medium_pair_question_over_the_page_and_its_neighbours() -> None:
    (q,) = derive([row(matched(V1, 4), matched(V2, 6, "medium"))])
    assert (q.kind, q.algo_b) == (KIND_MEDIUM_PAIR, 6)
    assert [c.page_number for c in q.candidates] == [5, 6, 7]
    (edge,) = derive([row(matched(V1, 1), matched(V2, 12, "medium"))])
    assert [c.page_number for c in edge.candidates] == [11, 12], "the last page has no next one"


@pytest.mark.parametrize("confidence", ["high", "group", "manual", "ai"])
def test_a_pair_that_is_not_medium_is_not_asked(confidence: str) -> None:
    """Mutation: the ``manual`` / ``ai`` cells are not doubtful -- an expert's cell and a cell the model already settled stay out."""
    assert derive([row(matched(V1, 4), matched(V2, 6, confidence))]) == []


def test_a_bridge_across_a_missing_version_is_not_asked() -> None:
    assert derive([row(matched(V1, 4), matched(V2, 6, "medium", flags=("bridge",)))]) == []


def test_a_sheet_an_expert_placed_asks_nothing() -> None:
    """The original's ``ca.get("manual")`` (``sheet_match.py:145``): the sheet A is a cell of an edited row."""
    assert derive([row(matched(V1, 2, "manual"), unmatched(V2, [3]))]) == []


def test_an_absent_cell_and_a_cell_with_no_candidates_ask_nothing() -> None:
    assert derive([row(matched(V1, 2), absent(V2))]) == []
    assert derive([row(matched(V1, 2), {"version_uid": V2, "state": "unmatched", "reason": "x", "candidates": []})]) == []


def test_a_sheet_inside_a_table_group_is_not_asked() -> None:
    """Sheets inside the range of a «▤» group of the pair of versions are decided by the group rule (``sheet_match.py:152-153``)."""
    rows = [
        row(matched(V1, 3), matched(V2, 3, "group")), row(matched(V1, 7), matched(V2, 8, "group")),
        row(matched(V1, 5), unmatched(V2, [9])),   # inside 3..7
        row(matched(V1, 10), unmatched(V2, [11])),  # outside
    ]
    assert [q.a.page_number for q in derive(rows)] == [10]


def test_a_specification_sheet_is_not_asked_and_is_not_a_candidate() -> None:
    spec = pages(**{"a": facts(V1, 2, title="Спецификация оборудования")})
    assert derive([row(matched(V1, 2), unmatched(V2, [3]))], spec) == [], "sheet A is a specification"
    cand = pages(**{"a": facts(V2, 4, designation="133-ЭО.СО")})
    (q,) = derive([row(matched(V1, 2), unmatched(V2, [3, 4]))], cand)
    assert [c.page_number for c in q.candidates] == [3], "a specification sheet is not a candidate"
    only = pages(**{"a": facts(V2, 3, title="Спецификация")})
    assert derive([row(matched(V1, 2), unmatched(V2, [3]))], only) == [], "no candidate left, no question"
    plan = pages(**{"a": facts(V1, 2, title="Спецификация. План этажа")})
    assert len(derive([row(matched(V1, 2), unmatched(V2, [3]))], plan)) == 1, "a plan, a scheme, a section or a detail is not one"


def test_a_page_without_a_stored_preview_cannot_be_shown() -> None:
    no_a = pages(**{"a": facts(V1, 2, preview=False)})
    assert derive([row(matched(V1, 2), unmatched(V2, [3]))], no_a) == []
    no_candidate = pages(**{"a": facts(V2, 3, preview=False)})
    (q,) = derive([row(matched(V1, 2), unmatched(V2, [3, 4]))], no_candidate)
    assert [c.page_number for c in q.candidates] == [4]


def test_at_most_four_candidates_are_offered_so_a_request_has_at_most_five_pictures() -> None:
    """Mutation: the slice ``[:4]`` removed -> nine candidates, ten pictures, over the executors' eight (``A-12``)."""
    (q,) = derive([row(matched(V1, 2), unmatched(V2, list(range(1, 10))))])
    assert len(q.candidates) == MAX_CANDIDATES_NO_PAIR == 4
    assert [c.page_number for c in q.candidates] == [1, 2, 3, 4]


def test_a_b_already_paired_with_another_a_is_remembered_with_the_candidates_of_its_own_cell() -> None:
    rows = [
        row(matched(V1, 1), matched(V2, 3, "high")),                 # B page 3 is paired with A page 1
        row(matched(V1, 2), unmatched(V2, [3, 4])),                   # A page 2 is asked about 3 and 4
        row(unmatched(V1, [2, 9]), matched(V2, 4)),                   # B page 4's own cell offers A pages 2 and 9
    ]
    (q,) = derive(rows)
    assert q.taken_b == frozenset({3}) and dict(q.back) == {4: (2, 9)}


def test_the_questions_of_every_transition_are_asked_in_order() -> None:
    rows = [
        row(matched(V1, 2), unmatched(V2, [3]), matched(V3, 5)),
        row(matched(V1, 6), matched(V2, 6, "high"), unmatched(V3, [7, 8])),
    ]
    questions = derive(rows, order=(V1, V2, V3))
    assert [(q.a.version_uid, q.a.page_number, q.b_version_uid) for q in questions] == [(V1, 2, V2), (V2, 6, V3)]


def test_a_specification_is_recognised_by_its_stamp_and_a_multi_sheet_one_by_its_neighbour() -> None:
    assert is_spec_page(facts(V1, 1, designation="133/23-ГК-ЭО.со")) and is_spec_page(facts(V1, 1, title="Спецификации оборудования"))
    assert not is_spec_page(facts(V1, 1, title="Схема. Спецификация")) and not is_spec_page(facts(V1, 1, title="План")) and not is_spec_page(None)
    assert not is_spec_page(facts(V1, 1, title="Спецификация. Узел 4")), "a detail is a drawing"
    two = pages(**{"a": facts(V1, 4, title="Спецификация"), "b": facts(V1, 5, title="Спецификация")})
    alone = pages(**{"a": facts(V1, 4, title="Спецификация")})
    assert is_multi_sheet_spec(4, V1, two) and is_multi_sheet_spec(5, V1, two)
    assert not is_multi_sheet_spec(4, V1, alone) and not is_multi_sheet_spec(3, V1, two)
