"""`NORM-STATUS-ORIGINAL-01`: the norm stage is partial only for a technical failure (owner 2026-11-16).

Pure over the fields the lookup and the review write on each observation; the flow path's behaviour on top of them is in
``tests/unit/analysis_extended/test_flow_repair.py`` and the older path's in ``tests/unit/runs/test_norm_coverage.py``.
"""

from __future__ import annotations

import pytest

from auditmanager.runs import extended_review as er
from auditmanager.runs.norm_stage_accounting import (
    NORM_REPLY_REFUSED,
    NO_NORM_NAMED_REASONS,
    account_norm_inputs,
    classify_norm_input,
)


def item(**fields):
    return fields


@pytest.mark.parametrize(("fields", "expected"), [
    (item(norm_status="not_applicable"), ("not_applicable", None)),
    (item(norm_status="not_found"), ("not_found", None)),
    (item(norm_status="unavailable", norm_reason="normative_query_required"), ("no_norm_named", None)),
    (item(norm_status="unavailable", norm_reason="query_not_proposed"), ("no_norm_named", None)),
    (item(norm_status="candidates", norm_review_status="reviewed", normative_context={"complete": True}), ("reviewed", None)),
    (item(norm_status="candidates", norm_review_status="reviewed", normative_context={"complete": False}),
     ("reviewed_context_incomplete", None)),
    (item(norm_status="candidates", norm_review_status="reviewed"), ("reviewed", None)),  # the older path keeps no context receipt
    (item(norm_status="candidates", norm_review_status="not_reviewed", normative_context={"complete": False}), ("refused", None)),
    (item(norm_status="candidates"), ("technical", "no_stored_outcome")),
    (item(norm_status="unavailable", norm_reason="lookup_unavailable"), ("technical", "lookup_unavailable")),
    (item(norm_status="unavailable", norm_reason="corpus_unavailable"), ("technical", "corpus_unavailable")),
    (item(norm_status="unavailable", norm_reason="semantic_lookup_failed"), ("technical", "semantic_lookup_failed")),
    (item(norm_status="unavailable", norm_reason="lookup_window_exhausted"), ("technical", "lookup_window_exhausted")),
    (item(norm_status="unavailable"), ("technical", "unknown")),
    (item(), ("technical", "no_stored_outcome")),
    (item(norm_status="something_new"), ("technical", "no_stored_outcome")),
])
def test_each_outcome_is_terminal_or_technical(fields, expected) -> None:
    assert classify_norm_input(fields) == expected


def test_the_accounting_balances_and_names_what_it_counted() -> None:
    items = [item(norm_status="not_applicable"), item(norm_status="not_found"),
             item(norm_status="unavailable", norm_reason="normative_query_required"),
             item(norm_status="candidates", norm_review_status="reviewed", normative_context={"complete": False})]
    outcome = account_norm_inputs(items)
    assert (outcome.status, outcome.reason, outcome.technical_gap) == ("completed", None, False)
    accounting = outcome.accounting
    assert (accounting["expected"], accounting["valid"], accounting["pending"], accounting["refused"], accounting["excluded"]) == (4, 2, 0, 0, 2)
    assert sum(accounting["outcomes"].values()) == 4 and accounting["technical"] == {}


def test_a_stage_of_inputs_with_no_normative_question_says_so() -> None:
    outcome = account_norm_inputs([item(norm_status="not_applicable"), item(norm_status="unavailable", norm_reason="normative_query_required")])
    assert (outcome.status, outcome.reason) == ("completed", "no_normative_question")
    assert (outcome.accounting["expected"], outcome.accounting["excluded"]) == (2, 2)
    empty = account_norm_inputs([])
    assert (empty.status, empty.reason, empty.accounting["expected"]) == ("completed", "no_normative_question", 0)


def test_a_refused_reply_wins_the_reason_over_a_failed_lookup() -> None:
    outcome = account_norm_inputs([item(norm_status="candidates", norm_review_status="not_reviewed"),
                                   item(norm_status="unavailable", norm_reason="lookup_unavailable"),
                                   item(norm_status="not_found")])
    assert (outcome.status, outcome.reason, outcome.technical_gap) == ("partial", NORM_REPLY_REFUSED, True)
    assert (outcome.accounting["valid"], outcome.accounting["pending"], outcome.accounting["refused"]) == (1, 1, 1)
    assert outcome.accounting["technical"] == {"lookup_unavailable": 1}


def test_the_reason_of_a_refused_reply_is_the_one_the_stage_already_wrote() -> None:
    assert NORM_REPLY_REFUSED == er.NORM_REPLY_REFUSED == "norm_verification_reply_refused"


def test_the_unnamed_norm_reasons_are_the_ones_the_lookup_writes() -> None:
    """The flow plan writes ``normative_query_required`` and the older paths ``query_not_proposed`` (`NORM-COVERAGE-01`)."""
    assert "normative_query_required" in NO_NORM_NAMED_REASONS
    assert er._NO_NORM_QUESTION <= NO_NORM_NAMED_REASONS
