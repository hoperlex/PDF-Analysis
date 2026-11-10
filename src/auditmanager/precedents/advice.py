"""The advice for one finding: votes, label, critic review, stop words and hints, from plain inputs.

This is the one entry point of the core, and the one the history replay calls once per replayed finding, so the replay measures the rules
that run in production. Without a vector the status is ``unavailable`` and nothing else is computed: there is no lexical path and no
fallback (`plan-v5` 2.2, K6).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from auditmanager.precedents.critic import CriticReview, review_of
from auditmanager.precedents.hints import Hint, build_hints
from auditmanager.precedents.labels import LabelPolicy, PrecedentLabel, compute_label
from auditmanager.precedents.models import CriticCandidate, FindingContext, ScoredCase, require_aware
from auditmanager.precedents.similarity import Thresholds
from auditmanager.precedents.stemming import StopWordMatcher
from auditmanager.precedents.votes import VoteSet, select_votes

STATUS_OK: Final[str] = "ok"
STATUS_UNAVAILABLE: Final[str] = "unavailable"
UNAVAILABLE_NO_VECTOR: Final[str] = "no_vector"

_NO_STOP_WORDS: Final[StopWordMatcher] = StopWordMatcher()


@dataclass(frozen=True, slots=True)
class PrecedentAdvice:
    """What the core says about one finding. When ``status`` is ``unavailable`` the label, votes and hints are empty."""

    status: str
    unavailable_reason: str | None
    label: PrecedentLabel | None
    vote_set: VoteSet | None
    review: CriticReview | None
    stop_words_found: tuple[str, ...]
    hints: tuple[Hint, ...]


def evaluate(
    finding: FindingContext,
    scored: Sequence[ScoredCase] | None,
    candidates: Sequence[CriticCandidate] = (),
    *,
    now: datetime,
    critic_in_plan: bool,
    stop_words: StopWordMatcher = _NO_STOP_WORDS,
    thresholds: Thresholds = Thresholds(),
    policy: LabelPolicy = LabelPolicy(),
) -> PrecedentAdvice:
    """Advise on ``finding``.

    ``scored`` is every case of the installation that has a vector, with its precomputed cosine against the finding's vector, or ``None``
    when the finding has no vector (the status is then ``unavailable``). ``candidates`` are the critic's candidates of the finding's run.
    ``now`` is the read time (production) or the run's end (replay); it bounds the decisions that exist and starts the 24-month window.
    ``critic_in_plan`` says whether the run's plan has a critic at all; the caller decides it and the core never derives it from a plan
    version. It has no default on purpose: a caller that does not know must say so. With ``False`` no finding of the run counts as
    reviewed (V3).
    """
    require_aware(now, "now")
    if scored is None:
        return PrecedentAdvice(
            status=STATUS_UNAVAILABLE,
            unavailable_reason=UNAVAILABLE_NO_VECTOR,
            label=None,
            vote_set=None,
            review=None,
            stop_words_found=(),
            hints=(),
        )
    vote_set = select_votes(finding, list(scored), as_of=now, thresholds=thresholds)
    review = review_of(finding, candidates, critic_in_plan=critic_in_plan)
    found = stop_words.matches(finding.finding_text, finding.recommendation_text)
    label = compute_label(vote_set, review, found, policy)
    hints = build_hints(finding, vote_set, label, review, as_of=now, thresholds=thresholds)
    return PrecedentAdvice(
        status=STATUS_OK,
        unavailable_reason=None,
        label=label,
        vote_set=vote_set,
        review=review,
        stop_words_found=found,
        hints=hints,
    )
