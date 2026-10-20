"""Expert-confirmed carryover of one decision to the next version (`W59-DECISION-CARRYOVER-01`).

A carryover is **an ordinary decision event on the target finding**, appended by the expert
who confirmed it, through :func:`~auditmanager.decisions.ledger.record_decision`. Nothing
else is written to the ledger: the source finding, its events and every other row stay as
they were, and a later verdict on the target supersedes the carried one exactly as it would
supersede any other event.

**Provenance lives in the event itself.** The schema has no provenance column, and none is
needed: the carried event's ``comment`` is a deterministic rendering
(:func:`carryover_comment`) of the carried-from finding, the carried decision event, both
versions and the comparison mode, with the source version's ordinal as the human-readable
«из версии N». The identities in it are opaque UIDs; the ordinal is display only and is
never read back as an identity. The confirming expert is the event's ``author_user_uid``
and ``author_label``, the time its ``recorded_at``. The command record claimed for the
idempotency key repeats the same provenance in its outcome.

Rules, under one transaction that holds both finding rows ``FOR UPDATE`` (an ordinary
``appendDecision`` on either finding takes a key-share lock through the event's foreign key,
so it waits for this transaction, and this one waits for it):

* the source finding's **current** verdict must be ``accepted`` or ``rejected`` and its
  verdict-bearing event must be exactly the decision the expert confirmed -- otherwise
  ``conflict`` / ``carryover_source_decision_not_current``;
* the target finding must carry no event at all (the conservative W59 rule of
  ``comparison/decision_carryover.py``: a comment also blocks) -- otherwise ``conflict`` /
  ``carryover_target_already_decided``;
* an exact repeat -- the target already carries the event this carryover renders -- answers
  that event, by any key and any expert, and appends nothing (the first confirmer stands);
* a severity on the carried ``accept`` is carried with it, or the carryover is refused
  ``carryover_severity_not_carryable`` when the target's observation cannot hold one. It is
  never dropped.

This module does not decide *which* pairs may be carried: the comparison context proves that
the recomputed comparison still proposes the pair before it calls :func:`carry_over_decision`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from auditmanager.decisions.ledger import (
    _SEVERITY_TARGET,
    DecisionEvent,
    decision_events_by_id,
    decision_history,
    record_decision,
)
from auditmanager.decisions.projection import current_verdicts
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    DecisionId,
    FindingObservationId,
    FindingUid,
    IdentityError,
    VersionUid,
)
from auditmanager.shared.identity.ids import UserUid

__all__ = [
    "CARRIED_EVENT_FOR_VERDICT",
    "CARRYOVER_COMMAND_TYPE",
    "CARRYOVER_CONFLICT_REASONS",
    "CARRYOVER_MODES",
    "CONFLICT_CARRYOVER_PAIR_NOT_PROPOSED",
    "CONFLICT_CARRYOVER_SEVERITY_NOT_CARRYABLE",
    "CONFLICT_CARRYOVER_SOURCE_DECISION_NOT_CURRENT",
    "CONFLICT_CARRYOVER_TARGET_ALREADY_DECIDED",
    "CarriedDecision",
    "CarryoverProvenance",
    "carry_over_decision",
    "carryover_comment",
]

CARRYOVER_COMMAND_TYPE: Final[str] = "carry_over_decision"

#: The verdicts a carryover can carry, and the event that carries each. ``pending`` (no
#: verdict, or a revocation) is not a decision and is never carried.
CARRIED_EVENT_FOR_VERDICT: Final[dict[str, str]] = {"accepted": "accept", "rejected": "reject"}

#: The comparison modes of ``compareDocumentVersions``, and how the provenance names them.
CARRYOVER_MODES: Final[dict[str, str]] = {
    "version": "сравнение версий",
    "stage": "сравнение стадий П → Р",
}

#: ``conflict`` details (``conflict_reason``) of a refused carryover. The first is raised by
#: the comparison context, which proves the pair; the others here, under the row locks.
CONFLICT_CARRYOVER_PAIR_NOT_PROPOSED: Final[str] = "carryover_pair_not_proposed"
CONFLICT_CARRYOVER_SOURCE_DECISION_NOT_CURRENT: Final[str] = "carryover_source_decision_not_current"
CONFLICT_CARRYOVER_TARGET_ALREADY_DECIDED: Final[str] = "carryover_target_already_decided"
CONFLICT_CARRYOVER_SEVERITY_NOT_CARRYABLE: Final[str] = "carryover_severity_not_carryable"
CARRYOVER_CONFLICT_REASONS: Final[tuple[str, ...]] = (
    CONFLICT_CARRYOVER_PAIR_NOT_PROPOSED,
    CONFLICT_CARRYOVER_SOURCE_DECISION_NOT_CURRENT,
    CONFLICT_CARRYOVER_TARGET_ALREADY_DECIDED,
    CONFLICT_CARRYOVER_SEVERITY_NOT_CARRYABLE,
)

_LOCK_FINDINGS = text(
    "SELECT finding_uid, version_uid FROM finding WHERE finding_uid IN :uids "
    "ORDER BY finding_uid COLLATE \"C\" FOR UPDATE"
).bindparams(bindparam("uids", expanding=True))


@dataclass(frozen=True, slots=True)
class CarryoverProvenance:
    """Where a carried decision comes from. Every field but the ordinal is an identity."""

    source_finding_uid: str
    source_decision_id: str
    source_version_uid: str
    #: Display only («из версии N»); never compared as an identity.
    source_version_ordinal: int
    target_version_uid: str
    mode: str


@dataclass(frozen=True, slots=True)
class CarriedDecision:
    """The carried event on the target, and whether this call appended it.

    ``replayed`` is ``True`` when the target already carried exactly this event (an exact
    repeat by any key or expert, or a replay of the same key); nothing was appended then.
    """

    event: DecisionEvent
    replayed: bool
    source_event: DecisionEvent
    provenance: CarryoverProvenance


def carryover_comment(provenance: CarryoverProvenance) -> str:
    """The carried event's comment: a fixed rendering of ``provenance``, byte-stable.

    It is how the ledger records where the decision came from without a new column, and the
    exact-repeat check compares it whole -- it is never parsed back.
    """
    _check_provenance(provenance)
    return (
        f"Решение перенесено из версии {provenance.source_version_ordinal} "
        f"({CARRYOVER_MODES[provenance.mode]}) после подтверждения экспертом. "
        f"Исходное решение {provenance.source_decision_id} по замечанию "
        f"{provenance.source_finding_uid} версии {provenance.source_version_uid}; "
        f"целевая версия {provenance.target_version_uid}."
    )


def _invalid(field: str) -> DomainError:
    return DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint="format")


def _check_provenance(provenance: CarryoverProvenance) -> None:
    if not isinstance(provenance, CarryoverProvenance):
        raise _invalid("provenance")
    for field, kind in (
        ("source_finding_uid", FindingUid),
        ("source_decision_id", DecisionId),
        ("source_version_uid", VersionUid),
        ("target_version_uid", VersionUid),
    ):
        try:
            kind.parse(getattr(provenance, field))
        except (IdentityError, TypeError):
            raise _invalid(field) from None
    ordinal = provenance.source_version_ordinal
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise _invalid("source_version_ordinal")
    if provenance.mode not in CARRYOVER_MODES:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="mode", constraint="enum")
    if provenance.source_version_uid == provenance.target_version_uid:
        raise _conflict(CONFLICT_CARRYOVER_PAIR_NOT_PROPOSED)


def _conflict(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.CONFLICT, aggregate_type="ExpertDecision", conflict_reason=reason,
    )


def _same_event(event: DecisionEvent, wanted: dict[str, str | None]) -> bool:
    return (
        event.finding_observation_id == wanted["finding_observation_id"]
        and event.event_type == wanted["event_type"]
        and event.verdict == wanted["verdict"]
        and event.severity == wanted["severity"]
        and event.comment == wanted["comment"]
    )


def carry_over_decision(
    session: Session,
    *,
    provenance: CarryoverProvenance,
    target_finding_uid: str,
    target_finding_observation_id: str,
    idempotency_key: str,
    author_label: str,
    author_user_uid: str,
) -> CarriedDecision:
    """Append the confirmed carryover on the target finding, or answer the one it carries.

    The caller owns the transaction and has already proved that the current comparison
    proposes ``provenance.source_finding_uid`` and ``target_finding_uid`` as an unchanged
    pair, and that ``author_user_uid`` holds the expert role. See the module docstring for
    every refusal.
    """
    from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint

    _check_provenance(provenance)
    for field, kind, value in (
        ("target_finding_uid", FindingUid, target_finding_uid),
        ("target_finding_observation_id", FindingObservationId, target_finding_observation_id),
        # The confirming expert is the point of a carryover: never an unknown author.
        ("author_user_uid", UserUid, author_user_uid),
    ):
        try:
            kind.parse(value)
        except (IdentityError, TypeError):
            raise _invalid(field) from None
    if target_finding_uid == provenance.source_finding_uid:
        raise _conflict(CONFLICT_CARRYOVER_PAIR_NOT_PROPOSED)

    # Both rows, in one order, before anything is read: see the module docstring.
    locked = {
        row.finding_uid: row.version_uid
        for row in session.execute(
            _LOCK_FINDINGS, {"uids": [provenance.source_finding_uid, target_finding_uid]},
        )
    }
    if (
        locked.get(provenance.source_finding_uid) != provenance.source_version_uid
        or locked.get(target_finding_uid) != provenance.target_version_uid
    ):
        raise _conflict(CONFLICT_CARRYOVER_PAIR_NOT_PROPOSED)

    verdicts = current_verdicts(session, [provenance.source_finding_uid])
    source = verdicts.get(provenance.source_finding_uid)
    if (
        source is None
        or source.current_verdict not in CARRIED_EVENT_FOR_VERDICT
        or source.latest_verdict_decision_id != provenance.source_decision_id
    ):
        raise _conflict(CONFLICT_CARRYOVER_SOURCE_DECISION_NOT_CURRENT)
    source_event = decision_events_by_id(session, [provenance.source_decision_id]).get(
        provenance.source_decision_id
    )
    if (
        source_event is None
        or source_event.finding_uid != provenance.source_finding_uid
        or source_event.verdict != source.current_verdict
    ):  # pragma: no cover - the view and the stream are one source of truth
        raise _conflict(CONFLICT_CARRYOVER_SOURCE_DECISION_NOT_CURRENT)

    event_type = CARRIED_EVENT_FOR_VERDICT[source.current_verdict]
    severity = source_event.severity if event_type == "accept" else None
    wanted: dict[str, str | None] = {
        "finding_observation_id": target_finding_observation_id,
        "event_type": event_type,
        "verdict": source.current_verdict,
        "severity": severity,
        "comment": carryover_comment(provenance),
    }

    history = decision_history(session, target_finding_uid)
    carried = next((event for event in history if _same_event(event, wanted)), None)
    if carried is not None:
        return CarriedDecision(carried, True, source_event, provenance)
    if history:
        raise _conflict(CONFLICT_CARRYOVER_TARGET_ALREADY_DECIDED)
    if severity is not None and not session.execute(
        _SEVERITY_TARGET,
        {"finding_uid": target_finding_uid, "finding_observation_id": target_finding_observation_id},
    ).scalar_one_or_none():
        raise _conflict(CONFLICT_CARRYOVER_SEVERITY_NOT_CARRYABLE)

    payload: dict[str, str] = {
        "command": "carry_over_decision.v1",
        "source_finding_uid": provenance.source_finding_uid,
        "source_decision_id": provenance.source_decision_id,
        "source_version_uid": provenance.source_version_uid,
        "target_version_uid": provenance.target_version_uid,
        "mode": provenance.mode,
        "target_finding_uid": target_finding_uid,
        "target_finding_observation_id": target_finding_observation_id,
        "author_label": author_label,
        "author_user_uid": author_user_uid,
    }
    commands = CommandRepository()
    claimed = commands.begin(
        session,
        command_type=CARRYOVER_COMMAND_TYPE,
        idempotency_key=idempotency_key,
        fingerprint=payload_fingerprint(payload),
    )
    if isinstance(claimed, CommandReplay):
        # Unreachable while the target's history is read above under the lock, because a
        # replayed key's event would already have been answered as carried. Kept fail-closed.
        decision_id = claimed.outcome.get("decision_id")
        replayed = (
            decision_events_by_id(session, [decision_id]).get(decision_id)
            if isinstance(decision_id, str) else None
        )
        if replayed is None or replayed.finding_uid != target_finding_uid:
            raise DomainError(ErrorCode.IDEMPOTENCY_KEY_STALE, command_type=CARRYOVER_COMMAND_TYPE)
        return CarriedDecision(replayed, True, source_event, provenance)

    event = record_decision(
        session,
        finding_uid=target_finding_uid,
        finding_observation_id=target_finding_observation_id,
        event_type=event_type,
        severity=severity,
        comment=wanted["comment"],
        command_id=str(claimed.command_id),
        author_label=author_label,
        author_user_uid=author_user_uid,
    )
    commands.succeed(
        session,
        command_id=claimed.command_id,
        outcome={
            "decision_id": event.decision_id,
            "source_finding_uid": provenance.source_finding_uid,
            "source_decision_id": provenance.source_decision_id,
            "source_version_uid": provenance.source_version_uid,
            "target_version_uid": provenance.target_version_uid,
            "mode": provenance.mode,
        },
    )
    return CarriedDecision(event, False, source_event, provenance)
