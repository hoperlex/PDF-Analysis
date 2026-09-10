"""The application guard and the database trigger must refuse the same moves.

This is the whole point of the module. If they disagree, one of them is wrong and the
caller learns which only in production. The agreement test walks the full cross product
of each machine's states, asks both, and compares.
"""

from __future__ import annotations

import os
import unittest

from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.statemachine import Topology, assert_initial, assert_transition, load


def _engine():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is unset. This suite runs against real PostgreSQL and never "
            "skips: a skip would let the agreement go unchecked and look green."
        )
    return create_engine(url, future=True)


class TopologyCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = _engine()
        with Session(cls.engine) as s:
            cls.topology: Topology = load(s)


class TheTopologyIsTheContractOne(TopologyCase):
    def test_exactly_the_three_machines_pc01_instantiates(self) -> None:
        self.assertEqual(
            self.topology.machines, frozenset({"audit_run", "blob", "command_idempotency"})
        )

    def test_no_import_job_or_attempt_machine_exists(self) -> None:
        for absent in ("import", "job", "attempt"):
            self.assertNotIn(absent, self.topology.machines)

    def test_there_is_no_succeeded_run_state(self) -> None:
        self.assertNotIn("succeeded", self.topology.states("audit_run"))

    def test_the_declared_run_terminals(self) -> None:
        terminals = {
            s for s in self.topology.states("audit_run") if self.topology.is_terminal("audit_run", s)
        }
        self.assertEqual(terminals, {"published", "partial", "failed", "cancelled"})


class TheGuardRefusesWhatTheContractDoesNotDeclare(TopologyCase):
    def test_a_declared_edge_passes(self) -> None:
        assert_transition(self.topology, "audit_run", "queued", "running")

    def test_an_undeclared_edge_is_refused_with_the_catalog_code(self) -> None:
        with self.assertRaises(DomainError) as caught:
            assert_transition(self.topology, "audit_run", "created", "published")
        self.assertIs(caught.exception.code, ErrorCode.STATE_TRANSITION_NOT_ALLOWED)

    def test_a_terminal_state_is_never_reopened(self) -> None:
        with self.assertRaises(DomainError):
            assert_transition(self.topology, "audit_run", "published", "running")

    def test_creation_outside_an_initial_state_is_refused(self) -> None:
        assert_initial(self.topology, "audit_run", "created")
        with self.assertRaises(DomainError):
            assert_initial(self.topology, "audit_run", "running")


class TheGuardAndTheTriggerAgree(TopologyCase):
    """The anti-drift proof, over the full cross product of every machine's states."""

    def _database_declares(self, machine: str, origin: str, target: str) -> bool:
        with Session(self.engine) as s:
            row = s.execute(
                text(
                    "SELECT 1 FROM contract_state_transition "
                    "WHERE machine = :m AND from_state = :f AND to_state = :t"
                ),
                {"m": machine, "f": origin, "t": target},
            ).first()
            return row is not None

    def test_every_pair_gets_the_same_answer_from_both(self) -> None:
        compared = 0
        for machine in sorted(self.topology.machines):
            states = sorted(self.topology.states(machine))
            for origin in states:
                for target in states:
                    guard_allows = True
                    try:
                        assert_transition(self.topology, machine, origin, target)
                    except DomainError:
                        guard_allows = False
                    db_allows = self._database_declares(machine, origin, target)
                    compared += 1
                    with self.subTest(machine=machine, edge=f"{origin}->{target}"):
                        self.assertEqual(
                            guard_allows,
                            db_allows,
                            f"{machine}: guard says {guard_allows}, "
                            f"contract_state_transition says {db_allows}",
                        )
        self.assertGreater(compared, 40, "the cross product was suspiciously small")

    def test_the_topology_table_is_frozen_against_inserts(self) -> None:
        with Session(self.engine) as s, self.assertRaises(DBAPIError):
            s.execute(
                text(
                    "INSERT INTO contract_state_transition (machine, from_state, to_state) "
                    "VALUES ('audit_run', 'published', 'running')"
                )
            )
            s.flush()


if __name__ == "__main__":
    unittest.main()
