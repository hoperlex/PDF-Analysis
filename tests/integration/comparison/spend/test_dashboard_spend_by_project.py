"""`UI-PARITY-P0A`: the project-scoped dashboard spend carries the comparison journal of that project's work.

The deployment's spend is the union of the two journals (`CMP-SPEND-01`): a Run's ``model_call`` rows and the
``comparison_model_call`` rows. Restricted to a project it is the same union, narrowed to the project's own rows -- a
Run's calls through ``audit_run.project_uid`` and a comparison call through the ``comparison_work`` it was made for
(``comparison_work.project_uid``), because a comparison call has no Run. Which comparison calls count is not
re-decided: the same ``completed`` / ``failed with a cost`` / ``unknown`` rule, here checked through the scoped
statement.

The lane database holds rows of other suites, so the scoped read of this test's **own** project is exact and the
whole-deployment read is compared by delta.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from auditmanager.dashboard.repository import DashboardRepository
from auditmanager.shared.identity import new_ulid


def _scoped(sessions: Any, project_uid: str) -> Any:
    with sessions() as session:
        return DashboardRepository().summary(session, project_uid=project_uid).run_spend


def test_the_scoped_spend_is_the_comparison_calls_of_this_projects_work_and_only_those(
    queue: Any, journal: Any, sessions: Any, project: str,
) -> None:
    item = queue.claimed()
    assert _scoped(sessions, project) is None, "a project that has spent nothing reports no spend"
    for row in (
        {"state": "completed", "cost_micros": 1_500_000, "cost_basis": "measured"},
        {"state": "completed", "cost_micros": 700_000, "cost_basis": "estimated"},
        {"state": "failed", "cost_micros": 300_000},                  # answered something unusable: counts
        {"state": "failed", "cost_micros": 0},                        # proven not to have spent: does not
        {"state": "unknown"},                                         # may have spent, unmeasured: counts, adds nothing
        {"state": "prepared", "estimate_micros": 5_000_000},          # not spent yet: does not
    ):
        journal.insert(item.work_id, item.attempt_id, **row)
    spend = _scoped(sessions, project)
    assert spend is not None
    assert (spend.model_call_count, spend.cost_micros, spend.basis) == (4, 2_500_000, "estimated")


def test_another_projects_spend_does_not_reach_this_projects_figure_and_both_reach_the_deployments(
    queue: Any, journal: Any, sessions: Any, project: str,
) -> None:
    item = queue.claimed()
    journal.insert(item.work_id, item.attempt_id, state="completed", cost_micros=2_000_000, cost_basis="measured")
    other = f"prj_{new_ulid()}"
    with sessions() as session:
        session.execute(
            text("INSERT INTO project (project_uid, name) VALUES (:p, 'UI-PARITY-P0A other')"), {"p": other}
        )
        session.commit()
    try:
        with sessions() as session:
            whole = DashboardRepository().summary(session).run_spend
        mine = _scoped(sessions, project)
        assert mine is not None and (mine.model_call_count, mine.cost_micros) == (1, 2_000_000)
        assert _scoped(sessions, other) is None, "the other project spent nothing; it must not inherit this one's call"
        assert whole is not None and whole.model_call_count >= mine.model_call_count
        assert whole.cost_micros >= mine.cost_micros
    finally:
        with sessions() as session:
            session.execute(text("DELETE FROM project WHERE project_uid = :p"), {"p": other})
            session.commit()
