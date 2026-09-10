"""The declared state topology, read from the database that enforces it.

``contract_state_transition`` is seeded by the migration from
``contracts/domain/v1/state-machines.json`` and frozen against further inserts. The
database trigger consults it, and so does this module: reading the same rows is what
stops the application guard and the trigger from drifting into disagreement. A second
copy of the topology in Python would be a second place to be wrong.

A ``NULL`` ``from_state`` declares the initial state - the only state an INSERT may
create. A state with no outgoing row is terminal by construction, not by a list.
"""

from __future__ import annotations

from typing import Final, Mapping

from sqlalchemy import text
from sqlalchemy.orm import Session

_QUERY: Final = text(
    "SELECT machine, from_state, to_state FROM contract_state_transition"
)


class Topology:
    """An immutable snapshot of the declared edges."""

    __slots__ = ("_edges", "_initial", "_states")

    def __init__(self, rows: list[tuple[str, str | None, str]]) -> None:
        edges: dict[tuple[str, str], set[str]] = {}
        initial: dict[str, set[str]] = {}
        states: dict[str, set[str]] = {}
        for machine, origin, target in rows:
            states.setdefault(machine, set()).add(target)
            if origin is None:
                initial.setdefault(machine, set()).add(target)
            else:
                states[machine].add(origin)
                edges.setdefault((machine, origin), set()).add(target)
        self._edges: Mapping[tuple[str, str], frozenset[str]] = {
            k: frozenset(v) for k, v in edges.items()
        }
        self._initial: Mapping[str, frozenset[str]] = {
            k: frozenset(v) for k, v in initial.items()
        }
        self._states: Mapping[str, frozenset[str]] = {
            k: frozenset(v) for k, v in states.items()
        }

    @property
    def machines(self) -> frozenset[str]:
        return frozenset(self._states)

    def states(self, machine: str) -> frozenset[str]:
        return self._states.get(machine, frozenset())

    def initial_states(self, machine: str) -> frozenset[str]:
        return self._initial.get(machine, frozenset())

    def successors(self, machine: str, state: str) -> frozenset[str]:
        return self._edges.get((machine, state), frozenset())

    def declares(self, machine: str, from_state: str, to_state: str) -> bool:
        return to_state in self.successors(machine, from_state)

    def is_terminal(self, machine: str, state: str) -> bool:
        """True when the state exists in this machine and has no outgoing edge."""
        return state in self.states(machine) and not self.successors(machine, state)


def load(session: Session) -> Topology:
    """Read the topology. Callers cache it; it cannot change without a migration."""
    rows = [(m, f, t) for m, f, t in session.execute(_QUERY)]
    if not rows:
        raise RuntimeError(
            "contract_state_transition is empty: the P02 migration head is not applied, "
            "so no transition can be checked against a declared topology"
        )
    return Topology(rows)
