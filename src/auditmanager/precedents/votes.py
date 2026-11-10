"""Who votes (`plan-v5` 2.1): the corpus rules and the independence of a vote.

A case gives one vote: its last non-carried ``accepted`` / ``rejected`` verdict taken as of a moment. The moment is the read time in
production and the run's end in the history replay, so a decision "from the future" is ignored by the same rule in both.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from auditmanager.precedents.models import (
    ORIGIN_CARRIED,
    ORIGIN_IMPORTED,
    REJECTION_LABELS,
    VERDICT_REJECTED,
    VOTING_VERDICTS,
    DecisionEvent,
    FindingContext,
    PrecedentCase,
    ScoredCase,
    require_aware,
)
from auditmanager.precedents.similarity import BAND_ANALOGOUS, Thresholds, band

#: A decision older than this many months no longer votes.
WINDOW_MONTHS: Final[int] = 24
#: At most this many votes come from one version of one document.
MAX_VOTES_PER_VERSION: Final[int] = 2

EXCLUDED_INACTIVE: Final[str] = "inactive"
EXCLUDED_NO_SECTION: Final[str] = "no_section"
EXCLUDED_OTHER_SECTION: Final[str] = "other_section"
EXCLUDED_OTHER_DATA_CLASS: Final[str] = "other_data_class"
EXCLUDED_BELOW_ANALOGOUS: Final[str] = "below_analogous"
EXCLUDED_NO_VOTE: Final[str] = "no_vote"
EXCLUDED_OUTSIDE_WINDOW: Final[str] = "outside_window"
EXCLUDED_SAME_RUN: Final[str] = "same_run"
EXCLUDED_VERSION_CAP: Final[str] = "version_cap"


def months_before(moment: datetime, months: int) -> datetime:
    """``moment`` shifted back by whole calendar months, the day clamped to the target month's length."""
    require_aware(moment, "moment")
    total = moment.year * 12 + (moment.month - 1) - months
    year, month_index = divmod(total, 12)
    month = month_index + 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


def case_vote(case: PrecedentCase, as_of: datetime) -> DecisionEvent | None:
    """The event that is the case's vote as of ``as_of``, or ``None`` when it has no vote.

    Events after ``as_of`` do not exist for the caller. Of the rest, only ``accepted`` / ``rejected`` events that are not ``carried`` are
    candidates (a carried decision is not an independent judgement, `DECISION-MEMORY-01` 3.7), and the latest of them is the vote; a
    comment event never reaches here because it carries no verdict. Equal moments keep the later-listed event.
    """
    require_aware(as_of, "as_of")
    chosen: DecisionEvent | None = None
    for event in case.decisions:
        if event.decided_at > as_of or event.verdict not in VOTING_VERDICTS or event.origin_kind == ORIGIN_CARRIED:
            continue
        if chosen is None or event.decided_at >= chosen.decided_at:
            chosen = event
    return chosen


def is_independent(event: DecisionEvent) -> bool:
    """A vote is independent unless the expert decided under a shown rejection label or a shown rejection fact of hint P5.

    A decision imported from a workbook was taken with no label ever shown, so it is independent by construction.
    """
    if event.origin_kind == ORIGIN_IMPORTED:
        return True
    if event.label_at_decision in REJECTION_LABELS:
        return False
    return event.history_verdict_shown != VERDICT_REJECTED


@dataclass(frozen=True, slots=True)
class Vote:
    """One counted vote: a case's verdict with the facts the label, the hints and the replay read."""

    case_id: str
    verdict: str
    decided_at: datetime
    cosine: float
    project_uid: str
    document_uid: str
    version_uid: str
    origin_kind: str
    independent: bool
    case: PrecedentCase

    @property
    def rejected(self) -> bool:
        return self.verdict == VERDICT_REJECTED


@dataclass(frozen=True, slots=True)
class VoteSet:
    """The counted votes in ascending order of (decision time, case id), and why every other scored case did not vote."""

    votes: tuple[Vote, ...]
    excluded: tuple[tuple[str, int], ...]

    def excluded_count(self, reason: str) -> int:
        return dict(self.excluded).get(reason, 0)

    @property
    def latest(self) -> Vote | None:
        return self.votes[-1] if self.votes else None


_EXCLUSION_ORDER: Final[tuple[str, ...]] = (
    EXCLUDED_INACTIVE,
    EXCLUDED_NO_SECTION,
    EXCLUDED_OTHER_SECTION,
    EXCLUDED_OTHER_DATA_CLASS,
    EXCLUDED_BELOW_ANALOGOUS,
    EXCLUDED_NO_VOTE,
    EXCLUDED_OUTSIDE_WINDOW,
    EXCLUDED_SAME_RUN,
    EXCLUDED_VERSION_CAP,
)


def select_votes(
    finding: FindingContext,
    scored: tuple[ScoredCase, ...] | list[ScoredCase],
    *,
    as_of: datetime,
    thresholds: Thresholds,
    window_months: int = WINDOW_MONTHS,
    max_votes_per_version: int = MAX_VOTES_PER_VERSION,
) -> VoteSet:
    """Apply the corpus rules of `plan-v5` 2.1 to the scored cases of one finding.

    A case votes when it is active, has a section equal to the finding's, shares the finding's ``data_class``, is analogous (cosine at or
    above the threshold), has a vote as of ``as_of`` inside the window, and is not from the finding's own run. Of the votes from one
    version of one document the ``max_votes_per_version`` most similar stay (a tie goes to the smaller case id).
    """
    window_start = months_before(as_of, window_months)
    counters: dict[str, int] = {}

    def skip(reason: str) -> None:
        counters[reason] = counters.get(reason, 0) + 1

    eligible: list[Vote] = []
    for item in scored:
        case = item.case
        if not case.active:
            skip(EXCLUDED_INACTIVE)
        elif case.section is None or finding.section is None:
            skip(EXCLUDED_NO_SECTION)
        elif case.section != finding.section:
            skip(EXCLUDED_OTHER_SECTION)
        elif case.data_class != finding.data_class:
            skip(EXCLUDED_OTHER_DATA_CLASS)
        elif band(item.cosine, thresholds) != BAND_ANALOGOUS:
            skip(EXCLUDED_BELOW_ANALOGOUS)
        else:
            event = case_vote(case, as_of)
            if event is None or event.verdict is None:
                skip(EXCLUDED_NO_VOTE)
            elif event.decided_at < window_start:
                skip(EXCLUDED_OUTSIDE_WINDOW)
            elif case.run_id == finding.run_id:
                skip(EXCLUDED_SAME_RUN)
            else:
                eligible.append(
                    Vote(
                        case_id=case.case_id,
                        verdict=event.verdict,
                        decided_at=event.decided_at,
                        cosine=item.cosine,
                        project_uid=case.project_uid,
                        document_uid=case.document_uid,
                        version_uid=case.version_uid,
                        origin_kind=event.origin_kind,
                        independent=is_independent(event),
                        case=case,
                    )
                )

    by_version: dict[str, list[Vote]] = {}
    for vote in eligible:
        by_version.setdefault(vote.version_uid, []).append(vote)
    kept: list[Vote] = []
    for group in by_version.values():
        group.sort(key=lambda vote: (-vote.cosine, vote.case_id))
        kept.extend(group[:max_votes_per_version])
        for _ in group[max_votes_per_version:]:
            skip(EXCLUDED_VERSION_CAP)

    kept.sort(key=lambda vote: (vote.decided_at, vote.case_id))
    excluded = tuple((reason, counters[reason]) for reason in _EXCLUSION_ORDER if reason in counters)
    return VoteSet(votes=tuple(kept), excluded=excluded)
