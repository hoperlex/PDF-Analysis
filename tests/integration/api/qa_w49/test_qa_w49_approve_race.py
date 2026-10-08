"""`W49-QA-01`, item 1 -- the approve race (`W49-PLAN.md` §3.3).

"Approval creates the account in the same transaction under ``FOR UPDATE`` ... Two
concurrent approvals: one wins, the other answers ``state_transition_not_allowed``."

Driven through the served ``approveRegistration`` on a fresh database, two administrators,
two idempotency keys, both requests released from the same instant after each has passed the
seam (see ``qa_kit.race``). Two variants: one administrator pressing twice with the same key
(an idempotent replay, which must not create a second account either), and an approval racing
a rejection (the request is decided once, and the loser is told which decision won).
"""

from __future__ import annotations

from sqlalchemy import Engine, text

from .qa_kit import (
    approve,
    committed_factory,
    credential_for,
    envelope,
    fresh_login,
    identity_surface,
    make_account,
    race,
    reject,
    request_row,
    submit,
)

_HOLD_REQUEST = "SELECT 1 FROM registration_request WHERE request_id = :rid FOR UPDATE"


def _two_admins_and_a_request(engine: Engine) -> tuple[str, str, str, str, str, str]:
    factory = committed_factory(engine)
    with factory() as session:
        first = make_account(
            session,
            login=fresh_login("race-admin-a"),
            names=("Первова", "Анна", None),
            roles=("expert", "admin"),
        )
        second = make_account(
            session,
            login=fresh_login("race-admin-b"),
            names=("Вторых", "Борис", None),
            roles=("expert", "admin"),
        )
        session.commit()
        credentials = (credential_for(session, first), credential_for(session, second))
    login = fresh_login("race-applicant")
    answer = submit(identity_surface(factory), login)
    assert answer.status == 201, answer.body
    with factory() as session:
        row = request_row(session, login)
    assert row is not None and row["status"] == "pending"
    return first, second, credentials[0], credentials[1], login, row["request_id"]


def test_two_administrators_approving_at_once_create_one_account(
    migrated_engine: Engine,
) -> None:
    first, second, first_cred, second_cred, login, rid = _two_admins_and_a_request(
        migrated_engine
    )
    factory = committed_factory(migrated_engine)
    left, right = identity_surface(factory), identity_surface(factory)

    answers, forced = race(
        migrated_engine,
        hold=_HOLD_REQUEST,
        params={"rid": rid},
        calls=[
            lambda: approve(left, first_cred, rid, roles=("expert",)),
            lambda: approve(right, second_cred, rid, roles=("expert", "admin")),
        ],
    )
    assert forced, "both approvals should have passed the seam and waited on the request's lock"

    statuses = sorted(answer.status for answer in answers)
    assert statuses == [200, 409], [(a.status, a.body) for a in answers]
    winner = next(a for a in answers if a.status == 200)
    loser = next(a for a in answers if a.status == 409)
    refusal = envelope(loser)
    assert refusal["error_code"] == "state_transition_not_allowed", refusal
    assert refusal.get("details") == {
        "machine": "registration_request",
        "current_state": "approved",
        "requested_state": "approved",
    }, refusal

    decided = envelope(winner)
    with factory() as session:
        accounts = session.execute(
            text("SELECT user_uid FROM app_user WHERE login = :login"), {"login": login}
        ).scalars().all()
        row = request_row(session, login)
    assert len(accounts) == 1, accounts
    assert row is not None
    assert row["status"] == "approved"
    assert row["created_user_uid"] == accounts[0] == decided["created_user_uid"]
    assert row["decided_by"] in {first, second}
    assert row["password_nulled"] is True


def test_one_administrator_pressing_twice_with_one_key_creates_one_account(
    migrated_engine: Engine,
) -> None:
    first, _second, first_cred, _second_cred, login, rid = _two_admins_and_a_request(
        migrated_engine
    )
    factory = committed_factory(migrated_engine)
    left, right = identity_surface(factory), identity_surface(factory)
    key = "qa49-same-key-pressed-twice"

    answers, _forced = race(
        migrated_engine,
        hold=_HOLD_REQUEST,
        params={"rid": rid},
        calls=[
            lambda: approve(left, first_cred, rid, key=key),
            lambda: approve(right, first_cred, rid, key=key),
        ],
    )
    # An identical repeat is a replay of the recorded outcome (`W49-PLAN.md` §3.4: the
    # approval takes an idempotency key "as other mutations"): both answers are the same 200,
    # never a second account and never a server fault.
    assert [answer.status for answer in answers] == [200, 200], [
        (a.status, a.body) for a in answers
    ]
    assert answers[0].body == answers[1].body
    with factory() as session:
        accounts = session.execute(
            text("SELECT user_uid FROM app_user WHERE login = :login"), {"login": login}
        ).scalars().all()
        row = request_row(session, login)
    assert len(accounts) == 1, accounts
    assert row is not None and row["status"] == "approved" and row["decided_by"] == first


def test_an_approval_and_a_rejection_at_once_decide_the_request_once(
    migrated_engine: Engine,
) -> None:
    first, second, first_cred, second_cred, login, rid = _two_admins_and_a_request(
        migrated_engine
    )
    factory = committed_factory(migrated_engine)
    left, right = identity_surface(factory), identity_surface(factory)

    answers, forced = race(
        migrated_engine,
        hold=_HOLD_REQUEST,
        params={"rid": rid},
        calls=[
            lambda: approve(left, first_cred, rid),
            lambda: reject(right, second_cred, rid, reason="Одновременно."),
        ],
    )
    assert forced, "both decisions should have passed the seam and waited on the request's lock"
    approved, rejected = answers
    assert sorted([approved.status, rejected.status]) == [200, 409], [
        (a.status, a.body) for a in answers
    ]
    with factory() as session:
        row = request_row(session, login)
        accounts = session.execute(
            text("SELECT user_uid FROM app_user WHERE login = :login"), {"login": login}
        ).scalars().all()
    assert row is not None
    if approved.status == 200:
        assert envelope(rejected)["error_code"] == "state_transition_not_allowed"
        assert envelope(rejected).get("details") == {
            "machine": "registration_request",
            "current_state": "approved",
            "requested_state": "rejected",
        }
        assert row["status"] == "approved" and row["decided_by"] == first
        assert len(accounts) == 1 and row["created_user_uid"] == accounts[0]
    else:
        assert envelope(approved)["error_code"] == "state_transition_not_allowed"
        assert envelope(approved).get("details") == {
            "machine": "registration_request",
            "current_state": "rejected",
            "requested_state": "approved",
        }
        assert row["status"] == "rejected" and row["decided_by"] == second
        assert accounts == [] and row["created_user_uid"] is None
