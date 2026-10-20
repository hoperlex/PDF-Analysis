"""`W61-DISPATCHER-01` -- the four «Диспетчер» operations, end to end over real rows.

``createAssignment``, ``listAssignments``, ``getAssignment`` and ``transitionAssignment``
through the shipped ``DispatchAdapter`` and the shipped credential port, inside the suite's
rolled-back transaction (the assignment tables refuse DELETE, so rollback is the only
cleanup). The rules themselves are ``auditmanager.dispatch``'s and are proven there without a
router (``tests/integration/dispatch``); what is asserted here is what the served operations
answer -- the seam's role register, the status codes, the closed detail values, the labels
the adapter resolves and the page shape.
"""

from __future__ import annotations

import json
import secrets
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.access.public import AccountRepository, UserRepository
from auditmanager.api.routers import build_router
from auditmanager.bootstrap.adapters import CredentialAdapter, DispatchAdapter
from auditmanager.documents.public import DocumentRepository
from w13_api_driver import Surface

from .identity_surface import SIGNER, credential_for, make_account


@pytest.fixture
def surface(session_factory: sessionmaker[Session]) -> Surface:
    return Surface(
        build_router(
            projects=None,  # type: ignore[arg-type]
            documents=None,  # type: ignore[arg-type]
            runs=None,  # type: ignore[arg-type]
            findings=None,  # type: ignore[arg-type]
            decisions=None,  # type: ignore[arg-type]
            exports=None,  # type: ignore[arg-type]
            credentials=CredentialAdapter(
                session_factory, users=UserRepository(), accounts=AccountRepository(), signer=SIGNER
            ),
            dispatch=DispatchAdapter(session_factory),
        )
    )


def _person(session: Session, tag: str, names: tuple[str, str], roles: tuple[str, ...]) -> str:
    return make_account(
        session,
        login=f"w61-{tag}-{secrets.token_hex(4)}@suite.invalid",
        names=(names[0], names[1], None),
        roles=roles,
    )


@pytest.fixture
def world(session: Session) -> Any:
    documents = DocumentRepository()
    project = documents.create_project(session, "Школа на 550 мест")
    other = documents.create_project(session, "Детский сад")
    built = {
        "admin": _person(session, "admin", ("Админова", "Ольга"), ("admin",)),
        "expert": _person(session, "expert", ("Экспертов", "Иван"), ("expert",)),
        "other_expert": _person(session, "other", ("Петрова", "Анна"), ("expert",)),
        "nobody": _person(session, "nobody", ("Безролев", "Глеб"), ()),
        "project": str(project.project_uid),
        "document": str(documents.create_document(session, project.project_uid, "КЖ-1")),
        "foreign_document": str(documents.create_document(session, other.project_uid, "АР-1")),
    }
    session.commit()
    return type("World", (), built)


def _send(surface: Surface, method: str, path: str, credential: str, body: Any = None) -> Any:
    payload = b"" if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"} if body is not None else {}
    return surface.send(method, path, headers=headers, body=payload, credential=credential)


def _json(answer: Any) -> Any:
    return json.loads(answer.body)


def _create(surface: Surface, session: Session, world: Any, **body: Any) -> Any:
    payload = {"project_uid": world.project, "assignee_user_uid": world.expert, **body}
    return _send(surface, "POST", "/assignments", credential_for(session, world.admin), payload)


def _move(surface: Surface, session: Session, uid: str, actor: str, **body: Any) -> Any:
    return _send(
        surface, "POST", f"/assignments/{uid}/transitions", credential_for(session, actor), body
    )


class TestCreate:
    def test_an_administrator_creates_and_the_answer_names_everyone(
        self, surface, session, world
    ) -> None:
        answer = _create(surface, session, world, document_uid=world.document, note="  до пятницы ")
        assert answer.status == 200, answer.body
        body = _json(answer)
        assert body["assignment_uid"].startswith("asg_")
        assert (body["project_name"], body["document_uid"], body["document_title"]) == (
            "Школа на 550 мест", world.document, "КЖ-1",
        )
        assert (body["assignee_user_uid"], body["assignee_label"]) == (world.expert, "Экспертов И.")
        assert (body["created_by_user_uid"], body["created_by_label"]) == (world.admin, "Админова О.")
        assert (body["status"], body["status_reason"], body["note"]) == ("assigned", None, "до пятницы")
        repeat = _create(surface, session, world, document_uid=world.document, note="до пятницы")
        assert repeat.status == 200 and _json(repeat)["assignment_uid"] == body["assignment_uid"]

    def test_the_seam_admits_only_admin_and_the_command_checks_again(
        self, surface, session, world
    ) -> None:
        for who in (world.expert, world.nobody):
            refused = _send(
                surface, "POST", "/assignments", credential_for(session, who),
                {"project_uid": world.project, "assignee_user_uid": world.expert},
            )
            assert refused.status == 403, refused.body
            assert _json(refused)["details"]["required_capability"] == "role:admin"

    @pytest.mark.parametrize(
        ("body", "status", "details"),
        [
            ({"assignee_user_uid": "admin"}, 422,
             {"field": "assignee_user_uid", "constraint": "active_expert_required"}),
            ({"document_uid": "foreign"}, 404, {"aggregate_type": "Document"}),
            ({"note": ""}, 422, None),
            ({"unexpected": 1}, 422, None),
        ],
    )
    def test_refusals(self, surface, session, world, body, status, details) -> None:
        resolved = {
            key: {"admin": world.admin, "foreign": world.foreign_document}.get(value, value)
            for key, value in body.items()
        }
        answer = _create(surface, session, world, **resolved)
        assert answer.status == status, answer.body
        if details is not None:
            assert _json(answer)["details"] == details

    def test_a_second_assignment_on_an_open_scope_is_409(self, surface, session, world) -> None:
        assert _create(surface, session, world).status == 200
        refused = _create(surface, session, world, assignee_user_uid=world.other_expert)
        assert refused.status == 409, refused.body
        assert _json(refused)["error_code"] == "conflict"
        assert _json(refused)["details"] == {
            "aggregate_type": "WorkAssignment", "conflict_reason": "assignment_open",
        }


class TestMoves:
    def test_the_expert_starts_and_completes_and_history_tells_it(
        self, surface, session, world
    ) -> None:
        uid = _json(_create(surface, session, world))["assignment_uid"]
        started = _move(surface, session, uid, world.expert, kind="started")
        assert started.status == 200 and _json(started)["status"] == "in_progress"
        repeat = _move(surface, session, uid, world.expert, kind="started")
        assert repeat.status == 200 and _json(repeat) == _json(started)
        done = _move(surface, session, uid, world.expert, kind="completed")
        assert _json(done)["status"] == "done"
        detail = _send(surface, "GET", f"/assignments/{uid}", credential_for(session, world.expert))
        assert detail.status == 200, detail.body
        history = _json(detail)["history"]
        assert [(e["kind"], e["actor_label"]) for e in history] == [
            ("assigned", "Админова О."), ("started", "Экспертов И."), ("completed", "Экспертов И."),
        ]
        assert all(e["event_id"].startswith("evt_") for e in history)
        refused = _move(surface, session, uid, world.expert, kind="started")
        assert refused.status == 409, refused.body
        assert _json(refused)["error_code"] == "state_transition_not_allowed"
        assert _json(refused)["details"] == {
            "machine": "work_assignment", "current_state": "done", "requested_state": "in_progress",
        }

    def test_who_may_move(self, surface, session, world) -> None:
        uid = _json(_create(surface, session, world))["assignment_uid"]
        hidden = _move(surface, session, uid, world.other_expert, kind="started")
        assert hidden.status == 404, hidden.body
        not_assignee = _move(surface, session, uid, world.admin, kind="started")
        assert not_assignee.status == 403, not_assignee.body
        assert _json(not_assignee)["details"]["required_capability"] == "assignment:assignee"
        not_admin = _move(surface, session, uid, world.expert, kind="cancelled")
        assert not_admin.status == 403
        assert _json(not_admin)["details"]["required_capability"] == "role:admin"
        role_less = _move(surface, session, uid, world.nobody, kind="started")
        assert role_less.status == 403  # the seam's R-80 refusal, before the port

    def test_reassign_and_return(self, surface, session, world) -> None:
        uid = _json(_create(surface, session, world))["assignment_uid"]
        needs_reason = _move(surface, session, uid, world.expert, kind="returned")
        assert needs_reason.status == 422
        assert _json(needs_reason)["details"] == {"field": "reason", "constraint": "required"}
        returned = _move(surface, session, uid, world.expert, kind="returned", reason="не мой раздел")
        assert (_json(returned)["status"], _json(returned)["status_reason"]) == ("returned", "не мой раздел")
        moved = _move(
            surface, session, uid, world.admin, kind="reassigned",
            new_assignee_user_uid=world.other_expert,
        )
        assert moved.status == 200, moved.body
        assert (_json(moved)["assignee_user_uid"], _json(moved)["assignee_label"]) == (
            world.other_expert, "Петрова А.",
        )
        detail = _json(_send(surface, "GET", f"/assignments/{uid}", credential_for(session, world.admin)))
        last = detail["history"][-1]
        assert (last["kind"], last["new_assignee_user_uid"], last["new_assignee_label"]) == (
            "reassigned", world.other_expert, "Петрова А.",
        )
        gone = _send(surface, "GET", f"/assignments/{uid}", credential_for(session, world.expert))
        assert gone.status == 404


class TestList:
    def test_visibility_filters_and_paging(self, surface, session, world) -> None:
        mine = _json(_create(surface, session, world))["assignment_uid"]
        theirs = _json(_create(
            surface, session, world, document_uid=world.document,
            assignee_user_uid=world.other_expert,
        ))["assignment_uid"]
        _move(surface, session, mine, world.expert, kind="started")
        admin = credential_for(session, world.admin)
        everything = _json(_send(surface, "GET", "/assignments", admin))
        assert [a["assignment_uid"] for a in everything["items"]] == [theirs, mine]
        assert everything["page"]["next_cursor"] is None
        first = _json(_send(surface, "GET", "/assignments?limit=1", admin))
        assert [a["assignment_uid"] for a in first["items"]] == [theirs]
        second = _json(_send(
            surface, "GET", f"/assignments?limit=1&cursor={first['page']['next_cursor']}", admin
        ))
        assert [a["assignment_uid"] for a in second["items"]] == [mine]
        progress = _json(_send(surface, "GET", "/assignments?status=in_progress", admin))
        assert [a["assignment_uid"] for a in progress["items"]] == [mine]
        expert = credential_for(session, world.expert)
        for query in ("", "?mine=true", "?mine=false"):
            own = _json(_send(surface, "GET", f"/assignments{query}", expert))
            assert [a["assignment_uid"] for a in own["items"]] == [mine], query
        assert _json(_send(surface, "GET", "/assignments?mine=true", admin))["items"] == []
        bad = _send(surface, "GET", "/assignments?status=open", admin)
        assert bad.status == 422, bad.body
        refused = _send(surface, "GET", "/assignments", credential_for(session, world.nobody))
        assert refused.status == 403
