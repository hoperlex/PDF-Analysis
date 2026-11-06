"""Reading the access journal back (contract 1.36.0, `UI-A-92`, `UI-A-94`).

The writer is :mod:`auditmanager.access.audit`: every ``access.*`` event is one row of the
append-only ``audit_event`` table, written in the transaction of the change it describes. This
module is the read side, and it reads **that table and nothing else** -- there is no second
store of sign-ins, so the time an account last signed in and the line of the journal that says
so are one fact and cannot disagree.

Two reads:

* :func:`read_access_events` -- the journal, newest first, one page at a time. The ordering is
  ``(occurred_at, sequence_no)`` and the cursor is an event's own ``evt_`` identity; the
  database resolves the ordering coordinates, so ``sequence_no`` is never sent to a client
  (``P02_SEAMS.md`` section 2.2), the same way the execution journal pages.
* :func:`last_sign_in_times` -- for a set of accounts, the instant of the latest
  ``access.sign_in_succeeded`` of each. An account that has none (it never signed in, or its
  last sign-in is older than the journal) is simply absent from the answer, and the API says
  ``null`` for it.

What a row may reveal is exactly what the writer allows into a payload (identities, a role, a
source word, one boolean, one count): there is no login text, no address and no secret in the
table to read.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.access.audit import ACCESS_EVENT_TYPES, AGGREGATE_TYPE

__all__ = ["AccessEvent", "last_sign_in_times", "read_access_events"]

#: The event whose latest instant is an account's last sign-in.
_SIGN_IN_SUCCEEDED: Final[str] = "access.sign_in_succeeded"

_EVENTS = text(
    """
    WITH anchor AS (
        SELECT e.occurred_at, e.sequence_no FROM audit_event e
         WHERE e.audit_event_id = CAST(:after AS text)
           AND e.aggregate_type = :aggregate_type
           AND e.event_type = ANY (CAST(:types AS text[]))
    )
    SELECT e.audit_event_id, e.event_type, e.aggregate_id, e.occurred_at, e.payload
      FROM audit_event e
     WHERE e.aggregate_type = :aggregate_type
       AND e.event_type = ANY (CAST(:types AS text[]))
       AND (CAST(:after AS text) IS NULL
            OR (e.occurred_at, e.sequence_no) < (SELECT occurred_at, sequence_no FROM anchor))
     ORDER BY e.occurred_at DESC, e.sequence_no DESC
     LIMIT :fetch
    """
)

_LAST_SIGN_INS = text(
    """
    SELECT e.aggregate_id, max(e.occurred_at)
      FROM audit_event e
     WHERE e.aggregate_type = :aggregate_type
       AND e.event_type = :event_type
       AND e.aggregate_id = ANY (CAST(:uids AS text[]))
     GROUP BY e.aggregate_id
    """
)


@dataclass(frozen=True, slots=True)
class AccessEvent:
    """One journal line, as the writer stored it. Optional facts are ``None`` when the type has none."""

    event_id: str
    event_type: str
    occurred_at: datetime
    #: The account the event is about (the row's aggregate identity).
    subject_uid: str
    #: The administrator who acted; ``None`` for a sign-in, a refusal and a host-command grant.
    actor_uid: str | None
    #: ``api`` or ``host_cli``.
    source: str
    #: The role a grant or a revoke names.
    role: str | None
    #: How many refusals started the cooling-off period (a ``sign_in_blocked`` row).
    failures: int | None
    #: Whether a sign-in used the seeded or reset password (a ``sign_in_succeeded`` row).
    default_credential: bool | None


def read_access_events(
    session: Session, *, after_event_id: str | None, limit: int
) -> tuple[AccessEvent, ...]:
    """Up to ``limit`` events, newest first, strictly older than the event ``after_event_id``.

    ``None`` starts at the newest. An id that is not an access event of the journal yields no
    rows rather than restarting the listing: a cursor is only ever handed out by this read.
    """
    rows = session.execute(
        _EVENTS,
        {
            "after": after_event_id,
            "aggregate_type": AGGREGATE_TYPE,
            "types": list(ACCESS_EVENT_TYPES),
            "fetch": limit,
        },
    ).all()
    return tuple(_event(row) for row in rows)


def last_sign_in_times(session: Session, user_uids: Sequence[str]) -> Mapping[str, datetime]:
    """``{user_uid: the instant of that account's latest successful sign-in}``.

    One statement for the whole set. An account with no recorded sign-in is absent.
    """
    if not user_uids:
        return {}
    rows = session.execute(
        _LAST_SIGN_INS,
        {
            "aggregate_type": AGGREGATE_TYPE,
            "event_type": _SIGN_IN_SUCCEEDED,
            "uids": sorted(set(user_uids)),
        },
    ).all()
    return {str(uid): instant for uid, instant in rows}


def _event(row: object) -> AccessEvent:
    event_id, event_type, aggregate_id, occurred_at, payload = row  # type: ignore[misc]
    body = dict(payload)
    return AccessEvent(
        event_id=str(event_id),
        event_type=str(event_type),
        occurred_at=occurred_at,
        subject_uid=str(aggregate_id),
        actor_uid=body.get("actor_uid"),
        source=str(body["source"]),
        role=body.get("role"),
        failures=body.get("failures"),
        default_credential=body.get("default_credential"),
    )
