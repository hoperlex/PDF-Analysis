"""The deployment's spend is the union of the two journals (`CMP-SPEND-01`, ADR-0025 decision 5, `R-29`).

``dashboard/repository.py`` ``_SPEND`` reads ``model_call`` (the Runs) **and** ``comparison_model_call``. What of the
comparison journal counts: a call that may have cost something -- ``completed``, ``failed`` with a cost, ``unknown``
(a call whose cost is unmeasured, so the basis turns to ``estimated``). An open call has not spent, and a failed one
without a cost was proven not to have. The lane database holds rows of other suites, so every assertion is a **delta**
of the very query the dashboard runs.

Mutation recorded in ``docs/program/CMP-SPEND-01.md``: the union without the comparison half (and one that counts an open
call).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from auditmanager.dashboard.repository import _SPEND, DashboardRepository, spend_record


def _figures(sessions: Any) -> tuple[int, int, int, int]:
    with sessions() as session:
        calls, cost, unmetered, unmeasured = tuple(session.execute(_SPEND).one())
    return int(calls), int(cost), int(unmetered), int(unmeasured)


def _delta(before: tuple[int, ...], after: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(a - b for a, b in zip(after, before))


def test_every_call_of_the_comparison_journal_that_may_have_cost_something_is_in_the_deployments_spend(
    queue: Any, journal: Any, sessions: Any,
) -> None:
    item = queue.claimed()
    before = _figures(sessions)
    rows = [
        {"state": "completed", "cost_micros": 1_500_000},                          # measured
        {"state": "completed", "cost_micros": 700_000, "cost_basis": "estimated"},
        {"state": "completed", "cost_micros": 0, "cost_basis": "unmetered"},
        {"state": "failed", "cost_micros": 300_000},                               # answered something unusable
        {"state": "failed", "cost_micros": 0},                                     # proven not to have spent: not counted
        {"state": "unknown"},                                                      # may have spent: an unmeasured call
        {"state": "prepared", "estimate_micros": 5_000_000},                       # not spent yet: not counted
        {"state": "sent", "estimate_micros": 5_000_000},
    ]
    for row in rows:
        journal.insert(item.work_id, item.attempt_id, **row)
    calls, cost, unmetered, unmeasured = _delta(before, _figures(sessions))
    assert (calls, cost, unmetered, unmeasured) == (5, 2_500_000, 1, 2)


def test_the_deployment_summary_carries_the_comparison_calls_in_its_spend(
    queue: Any, journal: Any, sessions: Any,
) -> None:
    item = queue.claimed()
    with sessions() as session:
        before = DashboardRepository().summary(session).run_spend
    journal.insert(item.work_id, item.attempt_id, state="completed", cost_micros=2_000_000)
    journal.insert(item.work_id, item.attempt_id, state="unknown")
    with sessions() as session:
        after = DashboardRepository().summary(session).run_spend
    assert after is not None
    before_calls = 0 if before is None else before.model_call_count
    before_cost = 0 if before is None else before.cost_micros
    assert after.model_call_count - before_calls == 2
    assert after.cost_micros - before_cost == 2_000_000
    assert after.basis == "estimated", "an unknown call is unmeasured, so the sum is not a measurement"


def test_the_per_run_form_of_the_query_reads_no_comparison_row(
    queue: Any, journal: Any, sessions: Any,
) -> None:
    """``... WHERE run_id = :run`` (how the HTTP run-path test and a per-run reader use it) never meets a comparison call."""
    item = queue.claimed()
    journal.insert(item.work_id, item.attempt_id, state="completed", cost_micros=9_000_000)
    with sessions() as session:
        row = session.execute(text(str(_SPEND) + " WHERE run_id = :r"), {"r": "run_NONE"}).one()
    assert tuple(int(v) for v in row) == (0, 0, 0, 0)


def test_a_deployment_with_only_unmetered_comparison_calls_reports_them_as_unmetered() -> None:
    """The rule of ``spend_record`` is unchanged by the union: every call unmetered means a zero and the basis ``unmetered``."""
    record = spend_record(2, 0, 2, 0)
    assert record is not None and (record.cost_micros, record.basis) == (0, "unmetered")
