"""The application-level transition guard.

The database is the enforcement: SQLSTATE ``AM001`` fires on an undeclared edge or a
non-initial INSERT, and no code path can bypass it. This guard exists to refuse the same
move *earlier*, with the typed catalog code already attached, so a caller learns what it
did wrong instead of reading a ``DBAPIError``.

It is deliberately not a second source of truth: it reads the topology the trigger reads.
"""

from __future__ import annotations

from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.statemachine.topology import Topology


def _refuse(detail: str) -> None:
    raise DomainError(ErrorCode.STATE_TRANSITION_NOT_ALLOWED, message=detail)


def assert_initial(topology: Topology, machine: str, state: str) -> None:
    """An aggregate may only be created in a declared initial state."""
    allowed = topology.initial_states(machine)
    if not allowed:
        _refuse(f"{machine} declares no initial state in the contract topology")
    if state not in allowed:
        _refuse(
            f"{machine} may only be created in {sorted(allowed)}; {state!r} was requested"
        )


def assert_transition(topology: Topology, machine: str, from_state: str, to_state: str) -> None:
    """Refuse an edge the contract does not declare."""
    if machine not in topology.machines:
        _refuse(f"{machine!r} is not one of the machines PC-01 instantiates")
    if topology.is_terminal(machine, from_state):
        _refuse(f"{machine} {from_state!r} is terminal; it is never reopened")
    if not topology.declares(machine, from_state, to_state):
        allowed = sorted(topology.successors(machine, from_state))
        _refuse(
            f"{machine} declares no edge {from_state!r} -> {to_state!r}; "
            f"from {from_state!r} the contract allows {allowed}"
        )
