"""`W49-QA-01`, items 11 and 12 -- what a purge refuses, and what a purge leaves behind.

`R-61` and `W49-PLAN.md` §3.1: an archived account that nothing references may be purged
irreversibly. "References" is the written register: ``app_user.archived_by``,
``app_user_role.granted_by``, ``registration_request.decided_by`` and
``expert_decision_event.author_user_uid`` restrict; ``registration_request.created_user_uid``
is history and is set NULL. A non-archived account answers ``state_transition_not_allowed``
against the ``app_user`` machine; a referenced one ``conflict`` with ``conflict_reason:
account_referenced``; oneself ``permission_denied`` with no detail (§3.2, §3.3).

Each refused case isolates **one** reference -- a reject rather than an approve for "decided
a request", because an approval also grants roles and would add a ``granted_by`` reference --
and asserts that the refused purge deleted nothing. The decision-event case drives the
**shipped** decision adapter, so the author column is written by the product, not by the
test.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from w13_api_driver import TEST_TOKEN

from .qa_kit import (
    PASSWORD,
    account_row,
    approve,
    committed_factory,
    credential_for,
    envelope,
    exchange,
    fresh_login,
    identity_surface,
    make_account,
    reject,
    request_row,
    send,
    status_read,
    submit,
)


def _admin(session: Session, tag: str) -> tuple[str, str]:
    uid = make_account(
        session,
        login=fresh_login(tag),
        names=("Чистова", "Чара", None),
        roles=("expert", "admin"),
    )
    return uid, credential_for(session, uid)


def _archive_directly(session: Session, uid: str, by: str) -> None:
    """Archive in the row, for setup only, when the archiving itself is not under test."""
    session.execute(
        text("UPDATE app_user SET archived_at = now(), archived_by = :by WHERE user_uid = :uid"),
        {"by": by, "uid": uid},
    )


def _purge(surface: Any, credential: str, uid: str) -> Any:
    return send(surface, "DELETE", f"/users/{uid}", credential=credential)


def _assert_referenced(answer: Any) -> None:
    assert answer.status == 409, answer.body
    body = envelope(answer)
    assert body["error_code"] == "conflict", body
    assert body.get("details") == {"conflict_reason": "account_referenced"}, body


# -- item 11: each refusal ---------------------------------------------------------------


def test_purging_an_active_account_is_a_state_transition_refusal(
    session_factory: sessionmaker[Session], session: Session
) -> None:
    surface = identity_surface(session_factory)
    _admin_uid, admin_cred = _admin(session, "purge-active-admin")
    target = make_account(
        session, login=fresh_login("still-active"), names=("Живая", "Жанна", None), roles=("expert",)
    )
    before = account_row(session, target)

    answer = _purge(surface, admin_cred, target)
    assert answer.status == 409, answer.body
    body = envelope(answer)
    assert body["error_code"] == "state_transition_not_allowed", body
    assert body.get("details") == {
        "machine": "app_user",
        "current_state": "active",
        "requested_state": "purged",
    }, body
    session.expire_all()
    assert account_row(session, target) == before


def test_purging_an_account_that_authored_a_decision_event_is_refused(
    session_factory: sessionmaker[Session],
    session: Session,
    shipped_router: Any,
    published_run: Any,
    suite_account: str,
) -> None:
    # The suite's own account is a complete `expert`; the shipped decision adapter records
    # its decision with the verified subject as the author.
    recorded = send(
        shipped_router,
        "POST",
        f"/findings/{published_run.finding_uid}/decisions",
        credential=TEST_TOKEN,
        body={
            "event_type": "accept",
            "finding_observation_id": published_run.finding_observation_id,
        },
        headers={"Idempotency-Key": f"qa49-{uuid.uuid4().hex[:16]}"},
    )
    assert recorded.status == 201, recorded.body
    authored = session.execute(
        text("SELECT count(*) FROM expert_decision_event WHERE author_user_uid = :u"),
        {"u": suite_account},
    ).scalar_one()
    assert authored == 1

    surface = identity_surface(session_factory)
    _admin_uid, admin_cred = _admin(session, "purge-author-admin")
    archived = send(surface, "POST", f"/users/{suite_account}/archive", credential=admin_cred)
    assert archived.status == 200, archived.body

    _assert_referenced(_purge(surface, admin_cred, suite_account))
    session.expire_all()
    assert account_row(session, suite_account) is not None


def test_purging_an_account_that_decided_a_request_is_refused(
    session_factory: sessionmaker[Session], session: Session
) -> None:
    surface = identity_surface(session_factory)
    admin_uid, admin_cred = _admin(session, "purge-decider-admin")
    decider, decider_cred = _admin(session, "purge-decider")
    login = fresh_login("decided")
    assert submit(surface, login).status == 201
    row = request_row(session, login)
    assert row is not None
    assert reject(surface, decider_cred, row["request_id"]).status == 200
    assert request_row(session, login)["decided_by"] == decider  # type: ignore[index]

    assert send(surface, "POST", f"/users/{decider}/archive", credential=admin_cred).status == 200
    _assert_referenced(_purge(surface, admin_cred, decider))
    session.expire_all()
    assert account_row(session, decider) is not None


def test_purging_an_account_that_archived_another_is_refused(
    session_factory: sessionmaker[Session], session: Session
) -> None:
    surface = identity_surface(session_factory)
    _admin_uid, admin_cred = _admin(session, "purge-archiver-admin")
    archiver, archiver_cred = _admin(session, "purge-archiver")
    victim = make_account(
        session, login=fresh_login("archived-by-b"), names=("Убранная", "Ульяна", None), roles=("expert",)
    )
    assert send(surface, "POST", f"/users/{victim}/archive", credential=archiver_cred).status == 200
    assert account_row(session, victim)["archived_by"] == archiver  # type: ignore[index]

    assert send(surface, "POST", f"/users/{archiver}/archive", credential=admin_cred).status == 200
    _assert_referenced(_purge(surface, admin_cred, archiver))
    session.expire_all()
    assert account_row(session, archiver) is not None


def test_purging_an_account_that_granted_a_role_is_refused(
    session_factory: sessionmaker[Session], session: Session
) -> None:
    """The register's fourth RESTRICT entry, ``app_user_role.granted_by`` -- not in the QA
    brief's list, added so that every restricting entry of `R-61` is driven once."""
    surface = identity_surface(session_factory)
    _admin_uid, admin_cred = _admin(session, "purge-granter-admin")
    granter, granter_cred = _admin(session, "purge-granter")
    grantee = make_account(
        session, login=fresh_login("granted"), names=("Повышенная", "Пола", None), roles=("expert",)
    )
    granted = send(
        surface,
        "PATCH",
        f"/users/{grantee}",
        credential=granter_cred,
        body={"roles": ["expert", "admin"]},
    )
    assert granted.status == 200, granted.body
    assert session.execute(
        text("SELECT granted_by FROM app_user_role WHERE user_uid = :u AND role = 'admin'"),
        {"u": grantee},
    ).scalar_one() == granter

    assert send(surface, "POST", f"/users/{granter}/archive", credential=admin_cred).status == 200
    _assert_referenced(_purge(surface, admin_cred, granter))
    session.expire_all()
    assert account_row(session, granter) is not None


@pytest.mark.parametrize("archived", [False, True], ids=["active-self", "archived-row-self"])
def test_purging_oneself_is_permission_denied_with_no_detail(
    session_factory: sessionmaker[Session], session: Session, archived: bool
) -> None:
    surface = identity_surface(session_factory)
    me, my_cred = _admin(session, "purge-self")
    answer = _purge(surface, my_cred, me)
    assert answer.status == 403, answer.body
    body = envelope(answer)
    assert body["error_code"] == "permission_denied", body
    assert not body.get("details"), body
    session.expire_all()
    assert account_row(session, me) is not None
    if archived:
        # An archived account cannot present a credential at all: the seam answers 401
        # before any rule about oneself is asked -- still nothing is deleted.
        other, _ = _admin(session, "purge-self-archiver")
        _archive_directly(session, me, other)
        late = _purge(surface, my_cred, me)
        assert late.status == 401, late.body
        session.expire_all()
        assert account_row(session, me) is not None


# -- item 12: the purge that succeeds ----------------------------------------------------


def test_purging_an_archived_unreferenced_account_frees_its_login_and_keeps_its_request(
    session_factory: sessionmaker[Session], session: Session
) -> None:
    surface = identity_surface(session_factory)
    admin_uid, admin_cred = _admin(session, "purge-ok-admin")
    login = fresh_login("purge-me")
    assert submit(surface, login).status == 201
    first_request = request_row(session, login)
    assert first_request is not None
    approved = approve(surface, admin_cred, first_request["request_id"])
    assert approved.status == 200, approved.body
    account = envelope(approved)["created_user_uid"]
    assert exchange(surface, login, PASSWORD).status == 200

    assert send(surface, "POST", f"/users/{account}/archive", credential=admin_cred).status == 200
    purged = _purge(surface, admin_cred, account)
    assert purged.status == 204, purged.body
    assert purged.body == b""

    session.expire_all()
    assert account_row(session, account) is None
    assert session.execute(
        text("SELECT count(*) FROM app_user_role WHERE user_uid = :u"), {"u": account}
    ).scalar_one() == 0
    survivor = session.execute(
        text(
            "SELECT request_id, status, login, decided_by, created_user_uid "
            "FROM registration_request WHERE request_id = :r"
        ),
        {"r": first_request["request_id"]},
    ).mappings().one()
    assert dict(survivor) == {
        "request_id": first_request["request_id"],
        "status": "approved",
        "login": login,
        "decided_by": admin_uid,
        "created_user_uid": None,
    }
    assert send(surface, "GET", f"/users/{account}", credential=admin_cred).status == 404
    assert exchange(surface, login, PASSWORD).status == 401

    # The login is free: a new application for it is accepted, approved, and signs in.
    assert submit(surface, login).status == 201
    second_request = request_row(session, login)
    assert second_request is not None
    assert second_request["request_id"] != first_request["request_id"]
    assert status_read(surface, login, PASSWORD).status == 200
    reborn = approve(surface, admin_cred, second_request["request_id"])
    assert reborn.status == 200, reborn.body
    assert envelope(reborn)["created_user_uid"] not in (None, account)
    assert exchange(surface, login, PASSWORD).status == 200


def test_the_purge_cascade_is_the_only_writer_of_created_user_uid(
    migrated_engine: Engine,
) -> None:
    """§3.3: the request row's guard "permits exactly that transition once and the later
    ``created_user_uid`` nulling by purge, nothing else" -- recognised by trigger depth, "so a
    manual UPDATE of that column is still refused". Both halves on one fresh database, so the
    guard is the one migrated by this tree (and a mutated copy's migration is the one tested
    there): the manual nulling is refused and changes nothing; the purge's cascade nulls it."""
    factory = committed_factory(migrated_engine)
    with factory() as session:
        admin = make_account(
            session,
            login=fresh_login("guard-admin"),
            names=("Стражева", "Стелла", None),
            roles=("expert", "admin"),
        )
        session.commit()
        admin_cred = credential_for(session, admin)
    surface = identity_surface(factory)
    login = fresh_login("guarded")
    assert submit(surface, login).status == 201
    with factory() as session:
        row = request_row(session, login)
    assert row is not None
    approved = approve(surface, admin_cred, row["request_id"])
    assert approved.status == 200, approved.body
    account = envelope(approved)["created_user_uid"]

    with pytest.raises(DBAPIError):
        with migrated_engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE registration_request SET created_user_uid = NULL "
                    "WHERE request_id = :r"
                ),
                {"r": row["request_id"]},
            )
    with factory() as session:
        assert request_row(session, login)["created_user_uid"] == account  # type: ignore[index]

    assert send(surface, "POST", f"/users/{account}/archive", credential=admin_cred).status == 200
    purged = send(surface, "DELETE", f"/users/{account}", credential=admin_cred)
    assert purged.status == 204, purged.body
    with factory() as session:
        after = request_row(session, login)
    assert after is not None
    assert after["status"] == "approved" and after["created_user_uid"] is None
