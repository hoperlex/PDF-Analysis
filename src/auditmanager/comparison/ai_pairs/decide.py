"""The acceptance rule: what the lane's rule makes of the answers (the original's ``pick_of``, ``reverse_cands`` and ``decide``).

Pure functions over validated answers; no database, no model. This is the one place a model's word can become an accepted AI
link, so every refusal is spelled out here and each is shown failing under a mutation (report section on safety).

An answer is accepted -- ``link_accepted`` -- only when **all** hold (``sheet_match.py:11-15`` docstring, ``decide`` ``:326-350``):

1. the question is a ``no_pair`` one (a ``medium_pair`` question only confirms or doubts the algorithm's pair, ``:332-337``);
2. the model named a candidate and the candidate number and the page it names agree (otherwise ``answer_mismatch``, ``:313-314``);
3. sheet A is **not inside a multi-sheet specification** (``hint_table``, ``:340-341``);
4. the confidence is **high** (``hint_confidence``, ``:342-343``);
5. **B is not already paired** with an A sheet (``hint_taken``, ``:344-345``);
6. the **reverse question** -- asked from B back to A's version -- returned **A with high** confidence (``hint_reverse``,
   ``:346-348``);
7. no other A sheet of the same version chose the same B (``hint_shared``, the original's ``hint_double``, ``:595-601``).

Nothing else is accepted, and an accepted answer is still only an AI layer: it never rewrites the matrix (ADR-0025 decision 3) and
a manual edit wins over it in the effective matrix.
"""

from __future__ import annotations

from collections.abc import Sequence

from auditmanager.comparison.ai_pairs.model import (
    DECISION_ANSWER_MISMATCH,
    DECISION_FAILED,
    DECISION_HINT_CONFIDENCE,
    DECISION_HINT_REVERSE,
    DECISION_HINT_SHARED,
    DECISION_HINT_TABLE,
    DECISION_HINT_TAKEN,
    DECISION_LINK_ACCEPTED,
    DECISION_MEDIUM_CONFIRM,
    DECISION_MEDIUM_NONE,
    DECISION_MEDIUM_OTHER,
    DECISION_MEDIUM_WEAK,
    DECISION_NONE,
    KIND_MEDIUM_PAIR,
    MAX_REVERSE_CANDIDATES,
    Answer,
    Question,
)

__all__ = [
    "PICK_MISMATCH",
    "PICK_NONE",
    "decide",
    "mark_shared",
    "needs_reverse",
    "pick_of",
    "reverse_candidates",
]

#: ``pick_of``: the model said that no candidate is the same sheet.
PICK_NONE = 0
#: ``pick_of``: the candidate number and the page it names disagree (the answer is dropped).
PICK_MISMATCH = -1


def pick_of(answer: Answer | None) -> tuple[int | None, str | None]:
    """``(page, confidence)`` of an answer: ``PICK_NONE`` for «none of them», ``PICK_MISMATCH`` when the number and the page
    disagree, ``None`` when there is no usable answer (``sheet_match.py:306-315``)."""
    if answer is None or not answer.ok:
        return None, None
    if not 1 <= answer.choice <= len(answer.cands):
        return PICK_NONE, answer.confidence
    if answer.page != answer.cands[answer.choice - 1]:
        return PICK_MISMATCH, answer.confidence
    return answer.cands[answer.choice - 1], answer.confidence


def reverse_candidates(question: Question, b_page: int, a_version_pages: int) -> tuple[int, ...]:
    """The candidates of the reverse question: the pages of A's version that B's own cell offers (at most three) and sheet A; when
    that is only A, its neighbours (``sheet_match.py:318-324``). Sorted, no repeats."""
    chosen = set(question.back.get(b_page, ())[:MAX_REVERSE_CANDIDATES]) | {question.a.page_number}
    if len(chosen) < 2:
        chosen |= {n for n in (question.a.page_number - 1, question.a.page_number + 1) if 1 <= n <= a_version_pages}
    return tuple(sorted(chosen))


def needs_reverse(question: Question, forward: Answer | None) -> int | None:
    """The B page whose reverse question is worth asking, or ``None``.

    Only a ``no_pair`` question has one (the decision of a ``medium_pair`` question never reads it, ``sheet_match.py:332-337``:
    asking it would only spend money); only an answer that names a page with **high** confidence can be accepted, so any other
    answer is not asked again; a sheet inside a multi-sheet specification or a B already paired ends as a hint whatever the
    reverse says (``sheet_match.py:562-567``)."""
    if question.kind == KIND_MEDIUM_PAIR:
        return None
    pick, confidence = pick_of(forward)
    if not pick or pick < 0 or confidence != "high":
        return None
    if question.multi or pick in question.taken_b:
        return None
    return pick


def decide(question: Question, forward: Answer | None, reverse: Answer | None) -> str:
    """The decision of a question from the forward answer and the reverse one (``sheet_match.py:326-350``)."""
    pick, confidence = pick_of(forward)
    if pick is None:
        return DECISION_FAILED
    if pick == PICK_MISMATCH:
        return DECISION_ANSWER_MISMATCH
    if question.kind == KIND_MEDIUM_PAIR:
        if pick == PICK_NONE:
            return DECISION_MEDIUM_NONE
        if pick == question.algo_b:
            return DECISION_MEDIUM_CONFIRM if confidence == "high" else DECISION_MEDIUM_WEAK
        return DECISION_MEDIUM_OTHER
    if pick == PICK_NONE:
        return DECISION_NONE
    if question.multi:
        return DECISION_HINT_TABLE
    if confidence != "high":
        return DECISION_HINT_CONFIDENCE
    if pick in question.taken_b:
        return DECISION_HINT_TAKEN
    reverse_pick, reverse_confidence = pick_of(reverse)
    if not (reverse_pick == question.a.page_number and reverse_confidence == "high"):
        return DECISION_HINT_REVERSE
    return DECISION_LINK_ACCEPTED


def mark_shared(decisions: Sequence[tuple[Question, str, int | None]]) -> list[str]:
    """Two sheets of the same version that chose the same B are both only a hint (``sheet_match.py:595-601``): the decisions in
    the order given, with every ``link_accepted`` that shares its (version of A, version of B, chosen page) with another
    ``link_accepted`` made ``hint_shared``. ``decisions`` are ``(question, decision, chosen page)``."""
    seen: dict[tuple[str, str, int | None], int] = {}
    for question, decision, pick in decisions:
        if decision == DECISION_LINK_ACCEPTED:
            key = (question.a.version_uid, question.b_version_uid, pick)
            seen[key] = seen.get(key, 0) + 1
    return [
        DECISION_HINT_SHARED
        if decision == DECISION_LINK_ACCEPTED and seen[(question.a.version_uid, question.b_version_uid, pick)] > 1
        else decision
        for question, decision, pick in decisions
    ]
