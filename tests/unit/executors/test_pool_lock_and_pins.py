"""`HOSTS-BACKEND-01` (ADR-0028 decision 4): the capacity pool is one fact written in several places that may not import one another.

The advisory lock is keyed on the pool in the claim, the dispatcher hint, the comparison mirror and the cell binding -- so every spelling of
that key must be the same key. This module holds the copies equal as **text** (no database): the three lock statements, the slot expression of
the pool in the executors' reads, in the jobs' hint and in the comparison mirror, and the unit counts. A copy that drifts turns a test red here
instead of letting two binds on one subscription both pass. The lock's behaviour on a real PostgreSQL (a lock held in one transaction blocks the
other's, whichever of the three statements took it) is ``tests/integration/executors/test_hosts_backend.py``.
"""

from __future__ import annotations

import re
from typing import Any

from auditmanager.comparison.spend import repository as spend
from auditmanager.executors import host_repository as hosts
from auditmanager.jobs import repository as jobs

PREFIX = "auditmanager.executor_connection|"


def _sql(statement: Any) -> str:
    return str(statement)


def test_the_claim_and_the_comparison_mirror_spell_the_connection_lock_alike() -> None:
    assert _sql(spend._LOCK_CONNECTION) == _sql(jobs._LOCK_CONNECTION)  # type: ignore[attr-defined]


def test_the_connection_lock_is_keyed_on_the_pool_when_the_connection_has_one_and_on_itself_otherwise() -> None:
    text = _sql(jobs._LOCK_CONNECTION)  # type: ignore[attr-defined]
    assert PREFIX in text
    assert "COALESCE((SELECT capacity_pool FROM executor_connection WHERE connection_id = :connection_id), :connection_id)" in text


def test_the_three_pool_locks_are_one_statement_and_share_the_prefix_of_the_connection_lock() -> None:
    jobs_pool, spend_pool = _sql(jobs._LOCK_POOL), _sql(spend._LOCK_POOL)  # type: ignore[attr-defined]
    repository_pool = hosts._LOCK_POOL  # type: ignore[attr-defined]
    assert jobs_pool == spend_pool == repository_pool.replace("\n", " ") or jobs_pool == spend_pool
    assert re.sub(r"\s+", " ", jobs_pool) == re.sub(r"\s+", " ", repository_pool)
    assert f"'{PREFIX}' || :pool" in jobs_pool
    assert f"'{PREFIX}' ||" in _sql(jobs._LOCK_CONNECTION)  # type: ignore[attr-defined]
    assert spend.CONNECTION_LOCK_KEY == PREFIX


def test_the_slot_expression_is_the_same_in_the_reads_the_hint_and_the_comparison_mirror() -> None:
    expression = hosts.pool_slots_sql(":pool")
    assert hosts.POOL_SLOTS == "SELECT " + expression + " AS slots"
    assert jobs._pool_slots_sql(":pool") == expression  # type: ignore[attr-defined]
    assert expression in _sql(spend._POOL_HAS_FREE_UNIT)  # type: ignore[attr-defined]


def test_the_slot_expression_takes_the_latest_event_then_the_reported_access_then_one() -> None:
    expression = hosts.pool_slots_sql(":pool")
    assert "ORDER BY slot_event.event_no DESC LIMIT 1" in expression
    assert "WHEN 'api' THEN 2 ELSE 1 END" in expression
    assert expression.rstrip().endswith(", 1)")


def test_the_units_of_a_pool_count_runs_once_by_cell_or_revision_and_active_calls() -> None:
    sql = hosts.POOL_UNITS
    for statement in (sql, _sql(spend._POOL_HAS_FREE_UNIT)):  # type: ignore[attr-defined]
        assert "JOIN audit_run_cell_binding b ON b.run_id = a.run_id" in statement
        assert " UNION SELECT " in statement.replace("UNION ", " UNION SELECT ", 1) or "UNION" in statement
        assert "UNION ALL" not in statement, "a run bound twice in a pool is one unit"
        assert "j.state IN ('leased', 'running', 'retry_wait')" in statement
        assert "active_call.state IN ('prepared', 'sent')" in statement
        assert "active_attempt.state IN ('created', 'leased', 'running')" in statement
        assert "call_connection.capacity_pool = :pool" in statement


def test_the_claim_side_count_excludes_its_own_run_and_the_call_side_excludes_nobody() -> None:
    assert "j.run_id <> :run_id" in hosts.POOL_UNITS
    assert ":run_id" not in _sql(spend._POOL_HAS_FREE_UNIT)  # type: ignore[attr-defined]


def test_the_hint_counts_planned_runs_per_pool_once_each_and_never_counts_calls() -> None:
    hint = _sql(jobs._NEXT_JOB)  # type: ignore[attr-defined]
    assert "SELECT pool_connection.capacity_pool, bound_cell.run_id FROM job pool_job" in hint
    assert "UNION ALL" not in hint
    assert "comparison_model_call" not in hint, "D-260: the hint counts runs, the claim counts calls too"
    assert "r.binding_state = 'bound' AND r.stage_plan IS NOT NULL" in hint
    assert "r.binding_state = 'pending' AND r.stage_plan IS NOT NULL AND CAST(:dispatch_groups AS boolean)" in hint
    assert "r.binding_state <> 'pending' AND r.stage_plan IS NULL" in hint, "the connection test leaves planned runs to their own branch"


def test_the_hint_offers_a_pending_planned_run_only_to_a_process_that_dispatches_it_and_only_while_nothing_holds_it_back() -> None:
    hint = _sql(jobs._NEXT_JOB)  # type: ignore[attr-defined]
    tail = hint[hint.index("r.binding_state = 'pending' AND r.stage_plan IS NOT NULL"):]
    assert "CAST(:dispatch_groups AS boolean) AND r.wait_reason IS NULL" in tail


def test_the_group_sweep_leaves_planned_runs_to_their_own_page() -> None:
    assert "r.stage_plan IS NULL" in _sql(jobs._PENDING_RUNS)  # type: ignore[attr-defined]
    assert "r.stage_plan IS NOT NULL" in _sql(jobs._PENDING_PLANNED_RUNS)  # type: ignore[attr-defined]
    assert "ORDER BY r.created_at, r.run_id LIMIT :batch_size" in _sql(jobs._PENDING_PLANNED_RUNS)  # type: ignore[attr-defined]


def test_the_run_only_wait_word_is_not_a_word_of_the_comparison_pair() -> None:
    from auditmanager.executors.model import WAIT_REASONS

    assert jobs.WAIT_MODEL_UNAVAILABLE == "model_unavailable"  # type: ignore[attr-defined]
    assert "model_unavailable" not in WAIT_REASONS, "WAIT_REASONS is what runs and comparison jobs share; model_unavailable is run-only"
