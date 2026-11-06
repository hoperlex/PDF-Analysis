"""Contract 1.36.0: the dispatcher's status counts, without a database.

``assignment_overview`` turns the repository's count per *last event kind* into a count per *status* -- two kinds
(``assigned`` and ``reassigned``) leave an assignment ``assigned`` -- answers all five statuses in the vocabulary's
order, and narrows exactly the way the listing does. The database half (the grouped statement itself, against real
rows) is ``tests/integration/dispatch/test_dispatch_commands.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.dispatch import policy
from auditmanager.dispatch.queries import assignment_overview
from auditmanager.shared.errors import DomainError, ErrorCode

ADMIN_UID = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAC"
EXPERT_UID = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAA"
PROJECT = "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV"


class _Repository:
    """Answers the grouped count the way the statement does: only the kinds that occur."""

    def __init__(self, counts: dict[str, int]) -> None:
        self._counts = counts
        self.asked: list[dict[str, Any]] = []

    def counts_by_kind(self, session: object, *, assignee_user_uid: str | None, project_uid: str | None) -> dict[str, int]:
        self.asked.append({"assignee": assignee_user_uid, "project": project_uid})
        return dict(self._counts)


def _overview(repository: _Repository, **kwargs: Any) -> dict[str, int]:
    arguments: dict[str, Any] = {"viewer_uid": ADMIN_UID, "viewer_roles": frozenset({"admin"})}
    arguments.update(kwargs)
    return dict(assignment_overview(object(), repository=repository, **arguments))  # type: ignore[arg-type]


def test_all_five_statuses_are_answered_in_the_vocabulary_order_with_zero_for_an_empty_one() -> None:
    answer = assignment_overview(object(), viewer_uid=ADMIN_UID, viewer_roles=frozenset({"admin"}), repository=_Repository({}))  # type: ignore[arg-type]
    assert [status for status, _ in answer] == list(policy.STATUSES)
    assert [count for _, count in answer] == [0, 0, 0, 0, 0]


def test_the_two_kinds_that_leave_work_assigned_are_one_count() -> None:
    counts = _overview(_Repository({"assigned": 3, "reassigned": 2, "started": 4, "completed": 1, "returned": 5, "cancelled": 6}))
    assert counts == {"assigned": 5, "in_progress": 4, "done": 1, "returned": 5, "cancelled": 6}


def test_every_kind_the_policy_knows_lands_in_exactly_one_status() -> None:
    counts = _overview(_Repository(dict.fromkeys(policy.STATUS_AFTER, 1)))
    assert sum(counts.values()) == len(policy.STATUS_AFTER)
    assert counts["assigned"] == 2 and all(counts[status] == 1 for status in policy.STATUSES if status != "assigned")


def test_the_scope_is_the_listings_and_has_no_status_filter() -> None:
    repository = _Repository({})
    _overview(repository, project_uid=PROJECT)
    _overview(repository, mine=True)
    _overview(repository, viewer_uid=EXPERT_UID, viewer_roles=frozenset({"expert"}))
    _overview(repository, viewer_uid=EXPERT_UID, viewer_roles=frozenset({"expert"}), mine=True)
    assert repository.asked == [
        {"assignee": None, "project": PROJECT},          # an administrator reads every assignment of the project
        {"assignee": ADMIN_UID, "project": None},        # `mine` narrows an administrator to their own
        {"assignee": EXPERT_UID, "project": None},       # an expert is always limited to their own...
        {"assignee": EXPERT_UID, "project": None},       # ...whatever `mine` says
    ]


def test_the_refusals_are_the_listings() -> None:
    with pytest.raises(DomainError) as nobody:
        _overview(_Repository({}), viewer_roles=frozenset())
    assert nobody.value.code is ErrorCode.PERMISSION_DENIED
    with pytest.raises(DomainError) as malformed:
        _overview(_Repository({}), project_uid="doc_01ARZ3NDEKTSV4RRFFQ69G5FAV")
    assert malformed.value.code is ErrorCode.VALIDATION_FAILED
    assert malformed.value.detail_fields == {"field": "project_uid", "constraint": "pattern"}
