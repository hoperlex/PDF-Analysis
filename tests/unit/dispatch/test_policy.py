"""`W61-DISPATCHER-01`: the dispatcher's rules, exhaustively and without a database.

The transition table is checked cell by cell against an independent statement of the
intended machine (``INTENDED`` below, written from the task's outcome, not read from the
module), every status times every kind; who may make each move; what an exact repeat
answers; and that the migration restates the module's vocabulary and bounds exactly.
"""

from __future__ import annotations

import importlib.util
from itertools import product
from pathlib import Path
from types import ModuleType

import pytest

from auditmanager.dispatch import policy
from auditmanager.dispatch.identity import AssignmentUid
from auditmanager.dispatch.policy import CurrentState, TransitionRequest, plan_transition
from auditmanager.shared.errors import DomainError, ErrorCode

ROOT = Path(__file__).resolve().parents[3]
MIGRATION = ROOT / "db/migrations/versions/20261020_0025_work_assignments.py"

EXPERT_UID = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAA"
OTHER_UID = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAB"
ADMIN_UID = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAC"

#: (status, kind) -> the status after, for every move the task allows; nothing else is.
INTENDED: dict[tuple[str, str], str] = {
    ("assigned", "started"): "in_progress",
    ("assigned", "returned"): "returned",
    ("assigned", "reassigned"): "assigned",
    ("assigned", "cancelled"): "cancelled",
    ("in_progress", "completed"): "done",
    ("in_progress", "returned"): "returned",
    ("in_progress", "reassigned"): "assigned",
    ("in_progress", "cancelled"): "cancelled",
    ("returned", "reassigned"): "assigned",
    ("returned", "cancelled"): "cancelled",
}

#: Cells whose request cannot differ from the latest event: ``in_progress`` is reached only by
#: ``started`` and ``done`` only by ``completed`` (neither carries a reason), and the
#: ``cancelled`` state below carries no reason either. ``returned`` differs by its reason.
REPEAT_CELLS = {("in_progress", "started"), ("done", "completed"), ("cancelled", "cancelled")}

#: A latest event that leaves the assignment in each status.
LAST_KIND_FOR = {
    "assigned": "assigned",
    "in_progress": "started",
    "done": "completed",
    "returned": "returned",
    "cancelled": "cancelled",
}


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_0025", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _state(status: str, *, assignee: str = EXPERT_UID) -> CurrentState:
    last = LAST_KIND_FOR[status]
    return CurrentState(
        current_assignee=assignee,
        last_kind=last,
        last_reason="старая причина" if last == "returned" else None,
        last_new_assignee=None,
    )


def _request(kind: str) -> TransitionRequest:
    return TransitionRequest(
        kind=kind,
        reason="причина" if kind == "returned" else None,
        new_assignee=OTHER_UID if kind == "reassigned" else None,
    )


def _actor_for(kind: str) -> tuple[str, frozenset[str]]:
    return (ADMIN_UID, frozenset({"admin"})) if kind in policy.ADMIN_KINDS else (
        EXPERT_UID, frozenset({"expert"}),
    )


def _code(call) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call()
    return caught.value


def test_the_migration_restates_the_vocabulary_and_bounds() -> None:
    migration = _migration()
    assert migration.EVENT_KINDS == policy.EVENT_KINDS
    assert migration.MAX_NOTE_LENGTH == policy.MAX_NOTE_LENGTH
    assert migration.MAX_REASON_LENGTH == policy.MAX_REASON_LENGTH
    assert migration.revision == "0025_work_assignments"
    assert migration.down_revision == "0024_version_classification"


def test_every_kind_has_a_status_and_terminality_is_the_tables_emptiness() -> None:
    assert set(policy.STATUS_AFTER) == set(policy.EVENT_KINDS)
    assert set(policy.STATUS_AFTER.values()) == set(policy.STATUSES)
    assert set(policy.ALLOWED_KINDS) == set(policy.STATUSES)
    assert policy.TERMINAL_STATUSES == {s for s, kinds in policy.ALLOWED_KINDS.items() if not kinds}
    assert policy.TERMINAL_KINDS == {"completed", "cancelled"}
    assert policy.OPEN_STATUSES == {"assigned", "in_progress", "returned"}
    assert policy.ASSIGNEE_KINDS | policy.ADMIN_KINDS == set(policy.TRANSITION_KINDS)
    assert not policy.ASSIGNEE_KINDS & policy.ADMIN_KINDS


@pytest.mark.parametrize(("status", "kind"), list(product(
    ("assigned", "in_progress", "done", "returned", "cancelled"),
    ("started", "completed", "returned", "reassigned", "cancelled"),
)))
def test_the_transition_table_cell_by_cell(status: str, kind: str) -> None:
    actor, roles = _actor_for(kind)
    state, request = _state(status), _request(kind)
    if (status, kind) in REPEAT_CELLS:
        # Only one event leads here and it carries no variable part, so the request is
        # necessarily the latest event repeated: answered, never refused, never appended.
        assert plan_transition(state, request, actor_uid=actor, actor_roles=roles) == "unchanged"
    elif (status, kind) in INTENDED:
        assert plan_transition(state, request, actor_uid=actor, actor_roles=roles) == "append"
        assert policy.STATUS_AFTER[kind] == INTENDED[(status, kind)]
    else:
        refused = _code(lambda: plan_transition(state, request, actor_uid=actor, actor_roles=roles))
        assert refused.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
        assert refused.detail_fields == {
            "machine": "work_assignment",
            "current_state": status,
            "requested_state": policy.STATUS_AFTER[kind],
        }


@pytest.mark.parametrize("kind", ["started", "completed", "returned"])
@pytest.mark.parametrize(
    ("actor", "roles", "capability"),
    [
        (ADMIN_UID, frozenset({"admin"}), "assignment:assignee"),
        (ADMIN_UID, frozenset({"admin", "expert"}), "assignment:assignee"),
        (OTHER_UID, frozenset({"expert"}), "assignment:assignee"),
        (EXPERT_UID, frozenset({"admin"}), "role:expert"),
        (EXPERT_UID, frozenset(), "role:expert"),
    ],
)
def test_only_the_assignee_expert_makes_the_experts_moves(kind, actor, roles, capability) -> None:
    status = "in_progress" if kind == "completed" else "assigned"
    refused = _code(
        lambda: plan_transition(_state(status), _request(kind), actor_uid=actor, actor_roles=roles)
    )
    assert refused.code is ErrorCode.PERMISSION_DENIED
    assert refused.detail_fields["required_capability"] == capability


@pytest.mark.parametrize("kind", ["reassigned", "cancelled"])
@pytest.mark.parametrize("roles", [frozenset({"expert"}), frozenset()])
def test_only_an_administrator_makes_the_administrators_moves(kind, roles) -> None:
    refused = _code(
        lambda: plan_transition(_state("assigned"), _request(kind), actor_uid=EXPERT_UID, actor_roles=roles)
    )
    assert refused.code is ErrorCode.PERMISSION_DENIED
    assert refused.detail_fields["required_capability"] == "role:admin"


def test_permission_is_decided_before_the_table() -> None:
    """A refused move from a terminal status tells an unauthorized caller nothing about it."""
    refused = _code(
        lambda: plan_transition(
            _state("done"), _request("cancelled"), actor_uid=EXPERT_UID, actor_roles=frozenset({"expert"})
        )
    )
    assert refused.code is ErrorCode.PERMISSION_DENIED


@pytest.mark.parametrize(
    ("last_kind", "request_", "actor", "roles"),
    [
        ("started", TransitionRequest("started"), EXPERT_UID, frozenset({"expert"})),
        ("completed", TransitionRequest("completed"), EXPERT_UID, frozenset({"expert"})),
        ("returned", TransitionRequest("returned", reason="нет данных"), EXPERT_UID, frozenset({"expert"})),
        ("cancelled", TransitionRequest("cancelled"), ADMIN_UID, frozenset({"admin"})),
        ("cancelled", TransitionRequest("cancelled", reason="закрыт"), ADMIN_UID, frozenset({"admin"})),
        (
            "reassigned",
            TransitionRequest("reassigned", reason="отпуск", new_assignee=EXPERT_UID),
            ADMIN_UID,
            frozenset({"admin"}),
        ),
    ],
)
def test_an_exact_repeat_is_unchanged(last_kind, request_, actor, roles) -> None:
    state = CurrentState(
        current_assignee=EXPERT_UID,
        last_kind=last_kind,
        last_reason=request_.reason,
        last_new_assignee=request_.new_assignee,
    )
    assert plan_transition(state, request_, actor_uid=actor, actor_roles=roles) == "unchanged"


def test_a_repeat_with_another_reason_or_assignee_is_not_a_repeat() -> None:
    returned = CurrentState(EXPERT_UID, "returned", "нет данных", None)
    refused = _code(lambda: plan_transition(
        returned, TransitionRequest("returned", reason="другое"), actor_uid=EXPERT_UID,
        actor_roles=frozenset({"expert"}),
    ))
    assert refused.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    cancelled = CurrentState(EXPERT_UID, "cancelled", None, None)
    refused = _code(lambda: plan_transition(
        cancelled, TransitionRequest("cancelled", reason="иначе"), actor_uid=ADMIN_UID,
        actor_roles=frozenset({"admin"}),
    ))
    assert refused.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    reassigned = CurrentState(EXPERT_UID, "reassigned", None, EXPERT_UID)
    assert plan_transition(
        reassigned, TransitionRequest("reassigned", new_assignee=OTHER_UID), actor_uid=ADMIN_UID,
        actor_roles=frozenset({"admin"}),
    ) == "append"


def test_reassigning_to_the_current_assignee() -> None:
    for status in ("assigned", "in_progress"):
        refused = _code(lambda: plan_transition(
            _state(status), TransitionRequest("reassigned", new_assignee=EXPERT_UID),
            actor_uid=ADMIN_UID, actor_roles=frozenset({"admin"}),
        ))
        assert refused.code is ErrorCode.VALIDATION_FAILED
        assert refused.detail_fields["constraint"] == "differs_from_current_assignee"
    assert plan_transition(
        _state("returned"), TransitionRequest("reassigned", new_assignee=EXPERT_UID),
        actor_uid=ADMIN_UID, actor_roles=frozenset({"admin"}),
    ) == "append"


@pytest.mark.parametrize(
    ("request_", "field", "constraint"),
    [
        (TransitionRequest("assigned"), "kind", "enum"),
        (TransitionRequest("approve"), "kind", "enum"),
        (TransitionRequest("returned"), "reason", "required"),
        (TransitionRequest("started", reason="x"), "reason", "not_allowed"),
        (TransitionRequest("completed", reason="x"), "reason", "not_allowed"),
        (TransitionRequest("reassigned"), "new_assignee_user_uid", "required"),
        (TransitionRequest("cancelled", new_assignee=OTHER_UID), "new_assignee_user_uid", "not_allowed"),
    ],
)
def test_the_requests_shape_is_checked_first(request_, field, constraint) -> None:
    refused = _code(lambda: plan_transition(
        _state("assigned"), request_, actor_uid=OTHER_UID, actor_roles=frozenset(),
    ))
    assert refused.code is ErrorCode.VALIDATION_FAILED
    assert refused.detail_fields == {"field": field, "constraint": constraint}


def test_reading() -> None:
    assert policy.can_read(current_assignee=EXPERT_UID, viewer_uid=ADMIN_UID, viewer_roles=frozenset({"admin"}))
    assert policy.can_read(current_assignee=EXPERT_UID, viewer_uid=EXPERT_UID, viewer_roles=frozenset({"expert"}))
    assert not policy.can_read(current_assignee=EXPERT_UID, viewer_uid=OTHER_UID, viewer_roles=frozenset({"expert"}))
    assert not policy.can_read(current_assignee=EXPERT_UID, viewer_uid=EXPERT_UID, viewer_roles=frozenset())
    with pytest.raises(DomainError) as caught:
        policy.require_reader(frozenset())
    assert caught.value.detail_fields["required_capability"] == "role:admin|expert"


def test_status_filters_and_text() -> None:
    assert policy.kinds_with_status("assigned") == {"assigned", "reassigned"}
    assert policy.kinds_with_status("done") == {"completed"}
    with pytest.raises(DomainError):
        policy.kinds_with_status("open")
    assert policy.normalize_text("  ", field="note", maximum=5) is None
    assert policy.normalize_text(None, field="note", maximum=5) is None
    assert policy.normalize_text(" ab ", field="note", maximum=5) == "ab"
    with pytest.raises(DomainError) as caught:
        policy.normalize_text("abcdef", field="note", maximum=5)
    assert caught.value.detail_fields == {"field": "note", "constraint": "max_length"}


def test_the_assignment_identity() -> None:
    minted = AssignmentUid.new()
    assert str(minted).startswith("asg_") and len(str(minted)) == 30
    assert AssignmentUid.parse(str(minted)) == minted
    for bad in ("prj_01ARZ3NDEKTSV4RRFFQ69G5FAV", "asg_01ARZ3NDEKTSV4RRFFQ69G5FAI", "asg_", 7):
        with pytest.raises(DomainError) as caught:
            AssignmentUid(bad)  # type: ignore[arg-type]
        assert caught.value.detail_fields == {"field": "assignment_uid", "constraint": "pattern"}
