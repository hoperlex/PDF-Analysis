"""The access journal: six ``access.*`` events in ``audit_event`` (`PROD-06`, ADR-0023 section 4).

`R-146n` item 6, `AD-10`: sign-in, role grant and password change leave a row in the
append-only ``audit_event`` table, **in the transaction of the change they describe**. A
writer that opened its own connection, or that swallowed its own failure, would let the
change commit without its event, or the event commit without its change; this one takes the
caller's :class:`~sqlalchemy.orm.Session` and lets every error propagate, so the two commit
or roll back together.

Modelled on :mod:`auditmanager.jobs.events` and local to this context (nothing outside
``access`` writes these types, and no other context's allow-list is widened for them).

What a payload may hold
-----------------------
Identities (``usr_`` ids), controlled classifiers (``source``, ``role``), one boolean and one
count -- nothing else. **Never** a password, a digest, a token, a cookie, a registration's
names or e-mail, an IP address or a user agent. An IP address is deliberately absent: behind
a terminator it is the proxy's unless ``ALPHA_TRUSTED_PROXY_CIDRS`` is set correctly, so it
would be a wrong fact written into an append-only table. Three independent things keep it so:

1. each event type has its own **allow-list of keys** (:data:`PAYLOAD_KEYS`); a key outside it
   is refused before the INSERT, whatever the caller passes;
2. each key has a **value rule** (an identity must parse as a ``usr_`` id, a role must be in
   the closed vocabulary, ``source`` must be one of two words, a count must be an integer):
   a token or an address cannot be smuggled in under an allowed key;
3. the public entry points (``record_*``) take **typed arguments**, not a mapping, so a caller
   cannot hand the writer a free-form payload in the first place.

Correlation
-----------
``audit_event.correlation_id`` carries the request's correlation id so an event can be tied
to the server log. The id lives in the API's transport layer, which this context may not
import; :func:`bind_correlation_id` is the context-local seam the transport binds it
through. An event written with nothing bound (the host command, a unit call, a request whose
transport has not bound one) carries ``NULL`` -- the column is nullable and a missing id is
not an error, but it is also not invented.

What is not journalled (ADR-0023 section 4): registration approval and rejection as such,
archive, restore, purge and unlock; attempts that start no cooling-off period; attempts on an
unknown login.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.access.models import ROLES, is_user_uid
from auditmanager.shared.identity import AuditEventId, CorrelationId

__all__ = [
    "ACCESS_EVENT_TYPES",
    "AGGREGATE_TYPE",
    "PAYLOAD_KEYS",
    "SOURCE_API",
    "SOURCE_HOST_CLI",
    "bind_correlation_id",
    "correlation_scope",
    "record_password_changed",
    "record_password_reset",
    "record_role_granted",
    "record_role_revoked",
    "record_sign_in_blocked",
    "record_sign_in_succeeded",
    "reset_correlation_id",
]

#: ``audit_event.aggregate_type`` of every event here: the account, addressed by its ``usr_`` id.
AGGREGATE_TYPE: Final[str] = "Account"

#: Where the change came from: the served API, or ``python -m auditmanager.access.grant``.
SOURCE_API: Final[str] = "api"
SOURCE_HOST_CLI: Final[str] = "host_cli"
_SOURCES: Final[frozenset[str]] = frozenset({SOURCE_API, SOURCE_HOST_CLI})

#: ``event_type`` -> (keys that must be present, keys that may be present). The union over all
#: six is the allow-list a test scans the stored payloads against; the writer enforces the
#: per-type one.
PAYLOAD_KEYS: Final[Mapping[str, tuple[frozenset[str], frozenset[str]]]] = {
    "access.sign_in_succeeded": (
        frozenset({"subject_uid", "source", "default_credential"}),
        frozenset(),
    ),
    "access.sign_in_blocked": (
        frozenset({"subject_uid", "source", "failures"}),
        frozenset(),
    ),
    # ``actor_uid`` is absent for the host command: nobody signed in to run it.
    "access.role_granted": (
        frozenset({"subject_uid", "role", "source"}),
        frozenset({"actor_uid"}),
    ),
    "access.role_revoked": (
        frozenset({"subject_uid", "actor_uid", "role", "source"}),
        frozenset(),
    ),
    "access.password_changed": (
        frozenset({"subject_uid", "actor_uid", "source"}),
        frozenset(),
    ),
    "access.password_reset": (
        frozenset({"subject_uid", "actor_uid", "source"}),
        frozenset(),
    ),
}

#: The six event types, in the order ADR-0023 section 4 lists them.
ACCESS_EVENT_TYPES: Final[tuple[str, ...]] = tuple(PAYLOAD_KEYS)

_INSERT = text(
    "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, aggregate_id, "
    "correlation_id, payload) VALUES (:event_id, :event_type, :aggregate_type, "
    ":aggregate_id, :correlation_id, CAST(:payload AS jsonb))"
)

#: The request being served, as the transport bound it; ``None`` outside a bound scope.
_CORRELATION: ContextVar[str | None] = ContextVar(
    "auditmanager_access_correlation_id", default=None
)


def bind_correlation_id(value: str) -> Token[str | None]:
    """Make ``value`` the correlation id of every event written in this context, until reset.

    A value that is not a contract ``CorrelationId`` is refused rather than dropped: an id the
    column's own CHECK would refuse must not turn into a missing id at INSERT time, far from
    the caller that bound it.
    """
    return _CORRELATION.set(str(CorrelationId.parse(value)))


def reset_correlation_id(token: Token[str | None]) -> None:
    """Undo one :func:`bind_correlation_id`."""
    _CORRELATION.reset(token)


@contextmanager
def correlation_scope(value: str) -> Iterator[None]:
    """:func:`bind_correlation_id` for the length of a ``with`` block."""
    token = bind_correlation_id(value)
    try:
        yield
    finally:
        reset_correlation_id(token)


def _user_uid(name: str, value: object) -> str:
    if not is_user_uid(value):
        raise ValueError(f"access journal: {name} is not a user identity")
    return str(value)


def _validated(event_type: str, payload: Mapping[str, object]) -> dict[str, object]:
    required, optional = PAYLOAD_KEYS[event_type]
    keys = set(payload)
    if not required <= keys:
        raise ValueError(f"access journal: {event_type} lacks {sorted(required - keys)}")
    if not keys <= required | optional:
        raise ValueError(
            f"access journal: {event_type} payload contains a non-allowlisted field "
            f"{sorted(keys - (required | optional))}"
        )
    checked: dict[str, object] = {}
    for key, value in payload.items():
        if key in ("subject_uid", "actor_uid"):
            checked[key] = _user_uid(key, value)
        elif key == "role":
            if value not in ROLES:
                raise ValueError("access journal: role is outside the closed vocabulary")
            checked[key] = value
        elif key == "source":
            if value not in _SOURCES:
                raise ValueError("access journal: source is outside the closed vocabulary")
            checked[key] = value
        elif key == "default_credential":
            if not isinstance(value, bool):
                raise ValueError("access journal: default_credential must be a boolean")
            checked[key] = value
        elif key == "failures":
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError("access journal: failures must be a positive integer")
            checked[key] = value
        else:  # pragma: no cover - PAYLOAD_KEYS and this chain are kept equal by a test
            raise ValueError(f"access journal: no value rule for {key!r}")
    return checked


def _append(session: Session, *, event_type: str, payload: Mapping[str, object]) -> None:
    """INSERT one event on the caller's session. It never commits and never swallows."""
    checked = _validated(event_type, payload)
    session.execute(
        _INSERT,
        {
            "event_id": str(AuditEventId.new()),
            "event_type": event_type,
            "aggregate_type": AGGREGATE_TYPE,
            "aggregate_id": checked["subject_uid"],
            "correlation_id": _CORRELATION.get(),
            "payload": json.dumps(checked, sort_keys=True),
        },
    )


def record_sign_in_succeeded(
    session: Session, *, subject_uid: str, default_credential: bool
) -> None:
    """``issueToken`` accepted a password. ``default_credential``: still the seeded or reset one."""
    _append(
        session,
        event_type="access.sign_in_succeeded",
        payload={
            "subject_uid": subject_uid,
            "source": SOURCE_API,
            "default_credential": default_credential,
        },
    )


def record_sign_in_blocked(session: Session, *, subject_uid: str, failures: int) -> None:
    """A failed attempt on a known account started a cooling-off period (at most once per period)."""
    _append(
        session,
        event_type="access.sign_in_blocked",
        payload={"subject_uid": subject_uid, "source": SOURCE_API, "failures": failures},
    )


def record_role_granted(
    session: Session, *, subject_uid: str, role: str, actor_uid: str | None, source: str
) -> None:
    """A role was added: ``actor_uid`` is the administrator, or ``None`` for the host command."""
    payload: dict[str, object] = {"subject_uid": subject_uid, "role": role, "source": source}
    if actor_uid is not None:
        payload["actor_uid"] = actor_uid
    _append(session, event_type="access.role_granted", payload=payload)


def record_role_revoked(
    session: Session, *, subject_uid: str, role: str, actor_uid: str
) -> None:
    """An administrator removed a role."""
    _append(
        session,
        event_type="access.role_revoked",
        payload={
            "subject_uid": subject_uid,
            "actor_uid": actor_uid,
            "role": role,
            "source": SOURCE_API,
        },
    )


def record_password_changed(session: Session, *, subject_uid: str) -> None:
    """``changePassword`` succeeded; the actor is the account itself."""
    _append(
        session,
        event_type="access.password_changed",
        payload={"subject_uid": subject_uid, "actor_uid": subject_uid, "source": SOURCE_API},
    )


def record_password_reset(session: Session, *, subject_uid: str, actor_uid: str) -> None:
    """``resetUserPassword``: an administrator set a temporary password."""
    _append(
        session,
        event_type="access.password_reset",
        payload={"subject_uid": subject_uid, "actor_uid": actor_uid, "source": SOURCE_API},
    )
