"""`D-74`. Asking whether a parent exists must not read the parent.

Two operations declare ``404`` for an identity in their path and prove it by reading the
parent through a method built to return the whole of it:

* ``listRunFindings`` called ``RunPort.get_run_status``, and the shipped
  ``RunAdapter.get_run_status`` assembles the run row, **every stage result** and the run's
  **cost** to answer a yes/no;
* ``listDecisionHistory`` called ``FindingPort.get_finding``, and the shipped
  ``FindingAdapter.get_finding`` reads the finding's evidence, its current verdict and
  **the whole decision history** -- which the very next line of that handler then reads a
  second time.

The repair is a narrow method on each port. What makes this a debt row rather than a chore
is stated in ``test_every_port_implementation_is_whole.py``; what is asserted here is the
other half, that the narrow method is actually narrow. A method named ``run_exists`` that
delegated to ``get_run_status`` would satisfy every existing test in this tree, keep the
cost it was added to remove, and read as done.

**The measurement is the statements the database is asked to run**, captured off
SQLAlchemy's own cursor event rather than counted by hand, and the assertions are about
which *tables* those statements name. Asserting an exact number of round trips would pin an
implementation detail; asserting that the stage, cost and ledger tables are never touched
pins the property `D-74` is about.
"""

from __future__ import annotations

from typing import Any, Iterator

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.shared.identity import AnalysisProfileId, PromptBundleId

from .conftest import PublishedRun


class _Statements:
    """Every SQL statement one connection was asked to run, in order."""

    def __init__(self) -> None:
        self.seen: list[str] = []

    def __call__(self, conn: Any, cursor: Any, statement: str, *_: Any) -> None:
        self.seen.append(" ".join(statement.split()).lower())

    def reset(self) -> None:
        """Forget everything so far.

        Called at the start of every measurement rather than relied on through fixture
        ordering: ``published_run`` writes a project, a document, a version, a run and a
        published finding, and a recorder that had been listening through that would report
        those statements as the ones the measured call made.
        """
        self.seen.clear()

    def naming(self, table: str) -> list[str]:
        return [statement for statement in self.seen if table in statement]


@pytest.fixture
def statements(connection: Any) -> Iterator[_Statements]:
    """A recorder on the suite's one connection, cleared for each measurement."""
    recorder = _Statements()
    event.listen(connection, "before_cursor_execute", recorder)
    try:
        yield recorder
    finally:
        event.remove(connection, "before_cursor_execute", recorder)


@pytest.fixture
def run_adapter(session_factory: sessionmaker[Session]) -> Any:
    from auditmanager.runs import InlineCarrier

    from auditmanager.bootstrap.adapters import RunAdapter

    return RunAdapter(
        session_factory,
        blob_store=None,
        adapter=None,
        provider_config=None,
        provider_mode="recorded",
        analysis_profile_id=str(AnalysisProfileId.new()),
        prompt_bundle_id=str(PromptBundleId.new()),
        carrier=InlineCarrier(),
    )


@pytest.fixture
def finding_adapter(session_factory: sessionmaker[Session]) -> Any:
    from auditmanager.bootstrap.adapters import FindingAdapter

    return FindingAdapter(session_factory)


class TestRunExistenceDoesNotAssembleTheRun:
    def test_it_answers_true_for_a_run_that_exists(
        self, run_adapter: Any, published_run: PublishedRun
    ) -> None:
        assert run_adapter.run_exists(run_id=published_run.run_id) is True

    def test_it_answers_false_for_one_that_does_not(self, run_adapter: Any) -> None:
        """False, not a refusal. Whether an absent parent is a ``404`` is the operation's
        statement about itself and belongs in the router that declares it, which is where
        `D-67` put it and where this change leaves it."""
        assert run_adapter.run_exists(run_id="run_01ARZ3NDEKTSV4RRFFQ69G5FAV") is False

    def test_it_reads_neither_the_stages_nor_the_cost(
        self, run_adapter: Any, published_run: PublishedRun, statements: _Statements
    ) -> None:
        statements.reset()
        run_adapter.run_exists(run_id=published_run.run_id)
        assert statements.naming("audit_run"), (
            "nothing asked the database about the run at all; this measurement is empty"
        )
        assert statements.naming("stage_result") == [], statements.seen
        assert statements.naming("model_call") == [], statements.seen

    def test_the_control_that_the_full_read_does_touch_them(
        self, run_adapter: Any, published_run: PublishedRun, statements: _Statements
    ) -> None:
        """The measurement can tell the two apart.

        Without this, a recorder that saw nothing at all would satisfy the assertions above
        and the narrowing would be proved by an instrument that was switched off.
        """
        statements.reset()
        run_adapter.get_run_status(run_id=published_run.run_id)
        assert statements.naming("stage_result"), statements.seen
        assert statements.naming("model_call"), statements.seen


class TestFindingExistenceDoesNotReadTheLedger:
    def test_it_answers_true_for_a_published_finding(
        self, finding_adapter: Any, published_run: PublishedRun
    ) -> None:
        assert finding_adapter.finding_exists(finding_uid=published_run.finding_uid) is True

    def test_it_answers_false_for_one_that_does_not(self, finding_adapter: Any) -> None:
        assert (
            finding_adapter.finding_exists(finding_uid="fnd_01ARZ3NDEKTSV4RRFFQ69G5FAV")
            is False
        )

    def test_it_does_not_read_the_decision_history(
        self, finding_adapter: Any, published_run: PublishedRun, statements: _Statements
    ) -> None:
        """The one that cost twice over: ``listDecisionHistory`` read the ledger to prove
        the finding exists and then read the ledger again to render it."""
        statements.reset()
        finding_adapter.finding_exists(finding_uid=published_run.finding_uid)
        assert statements.naming("finding"), (
            "nothing asked the database about the finding at all"
        )
        assert statements.naming("expert_decision_event") == [], statements.seen
        assert statements.naming("finding_evidence") == [], statements.seen

    def test_the_control_that_the_full_read_does_touch_them(
        self, finding_adapter: Any, published_run: PublishedRun, statements: _Statements
    ) -> None:
        statements.reset()
        finding_adapter.get_finding(finding_uid=published_run.finding_uid)
        assert statements.naming("expert_decision_event"), statements.seen
