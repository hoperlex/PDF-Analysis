"""From a run's findings, its vectors and the memory to the core's answer for each finding, and what a reader is shown of it.

One function builds the core's inputs and calls :func:`auditmanager.precedents.advice.evaluate` (:func:`evaluate_run`); the pass writes its answers and the
reads of ``getRunPrecedents`` and ``getFindingPrecedents`` evaluate again when the memory has moved, so the rules that label a finding at night are the
very rules that label it when an expert opens it.

**The per-section switch** (`ADR-0029` decision 6) is applied to what is *shown* (:func:`apply_section_switch`), never to what is *counted*: the pass
stores the label the rules gave, and a reader masks it. Where the section's refusal labels are off, a label to refusal (``often_rejected``,
``cancel_suggested``, whether or not the critic reviewed the finding) is shown as ``few`` -- «nothing in the row» in the contract's own words -- with the
counts still in ``votes``, the hints that spoke of refusal (P1, and P4 when the precedents lean to cancel) are dropped, and the finding is not in the
queue. A neutral label (``likely_accepted``, ``mixed``, ``few``, ``none``) is shown always. The mark the expert is shown is the mark recorded at his
decision (``ShownAtDecision``), so a refusal that was hidden never counts against the independence of his vote.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy.orm import Session

from auditmanager.precedents.advice import STATUS_OK, PrecedentAdvice, evaluate
from auditmanager.precedents.models import (
    HINT_CRITIC_DIVERGES,
    HINT_DOCUMENT_HISTORY,
    HINT_REJECTION_REASON,
    LABEL_CANCEL_SUGGESTED,
    LABEL_FEW,
    LABEL_OFTEN_REJECTED,
    REJECTION_LABELS,
    SHOWN_NEUTRAL,
    FindingContext,
    ScoredCase,
)
from auditmanager.precedents.run_pass import reads
from auditmanager.precedents.run_pass.critic_input import candidates_from_projection, link_token
from auditmanager.precedents.run_pass.reads import PassFinding, RunFacts, VersionPlace
from auditmanager.precedents.settings import SectionLabelSwitch, section_is_on, thresholds_for
from auditmanager.precedents.similarity import Thresholds
from auditmanager.precedents.stemming import StopWordMatcher

__all__ = [
    "Evaluation", "LabelView", "WIRE_HINT_CODES", "apply_section_switch", "evaluate_run", "row_of", "view_from_advice", "view_from_stored",
    "votes_of",
]

#: The core's hint codes (Cyrillic, the plan's) and the contract's (``PrecedentHintCode``: ``p1``, ``p4``, ``p5``).
WIRE_HINT_CODES: Final[Mapping[str, str]] = {HINT_REJECTION_REASON: "p1", HINT_CRITIC_DIVERGES: "p4", HINT_DOCUMENT_HISTORY: "p5"}
_VOTE_KEYS: Final[tuple[str, ...]] = ("total", "rejected", "accepted", "independent", "projects")


@dataclass(frozen=True, slots=True)
class Evaluation:
    """The core's answer for one finding, with the critic's projection it was made with and the neighbours it was made from (for the card)."""

    finding: PassFinding
    advice: PrecedentAdvice
    projection: Mapping[str, Any]
    scored: tuple[ScoredCase, ...]


@dataclass(frozen=True, slots=True)
class LabelView:
    """What a reader is shown of one finding: the contract's ``PrecedentFindingLabel`` without its revision.

    ``masked`` is true when a label to refusal was hidden because the section's switch is off. ``shown_code`` is the word to record as the mark in force
    at a decision (``decision_memory_decision.precedent_label_at_decision``): ``few`` for a masked label, ``neutral`` for a label to refusal shown without
    its push (the critic did not review the finding), else the label itself."""

    label: str
    critic_reviewed: bool
    votes: Mapping[str, int]
    hint_codes: tuple[str, ...]
    masked: bool
    shown_code: str

    @property
    def in_queue(self) -> bool:
        return self.label == LABEL_CANCEL_SUGGESTED


def votes_of(advice: PrecedentAdvice) -> dict[str, int]:
    """The five counts of the contract's ``PrecedentVotes`` from the core's vote set: every counted vote, how many of each verdict, how many independent,
    from how many projects."""
    assert advice.vote_set is not None and advice.label is not None
    votes = advice.vote_set.votes
    return {
        "total": advice.label.votes_total, "rejected": advice.label.votes_rejected, "accepted": advice.label.votes_accepted,
        "independent": advice.label.independent_total, "projects": len({vote.project_uid for vote in votes}),
    }


def row_of(evaluation: Evaluation) -> dict[str, Any]:
    """The row the pass stores for an evaluated finding: the label the rules gave (not masked), the counts and the critic's projection in ``votes``."""
    advice = evaluation.advice
    assert advice.label is not None and advice.review is not None
    return {
        "finding_uid": evaluation.finding.finding_uid,
        "label": advice.label.code,
        "critic_reviewed": advice.review.reviewed,
        "votes": {**votes_of(advice), "critic": dict(evaluation.projection)},
        "hint_codes": [WIRE_HINT_CODES[hint.code] for hint in advice.hints],
    }


def _shown_code(label: str, critic_reviewed: bool, masked: bool) -> str:
    if masked:
        return LABEL_FEW
    if label == LABEL_OFTEN_REJECTED and not critic_reviewed:
        return SHOWN_NEUTRAL
    return label


def apply_section_switch(label: str, critic_reviewed: bool, hint_codes: Sequence[str], *, section_on: bool) -> tuple[str, tuple[str, ...], bool]:
    """``(label, hint codes, masked)`` as shown. With the section's refusal labels off, a label to refusal becomes ``few`` and the hints that spoke
    of refusal go; the one hint that may remain is P5 (a neutral fact of the document's history), and P4 beside a label to acceptance."""
    if section_on or label not in REJECTION_LABELS:
        return label, tuple(hint_codes), False
    return LABEL_FEW, tuple(code for code in hint_codes if code == "p5"), True


def view_from_advice(advice: PrecedentAdvice, *, section_on: bool) -> LabelView:
    assert advice.status == STATUS_OK and advice.label is not None and advice.review is not None
    codes = tuple(WIRE_HINT_CODES[hint.code] for hint in advice.hints)
    label, hints, masked = apply_section_switch(advice.label.code, advice.review.reviewed, codes, section_on=section_on)
    return LabelView(label, advice.review.reviewed, votes_of(advice), hints, masked, _shown_code(advice.label.code, advice.review.reviewed, masked))


def view_from_stored(label: str, critic_reviewed: bool, votes: Mapping[str, Any], hint_codes: Sequence[str], *, section_on: bool) -> LabelView:
    shown, hints, masked = apply_section_switch(label, critic_reviewed, hint_codes, section_on=section_on)
    return LabelView(shown, critic_reviewed, {key: int(votes[key]) for key in _VOTE_KEYS}, hints, masked, _shown_code(label, critic_reviewed, masked))


def effective_thresholds(base: Thresholds, section: str | None, switches: Mapping[str, SectionLabelSwitch]) -> tuple[Thresholds, bool]:
    """``(the thresholds this section's labels are computed at, whether its refusal labels are on)``. A section that is on and has a tuned
    analogous threshold is computed at it; one whose tuned value does not stand beside the installation's other two is not on at all."""
    switch = None if section is None else switches.get(section)
    on = section_is_on(base, switch)
    return (thresholds_for(base, switch) if on else base), on


def evaluate_run(
    session: Session,
    *,
    run: RunFacts,
    place: VersionPlace,
    findings: Sequence[PassFinding],
    projections: Mapping[str, Mapping[str, Any]],
    now: datetime,
    thresholds: Thresholds,
    stop_words: StopWordMatcher,
    only: Sequence[str] | None = None,
) -> dict[str, Evaluation]:
    """The core's answer for every finding of the run that has a vector (``only`` narrows it to some). A finding with no vector is **not in the result**:
    its answer is «Недоступно», and nothing here looks for a case by any other means.

    ``thresholds`` are the ones to evaluate at (:func:`effective_thresholds` chose them). ``projections`` is the critic's part per finding
    (``critic_input.critic_projection``): the pass makes it from the saved extended review, a read takes it from the stored advice. A finding of a
    run whose version has no section is evaluated against no cases: a case of no section does not vote, and neither does a finding of none."""
    data_class = reads.data_class(session)
    wanted = {finding.finding_uid: finding for finding in findings if only is None or finding.finding_uid in only}
    if place.section is None:
        scanned = {uid: [] for uid, probe in reads.probe_rows(session, run.run_id).items() if probe.state == "done" and uid in wanted}
    else:
        scanned = reads.neighbours(
            session, run_id=run.run_id, section=place.section, data_class_=data_class, floor=thresholds.similar, only=None if only is None else list(only))
    cases = reads.load_cases(session, {case_id for rows in scanned.values() for case_id, _ in rows})
    results: dict[str, Evaluation] = {}
    for uid, neighbour_rows in scanned.items():
        finding = wanted.get(uid)
        if finding is None:
            continue
        scored = tuple(ScoredCase(cases[case_id], cosine) for case_id, cosine in neighbour_rows if case_id in cases)
        projection = dict(projections.get(uid) or {})
        in_plan, candidates = candidates_from_projection(projection, uid)
        context = FindingContext(
            finding_uid=uid, section=place.section, data_class=data_class, run_id=run.run_id, document_uid=place.document_uid,
            version_uid=run.version_uid, finding_text=finding.finding_text, recommendation_text=finding.recommendation_text,
            primary_source_id=link_token(uid), extended_observation_ref=None)
        advice = evaluate(
            context, scored, candidates, now=now, critic_in_plan=in_plan, stop_words=stop_words, thresholds=thresholds)
        results[uid] = Evaluation(finding, advice, projection, scored)
    return results
