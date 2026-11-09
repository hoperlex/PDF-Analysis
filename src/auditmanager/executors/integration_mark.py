"""The administrator's mark that a ``pull`` connection's command-line clients are authorised for this
integration (`EXEC2-ENROLL-01`, ADR-0026 decision 8, owner ruling `R-149b`).

It is one of four distinct statuses and implies none of the other three: *installed*, *authentication valid*,
*authorised for this integration* (this mark) and *model probe passed*. Whether a client is installed and
signed in is what the agent reports (``enrollment.py``); whether it may be used for this integration is the
administrator's statement, and this module only records it. It is written on the connection
(``executor_connection.integration_authorised_at`` / ``_by``, migration ``0046``) as the **current** mark;
the history of setting and clearing it is the audit trail (``executor.integration_authorised`` and
``executor.integration_authorisation_cleared``).

Setting a mark that is set, or clearing one that is absent, changes and journals nothing and answers the
connection as it stands.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.executors.model import CONSTRAINT_KIND_NOT_PULL, refuse_system_object
from auditmanager.executors.repository import ExecutorRepository
from auditmanager.ingest.public import (
    CommandReplay,
    CommandRepository,
    payload_fingerprint,
)
from auditmanager.jobs.public import append_execution_event
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey

__all__ = [
    "IntegrationMark",
    "IntegrationMarkRepository",
    "integration_marks_of",
    "set_integration_authorisation",
]

_AGGREGATE: Final[str] = "ExecutorConnection"
Journal = Callable[..., None]


@dataclass(frozen=True, slots=True)
class IntegrationMark:
    """The current mark of one connection: when it was set and by whom."""

    connection_id: str
    authorised_at: datetime
    authorised_by: str


class IntegrationMarkRepository:
    """The two columns of ``executor_connection`` the mark lives in. Stateless; never commits."""

    def marks_of(
        self, session: Session, connection_ids: Sequence[str]
    ) -> dict[str, IntegrationMark]:
        """The marks that are set, by connection (read by ``ExecutorRepository.integration_marks``, which the
        connection summaries use too)."""
        found = ExecutorRepository().integration_marks(session, connection_ids)
        return {
            connection_id: IntegrationMark(
                connection_id=connection_id, authorised_at=authorised_at, authorised_by=authorised_by)
            for connection_id, (authorised_at, authorised_by) in found.items()
        }

    def set_mark(self, session: Session, connection_id: str, *, actor_uid: str) -> bool:
        """Set the mark; ``False`` when it was already set (nothing changed)."""
        return bool(session.execute(text(
            "UPDATE executor_connection SET integration_authorised_at = clock_timestamp(), "
            "integration_authorised_by = :actor WHERE connection_id = :id "
            "AND integration_authorised_at IS NULL"
        ), {"id": connection_id, "actor": actor_uid}).rowcount)

    def clear_mark(self, session: Session, connection_id: str) -> bool:
        """Clear the mark; ``False`` when there was none (nothing changed)."""
        return bool(session.execute(text(
            "UPDATE executor_connection SET integration_authorised_at = NULL, "
            "integration_authorised_by = NULL WHERE connection_id = :id "
            "AND integration_authorised_at IS NOT NULL"
        ), {"id": connection_id}).rowcount)


def _admin(roles: Iterable[str]) -> None:
    if "admin" not in set(roles):
        raise DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:admin")


def integration_marks_of(
    session: Session, connection_ids: Sequence[str],
    repository: IntegrationMarkRepository | None = None,
) -> dict[str, IntegrationMark]:
    """The marks that are set among these connections: for a read model that shows them."""
    return (repository or IntegrationMarkRepository()).marks_of(session, connection_ids)


def set_integration_authorisation(
    session: Session, *, connection_id: str, authorised: bool, roles: Iterable[str],
    idempotency_key: str, actor_uid: str, executors: ExecutorRepository | None = None,
    repository: IntegrationMarkRepository | None = None,
    commands: CommandRepository | None = None, journal: Journal = append_execution_event,
) -> IntegrationMark | None:
    """Set or clear the mark and return the mark as it now stands (``None`` when there is none).

    Refusals: ``permission_denied``; ``not_found``; ``conflict`` / ``connection_archived``;
    ``validation_failed`` on ``kind`` (``kind_not_pull``). A repeat of the key answers the mark as it stands
    now, as every keyed command here answers its resource."""
    _admin(roles)
    store, marks, ledger = (
        executors or ExecutorRepository(), repository or IntegrationMarkRepository(),
        commands or CommandRepository(),
    )
    claimed = ledger.begin(
        session, command_type="set_executor_integration_authorisation",
        idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint({"connection_id": connection_id, "authorised": authorised}),
    )
    connection = store.get_connection(session, connection_id, lock=True)
    if connection is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type=_AGGREGATE)
    if isinstance(claimed, CommandReplay):
        return marks.marks_of(session, [connection_id]).get(connection_id)
    if connection.system_managed:
        # The mark of a system connection is set by «Использовать» of its host, never by hand (`HOSTS-BACKEND-01`).
        raise refuse_system_object()
    if connection.archived_at is not None:
        raise DomainError(ErrorCode.CONFLICT, message="the connection is archived",
                          conflict_reason="connection_archived")
    if connection.kind != "pull":
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, message="only a pull connection takes the mark",
            field="kind", constraint=CONSTRAINT_KIND_NOT_PULL,
        )
    changed = (marks.set_mark(session, connection_id, actor_uid=actor_uid) if authorised
               else marks.clear_mark(session, connection_id))
    if changed:
        journal(
            session,
            event_type=("executor.integration_authorised" if authorised
                        else "executor.integration_authorisation_cleared"),
            aggregate_type=_AGGREGATE, aggregate_id=connection_id,
            payload={"connection_id": connection_id, "actor_uid": actor_uid},
        )
    ledger.succeed(session, claimed.command_id, {"connection_id": connection_id})
    return marks.marks_of(session, [connection_id]).get(connection_id)
