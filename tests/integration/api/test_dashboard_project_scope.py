"""``getDashboardSummary?project_uid=...`` over the wire, through the shipped adapters (`UI-PARITY-P0A`).

The repository-level figures are asserted in ``tests/integration/dashboard/test_project_scope.py`` on a fresh database,
where every number is absolute. This module is the edge: the optional query parameter is declared, a project that does
not exist is the existing ``404 not_found`` envelope, a malformed one is ``422 validation_failed``, an empty one is the
absent parameter, and the unscoped read is what it was.

The suite shares a long-lived database (``OPERATING_CONSTRAINTS.md`` section 9), so the whole-deployment figures are
compared relatively, and the scoped ones -- of projects this test made -- absolutely.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from w13_api_driver import Surface

from .test_decision_journal import Decided, _append
from .test_query_surface import MixedRun, get, ok

DASHBOARD = "/dashboard"


def _verdicts(body: dict[str, Any]) -> dict[str, int]:
    return {row["verdict"]: row["count"] for row in body["findings_by_verdict"]}


def _states(body: dict[str, Any]) -> dict[str, int]:
    return {row["state"]: row["count"] for row in body["run_activity"]["by_state"]}


def _two_projects(router: Surface, session: Session) -> tuple[Decided, Decided]:
    """Project A: one accepted, one rejected, one pending finding. Project B: two accepted, one rejected."""
    first = Decided(router, MixedRun(session))
    second = Decided(router, MixedRun(session))
    _append(router, second.pending, "accept")
    return first, second


def test_the_scoped_panels_are_each_projects_own(shipped_router: Surface, session: Session) -> None:
    a, b = _two_projects(shipped_router, session)
    one = ok(get(shipped_router, f"{DASHBOARD}?project_uid={a.run.run.project_uid}"))
    two = ok(get(shipped_router, f"{DASHBOARD}?project_uid={b.run.run.project_uid}"))

    assert [row["project_uid"] for row in one["documents_by_project"]] == [a.run.run.project_uid]
    assert [row["project_uid"] for row in two["documents_by_project"]] == [b.run.run.project_uid]
    assert _verdicts(one) == {"pending": 1, "accepted": 1, "rejected": 1, "needs_manual_review": 0}
    assert _verdicts(two) == {"pending": 0, "accepted": 2, "rejected": 1, "needs_manual_review": 0}
    for body in (one, two):
        # One run each, and only that one: the other project's run is in no scoped figure.
        assert sum(_states(body).values()) == 1 and _states(body)["created"] == 1
        assert "spend" not in body["run_activity"], "no provider call in this project: spend is absent, not zero"
        assert len(body["section_breakdown"]) == 16 and sum(r["document_count"] for r in body["section_breakdown"]) == 0
        assert set(body) == {
            "documents_by_project", "findings_by_verdict", "run_activity", "section_breakdown",
            "awaiting_decision_findings",
        }
        # `UI-PARITY-P0B`, `R-150q`: the project's run is `created`, not a result, so no finding of it awaits a
        # decision on a current version -- while `findings_by_verdict` above, the all-time count, still sees them.
        assert body["awaiting_decision_findings"] == 0
        assert all(
            row["audit_counts"]["document_count"] == row["document_count"] and row["finding_count"] == 0
            for row in body["section_breakdown"]
        )


def test_the_unscoped_read_still_covers_every_project_and_an_empty_parameter_is_the_absent_one(
    shipped_router: Surface, session: Session
) -> None:
    a, b = _two_projects(shipped_router, session)
    whole = ok(get(shipped_router, DASHBOARD))
    empty = ok(get(shipped_router, f"{DASHBOARD}?project_uid="))
    assert empty == whole, "`?project_uid=` is the absent parameter, as an empty `?category=` is"
    listed = {row["project_uid"] for row in whole["documents_by_project"]}
    assert {a.run.run.project_uid, b.run.run.project_uid} <= listed
    # Relative, never absolute: the lane database carries other suites' rows.
    assert _verdicts(whole)["accepted"] >= 3 and _verdicts(whole)["rejected"] >= 2
    assert sum(_states(whole).values()) >= 2


def test_a_project_that_does_not_exist_is_the_existing_not_found_envelope(shipped_router: Surface) -> None:
    answer = get(shipped_router, f"{DASHBOARD}?project_uid=prj_01ARZ3NDEKTSV4RRFFQ69G5FAV")
    assert answer.status == 404, answer.body
    envelope = json.loads(answer.body)
    assert envelope["error_code"] == "not_found", "the refusal every project-scoped read answers with"


def test_a_malformed_project_identity_is_refused_not_ignored(shipped_router: Surface) -> None:
    for bad in ("not-a-project", "doc_01ARZ3NDEKTSV4RRFFQ69G5FAV", "prj_short"):
        answer = get(shipped_router, f"{DASHBOARD}?project_uid={bad}")
        assert answer.status == 422, (bad, answer.body)
        assert json.loads(answer.body)["error_code"] == "validation_failed"
