"""Translating a database refusal into the frozen catalog code.

``docs/program/P02_SEAMS.md`` section 3.2: the P02 migration head raises three custom
SQLSTATEs, and a caller **maps on the SQLSTATE, never on the message text**. This
module is the one place in the ingest slice that does that translation, so there is a
single site to read when asking how a trigger becomes a
:class:`~auditmanager.shared.errors.DomainError`.

Two rules are structural here rather than reviewed:

* the mapping is :data:`auditmanager.shared.db.schema.SQLSTATE_TO_CATALOG_CODE`, read
  from the shared kernel. This module does not restate it, because a restatement is a
  second place to be wrong;
* the envelope ``details`` are supplied by the *caller*, which knows which machine and
  which states it was asking about. Nothing is scraped out of the driver's message, so
  no fragment of SQL, no table name and no row value can ride out to a caller.

A refusal that is not one of the three custom SQLSTATEs is not translated: it is a
genuine integrity or availability fault and belongs to the caller's own handling.
"""

from __future__ import annotations

from typing import Any, Final

from sqlalchemy.exc import DBAPIError, IntegrityError

from auditmanager.shared.db.schema import (
    SQLSTATE_APPEND_ONLY_VIOLATION,
    SQLSTATE_IMMUTABLE_ROW_VIOLATION,
    SQLSTATE_TO_CATALOG_CODE,
    SQLSTATE_UNDECLARED_TRANSITION,
)
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "SQLSTATE_APPEND_ONLY_VIOLATION",
    "SQLSTATE_IMMUTABLE_ROW_VIOLATION",
    "SQLSTATE_UNDECLARED_TRANSITION",
    "UNIQUE_VIOLATION",
    "constraint_name_of",
    "domain_error_for",
    "sqlstate_of",
    "translate_database_refusal",
]

#: PostgreSQL's own ``unique_violation``. Not a custom guard: it is how the schema's
#: uniqueness invariants -- the command key, the version ordinal, the available-content
#: index -- announce themselves.
UNIQUE_VIOLATION: Final[str] = "23505"


def sqlstate_of(exc: BaseException) -> str | None:
    """The five-character SQLSTATE carried by a driver error, or ``None``.

    Reads the driver's structured field. It never inspects the message: the message is
    prose that may be localised, reworded by a PostgreSQL upgrade, or carry a row value.
    """
    original: Any = getattr(exc, "orig", exc)
    for attribute in ("sqlstate", "pgcode"):
        value = getattr(original, attribute, None)
        if isinstance(value, str) and value:
            return value
    diagnostic = getattr(original, "diag", None)
    value = getattr(diagnostic, "sqlstate", None)
    return value if isinstance(value, str) and value else None


def constraint_name_of(exc: BaseException) -> str | None:
    """The name of the constraint a refusal names, from the driver's diagnostics.

    Constraint names are deterministic here -- ``auditmanager.shared.db.schema``
    pins a naming convention precisely so a caller can branch on one -- and a name is
    schema vocabulary, never row data. It is still never rendered into a caller-visible
    message; it only selects which typed failure to raise.
    """
    original: Any = getattr(exc, "orig", exc)
    diagnostic = getattr(original, "diag", None)
    value = getattr(diagnostic, "constraint_name", None)
    return value if isinstance(value, str) and value else None


def domain_error_for(sqlstate: str, **details: Any) -> DomainError | None:
    """The typed failure one custom SQLSTATE maps to, or ``None`` if it is not ours."""
    code = SQLSTATE_TO_CATALOG_CODE.get(sqlstate)
    if code is None:
        return None
    return DomainError(ErrorCode(code), **details)


def translate_database_refusal(
    exc: DBAPIError | IntegrityError | BaseException,
    **details: Any,
) -> DomainError | None:
    """Map a driver refusal to a :class:`DomainError`, or ``None`` when it is not ours.

    ``details`` are the caller's own, screened by the envelope against the reported
    code's ``safe_detail_keys``. For ``state_transition_not_allowed`` those are
    ``machine``, ``current_state`` and ``requested_state``.
    """
    sqlstate = sqlstate_of(exc)
    if sqlstate is None:
        return None
    return domain_error_for(sqlstate, **details)
