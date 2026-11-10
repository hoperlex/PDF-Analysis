"""The values of the precedent core: what a case, a decision, a finding and a critic record are, as plain data.

Nothing here reads a database or a file. The consumers (the precedent pass of the composition root, the replay tool) build these values from
their own reads and hand them to the pure functions of this package. A field is named after the plan (`plan-v5` section 2) and carries only
what a rule of the core reads.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Final

#: The two verdicts that vote. The decision memory stores `accept` and `reject` events as these (`decision_memory/models.py`).
VERDICT_ACCEPTED: Final[str] = "accepted"
VERDICT_REJECTED: Final[str] = "rejected"
VOTING_VERDICTS: Final[frozenset[str]] = frozenset({VERDICT_ACCEPTED, VERDICT_REJECTED})

#: Where a decision came from. `carried` never votes; `imported` (a workbook read back) votes with no label ever shown.
ORIGIN_DIRECT: Final[str] = "direct"
ORIGIN_CARRIED: Final[str] = "carried"
ORIGIN_IMPORTED: Final[str] = "imported"
ORIGIN_KINDS: Final[frozenset[str]] = frozenset({ORIGIN_DIRECT, ORIGIN_CARRIED, ORIGIN_IMPORTED})

#: The labels of `plan-v5` 2.3. `neutral` is not a label: it is the stored name of a rejection label that was shown without its push
#: (a finding the critic did not review, V3), so it is not "a label to rejection in force" for the independence of a later decision.
LABEL_OFTEN_REJECTED: Final[str] = "often_rejected"
LABEL_CANCEL_SUGGESTED: Final[str] = "cancel_suggested"
LABEL_LIKELY_ACCEPTED: Final[str] = "likely_accepted"
LABEL_MIXED: Final[str] = "mixed"
LABEL_FEW: Final[str] = "few"
LABEL_NONE: Final[str] = "none"
SHOWN_NEUTRAL: Final[str] = "neutral"
LABEL_CODES: Final[frozenset[str]] = frozenset(
    {LABEL_OFTEN_REJECTED, LABEL_CANCEL_SUGGESTED, LABEL_LIKELY_ACCEPTED, LABEL_MIXED, LABEL_FEW, LABEL_NONE}
)
#: A decision taken while one of these was in force is not an independent vote (`plan-v5` 2.1).
REJECTION_LABELS: Final[frozenset[str]] = frozenset({LABEL_OFTEN_REJECTED, LABEL_CANCEL_SUGGESTED})

#: What the critic may advise on a candidate (`analysis/extended/review.py`, `_DECISIONS`). Only these two are a veto (`plan-v5` 2.4).
CRITIC_ACCEPT: Final[str] = "accept"
CRITIC_REJECT: Final[str] = "reject"
CRITIC_NEEDS_HUMAN: Final[str] = "needs_human"
CRITIC_VETO_DECISIONS: Final[frozenset[str]] = frozenset({CRITIC_ACCEPT, CRITIC_NEEDS_HUMAN})

#: The hints of `plan-v5` 2.5 that survive R-154 (P2 and P3 were AR v3 only). The codes are the plan's, in Cyrillic.
HINT_REJECTION_REASON: Final[str] = "П1"
HINT_CRITIC_DIVERGES: Final[str] = "П4"
HINT_DOCUMENT_HISTORY: Final[str] = "П5"

#: What the critic saw for a candidate (`plan-v5` 2.4).
CONTEXT_NORM_TEXT: Final[str] = "norm_text"
CONTEXT_NORM_IMAGES: Final[str] = "norm_images"
CONTEXT_PRECEDENTS: Final[str] = "precedents"


def require_aware(moment: datetime, name: str) -> None:
    """A moment without a zone cannot be ordered against another, and a silent guess would move a vote across the 24-month edge."""
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        raise ValueError(f"{name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class DecisionEvent:
    """One decision event of a case, as the memory ledger holds it.

    ``verdict`` is ``accepted``, ``rejected`` or anything else (a comment carries none); only the first two can vote. ``label_at_decision``
    is the label the server was giving the finding at that moment (`precedent_label_at_decision`, with the neutral display stored as
    ``neutral``); ``history_verdict_shown`` is the verdict of the document-history fact (hint P5) that was shown, or ``None``.
    """

    verdict: str | None
    decided_at: datetime
    origin_kind: str = ORIGIN_DIRECT
    label_at_decision: str | None = None
    history_verdict_shown: str | None = None

    def __post_init__(self) -> None:
        require_aware(self.decided_at, "decided_at")
        if self.origin_kind not in ORIGIN_KINDS:
            raise ValueError(f"unknown origin_kind {self.origin_kind!r}")


@dataclass(frozen=True, slots=True)
class CaseComment:
    """An expert's comment on a case. A comment never changes the case's vote."""

    text: str
    written_at: datetime

    def __post_init__(self) -> None:
        require_aware(self.written_at, "written_at")


@dataclass(frozen=True, slots=True)
class PrecedentCase:
    """A memory case with the identities the corpus rules read and its decision events.

    ``active`` is the state at read time (not withdrawn, not forgotten); the caller reads it from the live view, never from a nightly copy.
    ``section`` is ``None`` for a case that has none, and such a case never votes.
    """

    case_id: str
    section: str | None
    data_class: str
    project_uid: str
    document_uid: str
    version_uid: str
    run_id: str
    active: bool = True
    decisions: tuple[DecisionEvent, ...] = ()
    comments: tuple[CaseComment, ...] = ()


@dataclass(frozen=True, slots=True)
class ScoredCase:
    """A case with its precomputed cosine against the finding's vector (profile ``bge-m3-dense-v1``). The core never computes a cosine."""

    case: PrecedentCase
    cosine: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.cosine) or not -1.000001 <= self.cosine <= 1.000001:
            raise ValueError(f"cosine out of range for case {self.case.case_id!r}: {self.cosine!r}")


@dataclass(frozen=True, slots=True)
class FindingContext:
    """The finding the advice is for: its place (section, run, document, version) and the text the stop words are read from.

    ``primary_source_id`` is the finding's ``primary_text_<key>`` source (a text finding); ``extended_observation_ref`` is the candidate a
    candidate-finding came from. They link the finding to the critic's records (`plan-v5` 2.4).
    """

    finding_uid: str
    section: str | None
    data_class: str
    run_id: str
    document_uid: str
    version_uid: str
    finding_text: str
    recommendation_text: str = ""
    primary_source_id: str | None = None
    extended_observation_ref: str | None = None


@dataclass(frozen=True, slots=True)
class CriticCandidate:
    """One extended-review candidate with the critic's record for it, if any.

    ``decision`` is the critic's advice (``accept``, ``reject``, ``borderline``, ``needs_human``, ``rewrite``) or ``None`` when the critic
    did not review the candidate. ``context_kinds`` is what the critic saw (``norm_text``, ``norm_images``, ``precedents``).
    """

    candidate_id: str
    source_ids: tuple[str, ...] = ()
    decision: str | None = None
    context_kinds: frozenset[str] = frozenset()
