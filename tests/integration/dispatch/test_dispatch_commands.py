"""`W61-DISPATCHER-01` phase A: every command's allow/refuse matrix on real PostgreSQL.

Who may assign, move, read and purge, what an exact repeat answers, and what a conflicting
move is refused with -- each through ``auditmanager.dispatch.public`` against a fresh
migrated database, with the people made by the ``access`` boundary.
"""

from __future__ import annotations

import threading
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from auditmanager.access.public import AccountRepository
from auditmanager.dispatch.public import (
    AssignmentRecord,
    assign_work,
    get_assignment,
    list_assignments,
    transition_assignment,
)
from auditmanager.shared.errors import DomainError, ErrorCode

accounts = AccountRepository()

ADMIN = frozenset({"admin"})
EXPERT = frozenset({"expert"})
BOTH = frozenset({"admin", "expert"})
NONE: frozenset[str] = frozenset()


def _roles(session: Session, uid: str) -> frozenset[str]:
    """The role set read in the caller's transaction, as the composition root reads it."""
    return accounts.roles_of(session, uid)


def _assign(session: Session, cast: Any, *, actor: str | None = None, **overrides: Any) -> AssignmentRecord:
    actor = actor or cast.admin
    arguments: dict[str, Any] = {
        "project_uid": cast.project,
        "document_uid": None,
        "assignee_user_uid": cast.expert,
        "note": None,
    }
    arguments.update(overrides)
    record = assign_work(session, actor_uid=actor, actor_roles=_roles(session, actor), **arguments)
    session.commit()
    return record


def _move(session: Session, uid: str, kind: str, actor: str, **extra: Any) -> AssignmentRecord:
    record = transition_assignment(
        session, assignment_uid=uid, kind=kind, actor_uid=actor,
        actor_roles=_roles(session, actor), **extra,
    )
    session.commit()
    return record


def _refused(code: ErrorCode, call: Any, *args: Any, **kwargs: Any) -> DomainError:
    session = kwargs.get("session") or args[0]
    with pytest.raises(DomainError) as caught:
        call(*args, **kwargs)
    session.rollback()
    assert caught.value.code is code, (caught.value.code, caught.value.detail_fields)
    return caught.value


def _events(session: Session, uid: str) -> int:
    return int(
        session.execute(
            text("SELECT count(*) FROM work_assignment_event WHERE assignment_uid = :a"), {"a": uid}
        ).scalar_one()
    )


# -- assign ------------------------------------------------------------------------------


class TestAssign:
    def test_an_administrator_assigns_a_project_and_a_document(self, session, cast) -> None:
        whole = _assign(session, cast, note="  проверить до пятницы  ")
        assert whole.assignment_uid.startswith("asg_")
        assert (whole.project_uid, whole.document_uid, whole.assignee_user_uid) == (
            cast.project, None, cast.expert,
        )
        assert (whole.status, whole.note, whole.created_by_user_uid) == (
            "assigned", "проверить до пятницы", cast.admin,
        )
        assert whole.project_name == "Школа на 550 мест" and whole.document_title is None
        one = _assign(session, cast, document_uid=cast.document, assignee_user_uid=cast.other_expert)
        assert (one.document_uid, one.document_title, one.assignee_user_uid) == (
            cast.document, "КЖ-1", cast.other_expert,
        )
        assert one.assignment_uid != whole.assignment_uid
        history = get_assignment(
            session, assignment_uid=one.assignment_uid, viewer_uid=cast.admin, viewer_roles=ADMIN
        ).history
        assert [(e.kind, e.actor_user_uid, e.reason, e.new_assignee_user_uid) for e in history] == [
            ("assigned", cast.admin, None, None)
        ]
        assert history[0].event_id.startswith("evt_")

    @pytest.mark.parametrize("who", ["expert", "nobody"])
    def test_only_an_administrator_assigns(self, session, cast, who) -> None:
        actor = getattr(cast, who)
        refused = _refused(
            ErrorCode.PERMISSION_DENIED, assign_work, session, project_uid=cast.project,
            document_uid=None, assignee_user_uid=cast.expert, note=None, actor_uid=actor,
            actor_roles=_roles(session, actor),
        )
        assert refused.detail_fields["required_capability"] == "role:admin"
        assert session.execute(text("SELECT count(*) FROM work_assignment")).scalar_one() == 0

    def test_the_assignee_must_be_an_active_expert(self, session, cast) -> None:
        seed = str(session.execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one())
        accounts.archive_account(session, actor_uid=seed, user_uid=cast.other_expert)
        session.commit()
        unknown = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
        for assignee, problem in (
            (cast.admin, "expert role"),
            (cast.nobody, "expert role"),
            (cast.other_expert, "archived"),
            (unknown, "no such account"),
        ):
            refused = _refused(
                ErrorCode.VALIDATION_FAILED, assign_work, session, project_uid=cast.project,
                document_uid=None, assignee_user_uid=assignee, note=None, actor_uid=cast.admin,
                actor_roles=ADMIN,
            )
            assert refused.detail_fields == {
                "field": "assignee_user_uid", "constraint": "active_expert_required",
            }
            assert problem in str(refused)
        assert session.execute(text("SELECT count(*) FROM work_assignment")).scalar_one() == 0

    def test_the_scope_must_exist_and_the_document_belong_to_the_project(self, session, cast) -> None:
        for project, document, aggregate in (
            ("prj_01ARZ3NDEKTSV4RRFFQ69G5FAV", None, "Project"),
            (cast.project, "doc_01ARZ3NDEKTSV4RRFFQ69G5FAV", "Document"),
            (cast.project, cast.other_document, "Document"),
        ):
            refused = _refused(
                ErrorCode.NOT_FOUND, assign_work, session, project_uid=project,
                document_uid=document, assignee_user_uid=cast.expert, note=None,
                actor_uid=cast.admin, actor_roles=ADMIN,
            )
            assert refused.detail_fields == {"aggregate_type": aggregate}

    @pytest.mark.parametrize(
        ("field", "value", "constraint"),
        [
            ("project_uid", "doc_01ARZ3NDEKTSV4RRFFQ69G5FAV", "pattern"),
            ("document_uid", "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV", "pattern"),
            ("assignee_user_uid", "anna@example.com", "pattern"),
            ("note", "я" * 2001, "max_length"),
        ],
    )
    def test_malformed_input_is_refused(self, session, cast, field, value, constraint) -> None:
        arguments = {
            "project_uid": cast.project, "document_uid": None,
            "assignee_user_uid": cast.expert, "note": None, field: value,
        }
        refused = _refused(
            ErrorCode.VALIDATION_FAILED, assign_work, session, actor_uid=cast.admin,
            actor_roles=ADMIN, **arguments,
        )
        assert refused.detail_fields == {"field": field, "constraint": constraint}

    def test_an_exact_repeat_answers_the_stored_assignment(self, session, cast) -> None:
        first = _assign(session, cast, document_uid=cast.document, note="срочно")
        again = _assign(session, cast, document_uid=cast.document, note=" срочно ", actor=cast.admin_expert)
        assert again == first
        assert again.created_by_user_uid == cast.admin  # the first creator stands
        assert session.execute(text("SELECT count(*) FROM work_assignment")).scalar_one() == 1
        assert _events(session, first.assignment_uid) == 1

    @pytest.mark.parametrize("change", ["assignee", "note"])
    def test_another_assignment_on_an_open_scope_is_a_conflict(self, session, cast, change) -> None:
        _assign(session, cast, note="срочно")
        overrides = {"assignee_user_uid": cast.other_expert} if change == "assignee" else {"note": "не срочно"}
        arguments = {"project_uid": cast.project, "document_uid": None,
                     "assignee_user_uid": cast.expert, "note": "срочно", **overrides}
        refused = _refused(
            ErrorCode.CONFLICT, assign_work, session, actor_uid=cast.admin, actor_roles=ADMIN,
            **arguments,
        )
        assert refused.detail_fields == {
            "aggregate_type": "WorkAssignment", "conflict_reason": "assignment_open",
        }
        assert session.execute(text("SELECT count(*) FROM work_assignment")).scalar_one() == 1

    def test_scopes_are_independent_and_a_closed_scope_takes_new_work(self, session, cast) -> None:
        whole = _assign(session, cast)
        one = _assign(session, cast, document_uid=cast.document, assignee_user_uid=cast.other_expert)
        assert whole.assignment_uid != one.assignment_uid
        _move(session, whole.assignment_uid, "cancelled", cast.admin)
        fresh = _assign(session, cast)
        assert fresh.assignment_uid not in {whole.assignment_uid, one.assignment_uid}
        assert fresh.status == "assigned"

    def test_two_concurrent_creations_on_one_scope_write_one_assignment(
        self, migrated_engine: Engine, session, cast
    ) -> None:
        """The scope lock: the second waits, then finds the first and answers it."""
        first = Session(migrated_engine)
        second = Session(migrated_engine)
        results: list[Any] = []
        try:
            created = assign_work(
                first, project_uid=cast.project, document_uid=None, assignee_user_uid=cast.expert,
                note=None, actor_uid=cast.admin, actor_roles=ADMIN,
            )

            def contend() -> None:
                try:
                    results.append(
                        assign_work(
                            second, project_uid=cast.project, document_uid=None,
                            assignee_user_uid=cast.expert, note=None,
                            actor_uid=cast.admin_expert, actor_roles=BOTH,
                        )
                    )
                    second.commit()
                except Exception as exc:  # noqa: BLE001 - reported below
                    results.append(exc)

            worker = threading.Thread(target=contend)
            worker.start()
            worker.join(timeout=1.5)
            assert worker.is_alive(), "the second creation must wait for the first's scope lock"
            first.commit()
            worker.join(timeout=30)
            assert not worker.is_alive()
        finally:
            first.close()
            second.close()
        assert len(results) == 1 and isinstance(results[0], AssignmentRecord), results
        assert results[0].assignment_uid == created.assignment_uid
        assert session.execute(text("SELECT count(*) FROM work_assignment")).scalar_one() == 1


# -- transitions -------------------------------------------------------------------------


class TestTheExpertsMoves:
    def test_start_then_complete_and_exact_repeats_write_nothing(self, session, cast) -> None:
        uid = _assign(session, cast).assignment_uid
        started = _move(session, uid, "started", cast.expert)
        assert started.status == "in_progress"
        assert _move(session, uid, "started", cast.expert) == started
        done = _move(session, uid, "completed", cast.expert)
        assert done.status == "done"
        assert _move(session, uid, "completed", cast.expert) == done
        assert _events(session, uid) == 3
        refused = _refused(
            ErrorCode.STATE_TRANSITION_NOT_ALLOWED, transition_assignment, session,
            assignment_uid=uid, kind="started", actor_uid=cast.expert, actor_roles=EXPERT,
        )
        assert refused.detail_fields == {
            "machine": "work_assignment", "current_state": "done", "requested_state": "in_progress",
        }

    def test_completing_work_not_started_is_refused(self, session, cast) -> None:
        uid = _assign(session, cast).assignment_uid
        refused = _refused(
            ErrorCode.STATE_TRANSITION_NOT_ALLOWED, transition_assignment, session,
            assignment_uid=uid, kind="completed", actor_uid=cast.expert, actor_roles=EXPERT,
        )
        assert refused.detail_fields["current_state"] == "assigned"
        assert _events(session, uid) == 1

    def test_a_return_needs_a_reason_and_repeats_only_exactly(self, session, cast) -> None:
        uid = _assign(session, cast).assignment_uid
        _move(session, uid, "started", cast.expert)
        for blank in (None, "   "):
            refused = _refused(
                ErrorCode.VALIDATION_FAILED, transition_assignment, session, assignment_uid=uid,
                kind="returned", actor_uid=cast.expert, actor_roles=EXPERT, reason=blank,
            )
            assert refused.detail_fields == {"field": "reason", "constraint": "required"}
        returned = _move(session, uid, "returned", cast.expert, reason="нет исходных данных")
        assert (returned.status, returned.status_reason, returned.assignee_user_uid) == (
            "returned", "нет исходных данных", cast.expert,
        )
        assert _move(session, uid, "returned", cast.expert, reason=" нет исходных данных ") == returned
        refused = _refused(
            ErrorCode.STATE_TRANSITION_NOT_ALLOWED, transition_assignment, session,
            assignment_uid=uid, kind="returned", actor_uid=cast.expert, actor_roles=EXPERT,
            reason="другая причина",
        )
        assert refused.detail_fields["current_state"] == "returned"
        refused = _refused(
            ErrorCode.STATE_TRANSITION_NOT_ALLOWED, transition_assignment, session,
            assignment_uid=uid, kind="started", actor_uid=cast.expert, actor_roles=EXPERT,
        )
        assert refused.detail_fields["requested_state"] == "in_progress"
        assert _events(session, uid) == 3

    def test_an_expert_who_is_not_the_assignee_cannot_see_it(self, session, cast) -> None:
        uid = _assign(session, cast).assignment_uid
        for kind in ("started", "completed", "cancelled", "reassigned"):
            extra = {"new_assignee_user_uid": cast.other_expert} if kind == "reassigned" else {}
            refused = _refused(
                ErrorCode.NOT_FOUND, transition_assignment, session, assignment_uid=uid,
                kind=kind, actor_uid=cast.other_expert, actor_roles=EXPERT, **extra,
            )
            assert refused.detail_fields == {"aggregate_type": "WorkAssignment"}
        _refused(
            ErrorCode.NOT_FOUND, get_assignment, session, assignment_uid=uid,
            viewer_uid=cast.other_expert, viewer_roles=EXPERT,
        )
        assert _events(session, uid) == 1

    @pytest.mark.parametrize("who", ["admin", "admin_expert"])
    def test_an_administrator_does_not_make_the_experts_moves(self, session, cast, who) -> None:
        uid = _assign(session, cast).assignment_uid
        actor = getattr(cast, who)
        refused = _refused(
            ErrorCode.PERMISSION_DENIED, transition_assignment, session, assignment_uid=uid,
            kind="started", actor_uid=actor, actor_roles=_roles(session, actor),
        )
        assert refused.detail_fields == {
            "aggregate_type": "WorkAssignment", "required_capability": "assignment:assignee",
        }

    def test_an_administrator_who_is_the_assignee_works_as_an_expert(self, session, cast) -> None:
        uid = _assign(session, cast, assignee_user_uid=cast.admin_expert).assignment_uid
        assert _move(session, uid, "started", cast.admin_expert).status == "in_progress"

    def test_an_assignee_who_lost_the_expert_role_is_refused(self, session, cast) -> None:
        uid = _assign(session, cast).assignment_uid
        seed = str(session.execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one())
        accounts.set_roles(session, actor_uid=seed, user_uid=cast.expert, roles=set())
        session.commit()
        refused = _refused(
            ErrorCode.PERMISSION_DENIED, transition_assignment, session, assignment_uid=uid,
            kind="started", actor_uid=cast.expert, actor_roles=_roles(session, cast.expert),
        )
        assert refused.detail_fields["required_capability"] in {"role:expert", "role:admin|expert"}

    @pytest.mark.parametrize(
        ("kind", "extra", "field", "constraint"),
        [
            ("assigned", {}, "kind", "enum"),
            ("approved", {}, "kind", "enum"),
            ("started", {"reason": "потому что"}, "reason", "not_allowed"),
            ("completed", {"reason": "готово"}, "reason", "not_allowed"),
            ("started", {"new_assignee_user_uid": "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"},
             "new_assignee_user_uid", "not_allowed"),
            ("returned", {"reason": "я" * 2001}, "reason", "max_length"),
        ],
    )
    def test_malformed_moves_are_refused(self, session, cast, kind, extra, field, constraint) -> None:
        uid = _assign(session, cast).assignment_uid
        refused = _refused(
            ErrorCode.VALIDATION_FAILED, transition_assignment, session, assignment_uid=uid,
            kind=kind, actor_uid=cast.expert, actor_roles=EXPERT, **extra,
        )
        assert refused.detail_fields == {"field": field, "constraint": constraint}
        assert _events(session, uid) == 1

    def test_an_unknown_or_malformed_assignment(self, session, cast) -> None:
        refused = _refused(
            ErrorCode.NOT_FOUND, transition_assignment, session,
            assignment_uid="asg_01ARZ3NDEKTSV4RRFFQ69G5FAV", kind="started",
            actor_uid=cast.admin, actor_roles=ADMIN,
        )
        assert refused.detail_fields == {"aggregate_type": "WorkAssignment"}
        refused = _refused(
            ErrorCode.VALIDATION_FAILED, transition_assignment, session,
            assignment_uid="prj_01ARZ3NDEKTSV4RRFFQ69G5FAV", kind="started",
            actor_uid=cast.admin, actor_roles=ADMIN,
        )
        assert refused.detail_fields == {"field": "assignment_uid", "constraint": "pattern"}


class TestTheAdministratorsMoves:
    def test_reassign_moves_the_work_and_the_visibility(self, session, cast) -> None:
        uid = _assign(session, cast).assignment_uid
        _move(session, uid, "started", cast.expert)
        moved = _move(
            session, uid, "reassigned", cast.admin, new_assignee_user_uid=cast.other_expert,
            reason="отпуск",
        )
        assert (moved.status, moved.assignee_user_uid, moved.status_reason) == (
            "assigned", cast.other_expert, "отпуск",
        )
        assert _move(
            session, uid, "reassigned", cast.admin_expert,
            new_assignee_user_uid=cast.other_expert, reason="отпуск",
        ) == moved
        _refused(
            ErrorCode.NOT_FOUND, transition_assignment, session, assignment_uid=uid,
            kind="started", actor_uid=cast.expert, actor_roles=EXPERT,
        )
        assert _move(session, uid, "started", cast.other_expert).status == "in_progress"
        history = get_assignment(
            session, assignment_uid=uid, viewer_uid=cast.other_expert, viewer_roles=EXPERT
        ).history
        assert [(e.kind, e.actor_user_uid, e.new_assignee_user_uid) for e in history] == [
            ("assigned", cast.admin, None),
            ("started", cast.expert, None),
            ("reassigned", cast.admin, cast.other_expert),
            ("started", cast.other_expert, None),
        ]

    def test_reassigning_work_in_hand_to_its_assignee_is_refused(self, session, cast) -> None:
        uid = _assign(session, cast).assignment_uid
        refused = _refused(
            ErrorCode.VALIDATION_FAILED, transition_assignment, session, assignment_uid=uid,
            kind="reassigned", actor_uid=cast.admin, actor_roles=ADMIN,
            new_assignee_user_uid=cast.expert,
        )
        assert refused.detail_fields == {
            "field": "new_assignee_user_uid", "constraint": "differs_from_current_assignee",
        }

    def test_returned_work_may_go_back_to_the_same_expert(self, session, cast) -> None:
        uid = _assign(session, cast).assignment_uid
        _move(session, uid, "returned", cast.expert, reason="уточнить объём")
        again = _move(session, uid, "reassigned", cast.admin, new_assignee_user_uid=cast.expert)
        assert (again.status, again.assignee_user_uid) == ("assigned", cast.expert)
        assert _move(session, uid, "started", cast.expert).status == "in_progress"

    def test_the_new_assignee_must_be_an_active_expert(self, session, cast) -> None:
        uid = _assign(session, cast).assignment_uid
        for assignee in (cast.admin, cast.nobody, "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"):
            refused = _refused(
                ErrorCode.VALIDATION_FAILED, transition_assignment, session, assignment_uid=uid,
                kind="reassigned", actor_uid=cast.admin, actor_roles=ADMIN,
                new_assignee_user_uid=assignee,
            )
            assert refused.detail_fields == {
                "field": "new_assignee_user_uid", "constraint": "active_expert_required",
            }
        refused = _refused(
            ErrorCode.VALIDATION_FAILED, transition_assignment, session, assignment_uid=uid,
            kind="reassigned", actor_uid=cast.admin, actor_roles=ADMIN,
        )
        assert refused.detail_fields == {"field": "new_assignee_user_uid", "constraint": "required"}
        assert _events(session, uid) == 1

    @pytest.mark.parametrize("kind", ["reassigned", "cancelled"])
    def test_the_assignee_does_not_make_the_administrators_moves(self, session, cast, kind) -> None:
        uid = _assign(session, cast).assignment_uid
        extra = {"new_assignee_user_uid": cast.other_expert} if kind == "reassigned" else {}
        refused = _refused(
            ErrorCode.PERMISSION_DENIED, transition_assignment, session, assignment_uid=uid,
            kind=kind, actor_uid=cast.expert, actor_roles=EXPERT, **extra,
        )
        assert refused.detail_fields["required_capability"] == "role:admin"

    def test_cancel_is_terminal_and_repeats_exactly(self, session, cast) -> None:
        uid = _assign(session, cast).assignment_uid
        cancelled = _move(session, uid, "cancelled", cast.admin, reason="проект закрыт")
        assert (cancelled.status, cancelled.status_reason) == ("cancelled", "проект закрыт")
        assert _move(session, uid, "cancelled", cast.admin_expert, reason="проект закрыт") == cancelled
        for kind, actor, extra in (
            ("cancelled", cast.admin, {"reason": "иначе"}),
            ("cancelled", cast.admin, {}),
            ("started", cast.expert, {}),
            ("reassigned", cast.admin, {"new_assignee_user_uid": cast.other_expert}),
        ):
            refused = _refused(
                ErrorCode.STATE_TRANSITION_NOT_ALLOWED, transition_assignment, session,
                assignment_uid=uid, kind=kind, actor_uid=actor,
                actor_roles=_roles(session, actor), **extra,
            )
            assert refused.detail_fields["current_state"] == "cancelled"
        assert _events(session, uid) == 2

    def test_done_work_is_not_reassigned_or_cancelled(self, session, cast) -> None:
        uid = _assign(session, cast).assignment_uid
        _move(session, uid, "started", cast.expert)
        _move(session, uid, "completed", cast.expert)
        for kind, extra in (("cancelled", {}), ("reassigned", {"new_assignee_user_uid": cast.other_expert})):
            refused = _refused(
                ErrorCode.STATE_TRANSITION_NOT_ALLOWED, transition_assignment, session,
                assignment_uid=uid, kind=kind, actor_uid=cast.admin, actor_roles=ADMIN, **extra,
            )
            assert refused.detail_fields["current_state"] == "done"


# -- reads -------------------------------------------------------------------------------


class TestReads:
    def _three(self, session, cast) -> tuple[str, str, str]:
        mine = _assign(session, cast).assignment_uid
        theirs = _assign(
            session, cast, document_uid=cast.document, assignee_user_uid=cast.other_expert
        ).assignment_uid
        elsewhere = _assign(
            session, cast, project_uid=cast.other_project, assignee_user_uid=cast.admin_expert
        ).assignment_uid
        _move(session, mine, "started", cast.expert)
        return mine, theirs, elsewhere

    def test_an_administrator_reads_everything_newest_first(self, session, cast) -> None:
        mine, theirs, elsewhere = self._three(session, cast)
        listed = list_assignments(session, viewer_uid=cast.admin, viewer_roles=ADMIN)
        assert [r.assignment_uid for r in listed] == [elsewhere, theirs, mine]
        assert [r.assignment_uid for r in list_assignments(
            session, viewer_uid=cast.admin, viewer_roles=ADMIN, status="in_progress"
        )] == [mine]
        assert [r.assignment_uid for r in list_assignments(
            session, viewer_uid=cast.admin, viewer_roles=ADMIN, project_uid=cast.project
        )] == [theirs, mine]
        assert list_assignments(
            session, viewer_uid=cast.admin, viewer_roles=ADMIN, mine=True
        ) == ()
        assert [r.assignment_uid for r in list_assignments(
            session, viewer_uid=cast.admin_expert, viewer_roles=BOTH, mine=True
        )] == [elsewhere]

    def test_an_expert_reads_only_their_own_whatever_they_ask(self, session, cast) -> None:
        mine, _, _ = self._three(session, cast)
        for flag in (False, True):
            assert [r.assignment_uid for r in list_assignments(
                session, viewer_uid=cast.expert, viewer_roles=EXPERT, mine=flag
            )] == [mine]
        assert list_assignments(
            session, viewer_uid=cast.expert, viewer_roles=EXPERT, status="assigned"
        ) == ()
        detail = get_assignment(session, assignment_uid=mine, viewer_uid=cast.expert, viewer_roles=EXPERT)
        assert [e.kind for e in detail.history] == ["assigned", "started"]
        assert detail.assignment.status == "in_progress"

    def test_status_filters_cover_every_status(self, session, cast) -> None:
        mine, theirs, elsewhere = self._three(session, cast)
        _move(session, theirs, "returned", cast.other_expert, reason="не мой раздел")
        _move(session, elsewhere, "cancelled", cast.admin)
        by_status = {
            status: [r.assignment_uid for r in list_assignments(
                session, viewer_uid=cast.admin, viewer_roles=ADMIN, status=status
            )]
            for status in ("assigned", "in_progress", "done", "returned", "cancelled")
        }
        assert by_status == {
            "assigned": [], "in_progress": [mine], "done": [], "returned": [theirs],
            "cancelled": [elsewhere],
        }

    def test_refused_reads(self, session, cast) -> None:
        uid = _assign(session, cast).assignment_uid
        refused = _refused(
            ErrorCode.PERMISSION_DENIED, list_assignments, session, viewer_uid=cast.nobody,
            viewer_roles=NONE,
        )
        assert refused.detail_fields["required_capability"] == "role:admin|expert"
        _refused(
            ErrorCode.PERMISSION_DENIED, get_assignment, session, assignment_uid=uid,
            viewer_uid=cast.nobody, viewer_roles=NONE,
        )
        refused = _refused(
            ErrorCode.VALIDATION_FAILED, list_assignments, session, viewer_uid=cast.admin,
            viewer_roles=ADMIN, status="open",
        )
        assert refused.detail_fields == {"field": "status", "constraint": "enum"}
        refused = _refused(
            ErrorCode.VALIDATION_FAILED, list_assignments, session, viewer_uid=cast.admin,
            viewer_roles=ADMIN, project_uid="doc_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        )
        assert refused.detail_fields == {"field": "project_uid", "constraint": "pattern"}
        assert list_assignments(
            session, viewer_uid=cast.admin, viewer_roles=ADMIN,
            project_uid="prj_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        ) == ()


# -- purge -------------------------------------------------------------------------------


class TestPurge:
    @pytest.mark.parametrize("who", ["assignee", "creator", "actor", "new_assignee"])
    def test_an_account_the_dispatcher_names_is_not_purged(self, session, cast, who) -> None:
        seed = str(session.execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one())
        uid = _assign(session, cast, actor=cast.admin_expert).assignment_uid
        subject = {
            "assignee": cast.expert,
            "creator": cast.admin_expert,
            "actor": cast.admin,  # named only by the cancellation event it appends
            "new_assignee": cast.other_expert,
        }[who]
        if who == "actor":
            _move(session, uid, "cancelled", cast.admin)
        if who == "new_assignee":
            _move(session, uid, "reassigned", cast.admin, new_assignee_user_uid=cast.other_expert)
        accounts.archive_account(session, actor_uid=seed, user_uid=subject)
        session.commit()
        refused = _refused(
            ErrorCode.CONFLICT, accounts.purge_account, session, actor_uid=seed, user_uid=subject
        )
        assert refused.detail_fields == {"conflict_reason": "account_referenced"}
        assert accounts.get_account(session, subject) is not None
        assert {ref.split(".")[0] for ref in accounts.references_to(session, subject)} & {
            "work_assignment", "work_assignment_event",
        }

    def test_an_unreferenced_archived_account_still_purges(self, session, cast) -> None:
        seed = str(session.execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one())
        _assign(session, cast)
        accounts.archive_account(session, actor_uid=seed, user_uid=cast.nobody)
        accounts.purge_account(session, actor_uid=seed, user_uid=cast.nobody)
        session.commit()
        assert accounts.get_account(session, cast.nobody) is None
