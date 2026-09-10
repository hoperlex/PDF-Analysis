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
from typing import Any, Final, Mapping

from auditmanager.api.schemas.common import timestamp
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "DECLARED_EVENT_TYPES",
    "PC01_EVENT_TYPES",
    "AppendDecisionCommand",
    "DecisionEventView",
    "append_decision_body",
    "decision_event_body",
    "parse_append_decision_request",
]

#: ``#/components/schemas/DecisionEventType``.
DECLARED_EVENT_TYPES: Final[frozenset[str]] = frozenset(
    {"accept", "reject", "comment", "revoke"}
)

#: What PC-01 actually emits. `revoke` is declared so PD-01 revocation stays
#: implementable without a schema change; no PC-01 client offers it, and
#: `auditmanager.decisions.record_decision` refuses it.
PC01_EVENT_TYPES: Final[frozenset[str]] = frozenset({"accept", "reject", "comment"})

MAX_COMMENT: Final[int] = 4000

_OBSERVATION_PREFIX: Final[str] = "fobs_"


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


def append_decision_body(view: DecisionEventView, current_verdict: str) -> dict[str, Any]:
    """``AppendDecisionResponse``: the appended event and the projection that follows."""
    return {"event": decision_event_body(view), "current_verdict": current_verdict}


@dataclass(frozen=True, slots=True)
class AppendDecisionCommand:
    """A validated ``AppendDecisionRequest``."""

    event_type: str
    finding_observation_id: str
    comment: str | None


def parse_append_decision_request(payload: Mapping[str, Any]) -> AppendDecisionCommand:
    """Validate ``AppendDecisionRequest``."""
    unknown = sorted(set(payload) - {"event_type", "finding_observation_id", "comment"})
    if unknown:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="The request body carries a property the schema does not declare.",
            field=unknown[0],
            constraint="additionalProperties",
        )

    event_type = payload.get("event_type")
    if not isinstance(event_type, str) or event_type not in DECLARED_EVENT_TYPES:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="event_type must be one of: accept, comment, reject, revoke.",
            field="event_type",
            constraint="enum",
        )

    observation_id = payload.get("finding_observation_id")
    if not isinstance(observation_id, str) or not observation_id.startswith(
        _OBSERVATION_PREFIX
    ):
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="finding_observation_id is required and must be an observation identity.",
            field="finding_observation_id",
            constraint="pattern",
        )

    comment = payload.get("comment")
    if comment is not None:
        if not isinstance(comment, str) or not 1 <= len(comment) <= MAX_COMMENT:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message=f"comment must be 1 to {MAX_COMMENT} characters.",
                field="comment",
                constraint="length",
            )
    if event_type == "comment" and not comment:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="A comment event must carry a comment.",
            field="comment",
            constraint="required_for_comment",
        )

    return AppendDecisionCommand(
        event_type=event_type,
        finding_observation_id=observation_id,
        comment=comment,
    )
