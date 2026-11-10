"""`EXEC2-CAP-01` (ADR-0026 decision 1): the one rule "units in use below the capacity" is written in four places
that may not import one another, so a test holds the copies equal.

* ``jobs.repository``: the Run claim (``_CONNECTION_UNITS``) and the dispatcher hint (``_NEXT_JOB``);
* ``comparison.spend.repository``: the comparison call preparation (``_CONNECTION_HAS_FREE_UNIT``);
* ``executors.repository``: the reads (``_UNIT_COUNTS``) behind ``occupancy``, ``used_units`` and ``capacity_of``.

The statements are checked as text (no database): the states that make a unit, the capacity expression and its
default, and the shape of the comparison. The branch of the claim is checked with a recording session.
Container-free; the same rule on a real PostgreSQL is ``tests/integration/jobs/test_connection_capacity.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.comparison.spend import repository as spend
from auditmanager.executors import queries, repository as executors
from auditmanager.executors.model import DEFAULT_MAX_ACTIVE_RUNS, QUEUE_REASONS, RevisionSettings
from auditmanager.jobs import repository as jobs
from auditmanager.jobs.repository import JobRepository
from auditmanager.shared.errors import DomainError, ErrorCode

RUN_STATES = "('leased', 'running', 'retry_wait')"
CALL_STATES = "IN ('prepared', 'sent')"
ATTEMPT_STATES = "IN ('created', 'leased', 'running')"
CAPACITY_ORDER = "ORDER BY current_revision.revision_no DESC LIMIT 1"


def _sql(statement: Any) -> str:
    return str(statement)


# --- the states that make a unit are the same everywhere -------------------------------------------------


def test_the_job_states_of_an_active_run_are_the_same_in_the_claim_the_comparison_call_and_the_reads() -> None:
    assert jobs._ACTIVE_JOB_STATES == RUN_STATES  # type: ignore[attr-defined]
    assert executors._ACTIVE_RUN_JOB_STATES == RUN_STATES  # type: ignore[attr-defined]
    assert spend._ACTIVE_STATES_SQL == RUN_STATES  # type: ignore[attr-defined]
    for statement in (jobs._CONNECTION_UNITS, jobs._NEXT_JOB, executors._UNIT_COUNTS,  # type: ignore[attr-defined]
                      spend._CONNECTION_HAS_FREE_UNIT):  # type: ignore[attr-defined]
        assert RUN_STATES in _sql(statement)


def test_the_call_and_attempt_states_of_a_live_comparison_call_are_the_same_in_the_three_statements_that_count_it() -> None:
    claim = _sql(jobs._CONNECTION_UNITS)  # type: ignore[attr-defined]
    call = _sql(spend._CONNECTION_HAS_FREE_UNIT)  # type: ignore[attr-defined]
    read = _sql(executors._UNIT_COUNTS)  # type: ignore[attr-defined]
    assert f"active_call.state {CALL_STATES}" in claim and f"active_attempt.state {ATTEMPT_STATES}" in claim
    assert f"c.state {CALL_STATES}" in call and f"a.state {ATTEMPT_STATES}" in call
    assert f"c.state {CALL_STATES}" in read and f"a.state {ATTEMPT_STATES}" in read


def test_the_hint_counts_runs_only_as_it_always_did() -> None:
    """D-260 is the register's row for this: the hint does not see comparison calls, the claim does. If this
    assertion is turned round, that row closes in the same change."""
    assert "comparison_model_call" not in _sql(jobs._NEXT_JOB)  # type: ignore[attr-defined]


# --- the capacity is the current revision's, and one when absent ----------------------------------------


@pytest.mark.parametrize("statement", [
    jobs._CONNECTION_UNITS,  # type: ignore[attr-defined]
    spend._CONNECTION_HAS_FREE_UNIT,  # type: ignore[attr-defined]
    jobs._NEXT_JOB,  # type: ignore[attr-defined]
    executors._UNIT_COUNTS,  # type: ignore[attr-defined]
])
def test_every_statement_reads_the_capacity_of_the_highest_numbered_revision_and_defaults_it(statement: Any) -> None:
    text = _sql(statement)
    assert "current_revision.max_active_runs" in text
    assert CAPACITY_ORDER in text
    assert f"{CAPACITY_ORDER}), {DEFAULT_MAX_ACTIVE_RUNS})" in text, "the default of an absent capacity moved"


def test_the_default_capacity_is_one_in_the_model_and_in_the_sql() -> None:
    assert DEFAULT_MAX_ACTIVE_RUNS == 1
    assert f"{CAPACITY_ORDER}), 1)" in _sql(jobs._CONNECTION_UNITS)  # type: ignore[attr-defined]


def test_the_capacity_of_a_run_is_not_read_from_the_revision_the_run_froze() -> None:
    """A lowered or raised capacity governs new claims, so the claim looks at the connection's current revision,
    never at the Run's own: the capacity subquery filters on the connection only."""
    text = _sql(jobs._CONNECTION_UNITS)  # type: ignore[attr-defined]
    capacity = text[text.index("COALESCE((SELECT current_revision.max_active_runs"):]
    assert "current_revision.connection_id = :connection_id" in capacity
    assert "revision_id" not in capacity.replace("max_active_runs", "").replace("revision_no", "")


# --- the shape of the comparison ----------------------------------------------------------------------------


def test_the_claim_the_call_and_the_hint_compare_with_the_capacity_the_same_way() -> None:
    assert ") AS units_in_use," in _sql(jobs._CONNECTION_UNITS)  # type: ignore[attr-defined]
    assert ") < COALESCE((SELECT current_revision.max_active_runs" in _sql(spend._CONNECTION_HAS_FREE_UNIT)  # type: ignore[attr-defined]
    assert "loaded.units >= COALESCE((SELECT current_revision.max_active_runs" in _sql(jobs._NEXT_JOB)  # type: ignore[attr-defined]


def test_the_claim_excludes_the_run_it_is_claiming_and_the_call_excludes_nobody() -> None:
    assert "other.run_id <> :run_id" in _sql(jobs._CONNECTION_UNITS)  # type: ignore[attr-defined]
    assert ":run_id" not in _sql(spend._CONNECTION_HAS_FREE_UNIT)  # type: ignore[attr-defined]


def test_the_hint_names_each_held_run_once_and_counts_them_per_connection() -> None:
    hint = _sql(jobs._NEXT_JOB)  # type: ignore[attr-defined]
    assert "SELECT rev.connection_id AS capacity_key, active_job.run_id FROM job active_job" in hint
    assert "SELECT rev.connection_id, submitted_run.run_id FROM audit_run submitted_run" in hint
    assert " UNION SELECT" in hint and "UNION ALL" not in hint, "UNION (not UNION ALL) removes a run held twice"
    assert "loaded AS (SELECT capacity_key, count(*) AS units FROM held GROUP BY capacity_key)" in hint


def test_the_first_column_of_the_hint_is_a_capacity_key_because_it_also_holds_pools() -> None:
    """`D-664`: ``held`` and ``loaded`` count a connection's units under its id and a planned Run's under its capacity pool, so their first
    column is not named ``connection_id`` -- and each of the three joins that read it says what it compares the key with."""
    hint = _sql(jobs._NEXT_JOB)  # type: ignore[attr-defined]
    assert "loaded.connection_id" not in hint and "SELECT connection_id, count(*)" not in hint
    assert "JOIN loaded ON loaded.capacity_key = mine.connection_id" in hint, "a Run frozen to a connection"
    assert "WHERE loaded.capacity_key = group_member.connection_id" in hint, "a member of a pending Run's group"
    assert "JOIN loaded ON loaded.capacity_key = pool_connection.capacity_pool" in hint, "a planned Run's pool"


def test_the_reads_group_the_active_rows_instead_of_correlating_a_count_per_connection() -> None:
    text = _sql(executors._UNIT_COUNTS)  # type: ignore[attr-defined]
    assert text.count("GROUP BY rev.connection_id") == 2
    assert "rev.connection_id = k.connection_id" not in text


# --- the rest of the lane's seams -----------------------------------------------------------------------


def test_the_queue_reasons_are_the_contracts() -> None:
    assert (queries.QUEUE_AT_CAPACITY, queries.QUEUE_RUNNER_OFFLINE) == QUEUE_REASONS


def test_the_repository_stores_and_reads_the_capacity_with_every_other_setting() -> None:
    assert set(executors._SETTING_NAMES) == set(RevisionSettings.__slots__)  # type: ignore[attr-defined]
    columns = {name.strip() for name in executors._REVISION_COLUMNS.split(",")}  # type: ignore[attr-defined]
    assert set(executors._SETTING_NAMES) <= columns  # type: ignore[attr-defined]
    assert "max_active_runs" in executors._INTEGER_SETTINGS  # type: ignore[attr-defined]
    assert executors._typed_parameter("max_active_runs") == "CAST(:max_active_runs AS integer)"  # type: ignore[attr-defined]


# --- the claim's branch, with a recording session ---------------------------------------------------------


class _Result:
    def __init__(self, value: Any) -> None:
        self.value = value

    def scalar_one_or_none(self) -> Any:
        return self.value

    def one(self) -> Any:
        return self.value


class _Session:
    """Answers the three statements the claim's check makes and records which ran, in order."""

    def __init__(self, *, connection: str | None, units: int = 0, capacity: int = 1) -> None:
        self.connection, self.units, self.capacity = connection, units, capacity
        self.ran: list[Any] = []
        self.params: list[dict[str, Any]] = []

    def execute(self, statement: Any, params: dict[str, Any]) -> _Result:
        self.ran.append(statement)
        self.params.append(params)
        if statement is jobs._CONNECTION_OF_RUN:  # type: ignore[attr-defined]
            return _Result(self.connection)
        if statement is jobs._LOCK_CONNECTION:  # type: ignore[attr-defined]
            return _Result(None)
        assert statement is jobs._CONNECTION_UNITS, "the check ran a statement it does not own"  # type: ignore[attr-defined]
        return _Result((self.units, self.capacity))


def _claim_check(**kwargs: Any) -> _Session:
    session = _Session(**kwargs)
    JobRepository._hold_connection_limit(session, run_id="run_X")  # type: ignore[arg-type]
    return session


@pytest.mark.parametrize(("units", "capacity"), [(0, 1), (0, 3), (2, 3), (15, 16)])
def test_a_claim_passes_while_the_units_in_use_are_below_the_capacity(units: int, capacity: int) -> None:
    _claim_check(connection="exc_C", units=units, capacity=capacity)


@pytest.mark.parametrize(("units", "capacity"), [(1, 1), (3, 3), (16, 16), (3, 2), (2, 1)])
def test_a_claim_is_refused_with_a_conflict_once_the_units_reach_or_pass_the_capacity(units: int, capacity: int) -> None:
    """The last two rows are a lowered capacity: work in flight keeps its units, and a new claim waits."""
    with pytest.raises(DomainError) as refused:
        _claim_check(connection="exc_C", units=units, capacity=capacity)
    assert refused.value.code is ErrorCode.CONFLICT
    assert refused.value.detail_fields == {"aggregate_type": "ExecutorConnection"}


def test_the_connection_is_locked_before_its_units_are_counted() -> None:
    session = _claim_check(connection="exc_C", units=0, capacity=2)
    assert session.ran == [jobs._CONNECTION_OF_RUN, jobs._LOCK_CONNECTION, jobs._CONNECTION_UNITS]  # type: ignore[attr-defined]
    assert session.params[1] == {"connection_id": "exc_C"}
    assert session.params[2] == {"connection_id": "exc_C", "run_id": "run_X"}


def test_a_run_with_no_connection_takes_no_lock_and_counts_no_unit() -> None:
    """The `environment` source: no frozen revision, so no lock, no count and no limit, as before."""
    session = _claim_check(connection=None, units=99, capacity=1)
    assert session.ran == [jobs._CONNECTION_OF_RUN]  # type: ignore[attr-defined]
