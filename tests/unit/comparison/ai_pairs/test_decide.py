"""`CMP-VC-AIPAIR-01`: the acceptance rule, container-free.

The first test is the original's own ``test_decide_rules`` (``tests/test_version_comparison_sheet_match.py:51-67`` at ``23f379fd``)
ported case for case; the others pin the refusals one by one, so that a mutation of any one of them turns exactly its test red.
"""

from __future__ import annotations

import pytest

from auditmanager.comparison.ai_pairs.decide import (
    PICK_MISMATCH,
    PICK_NONE,
    decide,
    mark_shared,
    needs_reverse,
    pick_of,
    reverse_candidates,
)
from auditmanager.comparison.ai_pairs.model import (
    DECISIONS,
    KIND_MEDIUM_PAIR,
    KIND_NO_PAIR,
    Answer,
    Question,
    QuestionPage,
)

A_VERSION, B_VERSION = "ver_A", "ver_B"


def page(version: str, number: int) -> QuestionPage:
    return QuestionPage(version, number, f"cpr_{version}_{number}")


def question(**over: object) -> Question:
    base: dict[str, object] = dict(
        kind=KIND_NO_PAIR, a=page(A_VERSION, 2), b_version_uid=B_VERSION, candidates=(page(B_VERSION, 2), page(B_VERSION, 3)),
    )
    return Question(**{**base, **over})  # type: ignore[arg-type]


def ans(choice: int, page_number: int, confidence: str = "high", cands: tuple[int, ...] = (2, 3)) -> Answer:
    """``_ans`` of the original's tests."""
    return Answer(ok=True, choice=choice, page=page_number, confidence=confidence, reason="r", cands=cands)


FAILED = Answer(ok=False)


def test_the_originals_decide_rules_case_for_case() -> None:
    q = question()
    rev_ok = ans(1, 2, cands=(2, 4))
    assert decide(q, ans(2, 3), rev_ok) == "link_accepted"  # the original's «accepted»
    assert decide(q, ans(2, 2), rev_ok) == "answer_mismatch", "the candidate number and the page disagree"
    assert decide(q, ans(0, 0), None) == "none"
    assert decide(q, ans(2, 3, "medium"), rev_ok) == "hint_confidence"
    assert decide(q, ans(2, 3), ans(2, 4, cands=(2, 4))) == "hint_reverse"
    assert decide(q, ans(2, 3), ans(1, 2, "medium", cands=(2, 4))) == "hint_reverse"
    assert decide(question(multi=True), ans(2, 3), rev_ok) == "hint_table"
    assert decide(question(taken_b=frozenset({3})), ans(2, 3), rev_ok) == "hint_taken"
    assert decide(q, FAILED, None) == "failed"
    m = question(kind=KIND_MEDIUM_PAIR, a=page(A_VERSION, 5), candidates=(page(B_VERSION, 5), page(B_VERSION, 6), page(B_VERSION, 7)), algo_b=6)
    assert decide(m, ans(2, 6, cands=(5, 6, 7)), None) == "medium_confirm"
    assert decide(m, ans(2, 6, "low", cands=(5, 6, 7)), None) == "medium_weak"
    assert decide(m, ans(3, 7, cands=(5, 6, 7)), None) == "medium_other"
    assert decide(m, ans(0, 0, cands=(5, 6, 7)), None) == "medium_none"


def test_every_decision_the_rule_makes_is_one_the_table_allows() -> None:
    q = question()
    made = {
        decide(q, ans(2, 3), ans(1, 2, cands=(2, 4))), decide(q, ans(2, 2), None), decide(q, ans(0, 0), None),
        decide(q, ans(2, 3, "low"), None), decide(q, ans(2, 3), None), decide(question(multi=True), ans(2, 3), None),
        decide(question(taken_b=frozenset({3})), ans(2, 3), None), decide(q, FAILED, None),
    }
    assert made <= set(DECISIONS)


@pytest.mark.parametrize("confidence", ["medium", "low"])
def test_an_answer_is_accepted_only_with_high_confidence(confidence: str) -> None:
    """Mutation M1: the confidence test deleted -> a medium answer with an agreeing reverse becomes a link."""
    assert decide(question(), ans(2, 3, confidence), ans(1, 2, cands=(2, 4))) == "hint_confidence"


def test_an_answer_is_accepted_only_with_an_agreeing_reverse_question_that_is_high() -> None:
    """Mutation M2: the reverse test deleted -> every high answer becomes a link whatever the reverse says."""
    q = question()
    assert decide(q, ans(2, 3), None) == "hint_reverse", "no reverse answer at all"
    assert decide(q, ans(2, 3), FAILED) == "hint_reverse", "an unusable reverse answer"
    assert decide(q, ans(2, 3), ans(2, 4, cands=(2, 4))) == "hint_reverse", "the reverse names another sheet than A"
    assert decide(q, ans(2, 3), ans(0, 0, cands=(2, 4))) == "hint_reverse", "the reverse says none"
    assert decide(q, ans(2, 3), ans(1, 2, "medium", cands=(2, 4))) == "hint_reverse", "the reverse names A but not with high"
    assert decide(q, ans(2, 3), ans(1, 2, cands=(2, 4))) == "link_accepted"


def test_a_sheet_inside_a_multi_sheet_specification_is_never_accepted() -> None:
    """Mutation M3: the ``multi`` test deleted -> a high answer with an agreeing reverse becomes a link."""
    assert decide(question(multi=True), ans(2, 3), ans(1, 2, cands=(2, 4))) == "hint_table"


def test_a_b_that_is_already_paired_is_never_accepted() -> None:
    """Mutation M4: the ``taken_b`` test deleted -> the model re-pairs a B the algorithm (or an expert) already paired."""
    q = question(taken_b=frozenset({3}))
    assert decide(q, ans(2, 3), ans(1, 2, cands=(2, 4))) == "hint_taken"
    assert decide(question(taken_b=frozenset({2})), ans(2, 3), ans(1, 2, cands=(2, 4))) == "link_accepted", "only the chosen page counts"


def test_the_number_and_the_page_must_agree() -> None:
    assert pick_of(ans(2, 2)) == (PICK_MISMATCH, "high")
    assert pick_of(ans(5, 3)) == (PICK_NONE, "high"), "a number outside the list is read as none"
    assert pick_of(ans(2, 3)) == (3, "high")
    assert pick_of(None) == (None, None) and pick_of(FAILED) == (None, None)


def test_a_medium_pair_question_never_becomes_a_link() -> None:
    m = question(kind=KIND_MEDIUM_PAIR, candidates=(page(B_VERSION, 2), page(B_VERSION, 3)), algo_b=2)
    for forward in (ans(1, 2), ans(2, 3), ans(0, 0), ans(1, 2, "low")):
        assert decide(m, forward, ans(1, 2, cands=(2, 4))) != "link_accepted"


def test_two_sheets_that_chose_the_same_b_are_both_only_hints() -> None:
    """The original's ``hint_double`` (``sheet_match.py:595-601``): both, and only inside one pair of versions."""
    one, two, other = question(a=page(A_VERSION, 2)), question(a=page(A_VERSION, 4)), question(a=page(A_VERSION, 6))
    decisions = [(one, "link_accepted", 3), (two, "link_accepted", 3), (other, "link_accepted", 5)]
    assert mark_shared(decisions) == ["hint_shared", "hint_shared", "link_accepted"]
    elsewhere = question(a=page("ver_Z", 4), b_version_uid="ver_Y")
    assert mark_shared([(one, "link_accepted", 3), (elsewhere, "link_accepted", 3)]) == ["link_accepted", "link_accepted"]
    assert mark_shared([(one, "link_accepted", 3), (two, "hint_reverse", 3)]) == ["link_accepted", "hint_reverse"]


def test_the_reverse_question_is_asked_only_where_an_acceptance_depends_on_it() -> None:
    q = question()
    assert needs_reverse(q, ans(2, 3)) == 3
    assert needs_reverse(q, ans(2, 3, "medium")) is None, "only a high answer can be accepted"
    assert needs_reverse(q, ans(0, 0)) is None and needs_reverse(q, ans(2, 2)) is None and needs_reverse(q, FAILED) is None
    assert needs_reverse(question(multi=True), ans(2, 3)) is None, "a table is a hint whatever the reverse says"
    assert needs_reverse(question(taken_b=frozenset({3})), ans(2, 3)) is None
    m = question(kind=KIND_MEDIUM_PAIR, algo_b=2)
    assert needs_reverse(m, ans(1, 2)) is None and needs_reverse(m, ans(2, 3)) is None, "a medium question's decision never reads it"


def test_the_reverse_candidates_are_the_pages_of_bs_own_cell_and_sheet_a() -> None:
    q = question(back={3: (1, 4, 5, 9)})
    assert reverse_candidates(q, 3, 10) == (1, 2, 4, 5), "at most three of B's own candidates, and A"
    assert reverse_candidates(question(), 3, 10) == (1, 2, 3), "only A: its neighbours"
    assert reverse_candidates(question(a=page(A_VERSION, 1)), 3, 10) == (1, 2), "the first sheet has no previous page"
    assert reverse_candidates(question(a=page(A_VERSION, 10)), 3, 10) == (9, 10), "nor the last a next one"
