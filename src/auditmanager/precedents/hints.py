"""The hints of `plan-v5` 2.5 that remain after R-154: P1, P4 and P5, at most two per finding, with no model text in them.

P2 (importance) and P3 (norm) were rules of AR v3 only, and AR v3 is removed, so they are not built. The order below is the plan's table
order, and it is the priority when all three apply: the cap of two drops the last.

* P1, the reason for the rejections: only while the label is a rejection label shown with its push (not neutral). Its text is the comment
  of a rejecting voice, the most similar one that has a comment (a later approved pattern text will replace it).
* P4, the critic diverges: the critic reviewed the finding, it has exactly one linked candidate, and the critic's advice contradicts the precedents.
  The precedents lean to cancel (judged before the critic's veto, which would otherwise make the case impossible) and the critic says
  ``accept``, or the label is ``likely_accepted`` and the critic says ``reject``.
* P5, the document's history: a counted vote from another version of the same document with cosine at or above the history threshold. It
  is a neutral fact; a rejection shown by it takes the independence from the decision that follows (:func:`votes.is_independent`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

from auditmanager.precedents.critic import CriticReview
from auditmanager.precedents.labels import PrecedentLabel
from auditmanager.precedents.models import (
    CRITIC_ACCEPT,
    CRITIC_REJECT,
    HINT_CRITIC_DIVERGES,
    HINT_DOCUMENT_HISTORY,
    HINT_REJECTION_REASON,
    LABEL_LIKELY_ACCEPTED,
    REJECTION_LABELS,
    FindingContext,
)
from auditmanager.precedents.similarity import Thresholds
from auditmanager.precedents.votes import Vote, VoteSet

MAX_HINTS_PER_FINDING: Final[int] = 2
#: A comment longer than this is cut, with an ellipsis, so a hint stays a line.
MAX_HINT_TEXT: Final[int] = 300


@dataclass(frozen=True, slots=True)
class Hint:
    """One hint. ``code`` is P1, P4 or P5; the other fields are the facts it points at (never a model's wording)."""

    code: str
    case_id: str | None = None
    verdict: str | None = None
    cosine: float | None = None
    text: str | None = None
    critic_decision: str | None = None


def _clip(text: str) -> str:
    return text if len(text) <= MAX_HINT_TEXT else text[: MAX_HINT_TEXT - 1].rstrip() + "…"


def _rejection_reason(vote_set: VoteSet, as_of: datetime) -> Hint | None:
    commented: list[tuple[Vote, str]] = []
    for vote in vote_set.votes:
        if not vote.rejected:
            continue
        written = [comment for comment in vote.case.comments if comment.written_at <= as_of and comment.text.strip()]
        if written:
            commented.append((vote, max(written, key=lambda comment: comment.written_at).text.strip()))
    if not commented:
        return None
    vote, text = min(commented, key=lambda pair: (-pair[0].cosine, -pair[0].decided_at.timestamp(), pair[0].case_id))
    return Hint(code=HINT_REJECTION_REASON, case_id=vote.case_id, verdict=vote.verdict, cosine=vote.cosine, text=_clip(text))


def _critic_diverges(label: PrecedentLabel, review: CriticReview) -> Hint | None:
    if not review.reviewed or len(review.linked) != 1:
        return None
    decision = review.linked[0].decision
    if decision is None:
        return None
    leans_cancel = label.cancel_eligible_by_precedent and decision == CRITIC_ACCEPT
    leans_accept = label.code == LABEL_LIKELY_ACCEPTED and decision == CRITIC_REJECT
    if leans_cancel or leans_accept:
        return Hint(code=HINT_CRITIC_DIVERGES, critic_decision=decision)
    return None


def _document_history(finding: FindingContext, vote_set: VoteSet, thresholds: Thresholds) -> Hint | None:
    best: Vote | None = None
    for vote in vote_set.votes:
        if vote.document_uid != finding.document_uid or vote.version_uid == finding.version_uid or vote.cosine < thresholds.history:
            continue
        if best is None or (-vote.cosine, vote.case_id) < (-best.cosine, best.case_id):
            best = vote
    if best is None:
        return None
    return Hint(code=HINT_DOCUMENT_HISTORY, case_id=best.case_id, verdict=best.verdict, cosine=best.cosine)


def build_hints(
    finding: FindingContext,
    vote_set: VoteSet,
    label: PrecedentLabel,
    review: CriticReview,
    *,
    as_of: datetime,
    thresholds: Thresholds,
) -> tuple[Hint, ...]:
    candidates: list[Hint | None] = []
    if label.code in REJECTION_LABELS and not label.neutral:
        candidates.append(_rejection_reason(vote_set, as_of))
    candidates.append(_critic_diverges(label, review))
    candidates.append(_document_history(finding, vote_set, thresholds))
    return tuple(hint for hint in candidates if hint is not None)[:MAX_HINTS_PER_FINDING]
