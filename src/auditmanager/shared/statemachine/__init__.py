"""Shared state-machine kernel: the declared topology and the guard that reads it."""

from auditmanager.shared.statemachine.guard import assert_initial, assert_transition
from auditmanager.shared.statemachine.topology import Topology, load

__all__ = ["Topology", "assert_initial", "assert_transition", "load"]
