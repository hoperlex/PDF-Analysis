"""The transition guard's *reason*, which no test in the gate could redden.

`assert_transition` has three refusing branches and all three raise the **same** code,
`state_transition_not_allowed`, with **no details at all**. Only the message distinguishes
them. `tests/integration/shared_kernel/test_topology_guard.py` asserts

    with self.assertRaises(DomainError):
        assert_transition(self.topology, "audit_run", "published", "running")

and nothing more -- so deleting the terminal check leaves it green, because the
undeclared-edge check then refuses the same move. Removing `is_terminal` left all 816
tests green in the sweep.

**The refusal is unreddenable by construction; the reason is not.** `is_terminal` is
`state in states(machine) and not successors(machine, state)`, so whenever it is true
`declares(...)` is false for every target -- the later branch catches everything the
terminal branch catches, and no move can escape by deleting it. What is lost is the
diagnosis. A caller reopening a published run is told

    audit_run 'published' is terminal; it is never reopened

and without the check is told instead that the contract allows `[]` from `published`,
which is the same fact stated as an accident. That is the rule this file pins.

`tests/integration/shared_kernel/**` is not this session's to write, so the guard lives
here. The topology is loaded from the database that enforces it, exactly as the guard's
own callers load it -- a topology written out in Python would be the second source of
truth the module exists to avoid.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.statemachine import Topology, assert_transition, load


@pytest.fixture(scope="module")
def topology() -> Topology:
    url = os.environ.get("DATABASE_URL")
    assert url, "this suite runs against real PostgreSQL and never skips"
    with Session(create_engine(url, future=True)) as session:
        return load(session)


def test_published_really_is_terminal(topology: Topology) -> None:
    """The premise, asserted before anything depends on it. If `published` ever gained
    an outgoing edge, the case below would stop exercising the terminal branch and would
    pass for the wrong reason."""
    assert topology.is_terminal("audit_run", "published")
    assert topology.successors("audit_run", "published") == frozenset()


def test_reopening_a_terminal_state_is_refused_as_terminal_not_as_undeclared(
    topology: Topology,
) -> None:
    """The rule. Both branches refuse this move and both raise the same code with no
    details, so the message is the only thing that can tell them apart."""
    with pytest.raises(DomainError) as caught:
        assert_transition(topology, "audit_run", "published", "running")
    assert caught.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    message = str(caught.value)
    assert "is terminal; it is never reopened" in message, (
        f"the refusal reads {message!r}. A terminal state refused as an undeclared edge "
        "tells a caller the allowed set happens to be empty, not that the run is final."
    )


def test_an_undeclared_edge_from_a_live_state_names_what_is_allowed(
    topology: Topology,
) -> None:
    """The other branch, pinned so the two cannot be confused.

    `created` is not terminal -- it has successors -- so this move can only be refused by
    the declared-edge check, and its message must be the one that lists them.
    """
    assert not topology.is_terminal("audit_run", "created")
    with pytest.raises(DomainError) as caught:
        assert_transition(topology, "audit_run", "created", "published")
    message = str(caught.value)
    assert "declares no edge" in message
    assert "is terminal" not in message


def test_an_unknown_machine_is_refused_by_its_own_branch(topology: Topology) -> None:
    """The third branch. It fires before either of the others."""
    with pytest.raises(DomainError) as caught:
        assert_transition(topology, "not_a_machine", "a", "b")
    assert "is not one of the machines PC-01 instantiates" in str(caught.value)


def test_a_declared_edge_is_not_refused(topology: Topology) -> None:
    assert_transition(topology, "audit_run", "queued", "running")
