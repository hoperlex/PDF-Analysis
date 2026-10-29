"""The counts and the verdict codes of a transition (`CMP-SERIES-01`; the original's ``series.summary``)."""

from __future__ import annotations

import pytest

from auditmanager.comparison.series.model import VERDICT_ORDER
from auditmanager.comparison.series.verdict import PairFacts, summarize, transition_verdict, verdict_codes


def done(status: str, *, both: bool = True, ai: bool = False, style: bool = False) -> PairFacts:
    return PairFacts("done", status, both, ai, style)


def test_the_counts_follow_the_originals_summary() -> None:
    summary = summarize([
        done("same"), done("same"), done("same_zones_changed"), done("different"), done("different", style=True),
        done("needs_review"), done("unmatched", both=False), done("added", both=False), done("removed", both=False, ai=True),
        PairFacts("failed", None, True), PairFacts("queued", None, True),
    ])
    assert summary == {
        "sheets": 11, "compared": 8, "same": 2, "zones_only": 1, "different": 2, "style_only": 1,
        "needs_review": 2, "added": 1, "removed": 1, "failed": 1, "ai_dependent": 1,
    }


def test_style_only_counts_only_a_different_sheet() -> None:
    summary = summarize([PairFacts("done", "same", True, False, True), done("different", style=True)])
    assert summary["style_only"] == 1


@pytest.mark.parametrize(("pairs", "expected"), [
    ([done("same"), done("same")], ["content_same"]),
    ([done("same"), done("same_zones_changed")], ["content_same", "zones_only"]),
    ([done("same"), done("different")], ["different"]),
    ([done("same"), done("added", both=False)], ["composition_changed"]),
    ([done("same"), done("removed", both=False)], ["composition_changed"]),
    ([done("same"), done("needs_review")], ["needs_review"]),
    ([done("same"), done("unmatched", both=False)], ["needs_review"]),
    ([done("different"), done("added", both=False), done("needs_review")], ["different", "composition_changed", "needs_review"]),
])
def test_the_codes_of_a_complete_transition(pairs: list[PairFacts], expected: list[str]) -> None:
    _summary, codes = transition_verdict(pairs)
    assert codes == expected


def test_the_verdict_is_never_content_same_while_a_pair_is_missing_or_failed() -> None:
    """ADR-0025 decision 20 and the lane's brief: a half-compared transition must not read «Совпадает»."""
    for open_pair in (PairFacts("queued", None, True), PairFacts("computing", None, True)):
        _s, codes = transition_verdict([done("same"), open_pair])
        assert codes == ["incomplete"]
    _s, codes = transition_verdict([done("same"), PairFacts("failed", None, True)])
    assert "content_same" not in codes and codes == ["incomplete", "calculation_failed"]
    # a zone-only transition with a failed pair is not content_same / zones_only either
    _s, codes = transition_verdict([done("same_zones_changed"), PairFacts("failed", None, True)])
    assert "content_same" not in codes and "zones_only" not in codes


def test_a_transition_with_no_pair_has_nothing_to_say_but_that_it_is_incomplete() -> None:
    assert transition_verdict([])[1] == ["incomplete"]


def test_the_codes_come_in_the_order_the_contract_shows_them() -> None:
    summary = {"different": 1, "needs_review": 1, "added": 1, "removed": 0, "failed": 1, "zones_only": 0}
    codes = verdict_codes(summary, pairs_total=5, pairs_done=3)
    assert codes == ["incomplete", "different", "composition_changed", "needs_review", "calculation_failed"]
    assert codes == [c for c in VERDICT_ORDER if c in codes]


def test_a_verdict_always_has_at_least_one_code() -> None:
    for pairs in ([], [done("same")], [done("different")], [PairFacts("failed", None, True)]):
        assert 1 <= len(transition_verdict(pairs)[1]) <= 7
