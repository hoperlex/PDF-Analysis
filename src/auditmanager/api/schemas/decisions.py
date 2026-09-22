"""``DecisionEvent``, ``AppendDecisionRequest`` and ``AppendDecisionResponse``.

The ledger is append-only: an accept after a reject is a third event, and the current
verdict is a projection over the stream. Nothing here updates anything.

``sequence_no`` never appears -- not as a field and not inside a cursor.
``P02_SEAMS.md`` section 5.3 is explicit that the server's row sequence is never
exposed, and section 2.2 lists a database sequence value among the non-identities.
Client-visible ordering is ``(recorded_at, decision_id)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from auditmanager.api.schemas.common import timestamp
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "DecisionEventView",
    "DecisionRecordView",
    "append_decision_body",
    "check_comment_is_present_for_a_comment_event",
    "decision_event_body",
    "decision_record_body",
]

@dataclass(frozen=True, slots=True)
class DecisionEventView:
    """Exactly the frozen ``DecisionEvent``."""

    decision_id: str
    finding_uid: str
    finding_observation_id: str
    event_type: str
    author_label: str
    recorded_at: datetime
    verdict: str | None = None
    comment: str | None = None


def decision_event_body(view: DecisionEventView) -> dict[str, Any]:
    return {
        "decision_id": view.decision_id,
        "finding_uid": view.finding_uid,
        "finding_observation_id": view.finding_observation_id,
        "event_type": view.event_type,
        # Both are `oneOf [<value>, null]`: a comment event carries a null verdict, and
        # that is a fact about the event rather than a missing field.
        "verdict": view.verdict,
        "comment": view.comment,
        "author_label": view.author_label,
        "recorded_at": timestamp(view.recorded_at),
    }


@dataclass(frozen=True, slots=True)
class DecisionRecordView:
    """Exactly the frozen ``DecisionRecord``.

    ``DecisionEventView``'s fields and the finding context the journal carries beside
    them. It does not *compose* ``DecisionEventView``, for the same reason the contract's
    ``DecisionRecord`` does not compose ``DecisionEvent`` with ``allOf``: both shapes are
    closed, and a nested view would render a nested body.
    """

    decision_id: str
    finding_uid: str
    finding_observation_id: str
    event_type: str
    author_label: str
    recorded_at: datetime
    project_uid: str
    run_id: str
    category: str
    finding_text: str
    current_verdict: str
    decision_event_count: int
    verdict: str | None = None
    comment: str | None = None


def decision_record_body(view: DecisionRecordView) -> dict[str, Any]:
    """``DecisionRecord``: one journal entry, event and finding context together."""
    return {
        "decision_id": view.decision_id,
        "finding_uid": view.finding_uid,
        "finding_observation_id": view.finding_observation_id,
        "event_type": view.event_type,
        # `oneOf [<value>, null]`, as on ``DecisionEvent``: a comment event carries a null
        # verdict, and that is a fact about the event rather than a missing field.
        "verdict": view.verdict,
        "comment": view.comment,
        "author_label": view.author_label,
        "recorded_at": timestamp(view.recorded_at),
        "project_uid": view.project_uid,
        "run_id": view.run_id,
        "category": view.category,
        "finding_text": view.finding_text,
        "current_verdict": view.current_verdict,
        "decision_event_count": view.decision_event_count,
    }


def append_decision_body(view: DecisionEventView, current_verdict: str) -> dict[str, Any]:
    """``AppendDecisionResponse``: the appended event and the projection that follows."""
    return {"event": decision_event_body(view), "current_verdict": current_verdict}


#: ``#/components/schemas/AppendDecisionRequest.properties.comment.maxLength``, named for a
#: reader of this module. The bound itself is enforced by
#: :class:`auditmanager.api.schemas.models.AppendDecisionRequest`.
MAX_COMMENT: Final[int] = 4000


def check_comment_is_present_for_a_comment_event(
    *, event_type: str, comment: str | None
) -> None:
    """A ``comment`` event must carry a comment.

    The one rule of ``AppendDecisionRequest`` that no JSON Schema keyword expresses -- it is
    a dependency between two properties, and the frozen document states it in prose. It is
    checked at the edge, against the already-validated model, rather than left to the
    command layer, because it is a request-shape refusal and the caller needs to be told
    *which property* is missing.
    """
    if event_type == "comment" and not comment:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="A comment event must carry a comment.",
            field="comment",
            constraint="required_for_comment",
        )
