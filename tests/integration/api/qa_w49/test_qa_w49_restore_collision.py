"""`W49-QA-01`, item 5 -- restoring an account whose login an active account now holds.

`W49-PLAN.md` §3.1: ``uq_app_user_login`` is partial, ``WHERE archived_at IS NULL``, so an
archived account's login is free; §3.4 ``restoreUser``: "``conflict`` (``login_taken``) if an
active account now holds the login".

The login is taken back the way the product takes it: a registration for it is submitted (a
login held only by an archived account is not ``login_taken``, §3.3) and approved. Then the
archived account's restore must be refused with the closed reason, and must change nothing.
"""

from __future__ import annotations

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from .qa_kit import (
    account_row,
    approve,
    committed_factory,
    credential_for,
    envelope,
    fresh_login,
    identity_surface,
    make_account,
    race,
    request_row,
    send,
    submit,
)


def test_restore_is_refused_with_login_taken_once_the_login_is_held_again(
    session_factory: sessionmaker[Session], session: Session
) -> None:
    surface = identity_surface(session_factory)
    admin = make_account(
        session,
        login=fresh_login("restorer"),
        names=("Восстанова", "Римма", None),
        roles=("expert", "admin"),
    )
    admin_cred = credential_for(session, admin)
    login = fresh_login("collide")
    original = make_account(session, login=login, names=("Прежняя", "Нина", None), roles=("expert",))

    archived = send(surface, "POST", f"/users/{original}/archive", credential=admin_cred)
    assert archived.status == 200, archived.body
    assert envelope(archived)["archived_at"] is not None

    # The login is free for an application now, and the application can be approved.
    applied = submit(surface, login)
    assert applied.status == 201, applied.body
    row = request_row(session, login)
    assert row is not None
    approved = approve(surface, admin_cred, row["request_id"])
    assert approved.status == 200, approved.body
    newcomer = envelope(approved)["created_user_uid"]
    assert newcomer and newcomer != original

    session.expire_all()
    before = account_row(session, original)
    restored = send(surface, "POST", f"/users/{original}/restore", credential=admin_cred)
    assert restored.status == 409, restored.body
    refusal = envelope(restored)
    assert refusal["error_code"] == "conflict", refusal
    assert refusal.get("details") == {"conflict_reason": "login_taken"}, refusal

    session.expire_all()
    assert account_row(session, original) == before, "a refused restore changed the archived row"
    assert account_row(session, newcomer)["archived_at"] is None  # type: ignore[index]
    # And the archived account is still archived as the API reports it.
    read = send(surface, "GET", f"/users/{original}", credential=admin_cred)
    assert read.status == 200 and envelope(read)["archived_at"] is not None, read.body


def test_a_restore_racing_the_approval_that_takes_the_login_leaves_one_holder(
    migrated_engine: Engine,
) -> None:
    """The same collision with no winner yet: a restore and the approval of an application for
    the same login, released together. Exactly one may hold the login afterwards; the other is
    ``login_taken`` -- never a 5xx, never two active holders."""
    factory = committed_factory(migrated_engine)
    with factory() as session:
        restorer = make_account(
            session,
            login=fresh_login("race-restorer"),
            names=("Возвратова", "Вика", None),
            roles=("expert", "admin"),
        )
        approver = make_account(
            session,
            login=fresh_login("race-approver"),
            names=("Одоброва", "Ода", None),
            roles=("expert", "admin"),
        )
        login = fresh_login("race-login")
        original = make_account(
            session, login=login, names=("Ушедшая", "Ума", None), roles=("expert",)
        )
        session.commit()
        restorer_cred = credential_for(session, restorer)
        approver_cred = credential_for(session, approver)
    surface = identity_surface(factory)
    assert send(surface, "POST", f"/users/{original}/archive", credential=restorer_cred).status == 200
    assert submit(surface, login).status == 201
    with factory() as session:
        row = request_row(session, login)
    assert row is not None

    left, right = identity_surface(factory), identity_surface(factory)
    answers, forced = race(
        migrated_engine,
        hold=(
            "SELECT 1 FROM app_user u, registration_request r "
            "WHERE u.user_uid = :uid AND r.request_id = :rid FOR UPDATE"
        ),
        params={"uid": original, "rid": row["request_id"]},
        calls=[
            lambda: send(left, "POST", f"/users/{original}/restore", credential=restorer_cred),
            lambda: approve(right, approver_cred, row["request_id"]),
        ],
    )
    assert forced, "both requests should have passed the seam and waited on their rows"
    report = [(answer.status, answer.body) for answer in answers]
    assert sorted(answer.status for answer in answers) == [200, 409], report
    loser = envelope(next(answer for answer in answers if answer.status == 409))
    assert loser["error_code"] == "conflict", loser
    assert loser.get("details") == {"conflict_reason": "login_taken"}, loser
    with factory() as session:
        holders = session.execute(
            text("SELECT user_uid FROM app_user WHERE login = :l AND archived_at IS NULL"),
            {"l": login},
        ).scalars().all()
        after = request_row(session, login)
    assert len(holders) == 1, (holders, report)
    assert after is not None
    restored, approved = answers
    if restored.status == 200:
        assert holders == [original] and after["status"] == "pending"
    else:
        assert approved.status == 200 and holders == [after["created_user_uid"]]
