"""Queue projections express the contract's counts and state precedence."""

from __future__ import annotations

from datetime import UTC, datetime

from auditmanager.comparison.queue.model import queue_view

NOW = datetime(2026, 10, 29, tzinfo=UTC)


def _entry(state: str, n: int) -> dict:
    return {"comparison_launch_entry_id": f"cle_{n:026d}", "document_uid": f"doc_{n:026d}",
            "step": "profile", "state": state, "position": n, "restart": False, "reason": None,
            "comparison_ai_job_id": None, "comparison_series_id": None, "created_at": NOW, "updated_at": NOW}


def test_untouched_project_is_idle_without_a_queue_row() -> None:
    view = queue_view("prj_example", None, [])
    assert view["state"] == "idle" and view["counts"]["total"] == 0
    assert view["entries"] == [] and "updated_at" not in view


def test_counts_and_queue_precedence_come_from_durable_rows() -> None:
    queue = {"paused": False, "failure_reason": None, "updated_at": NOW}
    rows = [_entry("done", 1), _entry("waiting", 2), _entry("needs_consent", 3), _entry("failed", 4)]
    view = queue_view("prj_example", queue, rows)
    assert view["state"] == "running"
    assert view["counts"] == {"total": 4, "done": 1, "running": 0, "waiting": 1,
                              "needs_consent": 1, "skipped": 0, "failed": 1}
    assert queue_view("prj_example", {**queue, "paused": True}, rows)["state"] == "paused"
    assert queue_view("prj_example", {**queue, "failure_reason": "step_failed"}, rows)["state"] == "failed"
    assert queue_view("prj_example", queue, [_entry("done", 1)])["state"] == "done"
