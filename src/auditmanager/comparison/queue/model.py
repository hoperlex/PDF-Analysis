"""The launch queue's closed vocabulary and read projection."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any, Final

LAUNCH_KIND: Final[str] = "comparison_launch"
STEPS: Final[tuple[str, ...]] = ("profile", "matrix", "ai_pairs", "series", "ai_changes", "report")
AI_STEPS: Final[frozenset[str]] = frozenset({"ai_pairs", "ai_changes", "report"})
ACTIVE: Final[frozenset[str]] = frozenset({"waiting", "running", "needs_consent"})
TERMINAL: Final[frozenset[str]] = frozenset({"done", "skipped", "failed"})
STEP_ORDER: Final[dict[str, int]] = {name: index for index, name in enumerate(STEPS)}


def queue_view(project_uid: str, queue: Mapping[str, Any] | None, entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Contract shape derived from durable rows. Reading an untouched project is ``idle``."""
    counts = Counter(str(row["state"]) for row in entries)
    if queue is None or not entries:
        state = "idle"
    elif bool(queue["paused"]):
        state = "paused"
    elif queue["failure_reason"] is not None:
        state = "failed"
    elif any(row["state"] in ACTIVE for row in entries):
        state = "running"
    else:
        state = "done"
    result: dict[str, Any] = {
        "project_uid": project_uid,
        "state": state,
        "counts": {"total": len(entries), **{name: counts[name] for name in
                  ("done", "running", "waiting", "needs_consent", "skipped", "failed")}},
        "entries": [entry_view(row) for row in entries],
    }
    if queue is not None:
        result["updated_at"] = queue["updated_at"]
    return result


def entry_view(row: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "entry_id": row["comparison_launch_entry_id"], "document_uid": row["document_uid"],
        "step": row["step"], "state": row["state"], "position": row["position"],
        "restart": row["restart"], "created_at": row["created_at"], "updated_at": row["updated_at"],
    }
    for source, target in (("reason", "reason"), ("comparison_ai_job_id", "job_id"),
                           ("comparison_series_id", "series_id")):
        if row[source] is not None:
            result[target] = row[source]
    return result
