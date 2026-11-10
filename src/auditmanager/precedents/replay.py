"""The history replay (`plan-v5` 2.6, CRIT-REPLAY-01): where the per-section threshold of the cancel labels comes from.

This is a product tool, not a measurement: it replays the decisions the memory already holds through the rules that run in production
(:func:`auditmanager.precedents.advice.evaluate`) and says, per section, how good «снять» would have been. Synthetic data only proves that
the tool works; the administrator enables the cancel labels of a section from a report on real data.

For every replayed case (a *target*):

* **The time cut.** The moment is the end of the case's run, or, when the run was erased, the case's earliest decision. Every decision after
  the moment is invisible to the evaluation, the target's own and every neighbour's, so nothing "from the future" reaches a label.
* **Same-run votes** are excluded by the core's corpus rule, with the target's run.
* **The 70 / 30 split.** The targets of a section are ordered by the time of their decision; the earlier 70 % *fit* (the analogous cosine
  threshold is chosen from a small grid), the later 30 % *check* (the report). Equal moments never straddle the boundary: they go to the check.
* **Decisions under a shown rejection label** (the expert decided while «Обычно отклоняют» or «Рекомендуется снять» was in force, or after a
  shown rejection fact) are not independent. They stay out of the precision, the base rate and the harm, and are reported on their own.
* **The report** per section: the base rejection rate, the uplift of «снять» over it, the precision of «снять», and the harm (the share of
  accepted findings that received «снять»), with the section rule applied to the check slice.
* **The section rule:** precision >= 0.90 on >= 30 cancel cases, uplift >= 0.15, harm <= 2 %, and no «снять» on a protected finding that was
  accepted. «Protected» is the caller's flag per case: the core knows no such class (the AR v3 notion is gone with R-154).

The cancel measured is the cancel the product would show: a finding the critic did not review never gets one (V3), so a history with no
critic records measures nothing, and the report says so by its zero count. ``test_precedent_only`` repeats the check slice with the critic
and stop-word gates off, for information only; it never enables a section.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from fractions import Fraction
from typing import Final

from auditmanager.precedents.advice import evaluate
from auditmanager.precedents.labels import LabelPolicy
from auditmanager.precedents.models import (
    LABEL_CANCEL_SUGGESTED,
    VERDICT_REJECTED,
    CriticCandidate,
    DecisionEvent,
    FindingContext,
    PrecedentCase,
    ScoredCase,
)
from auditmanager.precedents.similarity import Thresholds
from auditmanager.precedents.stemming import StopWordMatcher
from auditmanager.precedents.votes import case_vote, is_independent

REPORT_SCHEMA: Final[str] = "precedent-replay/1"
FIT_PERCENT: Final[int] = 70
#: The analogous-cosine values tried on the fit slice. The default (0.85) is always tried as well.
DEFAULT_ANALOGOUS_GRID: Final[tuple[float, ...]] = (0.80, 0.85, 0.90)

SKIPPED_INACTIVE: Final[str] = "inactive"
SKIPPED_NO_SECTION: Final[str] = "no_section"
SKIPPED_OTHER_DATA_CLASS: Final[str] = "other_data_class"
SKIPPED_NO_VOTE: Final[str] = "no_vote"
SKIPPED_NO_VECTOR: Final[str] = "no_vector"
UNKNOWN_NEIGHBOURS: Final[str] = "neighbour_scores_without_a_case"

FIT_SELECTED: Final[str] = "selected"
FIT_NONE_QUALIFIED: Final[str] = "none_qualified"

FAIL_CASES: Final[str] = "cancel_cases_below_minimum"
FAIL_PRECISION: Final[str] = "precision_below_minimum"
FAIL_UPLIFT: Final[str] = "uplift_below_minimum"
FAIL_HARM: Final[str] = "harm_above_maximum"
FAIL_PROTECTED: Final[str] = "protected_finding_cancelled"

_FAR_FUTURE: Final[datetime] = datetime.max.replace(tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class SectionRule:
    """The admission rule of a section (`plan-v5` 2.6). Fractions, so no float edge decides a section."""

    min_precision: Fraction = Fraction(9, 10)
    min_cases: int = 30
    min_uplift: Fraction = Fraction(15, 100)
    max_harm: Fraction = Fraction(2, 100)
    max_protected_harm: int = 0


@dataclass(frozen=True, slots=True)
class ReplayCase:
    """One memory case as the replay reads it: the case, the finding's text and run facts, the critic's candidates for its run.

    ``run_finished_at`` is ``None`` when the run is erased. ``critic_in_plan`` is whether that run's plan had a critic. ``protected`` is the
    caller's flag for a finding that must never get «снять» wrongly.
    """

    case: PrecedentCase
    finding_text: str
    run_finished_at: datetime | None
    critic_in_plan: bool
    recommendation_text: str = ""
    primary_source_id: str | None = None
    extended_observation_ref: str | None = None
    candidates: tuple[CriticCandidate, ...] = ()
    protected: bool = False


def _ratio(numerator: int, denominator: int) -> Fraction | None:
    return Fraction(numerator, denominator) if denominator else None


def _rounded(value: Fraction | None) -> float | None:
    return None if value is None else round(float(value), 6)


@dataclass(frozen=True, slots=True)
class SliceMetrics:
    """The quality of «снять» over the independent decisions of one slice."""

    targets: int
    rejected: int
    accepted: int
    cancel: int
    cancel_rejected: int
    cancel_accepted: int
    protected_harm: int

    @property
    def base_reject_rate(self) -> Fraction | None:
        return _ratio(self.rejected, self.targets)

    @property
    def precision(self) -> Fraction | None:
        return _ratio(self.cancel_rejected, self.cancel)

    @property
    def uplift(self) -> Fraction | None:
        base, precision = self.base_reject_rate, self.precision
        return None if base is None or precision is None else precision - base

    @property
    def harm(self) -> Fraction | None:
        """The share of accepted findings that received «снять» (``None`` when nothing was accepted)."""
        return _ratio(self.cancel_accepted, self.accepted)

    def to_dict(self) -> dict[str, object]:
        return {
            "targets": self.targets,
            "rejected": self.rejected,
            "accepted": self.accepted,
            "base_reject_rate": _rounded(self.base_reject_rate),
            "cancel": self.cancel,
            "cancel_rejected": self.cancel_rejected,
            "cancel_accepted": self.cancel_accepted,
            "precision": _rounded(self.precision),
            "uplift": _rounded(self.uplift),
            "harm": _rounded(self.harm),
            "protected_harm": self.protected_harm,
        }


@dataclass(frozen=True, slots=True)
class ShownLabelCounts:
    """Decisions taken under a shown rejection label: reported on their own, outside every rate."""

    decisions: int
    rejected: int
    accepted: int

    def to_dict(self) -> dict[str, int]:
        return {"decisions": self.decisions, "rejected": self.rejected, "accepted": self.accepted}


def rule_failures(metrics: SliceMetrics, rule: SectionRule = SectionRule()) -> tuple[str, ...]:
    """What the check slice fails of the section rule; empty means the section may enable the cancel labels.

    Below the minimum number of cancel cases no rate is judged (a handful of cases proves nothing), but a cancel of a protected finding is
    never excused by a small sample.
    """
    protected = (FAIL_PROTECTED,) if metrics.protected_harm > rule.max_protected_harm else ()
    if metrics.cancel < rule.min_cases:
        return (FAIL_CASES, *protected)
    failures: list[str] = []
    precision, uplift, harm = metrics.precision, metrics.uplift, metrics.harm
    if precision is None or precision < rule.min_precision:
        failures.append(FAIL_PRECISION)
    if uplift is None or uplift < rule.min_uplift:
        failures.append(FAIL_UPLIFT)
    if harm is not None and harm > rule.max_harm:
        failures.append(FAIL_HARM)
    return (*failures, *protected)


def _qualifies_on_fit(metrics: SliceMetrics, rule: SectionRule) -> bool:
    """The fit slice asks of a threshold what the rule asks of the section, except the size: a 70 % slice is not asked for 30 cases."""
    if metrics.cancel < 1:
        return False
    relaxed = SectionRule(rule.min_precision, 1, rule.min_uplift, rule.max_harm, rule.max_protected_harm)
    return not rule_failures(metrics, relaxed)


@dataclass(frozen=True, slots=True)
class SectionReport:
    section: str
    targets: int
    fit_targets: int
    test_targets: int
    fit_selection: str
    analogous_threshold: float
    fit_grid: tuple[tuple[float, SliceMetrics], ...]
    test: SliceMetrics
    test_precedent_only: SliceMetrics
    shown_label_fit: ShownLabelCounts
    shown_label_test: ShownLabelCounts
    failures: tuple[str, ...]

    @property
    def meets_rule(self) -> bool:
        return not self.failures

    def to_dict(self) -> dict[str, object]:
        return {
            "section": self.section,
            "targets": self.targets,
            "fit_targets": self.fit_targets,
            "test_targets": self.test_targets,
            "fit_selection": self.fit_selection,
            "analogous_threshold": self.analogous_threshold,
            "fit_grid": [{"analogous_threshold": value, **metrics.to_dict()} for value, metrics in self.fit_grid],
            "test": self.test.to_dict(),
            "test_precedent_only": self.test_precedent_only.to_dict(),
            "under_shown_label": {"fit": self.shown_label_fit.to_dict(), "test": self.shown_label_test.to_dict()},
            "meets_rule": self.meets_rule,
            "failures": list(self.failures),
        }


@dataclass(frozen=True, slots=True)
class ReplayReport:
    data_class: str
    fit_percent: int
    default_analogous: float
    rule: SectionRule
    sections: tuple[SectionReport, ...]
    skipped: tuple[tuple[str, int], ...]

    def section(self, name: str) -> SectionReport:
        for report in self.sections:
            if report.section == name:
                return report
        raise KeyError(name)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": REPORT_SCHEMA,
            "data_class": self.data_class,
            "fit_percent": self.fit_percent,
            "default_analogous": self.default_analogous,
            "rule": {
                "min_precision": str(self.rule.min_precision),
                "min_cases": self.rule.min_cases,
                "min_uplift": str(self.rule.min_uplift),
                "max_harm": str(self.rule.max_harm),
                "max_protected_harm": self.rule.max_protected_harm,
            },
            "sections": [section.to_dict() for section in self.sections],
            "skipped": dict(self.skipped),
        }

    @property
    def digest(self) -> str:
        """sha256 of the canonical JSON of :meth:`to_dict`: what ``precedent_setting_event`` records when a section is enabled from this report."""
        body = json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(body.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class _Target:
    replay: ReplayCase
    vote: DecisionEvent
    cut: datetime
    independent: bool

    @property
    def case_id(self) -> str:
        return self.replay.case.case_id


def _cut_time(replay: ReplayCase) -> datetime:
    """The end of the case's run, or its earliest decision when the run is erased (a case with a vote has at least one decision)."""
    if replay.run_finished_at is not None:
        return replay.run_finished_at
    return min(event.decided_at for event in replay.case.decisions)


def _finding_of(replay: ReplayCase) -> FindingContext:
    case = replay.case
    return FindingContext(
        finding_uid=case.case_id,
        section=case.section,
        data_class=case.data_class,
        run_id=case.run_id,
        document_uid=case.document_uid,
        version_uid=case.version_uid,
        finding_text=replay.finding_text,
        recommendation_text=replay.recommendation_text,
        primary_source_id=replay.primary_source_id,
        extended_observation_ref=replay.extended_observation_ref,
    )


def _metrics(targets: Sequence[_Target], flags: Mapping[str, bool]) -> SliceMetrics:
    rejected = accepted = cancel = cancel_rejected = cancel_accepted = protected_harm = 0
    for target in targets:
        if not target.independent:
            continue
        is_rejected = target.vote.verdict == VERDICT_REJECTED
        rejected += 1 if is_rejected else 0
        accepted += 0 if is_rejected else 1
        if flags[target.case_id]:
            cancel += 1
            cancel_rejected += 1 if is_rejected else 0
            cancel_accepted += 0 if is_rejected else 1
            protected_harm += 1 if (not is_rejected and target.replay.protected) else 0
    return SliceMetrics(rejected + accepted, rejected, accepted, cancel, cancel_rejected, cancel_accepted, protected_harm)


def _shown(targets: Sequence[_Target]) -> ShownLabelCounts:
    dependent = [target for target in targets if not target.independent]
    rejected = sum(1 for target in dependent if target.vote.verdict == VERDICT_REJECTED)
    return ShownLabelCounts(len(dependent), rejected, len(dependent) - rejected)


def _split(targets: list[_Target], fit_percent: int) -> tuple[list[_Target], list[_Target]]:
    """The earlier ``fit_percent`` % by decision time to fit, the rest to check; equal moments never straddle the boundary."""
    ordered = sorted(targets, key=lambda target: (target.vote.decided_at, target.case_id))
    fit_count = len(ordered) * fit_percent // 100
    if fit_count >= len(ordered):
        return ordered, []
    boundary = ordered[fit_count].vote.decided_at
    fit = [target for target in ordered if target.vote.decided_at < boundary]
    test = [target for target in ordered if target.vote.decided_at >= boundary]
    return fit, test


def replay_history(
    cases: Sequence[ReplayCase],
    scores: Mapping[str, Mapping[str, float]],
    *,
    data_class: str,
    stop_words: StopWordMatcher = StopWordMatcher(),
    thresholds: Thresholds = Thresholds(),
    policy: LabelPolicy = LabelPolicy(),
    fit_percent: int = FIT_PERCENT,
    analogous_grid: Sequence[float] = DEFAULT_ANALOGOUS_GRID,
    rule: SectionRule = SectionRule(),
) -> ReplayReport:
    """Replay the decisions of ``data_class`` and report, per section, how «снять» would have done.

    ``scores[case_id]`` maps the case to the cosine against each other case that has a vector (``{}`` is a case with a vector and no
    neighbour); a case missing from ``scores`` has no vector and is skipped, and counted. A cosine for an id that is not in ``cases`` is
    ignored and counted.
    """
    if not 1 <= fit_percent <= 99:
        raise ValueError("fit_percent must be between 1 and 99")
    grid = sorted({*analogous_grid, thresholds.analogous})
    grid_thresholds = {
        value: Thresholds(analogous=value, similar=thresholds.similar, history=thresholds.history) for value in grid
    }  # validates every value before any work is done
    by_id = {replay.case.case_id: replay for replay in cases}
    if len(by_id) != len(cases):
        raise ValueError("a case id appears twice among the replayed cases")

    skipped: dict[str, int] = {}

    def skip(reason: str) -> None:
        skipped[reason] = skipped.get(reason, 0) + 1

    targets_by_section: dict[str, list[_Target]] = {}
    for replay in cases:
        case = replay.case
        if not case.active:
            skip(SKIPPED_INACTIVE)
        elif case.section is None:
            skip(SKIPPED_NO_SECTION)
        elif case.data_class != data_class:
            skip(SKIPPED_OTHER_DATA_CLASS)
        else:
            vote = case_vote(case, _FAR_FUTURE)
            if vote is None:
                skip(SKIPPED_NO_VOTE)
            elif case.case_id not in scores:
                skip(SKIPPED_NO_VECTOR)
            else:
                targets_by_section.setdefault(case.section, []).append(_Target(replay, vote, _cut_time(replay), is_independent(vote)))

    # the label of every target at every threshold of the grid: (the cancel the product shows, the cancel the precedents alone allow)
    outcomes: dict[tuple[str, float], tuple[bool, bool]] = {}
    for section_targets in targets_by_section.values():
        for target in section_targets:
            neighbours: list[ScoredCase] = []
            for other_id, cosine in scores[target.case_id].items():
                other = by_id.get(other_id)
                if other is None:
                    skip(UNKNOWN_NEIGHBOURS)
                elif other_id != target.case_id:
                    neighbours.append(ScoredCase(other.case, cosine))
            finding = _finding_of(target.replay)
            for value in grid:
                advice = evaluate(
                    finding,
                    neighbours,
                    target.replay.candidates,
                    now=target.cut,
                    critic_in_plan=target.replay.critic_in_plan,
                    stop_words=stop_words,
                    thresholds=grid_thresholds[value],
                    policy=policy,
                )
                if advice.label is None:
                    raise RuntimeError("a replayed case with a vector got no label")
                outcomes[(target.case_id, value)] = (advice.label.code == LABEL_CANCEL_SUGGESTED, advice.label.cancel_eligible_by_precedent)

    sections: list[SectionReport] = []
    for name in sorted(targets_by_section):
        fit, test = _split(targets_by_section[name], fit_percent)
        fit_grid = tuple((value, _metrics(fit, {t.case_id: outcomes[(t.case_id, value)][0] for t in fit})) for value in grid)
        qualifying = [(metrics.cancel, value) for value, metrics in fit_grid if _qualifies_on_fit(metrics, rule)]
        if qualifying:
            chosen, selection = max(qualifying)[1], FIT_SELECTED
        else:
            chosen, selection = thresholds.analogous, FIT_NONE_QUALIFIED
        gated = _metrics(test, {t.case_id: outcomes[(t.case_id, chosen)][0] for t in test})
        precedent_only = _metrics(test, {t.case_id: outcomes[(t.case_id, chosen)][1] for t in test})
        sections.append(
            SectionReport(
                section=name,
                targets=len(fit) + len(test),
                fit_targets=len(fit),
                test_targets=len(test),
                fit_selection=selection,
                analogous_threshold=chosen,
                fit_grid=fit_grid,
                test=gated,
                test_precedent_only=precedent_only,
                shown_label_fit=_shown(fit),
                shown_label_test=_shown(test),
                failures=rule_failures(gated, rule),
            )
        )
    return ReplayReport(
        data_class=data_class,
        fit_percent=fit_percent,
        default_analogous=thresholds.analogous,
        rule=rule,
        sections=tuple(sections),
        skipped=tuple(sorted(skipped.items())),
    )
