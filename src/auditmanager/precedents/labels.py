"""The labels of `plan-v5` 2.3 over a finding's counted votes, with the gates of 2.4 and the neutral display of V3.

All shares are integer comparisons (``rejected * 100 >= percent * total``), so no float edge moves a finding across a threshold.

``cancel_suggested`` is a *part* of ``often_rejected``: the finding first has to be often rejected over all its votes, and then it needs, over
its **independent** votes, the minimum count, the cancel share and two projects; the latest vote overall has to be a rejection (a later
acceptance, even a dependent one, is the strongest sign against a cancel); and the critic reviewed the finding without a veto, and no stop
word is in its text. Whatever fails is listed in ``cancel_blockers`` so the reason is never silent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from auditmanager.precedents.critic import CriticReview
from auditmanager.precedents.models import (
    LABEL_CANCEL_SUGGESTED,
    LABEL_FEW,
    LABEL_LIKELY_ACCEPTED,
    LABEL_MIXED,
    LABEL_NONE,
    LABEL_OFTEN_REJECTED,
    SHOWN_NEUTRAL,
)
from auditmanager.precedents.votes import VoteSet

BLOCKER_INDEPENDENT_VOTES: Final[str] = "independent_votes_below_minimum"
BLOCKER_CANCEL_SHARE: Final[str] = "rejected_share_below_cancel_share"
BLOCKER_LAST_VOTE: Final[str] = "last_vote_not_a_rejection"
BLOCKER_PROJECTS: Final[str] = "fewer_than_two_projects"
BLOCKER_NOT_REVIEWED: Final[str] = "not_reviewed_by_critic"
BLOCKER_CRITIC_VETO: Final[str] = "critic_veto"
BLOCKER_STOP_WORD: Final[str] = "stop_word"


@dataclass(frozen=True, slots=True)
class LabelPolicy:
    """The numbers of `plan-v5` 2.3 (R3). Percentages are integers."""

    min_votes: int = 5
    often_percent: int = 80
    cancel_min_independent: int = 5
    cancel_percent: int = 90
    cancel_min_projects: int = 2

    def __post_init__(self) -> None:
        if not (self.min_votes >= 1 and self.cancel_min_independent >= 1 and self.cancel_min_projects >= 1):
            raise ValueError("vote and project minimums must be at least 1")
        if not (50 < self.often_percent <= 100 and self.often_percent <= self.cancel_percent <= 100):
            raise ValueError("percentages must satisfy 50 < often_percent <= cancel_percent <= 100")


@dataclass(frozen=True, slots=True)
class PrecedentLabel:
    """The label of one finding.

    ``code`` is the label; ``neutral`` is true when a rejection label is shown without its push because the critic did not review the
    finding (V3), and then ``caption`` is the neutral line. ``shown_code`` is the value to store as the label in force
    (``precedent_label_at_decision``): ``neutral`` for a neutral display, else ``code``. ``cancel_eligible_by_precedent`` is true when the
    votes alone meet every cancel condition, before the critic and stop-word gates.
    """

    code: str
    neutral: bool
    caption: str | None
    votes_total: int
    votes_rejected: int
    votes_accepted: int
    independent_total: int
    independent_rejected: int
    cancel_eligible_by_precedent: bool
    cancel_blockers: tuple[str, ...]

    @property
    def in_cancel_queue(self) -> bool:
        return self.code == LABEL_CANCEL_SUGGESTED

    @property
    def shown_code(self) -> str:
        return SHOWN_NEUTRAL if self.neutral else self.code


def _neutral_caption(total: int) -> str:
    return f"Прецедентов: {total} (критик не разбирал)"


def compute_label(
    vote_set: VoteSet,
    review: CriticReview,
    stop_words_found: tuple[str, ...],
    policy: LabelPolicy = LabelPolicy(),
) -> PrecedentLabel:
    votes = vote_set.votes
    total = len(votes)
    rejected = sum(1 for vote in votes if vote.rejected)
    accepted = total - rejected
    independent = [vote for vote in votes if vote.independent]
    independent_total = len(independent)
    independent_rejected = sum(1 for vote in independent if vote.rejected)

    def build(code: str, caption: str | None, *, neutral: bool = False, eligible: bool = False, blockers: tuple[str, ...] = ()) -> PrecedentLabel:
        return PrecedentLabel(
            code=code,
            neutral=neutral,
            caption=caption,
            votes_total=total,
            votes_rejected=rejected,
            votes_accepted=accepted,
            independent_total=independent_total,
            independent_rejected=independent_rejected,
            cancel_eligible_by_precedent=eligible,
            cancel_blockers=blockers,
        )

    if total == 0:
        return build(LABEL_NONE, None)
    if total < policy.min_votes:
        return build(LABEL_FEW, None)

    if rejected * 100 >= policy.often_percent * total:
        blockers: list[str] = []
        if independent_total < policy.cancel_min_independent:
            blockers.append(BLOCKER_INDEPENDENT_VOTES)
        elif independent_rejected * 100 < policy.cancel_percent * independent_total:
            blockers.append(BLOCKER_CANCEL_SHARE)
        latest = vote_set.latest
        if latest is None or not latest.rejected:
            blockers.append(BLOCKER_LAST_VOTE)
        if len({vote.project_uid for vote in independent if vote.rejected}) < policy.cancel_min_projects:
            blockers.append(BLOCKER_PROJECTS)
        eligible = not blockers
        if not review.reviewed:
            blockers.append(BLOCKER_NOT_REVIEWED)
        if review.veto:
            blockers.append(BLOCKER_CRITIC_VETO)
        if stop_words_found:
            blockers.append(BLOCKER_STOP_WORD)
        if not blockers:
            return build(
                LABEL_CANCEL_SUGGESTED,
                f"Рекомендуется снять · {independent_rejected} из {independent_total}",
                eligible=True,
            )
        if not review.reviewed:
            return build(LABEL_OFTEN_REJECTED, _neutral_caption(total), neutral=True, eligible=eligible, blockers=tuple(blockers))
        return build(LABEL_OFTEN_REJECTED, f"Обычно отклоняют · {rejected} из {total}", eligible=eligible, blockers=tuple(blockers))

    if accepted * 100 >= policy.often_percent * total:
        return build(LABEL_LIKELY_ACCEPTED, f"Обычно принимают · {accepted} из {total}")
    return build(LABEL_MIXED, f"Решения расходятся · {accepted} ✓ / {rejected} ✕")
