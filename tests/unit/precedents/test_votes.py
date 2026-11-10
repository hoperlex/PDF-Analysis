"""`plan-v5` 2.1: who votes, and which votes are independent. Each rule has a test in which only that rule can keep the offender out."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from auditmanager.precedents.models import DecisionEvent
from auditmanager.precedents.similarity import Thresholds
from auditmanager.precedents.votes import (
    EXCLUDED_BELOW_ANALOGOUS,
    EXCLUDED_INACTIVE,
    EXCLUDED_NO_SECTION,
    EXCLUDED_NO_VOTE,
    EXCLUDED_OTHER_DATA_CLASS,
    EXCLUDED_OTHER_SECTION,
    EXCLUDED_OUTSIDE_WINDOW,
    EXCLUDED_SAME_RUN,
    EXCLUDED_VERSION_CAP,
    case_vote,
    is_independent,
    months_before,
    select_votes,
)
from tests.unit.precedents.builders import ACCEPTED, NOW, REJECTED, ago, case, finding, scored

TH = Thresholds()


def _votes(items, **kwargs):
    return select_votes(finding(), items, as_of=NOW, thresholds=TH, **kwargs)


def _ids(vote_set):
    return [vote.case_id for vote in vote_set.votes]


def test_a_plain_case_votes_once_with_its_verdict():
    vote_set = _votes([scored(case("a", REJECTED)), scored(case("b", ACCEPTED))])
    assert sorted((vote.case_id, vote.verdict) for vote in vote_set.votes) == [("a", REJECTED), ("b", ACCEPTED)]
    assert vote_set.excluded == ()


@pytest.mark.parametrize(
    ("offender", "cosine", "reason"),
    [
        (case("x", active=False), 0.9, EXCLUDED_INACTIVE),
        (case("x", section="S2"), 0.9, EXCLUDED_OTHER_SECTION),
        (case("x", section=None), 0.9, EXCLUDED_NO_SECTION),
        (case("x", data_class="test"), 0.9, EXCLUDED_OTHER_DATA_CLASS),
        (case("x"), 0.8499, EXCLUDED_BELOW_ANALOGOUS),
        (case("x", verdict=None), 0.9, EXCLUDED_NO_VOTE),
        (case("x", verdict="needs_info"), 0.9, EXCLUDED_NO_VOTE),
        (case("x", days_ago=800), 0.9, EXCLUDED_OUTSIDE_WINDOW),
        (case("x", run="run-F"), 0.9, EXCLUDED_SAME_RUN),
        (case("x", origin="carried"), 0.9, EXCLUDED_NO_VOTE),
    ],
)
def test_each_corpus_rule_keeps_its_offender_out_and_says_why(offender, cosine, reason):
    vote_set = _votes([scored(case("good")), scored(offender, cosine)])
    assert _ids(vote_set) == ["good"]
    assert vote_set.excluded == ((reason, 1),)


def test_a_finding_without_a_section_has_no_corpus():
    vote_set = select_votes(finding(section=None), [scored(case("a"))], as_of=NOW, thresholds=TH)
    assert vote_set.votes == ()
    assert vote_set.excluded == ((EXCLUDED_NO_SECTION, 1),)


def test_the_edges_are_inclusive_at_the_analogous_cosine_and_the_24_month_start():
    on_edge = case("edge", decisions=(DecisionEvent(REJECTED, months_before(NOW, 24)),))
    just_older = case("old", decisions=(DecisionEvent(REJECTED, months_before(NOW, 24) - timedelta(seconds=1)),))
    vote_set = _votes([scored(case("cos"), 0.85), scored(on_edge), scored(just_older)])
    assert sorted(_ids(vote_set)) == ["cos", "edge"]
    assert vote_set.excluded == ((EXCLUDED_OUTSIDE_WINDOW, 1),)


def test_months_before_clamps_the_day_and_keeps_the_zone():
    assert months_before(datetime(2026, 3, 31, 8, tzinfo=timezone.utc), 1) == datetime(2026, 2, 28, 8, tzinfo=timezone.utc)
    assert months_before(datetime(2026, 1, 15, tzinfo=timezone.utc), 14) == datetime(2024, 11, 15, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        months_before(datetime(2026, 1, 15), 1)


def test_a_case_has_one_vote_its_last_verdict_and_a_comment_event_does_not_change_it():
    flipped = case("flip", decisions=(DecisionEvent(REJECTED, ago(90)), DecisionEvent(ACCEPTED, ago(60)), DecisionEvent(None, ago(10))))
    vote_set = _votes([scored(flipped)])
    assert [(vote.case_id, vote.verdict) for vote in vote_set.votes] == [("flip", ACCEPTED)]


def test_a_decision_after_the_as_of_moment_does_not_exist():
    later = case("later", decisions=(DecisionEvent(REJECTED, ago(90)), DecisionEvent(ACCEPTED, NOW + timedelta(days=1))))
    only_future = case("future", decisions=(DecisionEvent(REJECTED, NOW + timedelta(seconds=1)),))
    vote_set = _votes([scored(later), scored(only_future)])
    assert [(vote.case_id, vote.verdict) for vote in vote_set.votes] == [("later", REJECTED)]
    assert vote_set.excluded == ((EXCLUDED_NO_VOTE, 1),)
    assert case_vote(later, NOW + timedelta(days=2)).verdict == ACCEPTED


def test_a_carried_decision_does_not_vote_and_does_not_override_the_expert():
    carried_only = case("carried", origin="carried")
    after_direct = case("mixed", decisions=(DecisionEvent(REJECTED, ago(90)), DecisionEvent(ACCEPTED, ago(60), "carried")))
    vote_set = _votes([scored(carried_only), scored(after_direct)])
    assert [(vote.case_id, vote.verdict) for vote in vote_set.votes] == [("mixed", REJECTED)]
    assert vote_set.excluded == ((EXCLUDED_NO_VOTE, 1),)


def test_an_imported_decision_votes_and_is_independent_even_if_a_label_is_recorded():
    imported = case("imp", origin="imported", label="cancel_suggested")
    vote_set = _votes([scored(imported)])
    assert [(vote.case_id, vote.origin_kind, vote.independent) for vote in vote_set.votes] == [("imp", "imported", True)]


def test_at_most_two_votes_per_document_version_the_most_similar_and_the_smaller_id_on_a_tie():
    items = [
        scored(case("v1", version="same"), 0.88),
        scored(case("v3", version="same"), 0.95),
        scored(case("v2", version="same"), 0.88),
        scored(case("v4", version="same"), 0.88),
        scored(case("other", version="elsewhere"), 0.86),
    ]
    vote_set = _votes(items)
    assert sorted(_ids(vote_set)) == ["other", "v1", "v3"]
    assert vote_set.excluded == ((EXCLUDED_VERSION_CAP, 2),)


def test_a_case_that_already_failed_a_rule_does_not_use_up_a_version_slot():
    items = [scored(case("late", version="same", days_ago=800), 0.99), scored(case("a", version="same"), 0.9), scored(case("b", version="same"), 0.9)]
    assert sorted(_ids(_votes(items))) == ["a", "b"]


def test_votes_come_in_decision_time_order_whatever_the_input_order():
    items = [scored(case("late", days_ago=5)), scored(case("early", days_ago=50)), scored(case("mid", days_ago=20))]
    assert _ids(_votes(items)) == ["early", "mid", "late"]
    assert _ids(_votes(list(reversed(items)))) == ["early", "mid", "late"]


@pytest.mark.parametrize(
    ("label", "history", "expected"),
    [
        (None, None, True),
        ("often_rejected", None, False),
        ("cancel_suggested", None, False),
        ("likely_accepted", None, True),
        ("mixed", None, True),
        ("few", None, True),
        ("neutral", None, True),
        (None, REJECTED, False),
        (None, ACCEPTED, True),
        ("likely_accepted", REJECTED, False),
    ],
)
def test_a_vote_is_independent_unless_a_rejection_label_was_in_force_or_a_rejection_fact_was_shown(label, history, expected):
    assert is_independent(DecisionEvent(REJECTED, ago(5), "direct", label, history)) is expected
    vote_set = _votes([scored(case("a", label=label, history=history))])
    assert vote_set.votes[0].independent is expected


def test_a_naive_moment_or_an_unknown_origin_is_refused_not_guessed():
    with pytest.raises(ValueError):
        DecisionEvent(REJECTED, datetime(2026, 1, 1))
    with pytest.raises(ValueError):
        DecisionEvent(REJECTED, ago(1), "typed-by-hand")
