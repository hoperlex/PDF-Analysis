"""Reads over the executor tables: what a list shows, what a detail shows, what a run start
resolves. Nothing here writes except :func:`sweep`, which ends the probes nobody can still be
running (``ExecutorRepository.sweep_probes``) so that a stale ``requested`` is never shown.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from auditmanager.executors.model import (
    ConnectionSummary,
    ProbeRecord,
    ResolvedRoute,
    RevisionRecord,
    RouteRecord,
)
from auditmanager.executors.repository import PROBE_HISTORY, ExecutorRepository
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "ConnectionDetail",
    "connection_detail",
    "list_connection_summaries",
    "list_routes",
    "resolve_route",
    "sweep",
]


@dataclass(frozen=True, slots=True)
class ConnectionDetail:
    summary: ConnectionSummary
    revisions: tuple[RevisionRecord, ...]
    latest_probe_by_revision: dict[str, ProbeRecord]
    probes: tuple[ProbeRecord, ...]


def sweep(session: Session, repository: ExecutorRepository | None = None) -> int:
    """End the probes nobody took in 120 s (``no_worker``) or that outlived their timeout."""
    return (repository or ExecutorRepository()).sweep_probes(session)


def _summaries(
    session: Session, store: ExecutorRepository, connections: list,
) -> tuple[ConnectionSummary, ...]:
    ids = [connection.connection_id for connection in connections]
    revisions = store.current_revisions(session, ids)
    secrets = store.current_secrets(session, ids)
    routed: dict[str, list[str]] = {}
    for route in store.current_routes(session):
        for connection_id in (route.primary_connection_id, route.standby_connection_id):
            if connection_id is not None:
                routed.setdefault(connection_id, []).append(route.work_kind)
    return tuple(
        ConnectionSummary(
            connection=connection,
            current_revision=revisions.get(connection.connection_id),
            secrets=tuple(secrets.get(connection.connection_id, ())),
            routed_work_kinds=tuple(sorted(set(routed.get(connection.connection_id, ())))),
        )
        for connection in connections
    )


def list_connection_summaries(
    session: Session, repository: ExecutorRepository | None = None
) -> tuple[ConnectionSummary, ...]:
    store = repository or ExecutorRepository()
    return _summaries(session, store, store.list_connections(session))


def connection_detail(
    session: Session, connection_id: str, repository: ExecutorRepository | None = None
) -> ConnectionDetail:
    store = repository or ExecutorRepository()
    store.sweep_probes(session)
    connection = store.get_connection(session, connection_id)
    if connection is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="ExecutorConnection")
    (summary,) = _summaries(session, store, [connection])
    return ConnectionDetail(
        summary=summary,
        revisions=tuple(store.list_revisions(session, connection_id)),
        latest_probe_by_revision=store.latest_probe_by_revision(session, connection_id),
        probes=tuple(store.list_probes(session, connection_id, limit=PROBE_HISTORY)),
    )


def list_routes(
    session: Session, repository: ExecutorRepository | None = None
) -> tuple[RouteRecord, ...]:
    return tuple((repository or ExecutorRepository()).current_routes(session))


def resolve_route(
    session: Session, work_kind: str, repository: ExecutorRepository | None = None
) -> ResolvedRoute | None:
    """The route of a kind of model work with the current revision of each side, or ``None``
    when no route is set. A side that is archived or has no revision resolves to ``None`` and
    is not hidden: the caller decides (``EXEC-HTTP-01`` refuses with ``executor_route_missing``
    or journals the use of the standby). Nothing here falls back."""
    store = repository or ExecutorRepository()
    route = store.current_route(session, work_kind)
    if route is None:
        return None
    ids = [route.primary_connection_id] + (
        [route.standby_connection_id] if route.standby_connection_id else []
    )
    revisions = store.current_revisions(session, ids)
    live = {
        connection_id for connection_id in ids
        if (found := store.get_connection(session, connection_id)) is not None
        and found.archived_at is None
    }

    def side(connection_id: str | None) -> RevisionRecord | None:
        return revisions.get(connection_id) if connection_id in live else None

    return ResolvedRoute(
        work_kind=work_kind, primary=side(route.primary_connection_id),
        standby=side(route.standby_connection_id), route=route,
    )
