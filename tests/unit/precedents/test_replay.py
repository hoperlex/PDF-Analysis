"""`plan-v5` 2.6 (CRIT-REPLAY-01): the history replay. Each rule has a test in which only that rule can produce the asserted number."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from datetime import timedelta
from fractions import Fraction

import pytest

from auditmanager.precedents.models import CriticCandidate, DecisionEvent
from auditmanager.precedents.replay import (
    FAIL_CASES,
    FAIL_HARM,
    FAIL_PRECISION,
    FAIL_PROTECTED,
    FAIL_UPLIFT,
    FIT_NONE_QUALIFIED,
    FIT_SELECTED,
    ReplayCase,
    SectionRule,
    ShownLabelCounts,
    SliceMetrics,
    replay_history,
    rule_failures,
)
from auditmanager.precedents.stemming import compile_stop_words
from tests.unit.precedents.builders import ACCEPTED, NOW, REJECTED, case

T0 = NOW - timedelta(days=200)
OLD = NOW - timedelta(days=400)


def _target(
    case_id: str,
    verdict: str,
    when,
    *,
    section: str = "S1",
    label: str | None = None,
    history: str | None = None,
    run: str | None = None,
    run_finished_at="default",
    critic: str | None = "reject",
    in_plan: bool = True,
    protected: bool = False,
    text: str = "Толщина защитного слоя не соответствует проекту.",
    data_class: str = "real",
    project: str = "pt",
    later: tuple[DecisionEvent, ...] = (),
) -> ReplayCase:
    prepared = case(
        case_id,
        decisions=(DecisionEvent(verdict, when, "direct", label, history), *later),
        section=section,
        run=run,
        data_class=data_class,
        project=project,
    )
    finished = when - timedelta(hours=1) if run_finished_at == "default" else run_finished_at
    candidates = (CriticCandidate(f"cand-{case_id}", (f"primary_text_{case_id}",), critic),) if critic is not None else ()
    return ReplayCase(
        prepared,
        text,
        finished,
        in_plan,
        primary_source_id=f"primary_text_{case_id}",
        candidates=candidates,
        protected=protected,
    )


def _old(index: int, *, section: str = "S1", when=None, extra: tuple[DecisionEvent, ...] = (), run: str | None = None) -> ReplayCase:
    moment = when or OLD - timedelta(days=index)
    prepared = case(
        f"old{index}",
        decisions=(DecisionEvent(REJECTED, moment), *extra),
        section=section,
        project=f"p{index % 3}",
        run=run,
    )
    return ReplayCase(prepared, "давнее решение", moment - timedelta(hours=1), True)


@dataclass(frozen=True)
class Spec:
    """One replayed target: its verdict and whether its vector has the six old rejecting neighbours (so «снять» fires for it)."""

    verdict: str
    flagged: bool
    label: str | None = None
    history: str | None = None
    protected: bool = False
    critic: str | None = "reject"
    in_plan: bool = True
    section: str = "S1"
    text: str = "Толщина защитного слоя не соответствует проекту."


def _build(specs, *, cosine: float = 0.9, olds=None, id_of=lambda index: f"t{index:03d}"):
    olds = olds if olds is not None else [_old(index) for index in range(6)]
    cases = list(olds)
    scores = {}
    for index, spec in enumerate(specs):
        case_id = id_of(index)
        cases.append(
            _target(
                case_id,
                spec.verdict,
                T0 + timedelta(hours=index),
                section=spec.section,
                label=spec.label,
                history=spec.history,
                critic=spec.critic,
                in_plan=spec.in_plan,
                protected=spec.protected,
                text=spec.text,
            )
        )
        scores[case_id] = {old.case.case_id: cosine for old in olds if old.case.section == spec.section} if spec.flagged else {}
    return cases, scores


def _pattern(count: int):
    """Index % 4: 0 flagged and rejected, 1 and 2 plain accepted, 3 plain rejected."""
    kinds = [Spec(REJECTED, True), Spec(ACCEPTED, False), Spec(ACCEPTED, False), Spec(REJECTED, False)]
    return [kinds[index % 4] for index in range(count)]


def _replay(cases, scores, **kwargs):
    kwargs.setdefault("data_class", "real")
    return replay_history(cases, scores, **kwargs)


# ---- the time cut ----------------------------------------------------------------------------------------------------------------------


def test_a_decision_after_the_cut_does_not_reach_the_label():
    flipped = [_old(i, extra=(DecisionEvent(ACCEPTED, T0 + timedelta(days=10)),)) for i in range(6)]
    cases, scores = _build([Spec(REJECTED, True)], olds=flipped)
    report = _replay(cases, scores)
    # as of the run's end the six neighbours had rejected; their later acceptances are the future
    assert report.section("S1").test.cancel == 1


def test_neighbours_that_were_decided_only_after_the_cut_do_not_vote_at_all():
    late = [_old(i, when=T0 + timedelta(days=5, hours=i)) for i in range(6)]
    cases, scores = _build([Spec(REJECTED, True)], olds=late)
    section = _replay(cases, scores).section("S1")
    assert (section.test.cancel, section.test_precedent_only.cancel) == (0, 0)


@pytest.mark.parametrize(
    ("run_finished_days", "neighbours_days", "cancel", "why"),
    [
        (2.0, 1.0, 1, "the run ended at +2d, so a neighbour decided at +1d is in the past"),
        (2.0, 2.5, 0, "the cut is the run's end (+2d), not the target's own decision (+3d): +2.5d is the future"),
        (None, 2.5, 1, "the run is erased, so the cut is the target's earliest decision (+3d): +2.5d is the past"),
        (None, 3.5, 0, "the run is erased and +3.5d is after the target's earliest decision"),
    ],
)
def test_the_cut_is_the_end_of_the_run_or_the_earliest_decision_when_the_run_is_erased(run_finished_days, neighbours_days, cancel, why):
    olds = [_old(i, when=T0 + timedelta(days=neighbours_days, hours=i)) for i in range(6)]
    finished = None if run_finished_days is None else T0 + timedelta(days=run_finished_days)
    # the target was decided twice: its earliest decision (+3d) is the cut of an erased run, and the later one (+6d) must not move it
    later = (DecisionEvent(REJECTED, T0 + timedelta(days=6)),)
    target = _target("t000", REJECTED, T0 + timedelta(days=3), run_finished_at=finished, later=later)
    report = _replay([*olds, target], {"t000": {old.case.case_id: 0.9 for old in olds}})
    assert report.section("S1").test.cancel == cancel, why


def test_votes_of_the_same_run_are_excluded():
    same_run = [_old(i, run="run-shared") for i in range(6)]
    target = _target("t000", REJECTED, T0, run="run-shared")
    report = _replay([*same_run, target], {"t000": {old.case.case_id: 0.9 for old in same_run}})
    assert report.section("S1").test_precedent_only.cancel == 0
    other_run = [_old(i) for i in range(6)]
    report = _replay([*other_run, target], {"t000": {old.case.case_id: 0.9 for old in other_run}})
    assert report.section("S1").test_precedent_only.cancel == 1


# ---- the 70 / 30 split by time -------------------------------------------------------------------------------------------------------


def test_the_split_is_70_30_by_decision_time_whatever_the_order_of_the_input():
    # ten targets: the three latest are flagged and rejected, the seven earlier are plain
    specs = [Spec(ACCEPTED if i % 2 else REJECTED, False) for i in range(7)] + [Spec(REJECTED, True)] * 3
    cases, scores = _build(specs, id_of=lambda index: f"t{99 - index:03d}")  # the ids run against the time: the order is the decision time's
    random.Random(7).shuffle(cases)
    section = _replay(cases, scores).section("S1")
    assert (section.targets, section.fit_targets, section.test_targets) == (10, 7, 3)
    assert section.test.cancel == 3 and section.test.targets == 3
    assert all(metrics.cancel == 0 for _, metrics in section.fit_grid)


def test_cancels_in_the_early_slice_are_not_the_reported_ones():
    specs = [Spec(REJECTED, True)] * 3 + [Spec(ACCEPTED, False)] * 4 + [Spec(REJECTED, False)] * 3
    cases, scores = _build(specs)
    section = _replay(cases, scores).section("S1")
    assert section.test.cancel == 0 and section.test.targets == 3
    assert max(metrics.cancel for _, metrics in section.fit_grid) == 3


def test_rounding_goes_down_for_the_fit_and_each_section_splits_on_its_own():
    s1 = [Spec(REJECTED, False)] * 7
    s2 = [Spec(ACCEPTED, False, section="S2")] * 4
    cases, scores = _build(s1 + s2)
    report = _replay(cases, scores)
    assert [(s.section, s.fit_targets, s.test_targets) for s in report.sections] == [("S1", 4, 3), ("S2", 2, 2)]


def test_equal_decision_moments_never_straddle_the_boundary():
    cases, scores = _build([Spec(REJECTED, False)] * 10)
    same = T0 + timedelta(hours=6)
    cases = [
        ReplayCase(
            case(c.case.case_id, decisions=(DecisionEvent(REJECTED, same),)) if c.case.case_id in {f"t00{i}" for i in range(6, 10)} else c.case,
            c.finding_text,
            c.run_finished_at,
            c.critic_in_plan,
        )
        for c in cases
    ]
    section = _replay(cases, scores).section("S1")
    assert (section.fit_targets, section.test_targets) == (6, 4)  # the boundary (the 8th decision) falls inside the tie of 4: all go to the check


def test_the_threshold_is_chosen_on_the_fit_slice_and_the_default_is_kept_when_nothing_qualifies():
    cases, scores = _build(_pattern(20), cosine=0.82)
    section = _replay(cases, scores).section("S1")
    assert (section.fit_selection, section.analogous_threshold) == (FIT_SELECTED, 0.8)
    assert {value: metrics.cancel for value, metrics in section.fit_grid} == {0.8: 4, 0.85: 0, 0.9: 0}
    assert section.test.cancel == 1  # index 16, flagged at 0.8

    cases, scores = _build(_pattern(20), cosine=0.9)
    section = _replay(cases, scores).section("S1")
    assert (section.fit_selection, section.analogous_threshold) == (FIT_SELECTED, 0.9)  # every value qualifies equally: the strictest wins

    cases, scores = _build(_pattern(20), cosine=0.7)
    section = _replay(cases, scores).section("S1")
    assert (section.fit_selection, section.analogous_threshold) == (FIT_NONE_QUALIFIED, 0.85)


def test_a_threshold_that_cancels_accepted_findings_on_the_fit_slice_does_not_qualify():
    # the flagged fit targets are all accepted: precision 0, so no value qualifies even though all of them cancel
    specs = [Spec(ACCEPTED, True)] * 4 + [Spec(REJECTED, False)] * 6 + [Spec(ACCEPTED, False)] * 10
    cases, scores = _build(specs)
    section = _replay(cases, scores).section("S1")
    assert section.fit_selection == FIT_NONE_QUALIFIED and section.analogous_threshold == 0.85
    assert all(metrics.cancel == 4 and metrics.cancel_rejected == 0 for _, metrics in section.fit_grid)


def test_the_default_threshold_is_always_tried_next_to_the_grid():
    cases, scores = _build(_pattern(20), cosine=0.82)
    section = _replay(cases, scores, analogous_grid=(0.8,)).section("S1")
    assert [value for value, _ in section.fit_grid] == [0.8, 0.85]


# ---- decisions under a shown label ---------------------------------------------------------------------------------------------------


def test_decisions_under_a_shown_rejection_label_are_outside_the_rates_and_reported_apart():
    specs = _pattern(14) + [
        Spec(REJECTED, True),  # 14: independent, cancelled, rejected
        Spec(REJECTED, True),  # 15: independent, cancelled, rejected
        Spec(ACCEPTED, True, label="cancel_suggested"),  # 16: decided under the shown cancel label
        Spec(ACCEPTED, True, label="often_rejected"),  # 17: decided under the shown rejection label
        Spec(ACCEPTED, False),  # 18: independent, plain
        Spec(REJECTED, False, history=REJECTED),  # 19: decided after a shown rejection fact
    ]
    cases, scores = _build(specs)
    section = _replay(cases, scores).section("S1")
    assert section.test_targets == 6
    test = section.test
    assert (test.targets, test.rejected, test.accepted) == (3, 2, 1)
    assert (test.cancel, test.cancel_rejected, test.cancel_accepted) == (2, 2, 0)
    assert test.harm == Fraction(0) and test.precision == Fraction(1)
    assert section.shown_label_test == ShownLabelCounts(decisions=3, rejected=1, accepted=2)
    # the information block counts the same independent decisions only
    assert section.test_precedent_only.targets == 3 and section.test_precedent_only.cancel_accepted == 0


def test_a_neutral_label_that_was_shown_does_not_make_a_decision_dependent():
    specs = _pattern(14) + [Spec(ACCEPTED, True, label="neutral"), Spec(ACCEPTED, True, label="likely_accepted")] + [Spec(REJECTED, False)] * 4
    cases, scores = _build(specs)
    section = _replay(cases, scores).section("S1")
    assert section.shown_label_test == ShownLabelCounts(0, 0, 0)
    assert section.test.targets == 6 and section.test.cancel_accepted == 2


# ---- the numbers ---------------------------------------------------------------------------------------------------------------------


def test_base_rate_uplift_precision_and_harm_of_a_small_check_slice():
    cases, scores = _build(_pattern(20), cosine=0.9)
    test = _replay(cases, scores).section("S1").test
    # the check slice is targets 14..19: plain accepted, plain rejected, flagged rejected, plain accepted, plain accepted, plain rejected
    assert (test.targets, test.rejected, test.accepted, test.cancel, test.cancel_rejected, test.cancel_accepted) == (6, 3, 3, 1, 1, 0)
    assert (test.base_reject_rate, test.precision, test.uplift, test.harm) == (Fraction(1, 2), Fraction(1), Fraction(1, 2), Fraction(0))


def test_a_cancelled_accepted_finding_is_the_harm_and_lowers_the_precision():
    specs = _pattern(20)
    specs[16] = Spec(ACCEPTED, True)
    cases, scores = _build(specs)
    test = _replay(cases, scores).section("S1").test
    assert (test.cancel, test.cancel_rejected, test.cancel_accepted) == (1, 0, 1)
    assert test.precision == Fraction(0) and test.harm == Fraction(1, 4)  # one of the four accepted findings of the slice


def test_a_protected_accepted_finding_that_got_a_cancel_is_counted_and_fails_the_section_even_on_a_small_sample():
    specs = _pattern(20)
    specs[16] = Spec(ACCEPTED, True, protected=True)
    cases, scores = _build(specs)
    section = _replay(cases, scores).section("S1")
    assert section.test.protected_harm == 1
    assert section.failures == (FAIL_CASES, FAIL_PROTECTED) and not section.meets_rule
    unprotected = _pattern(20)
    unprotected[16] = Spec(ACCEPTED, True)
    cases, scores = _build(unprotected)
    assert _replay(cases, scores).section("S1").test.protected_harm == 0


def test_a_history_without_a_critic_measures_no_cancel_and_the_information_block_says_what_the_precedents_alone_would_do():
    specs = [Spec(s.verdict, s.flagged, in_plan=False) for s in _pattern(20)]
    cases, scores = _build(specs)
    section = _replay(cases, scores).section("S1")
    assert section.test.cancel == 0 and section.test_precedent_only.cancel == 1
    assert section.failures == (FAIL_CASES,)


def test_a_stop_word_in_the_finding_takes_the_cancel_away_from_the_measure():
    specs = [Spec(s.verdict, s.flagged, text="Не указана арматурой марка.") for s in _pattern(20)]
    cases, scores = _build(specs)
    plain = _replay(cases, scores).section("S1")
    stopped = _replay(cases, scores, stop_words=compile_stop_words(["арматура"])).section("S1")
    assert plain.test.cancel == 1  # no stop word listed: the flagged finding of the check slice gets its «снять»
    assert stopped.test.cancel == 0 and stopped.test_precedent_only.cancel == 1  # listed: the cancel is gone, the precedents alone still allow it


# ---- the section rule ------------------------------------------------------------------------------------------------------------------


def _m(targets, rejected, cancel, cancel_rejected, protected_harm=0) -> SliceMetrics:
    return SliceMetrics(targets, rejected, targets - rejected, cancel, cancel_rejected, cancel - cancel_rejected, protected_harm)


@pytest.mark.parametrize(
    ("metrics", "expected"),
    [
        (_m(100, 50, 30, 30), ()),
        (_m(100, 50, 29, 29), (FAIL_CASES,)),
        (_m(100, 50, 0, 0), (FAIL_CASES,)),
        # precision exactly 0.90, uplift well above, harm exactly 2 % of the 150 accepted findings
        (_m(300, 150, 30, 27), ()),
        # one accepted finding fewer: 3 of 149 is more than 2 %
        (_m(299, 150, 30, 27), (FAIL_HARM,)),
        # precision 26 / 30 is below 0.90 (harm 4 of 300 is fine)
        (_m(600, 300, 30, 26), (FAIL_PRECISION,)),
        # all three edges at once: precision 0.90, base rate 0.75, uplift exactly 0.15, harm exactly 2 %
        (_m(600, 450, 30, 27), ()),
        # the same with one more rejection in the base: the uplift is 0.1496 and nothing else changes
        (_m(601, 451, 30, 27), (FAIL_UPLIFT,)),
        # nothing was accepted: no harm to measure, and no uplift either, the base rate being 1
        (_m(100, 100, 30, 30), (FAIL_UPLIFT,)),
        (_m(600, 300, 30, 30, protected_harm=1), (FAIL_PROTECTED,)),
        (_m(100, 50, 2, 1, protected_harm=1), (FAIL_CASES, FAIL_PROTECTED)),
    ],
)
def test_the_section_rule_at_its_edges(metrics, expected):
    assert rule_failures(metrics) == expected


def test_the_rule_is_a_parameter():
    loose = SectionRule(min_cases=1, min_precision=Fraction(1, 2), min_uplift=Fraction(0), max_harm=Fraction(1))
    assert rule_failures(_m(100, 50, 2, 1), loose) == ()
    assert rule_failures(_m(100, 50, 2, 1)) == (FAIL_CASES,)


def test_a_section_with_thirty_precise_cancels_meets_the_rule_with_the_defaults_and_each_miss_names_itself():
    specs = [[Spec(REJECTED, True), Spec(REJECTED, False), Spec(ACCEPTED, False)][index % 3] for index in range(300)]
    cases, scores = _build(specs)
    section = _replay(cases, scores).section("S1")
    assert (section.fit_targets, section.test_targets, section.analogous_threshold) == (210, 90, 0.9)
    assert (section.test.cancel, section.test.precision, section.test.harm) == (30, Fraction(1), Fraction(0))
    assert section.meets_rule and section.failures == ()

    # a cancel on an accepted finding: 1 of 31 accepted findings of the slice is 3.2 %, over the 2 % of the rule
    worse = list(specs)
    worse[210] = Spec(ACCEPTED, True)
    cases, scores = _build(worse)
    section = _replay(cases, scores).section("S1")
    assert section.failures == (FAIL_HARM,)

    # a flagged finding without its vector neighbours: 29 cancels are not enough
    fewer = list(specs)
    fewer[210] = Spec(REJECTED, False)
    cases, scores = _build(fewer)
    assert _replay(cases, scores).section("S1").failures == (FAIL_CASES,)


# ---- skips, validation and the digest ----------------------------------------------------------------------------------------------


def test_what_is_not_replayed_is_counted_not_dropped_silently():
    olds = [_old(i) for i in range(6)]
    target = _target("t000", REJECTED, T0)
    withdrawn = ReplayCase(case("gone", REJECTED, active=False), "x", None, True)
    no_section = ReplayCase(case("nosec", REJECTED, section=None), "x", None, True)
    other_class = _target("test-data", REJECTED, T0, data_class="test")
    carried_only = ReplayCase(case("carried", REJECTED, origin="carried"), "x", None, True)
    no_vector = _target("t-novec", REJECTED, T0 + timedelta(hours=1))
    scores = {"t000": {**{old.case.case_id: 0.9 for old in olds}, "ghost": 0.99}, "test-data": {}, "carried": {}, "gone": {}, "nosec": {}}
    report = _replay([*olds, target, withdrawn, no_section, other_class, carried_only, no_vector], scores)
    assert dict(report.skipped) == {
        "inactive": 1,
        "no_section": 1,
        "other_data_class": 1,
        "no_vote": 1,
        "no_vector": 7,  # the six old neighbours and `t-novec` have no scores of their own
        "neighbour_scores_without_a_case": 1,
    }
    assert [section.section for section in report.sections] == ["S1"] and report.section("S1").targets == 1


@pytest.mark.parametrize("percent", [0, 100, -5])
def test_a_fit_share_outside_1_to_99_is_refused(percent):
    with pytest.raises(ValueError):
        _replay([], {}, fit_percent=percent)


def test_a_grid_value_the_thresholds_do_not_allow_and_a_repeated_case_id_are_refused():
    with pytest.raises(ValueError):
        _replay([], {}, analogous_grid=(0.7,))
    twice = _target("t000", REJECTED, T0)
    with pytest.raises(ValueError):
        _replay([twice, twice], {"t000": {}})


def test_the_digest_is_stable_and_is_the_hash_of_the_canonical_report():
    cases, scores = _build(_pattern(20), cosine=0.9)
    report = _replay(cases, scores)
    body = json.dumps(report.to_dict(), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    assert report.digest == hashlib.sha256(body.encode("utf-8")).hexdigest()
    assert len(report.digest) == 64 and report.to_dict()["schema"] == "precedent-replay/1"

    again = _replay(*_build(_pattern(20), cosine=0.9))
    assert again.digest == report.digest and again == report

    shuffled_cases = list(cases)
    random.Random(3).shuffle(shuffled_cases)
    shuffled_scores = {key: dict(reversed(list(value.items()))) for key, value in reversed(list(scores.items()))}
    assert _replay(shuffled_cases, shuffled_scores).digest == report.digest


def test_the_digest_follows_every_input_that_changes_the_report():
    cases, scores = _build(_pattern(20), cosine=0.9)
    base = _replay(cases, scores).digest
    specs = _pattern(20)
    specs[16] = Spec(ACCEPTED, True)
    assert _replay(*_build(specs, cosine=0.9)).digest != base
    assert _replay(cases, scores, rule=SectionRule(min_cases=29)).digest != base
    assert _replay(cases, scores, fit_percent=60).digest != base
    assert _replay(cases, scores, analogous_grid=(0.8,)).digest != base


def test_the_report_is_plain_json():
    cases, scores = _build(_pattern(20), cosine=0.9)
    report = _replay(cases, scores)
    assert json.loads(json.dumps(report.to_dict(), ensure_ascii=False)) == report.to_dict()
    section = report.to_dict()["sections"][0]
    assert section["test"]["precision"] == 1.0 and section["under_shown_label"]["test"] == {"decisions": 0, "rejected": 0, "accepted": 0}
