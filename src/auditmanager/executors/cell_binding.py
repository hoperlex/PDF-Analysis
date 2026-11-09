"""Binding every cell of a planned run to a server, at dispatch (`HOSTS-BACKEND-01`, ADR-0028 decisions 4, 5, 15 and 16).

A run started under the stage layout freezes ``audit_run.stage_plan``; this module reads only ``cells[*]`` of it -- the cell key, the model and the
access. At dispatch, in the claim transaction, **every cell is bound at once**, each to a member of the system group of its (model, access); the
result is written once to ``audit_run_cell_binding`` (a trigger refuses a second write) and ``binding_state`` moves ``pending`` -> ``bound``, which
the database allows only when every cell has its row. If one cell has no member to take it, **nothing is bound**: the run stays ``pending`` and
says why. No attempt is spent by waiting, because the Attempt is created after the binding, in the same transaction, and a refused claim writes
nothing.

**The unit of capacity** is the pair (run, ``capacity_pool``), the pool being ``<host_id>:<provider>``; a pool has as many units as the host's
slots of the provider (``hosts.slots_in_force``). A run takes one unit in each pool its cells use, however many cells share a pool (calls of a run are
sequential), and keeps it until its Job ends. The decision is taken under the pool locks (:func:`pools_of`: every pool a cell *might* be bound
in, locked in ascending order by the caller), so two binds on one subscription cannot both pass.

**Which member.** Among the members of the cell's system group that are not archived, whose snapshot is the connection's current revision and
that are available (``hosts.model_reasons`` is empty), the cell prefers a pool its run already holds (it costs no unit) and otherwise takes the
member of the least loaded pool (``group_selection.choose``), ties broken by a stateless hash of the run and the cell -- no group row is locked, so
the lock order of ADR-0028 decision 15 holds (worker intake, pools ascending, control, run, job).

**The wait.** :class:`CellWait` names each cell that cannot be bound and the cause. The run's wait reason is ``model_unavailable`` when *any* cell has
no available member at all (offline, no login, switched off, not verified, cooling down, on no server): the 30-minute expiry of `R-149c` applies to
it. It is ``executor_at_capacity`` when every cell has an available member and the only trouble is that the pools are full: waiting for capacity never
expires (ADR-0026 decision 15). This is the one place the wording of the task file («any cell lacks a free eligible member -> ``model_unavailable``») was
read narrowly; :data:`CAPACITY_WAIT_REASON` is the switch.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.executors.group_selection import GroupMember, choose
from auditmanager.executors.host_commands import HostFacts, member_reasons, read_hosts
from auditmanager.executors.host_repository import HostRepository
from auditmanager.executors.hosts import (
    ACCESSES,
    REASON_NOT_ON_ANY_SERVER,
    REASON_ORDER,
    access_of_billing,
    pair_group_name,
    split_pool,
)
from auditmanager.executors.repository import ExecutorRepository
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "AT_CAPACITY",
    "BindOutcome",
    "BoundCell",
    "CAPACITY_WAIT_REASON",
    "CellRequest",
    "CellWait",
    "WAIT_MODEL_UNAVAILABLE",
    "bind_cells",
    "bound_pools_of_run",
    "cell_binding_of",
    "cell_requests",
    "evaluate_wait",
    "pool_has_room",
    "pools_of",
    "write_bindings",
]

#: The wait reason of a planned run with a cell that no available member can take (``RunQueueReason`` of the contract).
WAIT_MODEL_UNAVAILABLE: Final[str] = "model_unavailable"
#: The cause given for a cell whose members are available and whose pools are full (a ``CellWait.cause``).
AT_CAPACITY: Final[str] = "at_capacity"
#: What a run waits with when the only trouble is full pools. ``executor_at_capacity`` never expires; set to :data:`WAIT_MODEL_UNAVAILABLE` to
#: have the 30-minute expiry apply to a full pool as well (the literal reading of the task file).
CAPACITY_WAIT_REASON: Final[str] = "executor_at_capacity"


@dataclass(frozen=True, slots=True)
class CellRequest:
    """One cell of a plan as binding reads it."""

    cell_key: str
    model_id: str
    access: str


@dataclass(frozen=True, slots=True)
class BoundCell:
    """The member a cell is bound to (the row of ``audit_run_cell_binding`` and what ``binding_for(cell)`` reads back)."""

    cell_key: str
    group_revision_id: str
    connection_id: str
    connection_revision_id: str
    host_id: str
    provider: str
    access: str
    model_id: str

    @property
    def pool(self) -> str:
        return f"{self.host_id}:{self.provider}"


@dataclass(frozen=True, slots=True)
class CellWait:
    """A cell that cannot be bound now and why: a ``ModelUnavailableReason`` word, or :data:`AT_CAPACITY`."""

    cell_key: str
    model_id: str
    access: str
    cause: str


@dataclass(frozen=True, slots=True)
class BindOutcome:
    """The decision: every cell bound, or the run's wait reason and the cells that wait. Exactly one of ``bound`` and ``reason`` is set."""

    bound: tuple[BoundCell, ...] | None
    reason: str | None
    waits: tuple[CellWait, ...] = ()


@dataclass(frozen=True, slots=True)
class _Candidate:
    """One member of a cell's system group, with what decides whether it may take the cell now."""

    connection_id: str
    connection_revision_id: str
    host_id: str
    provider: str
    pool: str
    reasons: tuple[str, ...]
    in_service: bool


def cell_requests(stage_plan: Mapping[str, Any]) -> list[CellRequest]:
    """The cells of a frozen plan, in the plan's order. A cell that names no model or no access is the plan's defect and is refused, never repaired."""
    found: list[CellRequest] = []
    for cell in stage_plan.get("cells", ()):
        key, model, access = cell.get("cell_key"), cell.get("model_id"), cell.get("access")
        if not isinstance(key, str) or not isinstance(model, str) or access not in ACCESSES:
            raise DomainError(ErrorCode.INTERNAL_ERROR, message="a cell of the stage plan has no key, model or access")
        found.append(CellRequest(key, model, access))
    return found


# --- what is read: the system group of each pair, its members, and what is true of each now -----------------------------------


def _current_group(session: Session, model_id: str, access: str) -> tuple[str, list[tuple[str, str]]] | None:
    """``(group revision id, [(connection id, connection revision id)])`` of the live system group of the pair, or ``None``."""
    row = session.execute(text(
        "SELECT g.group_id, v.group_revision_id FROM executor_group g "
        "JOIN LATERAL (SELECT r.group_revision_id FROM executor_group_revision r WHERE r.group_id = g.group_id "
        "ORDER BY r.revision_no DESC LIMIT 1) v ON true "
        "WHERE g.system_managed AND g.archived_at IS NULL AND g.display_name = :name"
    ), {"name": pair_group_name(model_id, access)}).first()
    if row is None:
        return None
    members = session.execute(text(
        "SELECT connection_id, connection_revision_id FROM executor_group_member WHERE group_revision_id = :rev "
        "ORDER BY connection_id"), {"rev": row[1]}).all()
    return str(row[1]), [(str(item[0]), str(item[1])) for item in members]


def pools_of(session: Session, cells: Sequence[CellRequest]) -> list[str]:
    """Every pool a cell might be bound in: the pool of each member of the current revision of each cell's system group, sorted ascending. An
    unlocked read; the caller locks them in this order, reads it again under the locks and locks what is new (a group revised in between)."""
    pools: set[str] = set()
    for model_id, access in sorted({(cell.model_id, cell.access) for cell in cells}):
        group = _current_group(session, model_id, access)
        if group is None:
            continue
        rows = session.execute(text(
            "SELECT DISTINCT capacity_pool FROM executor_connection WHERE connection_id = ANY(:ids) AND capacity_pool IS NOT NULL"
        ), {"ids": [cid for cid, _ in group[1]]}).all()
        pools.update(str(row[0]) for row in rows)
    return sorted(pools)


def bound_pools_of_run(session: Session, run_id: str) -> list[str]:
    """The pools a bound run's cells are bound in, sorted ascending: what the claim of its retry locks."""
    rows = session.execute(text(
        "SELECT DISTINCT c.capacity_pool FROM audit_run_cell_binding b "
        "JOIN executor_connection_revision rev ON rev.revision_id = b.connection_revision_id "
        "JOIN executor_connection c ON c.connection_id = rev.connection_id "
        "WHERE b.run_id = :run AND c.capacity_pool IS NOT NULL ORDER BY c.capacity_pool"), {"run": run_id}).all()
    return [str(row[0]) for row in rows]


def _candidates(
    session: Session, cells: Sequence[CellRequest], *, execs: ExecutorRepository, hosts: HostRepository,
) -> tuple[dict[tuple[str, str], tuple[str, list[_Candidate]]], dict[str, HostFacts]]:
    """For each (model, access) of the cells: the group revision and its members with their reasons; and the facts of every host involved."""
    groups = {pair: _current_group(session, *pair) for pair in sorted({(c.model_id, c.access) for c in cells})}
    connection_ids = sorted({cid for group in groups.values() if group is not None for cid, _ in group[1]})
    connections = {cid: execs.get_connection(session, cid) for cid in connection_ids}
    currents = execs.current_revisions(session, connection_ids)
    host_ids = sorted({conn.host_id for conn in connections.values() if conn is not None and conn.host_id is not None})
    facts = {item.record.host_id: item for item in read_hosts(session, host_ids, repo=hosts, include_archived=True)}
    found: dict[tuple[str, str], tuple[str, list[_Candidate]]] = {}
    for pair, group in groups.items():
        if group is None:
            continue
        members: list[_Candidate] = []
        for connection_id, snapshot in group[1]:
            connection = connections.get(connection_id)
            if connection is None or connection.host_id is None or connection.capacity_pool is None:
                continue
            host_id, provider = split_pool(connection.capacity_pool)
            host = facts.get(host_id)
            current = currents.get(connection_id)
            in_service = (
                connection.archived_at is None and host is not None and host.record.archived_at is None
                and current is not None and current.revision_id == snapshot)
            reasons: list[str] = []
            if host is not None and current is not None:
                reasons, _full = member_reasons(host, provider=provider, access=pair[1], model_id=pair[0])
            members.append(_Candidate(
                connection_id=connection_id, connection_revision_id=snapshot, host_id=host_id, provider=provider,
                pool=connection.capacity_pool, reasons=tuple(reasons), in_service=in_service))
        found[pair] = (group[0], members)
    return found, facts


def _cause_of(members: Sequence[_Candidate]) -> str:
    """The reason a cell with no available member waits for: the most actionable one of the member closest to being available."""
    live = [item for item in members if item.in_service]
    if not live:
        return REASON_NOT_ON_ANY_SERVER
    closest = min(live, key=lambda item: (len(item.reasons), item.connection_id))
    return min(closest.reasons, key=REASON_ORDER.index) if closest.reasons else REASON_NOT_ON_ANY_SERVER


def _rotation(run_id: str, cell_key: str) -> int:
    """A stateless tie-break: the same run and cell always give the same number, different cells and runs spread."""
    return int(hashlib.sha256(f"{run_id}|{cell_key}".encode()).hexdigest()[:12], 16)


# --- the decision -----------------------------------------------------------------------------------------------------


def _decide(
    run_id: str, cells: Sequence[CellRequest], groups: Mapping[tuple[str, str], tuple[str, list[_Candidate]]],
    facts: Mapping[str, HostFacts],
) -> BindOutcome:
    """Pure over what was read: every cell bound, or the cells that wait and the run's reason. The pools' units in use are the facts' (they
    exclude this run: a pending run holds none, and a bound run's retry is decided with the units of the *other* runs, see ``jobs``)."""
    held: set[str] = set()
    bound: list[BoundCell] = []
    waits: list[CellWait] = []
    for cell in cells:
        group = groups.get((cell.model_id, cell.access))
        members = [] if group is None else group[1]
        available = [item for item in members if item.in_service and not item.reasons]
        if not available:
            waits.append(CellWait(cell.cell_key, cell.model_id, cell.access, _cause_of(members)))
            continue

        def room(item: _Candidate) -> tuple[int, int]:
            slot = facts[item.host_id].slot_of(item.provider)
            return (0, 1) if slot is None else (slot.in_use, slot.slots)

        free = [item for item in available if item.pool in held or room(item)[0] < room(item)[1]]
        if not free:
            waits.append(CellWait(cell.cell_key, cell.model_id, cell.access, AT_CAPACITY))
            continue
        preferred = [item for item in free if item.pool in held] or free
        used = {item.connection_id: 0 if item.pool in held else room(item)[0] for item in preferred}
        capacity = {item.connection_id: max(1, room(item)[1]) for item in preferred}
        chosen_id = choose(
            [GroupMember(item.connection_id) for item in preferred], used, capacity, _rotation(run_id, cell.cell_key))
        assert group is not None and chosen_id is not None
        chosen = next(item for item in preferred if item.connection_id == chosen_id)
        held.add(chosen.pool)
        bound.append(BoundCell(
            cell_key=cell.cell_key, group_revision_id=group[0], connection_id=chosen.connection_id,
            connection_revision_id=chosen.connection_revision_id, host_id=chosen.host_id, provider=chosen.provider,
            access=cell.access, model_id=cell.model_id))
    if waits:
        unavailable = any(item.cause != AT_CAPACITY for item in waits)
        return BindOutcome(bound=None, reason=WAIT_MODEL_UNAVAILABLE if unavailable else CAPACITY_WAIT_REASON, waits=tuple(waits))
    return BindOutcome(bound=tuple(bound), reason=None)


def bind_cells(
    session: Session, *, run_id: str, cells: Sequence[CellRequest], execs: ExecutorRepository | None = None,
    hosts: HostRepository | None = None,
) -> BindOutcome:
    """Decide the binding of every cell of a planned run, **under the pool locks the caller holds** (:func:`pools_of`). Writes nothing.

    Every cell is bound or none is: a cell with no available member, or whose pools are all full, makes the outcome a wait naming that cell and
    the cause. See the module note for which wait reason follows."""
    store, host_store = execs or ExecutorRepository(), hosts or HostRepository()
    groups, facts = _candidates(session, cells, execs=store, hosts=host_store)
    return _decide(run_id, cells, groups, facts)


def evaluate_wait(
    session: Session, *, run_id: str, cells: Sequence[CellRequest], execs: ExecutorRepository | None = None,
    hosts: HostRepository | None = None,
) -> BindOutcome:
    """What binding would decide **now**, without a lock and without a write: the sweep's reading of a pending planned run, and the run's wait
    detail (the cells and the causes) for whoever shows it. The binding itself re-decides under the locks."""
    return bind_cells(session, run_id=run_id, cells=cells, execs=execs, hosts=hosts)


def write_bindings(session: Session, *, run_id: str, bound: Sequence[BoundCell]) -> None:
    """Write the rows of ``audit_run_cell_binding``, once, in the transaction that binds the run. The database refuses a row for a run that is
    not pending with a plan, for a cell that is not the plan's, and for a member that is not a system member of the group revision pinning the
    cell's model; and refuses every update and delete."""
    for item in bound:
        session.execute(text(
            "INSERT INTO audit_run_cell_binding (run_id, cell_key, group_revision_id, connection_revision_id) "
            "VALUES (:run, :cell, :group, :revision)"
        ), {"run": run_id, "cell": item.cell_key, "group": item.group_revision_id, "revision": item.connection_revision_id})


def pool_has_room(
    session: Session, pool: str, *, exclude_run_id: str, hosts: HostRepository | None = None,
) -> bool:
    """Does the pool have a unit for the run: the units the *other* runs and the comparison calls hold are fewer than the slots? Asked under the
    pool's lock (the retry of a bound run: its own unit is not held while its Job is queued)."""
    store = hosts or HostRepository()
    return store.pool_units(session, pool, exclude_run_id=exclude_run_id) < store.pool_slots(session, pool)


def cell_binding_of(session: Session, run_id: str, cell_key: str) -> BoundCell | None:
    """The member a cell of a run was bound to, read back (what ``binding_for(cell)`` uses), or ``None`` while the run is unbound."""
    row = session.execute(text(
        "SELECT b.cell_key, b.group_revision_id, rev.connection_id, b.connection_revision_id, c.capacity_pool, rev.billing, rev.pin_id "
        "FROM audit_run_cell_binding b JOIN executor_connection_revision rev ON rev.revision_id = b.connection_revision_id "
        "JOIN executor_connection c ON c.connection_id = rev.connection_id WHERE b.run_id = :run AND b.cell_key = :cell"
    ), {"run": run_id, "cell": cell_key}).first()
    if row is None:
        return None
    host_id, provider = split_pool(str(row[4]))
    return BoundCell(
        cell_key=str(row[0]), group_revision_id=str(row[1]), connection_id=str(row[2]), connection_revision_id=str(row[3]),
        host_id=host_id, provider=provider, access=access_of_billing(str(row[5])), model_id=str(row[6]))
