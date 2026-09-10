"""The append-only expert decision ledger.

Every event is a new ``decision_id``. Nothing is ever updated and nothing is ever
removed: ``UPDATE`` and ``DELETE`` on ``expert_decision_event`` raise SQLSTATE ``AM002``
from a trigger, so "append-only" is a property of the database rather than a discipline
this module asks callers to keep. There is no row to overwrite, which is what makes the
current verdict a projection instead of a cache.

Two things this module refuses, and why:

* **The model never writes a verdict.** ``record_decision`` is reached from the expert's
  command surface only; nothing in ``findings`` calls it and no analysis stage does.
  A verdict is what a human said about a finding, and a ledger that could be written by
  the thing being judged would make every usefulness measurement circular.
* **``revoke`` is refused.** It is in the database enum so PD-01 stays implementable
  without a schema change, and the projection already gives it the right meaning. But
  PC-01 emits no revocation event and the UI offers none, so accepting one here would
  create a producer the programme has not decided to have. The refusal names that,
  rather than failing on a constraint the caller cannot read.

``author_label`` is ``OD-12``: one configured local reviewer label, persisted server-side
with each event. It is a label, not a subject identity, and it authorizes nothing. It is
never taken from a request body — PC-01 has no authentication, and a client-supplied
"who did this" would be a subject identity in all but name.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from auditmanager.findings.queries import finding_exists, observation_belongs_to_finding
from auditmanager.shared.db import SQLSTATE_TO_CATALOG_CODE, nested_transaction
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DecisionId

#: The event types PC-01 produces. ``revoke`` is declared in the database enum and has
#: no PC-01 producer; see the module docstring.
PC01_EVENT_TYPES: Final[frozenset[str]] = frozenset({"accept", "reject", "comment"})

#: Every event type the ledger schema declares, PC-01 producer or not.
DECLARED_EVENT_TYPES: Final[frozenset[str]] = PC01_EVENT_TYPES | {"revoke"}

#: The verdict each event type carries. ``comment`` carries none: a comment is not a
#: judgement, and the projection must not move because somebody wrote a note.
VERDICT_FOR_EVENT: Final[dict[str, str | None]] = {
    "accept": "accepted",
    "reject": "rejected",
    "comment": None,
    "revoke": "pending",
}

#: OD-12. The single local reviewer label this deployment records. A different label is
#: a configuration change at the composition root, never a field in a request.
CONFIGURED_AUTHOR_LABEL: Final[str] = "local-reviewer"

_INSERT_EVENT = text(
    """
    INSERT INTO expert_decision_event (
        decision_id, finding_uid, finding_observation_id, event_type,
        verdict, comment, author_label, command_id, correlation_id
    ) VALUES (
        :decision_id, :finding_uid, :finding_observation_id, :event_type,
        :verdict, :comment, :author_label, :command_id, :correlation_id
    )
    RETURNING decision_id, recorded_at
    """
)

_EVENT_BY_COMMAND = text(
    """
    SELECT decision_id, finding_uid, finding_observation_id, event_type,
           verdict, comment, author_label, command_id, recorded_at
    FROM expert_decision_event
    WHERE command_id = :command_id
    """
)

_EVENTS_FOR_FINDING = text(
    """
    SELECT decision_id, finding_uid, finding_observation_id, event_type,
           verdict, comment, author_label, command_id, recorded_at
    FROM expert_decision_event
    WHERE finding_uid = :finding_uid
    ORDER BY sequence_no
    """
)


@dataclass(frozen=True, slots=True)
class DecisionEvent:
    """One appended event, as it now stands in the ledger for ever.

    ``sequence_no`` is deliberately absent. The contract lists a database sequence value
    exposed to a client among the non-identities, so it is never returned and never
    embedded in a cursor; client-visible ordering is ``(recorded_at, decision_id)``.
    """

    decision_id: str
    finding_uid: str
    finding_observation_id: str
    event_type: str
    verdict: str | None
    comment: str | None
    author_label: str
    command_id: str | None
    recorded_at: object | None = None


def _translate(exc: DBAPIError) -> DomainError:
    """Map a refusal on SQLSTATE, never on message text."""
    sqlstate = getattr(getattr(exc, "orig", None), "sqlstate", None) or getattr(
        exc, "code", None
    )
    mapped = SQLSTATE_TO_CATALOG_CODE.get(str(sqlstate)) if sqlstate else None
    if mapped is not None:
        return DomainError(
            ErrorCode(mapped), message=f"the ledger refused the write ({sqlstate})"
        )
    return DomainError(ErrorCode.INTERNAL_ERROR, message="the ledger refused the write")


def _existing_event(session: Session, command_id: str) -> "DecisionEvent | None":
    """The event already appended under this command key, if any.

    Called twice on purpose. Once before doing any work, so a replay is answered from
    the ledger rather than re-decided; and once after a unique-index violation, because
    between those two moments another writer may have appended. The index is the
    enforcement — this lookup only decides what the caller is told.
    """
    row = session.execute(_EVENT_BY_COMMAND, {"command_id": command_id}).mappings().first()
    return None if row is None else _row_to_event(row)


def _row_to_event(row) -> DecisionEvent:  # noqa: ANN001 - a SQLAlchemy RowMapping
    return DecisionEvent(
        decision_id=row["decision_id"],
        finding_uid=row["finding_uid"],
        finding_observation_id=row["finding_observation_id"],
        event_type=row["event_type"],
        verdict=row["verdict"],
        comment=row["comment"],
        author_label=row["author_label"],
        command_id=row["command_id"],
        recorded_at=row["recorded_at"],
    )


def record_decision(
    session: Session,
    *,
    finding_uid: str,
    finding_observation_id: str,
    event_type: str,
    comment: str | None = None,
    command_id: str | None = None,
    correlation_id: str | None = None,
    author_label: str = CONFIGURED_AUTHOR_LABEL,
) -> DecisionEvent:
    """Append one expert decision event. Never updates and never deletes.

    ``author_label`` defaults to the deployment's configured label and is supplied by
    the composition root when it differs — it is not a field a client fills in.

    Replaying the same command under one idempotency key appends exactly one event: the
    unique index on ``command_id`` is the enforcement, and a second attempt returns the
    event that already exists rather than a conflict the caller must interpret.
    """
    if event_type == "revoke":
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=(
                "revoke is declared in the ledger so PD-01 stays implementable without "
                "a schema change, but PC-01 emits no revocation event and offers none "
                "in the UI"
            ),
        )
    if event_type not in PC01_EVENT_TYPES:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=f"{event_type!r} is not one of the decision events PC-01 produces",
        )
    if event_type == "comment" and not (comment and comment.strip()):
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="a comment event must carry a comment",
        )
    if not author_label.strip():
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, message="author_label must not be empty"
        )

    # An idempotent replay is answered from the ledger before anything is validated
    # again: the first attempt already decided, and re-deciding could disagree.
    if command_id is not None:
        existing = _existing_event(session, command_id)
        if existing is not None:
            return existing

    if not finding_exists(session, finding_uid):
        # Reached for an unknown finding and for an *ungrounded* observation alike: an
        # ungrounded observation carries no finding_uid, so there is nothing to judge.
        raise DomainError(
            ErrorCode.NOT_FOUND,
            message="no published finding carries that identity",
        )
    if not observation_belongs_to_finding(
        session, finding_uid=finding_uid, finding_observation_id=finding_observation_id
    ):
        raise DomainError(
            ErrorCode.NOT_FOUND,
            message="that observation does not carry that finding identity",
        )

    parameters = {
        "decision_id": DecisionId.new().value,
        "finding_uid": finding_uid,
        "finding_observation_id": finding_observation_id,
        "event_type": event_type,
        "verdict": VERDICT_FOR_EVENT[event_type],
        "comment": comment,
        "author_label": author_label,
        "command_id": command_id,
        "correlation_id": correlation_id,
    }

    try:
        # A savepoint, so a lost race on the command_id index does not discard the
        # caller's whole unit of work: the other writer's event is the answer.
        with nested_transaction(session):
            row = session.execute(_INSERT_EVENT, parameters).mappings().one()
    except IntegrityError:
        # Lost the race on the command_id index: the other writer's event is the answer,
        # not a conflict the caller has to interpret. Exactly one event exists either
        # way, which is what the idempotency guarantee actually says.
        if command_id is not None:
            existing = _existing_event(session, command_id)
            if existing is not None:
                return existing
        raise DomainError(
            ErrorCode.CONFLICT, message="the ledger refused the appended event"
        ) from None
    except DBAPIError as exc:
        raise _translate(exc) from exc

    return DecisionEvent(
        decision_id=row["decision_id"],
        finding_uid=finding_uid,
        finding_observation_id=finding_observation_id,
        event_type=event_type,
        verdict=VERDICT_FOR_EVENT[event_type],
        comment=comment,
        author_label=author_label,
        command_id=command_id,
        recorded_at=row["recorded_at"],
    )


def decision_history(session: Session, finding_uid: str) -> tuple[DecisionEvent, ...]:
    """Every event for one finding, oldest first, in the server's total order.

    History is the point of the ledger: this returns all of it, including events a later
    one superseded, because a superseded verdict is a record of what the expert once
    said and not a mistake to be tidied away.
    """
    rows = session.execute(_EVENTS_FOR_FINDING, {"finding_uid": finding_uid}).mappings().all()
    return tuple(_row_to_event(row) for row in rows)
