"""The dispatcher's reads: a listing of assignments and one assignment with its history.

Both are projections over ``work_assignment`` and its events (the
``work_assignment_current`` view); nothing is stored in these shapes. Visibility is
:func:`.policy.can_read`: an administrator reads every assignment, an expert reads only the
assignments currently given to them, and an account with neither role reads nothing
(`R-80`).

The listing is complete and newest first; the edge pages what it is given and never
re-sorts, as for every other listing in this system.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from auditmanager.access.public import ROLE_ADMIN
from auditmanager.dispatch.identity import AssignmentUid
from auditmanager.dispatch.policy import (
    AGGREGATE_TYPE,
    STATUS_AFTER,
    STATUSES,
    can_read,
    kinds_with_status,
    require_reader,
)
from auditmanager.dispatch.repository import (
    AssignmentEvent,
    AssignmentRecord,
    AssignmentRepository,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdentityError, ProjectUid

__all__ = ["AssignmentDetail", "assignment_overview", "get_assignment", "list_assignments"]


@dataclass(frozen=True, slots=True)
class AssignmentDetail:
    """One assignment and its whole history, oldest event first."""

    assignment: AssignmentRecord
    history: tuple[AssignmentEvent, ...]


def list_assignments(
    session: Session,
    *,
    viewer_uid: str,
    viewer_roles: frozenset[str],
    mine: bool = False,
    status: str | None = None,
    project_uid: str | None = None,
    repository: AssignmentRepository | None = None,
) -> tuple[AssignmentRecord, ...]:
    """Assignments the viewer may read, narrowed by ``mine``, ``status`` and ``project_uid``.

    ``mine`` limits an administrator to the work given to them; an expert who is not an
    administrator is always limited so, whatever ``mine`` says -- that is what "an expert reads
    their own" means, not a filter they may lift. ``status`` is one of the five statuses
    (``validation_failed`` otherwise); ``project_uid`` must be well formed and need not exist
    (an unknown project lists nothing).
    """
    roles = frozenset(viewer_roles)
    require_reader(roles)
    kinds = None if status is None else kinds_with_status(status)
    assignee, project = _scope(viewer_uid, roles, mine=mine, project_uid=project_uid)
    return (repository or AssignmentRepository()).list(
        session, assignee_user_uid=assignee, project_uid=project, kinds=kinds
    )


def assignment_overview(
    session: Session,
    *,
    viewer_uid: str,
    viewer_roles: frozenset[str],
    mine: bool = False,
    project_uid: str | None = None,
    repository: AssignmentRepository | None = None,
) -> tuple[tuple[str, int], ...]:
    """Every status with the number of assignments in it, over :func:`list_assignments`'s scope.

    The scope is the listing's -- what the viewer may read, ``mine``, ``project_uid`` -- and the
    listing's status filter is deliberately absent: each count is what choosing that status
    would list. All five statuses are answered, in :data:`~.policy.STATUSES` order, ``0`` for one
    that no assignment is in (contract 1.36.0).
    """
    roles = frozenset(viewer_roles)
    require_reader(roles)
    assignee, project = _scope(viewer_uid, roles, mine=mine, project_uid=project_uid)
    by_kind = (repository or AssignmentRepository()).counts_by_kind(
        session, assignee_user_uid=assignee, project_uid=project
    )
    counts = dict.fromkeys(STATUSES, 0)
    for kind, count in by_kind.items():
        counts[STATUS_AFTER[kind]] += count
    return tuple(counts.items())


def _scope(
    viewer_uid: str, roles: frozenset[str], *, mine: bool, project_uid: str | None
) -> tuple[str | None, str | None]:
    """``(assignee filter, project filter)``: the narrowing both reads apply."""
    project = None
    if project_uid is not None:
        try:
            project = str(ProjectUid.parse(project_uid))
        except IdentityError:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, field="project_uid", constraint="pattern"
            ) from None
    assignee = viewer_uid if (mine or ROLE_ADMIN not in roles) else None
    return assignee, project


def get_assignment(
    session: Session,
    *,
    assignment_uid: str,
    viewer_uid: str,
    viewer_roles: frozenset[str],
    repository: AssignmentRepository | None = None,
) -> AssignmentDetail:
    """One assignment with its history, or ``not_found`` when it is absent or not visible."""
    roles = frozenset(viewer_roles)
    require_reader(roles)
    uid = AssignmentUid.parse(assignment_uid)
    repository = repository or AssignmentRepository()
    record = repository.get(session, uid)
    if record is None or not can_read(
        current_assignee=record.assignee_user_uid, viewer_uid=viewer_uid, viewer_roles=roles
    ):
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type=AGGREGATE_TYPE)
    return AssignmentDetail(assignment=record, history=repository.history(session, uid))
