"""Reads over the executor tables: what a list shows, what a detail shows, what a run start
resolves. Nothing here writes except :func:`sweep`, which ends the probes nobody can still be
running (``ExecutorRepository.sweep_probes``) so that a stale ``requested`` is never shown.

`EXEC2-CAP-01` (ADR-0026 decision 1) adds the capacity reads: :func:`used_units` and
:func:`capacity_of` for a caller that has to decide on one connection (``EXEC2-GROUP-RUN-01`` and
``EXEC2-GROUP-CMP-01`` import them), :func:`occupancies` for the connection read models and
:func:`run_queue_reason` for a Run's status. All of them are derived from the database at the moment
they are called and are stored nowhere.
"""

from __future__ import annotations

from collections.abc import Sequence
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
    "QUEUE_AT_CAPACITY",
    "QUEUE_RUNNER_OFFLINE",
    "ConnectionDetail",
    "Occupancy",
    "OccupiedConnectionSummary",
    "RunExecutor",
    "capacity_of",
    "connection_detail",
    "executor_of_revision",
    "list_connection_summaries",
    "list_routes",
    "occupancies",
    "occupancy_of",
    "resolve_route",
    "run_queue_reason",
    "sweep",
    "used_units",
]

#: ``RunQueueReason`` of the contract (``model.QUEUE_REASONS``; a unit test holds them equal).
QUEUE_AT_CAPACITY = "executor_at_capacity"
QUEUE_RUNNER_OFFLINE = "runner_offline"


@dataclass(frozen=True, slots=True)
class Occupancy:
    """``ExecutorOccupancy`` of the contract: the capacity of a connection and what is using it.

    A *unit* is a Run in ``leased``, ``running`` or ``retry_wait`` or a comparison model call in
    ``prepared`` or ``sent`` whose attempt is live; each counts one for its whole life. The connection
    is full when the two counts reach the capacity of its current revision.
    """

    capacity: int
    active_runs: int
    active_calls: int

    @property
    def used(self) -> int:
        return self.active_runs + self.active_calls

    @property
    def has_free_unit(self) -> bool:
        return self.used < self.capacity


@dataclass(frozen=True, slots=True, kw_only=True)
class OccupiedConnectionSummary(ConnectionSummary):
    """A :class:`ConnectionSummary` that also carries the connection's occupancy at read time."""

    occupancy: Occupancy


@dataclass(frozen=True, slots=True)
class ConnectionDetail:
    summary: OccupiedConnectionSummary
    revisions: tuple[RevisionRecord, ...]
    latest_probe_by_revision: dict[str, ProbeRecord]
    probes: tuple[ProbeRecord, ...]


@dataclass(frozen=True, slots=True)
class RunExecutor:
    """Which executor a run is on, for a run's status (`EXEC-PAR-START-01`): the connection, the
    name an administrator gave it and the model its revision pins. Nothing else -- no kind, no
    address, no key, no probe."""

    connection_id: str
    display_name: str
    pin_id: str


def executor_of_revision(
    session: Session, revision_id: str, repository: ExecutorRepository | None = None
) -> RunExecutor | None:
    """The executor a frozen revision belongs to, or ``None`` when the revision (or its
    connection) is not there. The revision is the run's frozen one, so an archived connection
    still answers: the run was on it."""
    store = repository or ExecutorRepository()
    revision = store.get_revision(session, revision_id)
    if revision is None:
        return None
    connection = store.get_connection(session, revision.connection_id)
    if connection is None:
        return None
    return RunExecutor(
        connection_id=connection.connection_id, display_name=connection.display_name,
        pin_id=revision.settings.pin_id,
    )


def sweep(session: Session, repository: ExecutorRepository | None = None) -> int:
    """End the probes nobody took in 120 s (``no_worker``) or that outlived their timeout."""
    return (repository or ExecutorRepository()).sweep_probes(session)


def _summaries(
    session: Session, store: ExecutorRepository, connections: list,
) -> tuple[OccupiedConnectionSummary, ...]:
    ids = [connection.connection_id for connection in connections]
    revisions = store.current_revisions(session, ids)
    secrets = store.current_secrets(session, ids)
    counts = store.unit_counts(session, ids)
    routed: dict[str, list[str]] = {}
    for route in store.current_routes(session):
        for connection_id in (route.primary_connection_id, route.standby_connection_id):
            if connection_id is not None:
                routed.setdefault(connection_id, []).append(route.work_kind)
    return tuple(
        OccupiedConnectionSummary(
            connection=connection,
            current_revision=revisions.get(connection.connection_id),
            secrets=tuple(secrets.get(connection.connection_id, ())),
            routed_work_kinds=tuple(sorted(set(routed.get(connection.connection_id, ())))),
            occupancy=Occupancy(*counts[connection.connection_id]),
        )
        for connection in connections
    )


def list_connection_summaries(
    session: Session, repository: ExecutorRepository | None = None
) -> tuple[OccupiedConnectionSummary, ...]:
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


# --- capacity (`EXEC2-CAP-01`, ADR-0026 decision 1) --------------------------------------------------------------


def occupancies(
    session: Session, connection_ids: Sequence[str], repository: ExecutorRepository | None = None
) -> dict[str, Occupancy]:
    """The occupancy of each named connection, in one statement. A connection that does not exist is
    absent from the answer."""
    store = repository or ExecutorRepository()
    return {
        connection_id: Occupancy(*counts)
        for connection_id, counts in store.unit_counts(session, connection_ids).items()
    }


def occupancy_of(
    session: Session, connection_id: str, repository: ExecutorRepository | None = None
) -> Occupancy:
    """The occupancy of one connection; ``not_found`` for one that does not exist."""
    found = occupancies(session, [connection_id], repository).get(connection_id)
    if found is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="ExecutorConnection")
    return found


def used_units(
    session: Session, connection_id: str, repository: ExecutorRepository | None = None
) -> int:
    """How many units of the connection are in use now: its Runs in ``leased``, ``running`` or
    ``retry_wait`` plus its comparison model calls in ``prepared`` or ``sent`` whose attempt is live.

    This is the number the Run claim, the dispatcher hint and the comparison call compare with
    :func:`capacity_of` under the connection's advisory lock. Called without that lock it is a
    reading, not a reservation: a caller that must not oversubscribe takes the lock first
    (``EXEC2-GROUP-RUN-01`` does, inside the claim transaction)."""
    return occupancy_of(session, connection_id, repository).used


def capacity_of(
    session: Session, connection_id: str, repository: ExecutorRepository | None = None
) -> int:
    """``max_active_runs`` of the connection's **current** revision, 1 when that is absent (a revision
    written before the setting existed, or a connection with no revision). A lowered capacity governs new
    claims only and never stops work in flight."""
    return occupancy_of(session, connection_id, repository).capacity


def run_queue_reason(
    session: Session, run_id: str, repository: ExecutorRepository | None = None
) -> str | None:
    """Why a Run waits for its executor, derived now (``RunQueueReason`` of the contract).

    ``runner_offline`` when its connection is a ``pull`` connection and none of its runner tokens was seen
    recently; otherwise ``executor_at_capacity`` when the connection has no free unit; otherwise ``None``,
    which is also the answer for a Run that is not waiting (running, ended, or of the ``environment``
    source, which froze no connection). An offline runner is named first even when the connection is also
    full (the EXEC-2 integrator's ruling): it is the cause an administrator can act on, since the units held
    by a connection nobody serves will not free until its work times out."""
    store = repository or ExecutorRepository()
    found = store.queued_run_connection(session, run_id)
    if found is None:
        return None
    connection_id, kind = found
    if kind == "pull" and not store.runner_online(session, connection_id):
        return QUEUE_RUNNER_OFFLINE
    if not occupancy_of(session, connection_id, store).has_free_unit:
        return QUEUE_AT_CAPACITY
    return None
