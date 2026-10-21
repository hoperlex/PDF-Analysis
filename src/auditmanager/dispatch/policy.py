"""The dispatcher's rules, with no I/O: statuses, allowed moves, who may make them, repeats.

Everything the database does not decide is decided here, and only here. The schema stores
events (``0025_work_assignments``); this module says what they mean.

**Status is derived from the latest event** (:data:`STATUS_AFTER`): ``assigned`` and
``reassigned`` leave the assignment ``assigned``; ``started`` makes it ``in_progress``;
``completed`` makes it ``done``; ``returned`` and ``cancelled`` name themselves. ``done`` and
``cancelled`` are terminal. An assignment that is not terminal is **open**.

**Allowed moves** (:data:`ALLOWED_KINDS`), from each status:

* ``assigned``    -> started, returned, reassigned, cancelled
* ``in_progress`` -> completed, returned, reassigned, cancelled
* ``returned``    -> reassigned, cancelled (the expert gave it back; an administrator decides)
* ``done``, ``cancelled`` -> nothing

**Who may make them** (`R-60`: roles are a set; an administrator without ``expert`` reads and
does not decide an expert's work):

* ``started``, ``completed``, ``returned`` -- only the **current assignee**, holding
  ``expert``. An administrator who is not the assignee is ``permission_denied``.
* ``reassigned``, ``cancelled`` -- ``admin``. Creating an assignment too.

**Reading.** An administrator reads every assignment; an expert reads the assignments whose
current assignee they are. Anything else is ``not_found``: the catalog's rule is that a
response never reveals a resource the caller may not see.

**Exact repeats.** A request equal to the latest event (same kind, same reason, same new
assignee), from someone allowed to make it, answers the current state and writes nothing --
the first actor's event stands. Anything else that the table does not allow is
``state_transition_not_allowed`` with the ``work_assignment`` machine's details.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Literal

from auditmanager.access.public import ROLE_ADMIN, ROLE_EXPERT
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "AGGREGATE_TYPE",
    "ALLOWED_KINDS",
    "ASSIGNEE_KINDS",
    "ADMIN_KINDS",
    "CAPABILITY_ASSIGNEE",
    "CONFLICT_ASSIGNMENT_OPEN",
    "CONSTRAINT_ACTIVE_EXPERT",
    "CONSTRAINT_ASSIGNEE_UNCHANGED",
    "EVENT_KINDS",
    "KIND_ASSIGNED",
    "KIND_CANCELLED",
    "KIND_COMPLETED",
    "KIND_REASSIGNED",
    "KIND_RETURNED",
    "KIND_STARTED",
    "MACHINE",
    "MAX_NOTE_LENGTH",
    "MAX_REASON_LENGTH",
    "OPEN_STATUSES",
    "STATUSES",
    "STATUS_AFTER",
    "STATUS_ASSIGNED",
    "STATUS_CANCELLED",
    "STATUS_DONE",
    "STATUS_IN_PROGRESS",
    "STATUS_RETURNED",
    "TERMINAL_KINDS",
    "TERMINAL_STATUSES",
    "TRANSITION_KINDS",
    "CurrentState",
    "TransitionRequest",
    "can_read",
    "kinds_with_status",
    "normalize_text",
    "plan_transition",
    "require_admin",
    "require_reader",
]

#: The machine name a refused move reports (``state_transition_not_allowed`` details).
MACHINE: Final[str] = "work_assignment"
#: ``aggregate_type`` on ``not_found``, ``permission_denied`` and ``conflict``.
AGGREGATE_TYPE: Final[str] = "WorkAssignment"

KIND_ASSIGNED: Final[str] = "assigned"
KIND_STARTED: Final[str] = "started"
KIND_COMPLETED: Final[str] = "completed"
KIND_RETURNED: Final[str] = "returned"
KIND_REASSIGNED: Final[str] = "reassigned"
KIND_CANCELLED: Final[str] = "cancelled"

#: The event vocabulary, in the order migration ``0025`` declares it (held equal by a test).
EVENT_KINDS: Final[tuple[str, ...]] = (
    KIND_ASSIGNED,
    KIND_STARTED,
    KIND_COMPLETED,
    KIND_RETURNED,
    KIND_REASSIGNED,
    KIND_CANCELLED,
)
#: What a transition request may name: every kind but the creation event.
TRANSITION_KINDS: Final[tuple[str, ...]] = tuple(k for k in EVENT_KINDS if k != KIND_ASSIGNED)

STATUS_ASSIGNED: Final[str] = "assigned"
STATUS_IN_PROGRESS: Final[str] = "in_progress"
STATUS_DONE: Final[str] = "done"
STATUS_RETURNED: Final[str] = "returned"
STATUS_CANCELLED: Final[str] = "cancelled"

STATUSES: Final[tuple[str, ...]] = (
    STATUS_ASSIGNED,
    STATUS_IN_PROGRESS,
    STATUS_DONE,
    STATUS_RETURNED,
    STATUS_CANCELLED,
)

#: The status an assignment is in after an event of each kind.
STATUS_AFTER: Final[Mapping[str, str]] = {
    KIND_ASSIGNED: STATUS_ASSIGNED,
    KIND_REASSIGNED: STATUS_ASSIGNED,
    KIND_STARTED: STATUS_IN_PROGRESS,
    KIND_COMPLETED: STATUS_DONE,
    KIND_RETURNED: STATUS_RETURNED,
    KIND_CANCELLED: STATUS_CANCELLED,
}

TERMINAL_STATUSES: Final[frozenset[str]] = frozenset({STATUS_DONE, STATUS_CANCELLED})
OPEN_STATUSES: Final[frozenset[str]] = frozenset(STATUSES) - TERMINAL_STATUSES
#: The kinds whose event leaves an assignment terminal.
TERMINAL_KINDS: Final[frozenset[str]] = frozenset(
    kind for kind, status in STATUS_AFTER.items() if status in TERMINAL_STATUSES
)

#: From each status, the kinds a transition may append. A status with none is terminal.
ALLOWED_KINDS: Final[Mapping[str, frozenset[str]]] = {
    STATUS_ASSIGNED: frozenset({KIND_STARTED, KIND_RETURNED, KIND_REASSIGNED, KIND_CANCELLED}),
    STATUS_IN_PROGRESS: frozenset(
        {KIND_COMPLETED, KIND_RETURNED, KIND_REASSIGNED, KIND_CANCELLED}
    ),
    STATUS_RETURNED: frozenset({KIND_REASSIGNED, KIND_CANCELLED}),
    STATUS_DONE: frozenset(),
    STATUS_CANCELLED: frozenset(),
}

#: The moves only the current assignee (an expert) makes, and the administrator's moves.
ASSIGNEE_KINDS: Final[frozenset[str]] = frozenset({KIND_STARTED, KIND_COMPLETED, KIND_RETURNED})
ADMIN_KINDS: Final[frozenset[str]] = frozenset({KIND_REASSIGNED, KIND_CANCELLED})

#: Kinds that carry a reason: required on ``returned``, optional on the administrator's moves.
_REASON_REQUIRED: Final[frozenset[str]] = frozenset({KIND_RETURNED})
_REASON_ALLOWED: Final[frozenset[str]] = frozenset({KIND_RETURNED, KIND_REASSIGNED, KIND_CANCELLED})

MAX_NOTE_LENGTH: Final[int] = 2000
MAX_REASON_LENGTH: Final[int] = 2000

#: ``permission_denied`` ``required_capability`` when the caller is not the assignee.
CAPABILITY_ASSIGNEE: Final[str] = "assignment:assignee"
#: ``conflict`` ``conflict_reason``: the scope (project, or project and document) already has
#: an open assignment with a different assignee or note; reassign or cancel that one.
CONFLICT_ASSIGNMENT_OPEN: Final[str] = "assignment_open"
#: ``validation_failed`` ``constraint`` on ``assignee_user_uid`` / ``new_assignee_user_uid``:
#: the account does not exist, is archived, or does not hold ``expert``.
CONSTRAINT_ACTIVE_EXPERT: Final[str] = "active_expert_required"
#: ``validation_failed`` ``constraint`` on ``new_assignee_user_uid``: a reassignment of an
#: ``assigned`` or ``in_progress`` assignment must name somebody else.
CONSTRAINT_ASSIGNEE_UNCHANGED: Final[str] = "differs_from_current_assignee"


def kinds_with_status(status: str) -> frozenset[str]:
    """The event kinds whose event leaves an assignment in ``status`` (the list filter)."""
    if status not in STATUSES:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="status", constraint="enum")
    return frozenset(kind for kind, after in STATUS_AFTER.items() if after == status)


def normalize_text(raw: str | None, *, field: str, maximum: int) -> str | None:
    """Trim; an empty or absent value is ``None``; longer than ``maximum`` is refused."""
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint="type")
    cleaned = raw.strip()
    if not cleaned:
        return None
    if len(cleaned) > maximum:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=f"{field} is longer than {maximum} characters",
            field=field,
            constraint="max_length",
        )
    return cleaned


def require_admin(roles: frozenset[str]) -> None:
    """Creating, reassigning and cancelling are administrative acts."""
    if ROLE_ADMIN not in roles:
        raise DomainError(
            ErrorCode.PERMISSION_DENIED,
            message="only an administrator assigns, reassigns or cancels work",
            aggregate_type=AGGREGATE_TYPE,
            required_capability="role:admin",
        )


def require_reader(roles: frozenset[str]) -> None:
    """`R-80`: an account without a role reads no product data."""
    if not roles & {ROLE_ADMIN, ROLE_EXPERT}:
        raise DomainError(
            ErrorCode.PERMISSION_DENIED,
            aggregate_type=AGGREGATE_TYPE,
            required_capability="role:admin|expert",
        )


def can_read(*, current_assignee: str, viewer_uid: str, viewer_roles: frozenset[str]) -> bool:
    """An administrator reads every assignment; an expert reads the ones assigned to them."""
    if ROLE_ADMIN in viewer_roles:
        return True
    return ROLE_EXPERT in viewer_roles and current_assignee == viewer_uid


@dataclass(frozen=True, slots=True)
class CurrentState:
    """What a transition is decided against: the derived state and the latest event."""

    current_assignee: str
    last_kind: str
    last_reason: str | None
    last_new_assignee: str | None

    @property
    def status(self) -> str:
        try:
            return STATUS_AFTER[self.last_kind]
        except KeyError:  # pragma: no cover - the CHECK admits only the six kinds
            raise DomainError(
                ErrorCode.INTERNAL_ERROR, message=f"unknown assignment event kind {self.last_kind!r}"
            ) from None


@dataclass(frozen=True, slots=True)
class TransitionRequest:
    """A requested move, already normalized (:func:`normalize_text` on the reason)."""

    kind: str
    reason: str | None = None
    new_assignee: str | None = None


def _validate_shape(request: TransitionRequest) -> None:
    if request.kind not in TRANSITION_KINDS:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="kind", constraint="enum")
    if request.kind in _REASON_REQUIRED and request.reason is None:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="returning an assignment needs a reason",
            field="reason",
            constraint="required",
        )
    if request.kind not in _REASON_ALLOWED and request.reason is not None:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=f"a {request.kind} event carries no reason",
            field="reason",
            constraint="not_allowed",
        )
    if request.kind == KIND_REASSIGNED and request.new_assignee is None:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="a reassignment names the new assignee",
            field="new_assignee_user_uid",
            constraint="required",
        )
    if request.kind != KIND_REASSIGNED and request.new_assignee is not None:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="only a reassignment names a new assignee",
            field="new_assignee_user_uid",
            constraint="not_allowed",
        )


def _authorize(
    state: CurrentState, request: TransitionRequest, actor_uid: str, actor_roles: frozenset[str]
) -> None:
    if request.kind in ADMIN_KINDS:
        require_admin(actor_roles)
        return
    # An assignee's move. The caller already passed :func:`can_read`, so an expert who is not
    # the assignee never gets here (``not_found``); an administrator who is not may.
    if state.current_assignee != actor_uid:
        raise DomainError(
            ErrorCode.PERMISSION_DENIED,
            message="only the expert the work is assigned to starts, completes or returns it",
            aggregate_type=AGGREGATE_TYPE,
            required_capability=CAPABILITY_ASSIGNEE,
        )
    if ROLE_EXPERT not in actor_roles:
        raise DomainError(
            ErrorCode.PERMISSION_DENIED,
            aggregate_type=AGGREGATE_TYPE,
            required_capability="role:expert",
        )


def _is_exact_repeat(state: CurrentState, request: TransitionRequest) -> bool:
    return (
        state.last_kind == request.kind
        and state.last_reason == request.reason
        and state.last_new_assignee == request.new_assignee
    )


def plan_transition(
    state: CurrentState,
    request: TransitionRequest,
    *,
    actor_uid: str,
    actor_roles: frozenset[str],
) -> Literal["append", "unchanged"]:
    """Decide one move: ``"append"`` its event, answer ``"unchanged"``, or refuse.

    Order: the request's own shape (``validation_failed``), who may make it
    (``permission_denied``), an exact repeat (``"unchanged"``), the transition table
    (``state_transition_not_allowed``), and a reassignment that names the current assignee of
    work still in hand (``validation_failed``). Whether a new assignee is an active expert is
    the caller's check, because it reads the account.
    """
    _validate_shape(request)
    _authorize(state, request, actor_uid, actor_roles)
    if _is_exact_repeat(state, request):
        return "unchanged"
    status = state.status
    if request.kind not in ALLOWED_KINDS[status]:
        requested = STATUS_AFTER[request.kind]
        raise DomainError(
            ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
            message=f"an assignment that is {status} cannot become {requested} by {request.kind}",
            machine=MACHINE,
            current_state=status,
            requested_state=requested,
        )
    if (
        request.kind == KIND_REASSIGNED
        and status != STATUS_RETURNED
        and request.new_assignee == state.current_assignee
    ):
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="the work is already assigned to this expert",
            field="new_assignee_user_uid",
            constraint=CONSTRAINT_ASSIGNEE_UNCHANGED,
        )
    return "append"
