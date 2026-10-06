"""`W49-QA-01`, item 6 -- the queue cap at 100 and at 101.

`W49-PLAN.md` §3.3: "more than 100 pending requests answers ``conflict``" -- the closed reason
``queue_full``. So the 100th pending request is accepted and the 101st is refused; a decided
request does not count; and two applications racing for the last place cannot both get it.

A fresh database, so "pending" counts exactly the rows this test made. 98 rows are written
directly with one digest (the queue's own content is not under test, and 98 derivations would
only cost time); the 99th, 100th and 101st go through the served ``submitRegistration``.
"""

from __future__ import annotations

from sqlalchemy import Engine, text

from auditmanager.access.passwords import hash_password
from auditmanager.shared.identity.ids import RegistrationRequestId

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


def _fill(engine: Engine, count: int) -> None:
    stored = hash_password("qa49-direct-row-passphrase")
    with engine.begin() as connection:
        for index in range(count):
            connection.execute(
                text(
                    "INSERT INTO registration_request (request_id, login, last_name, first_name, "
                    "password_algorithm, password_iterations, password_salt, password_hash) "
                    "VALUES (:rid, :login, 'Очередная', 'Ева', :alg, :it, :salt, :digest)"
                ),
                {
                    "rid": str(RegistrationRequestId.new()),
                    "login": f"qa49-queue-{index:03d}@qa.invalid",
                    "alg": stored.algorithm,
                    "it": stored.iterations,
                    "salt": stored.salt,
                    "digest": stored.digest,
                },
            )


def _pending(engine: Engine) -> int:
    with engine.connect() as connection:
        return int(
            connection.execute(
                text("SELECT count(*) FROM registration_request WHERE status = 'pending'")
            ).scalar_one()
        )


def test_the_hundredth_is_accepted_the_hundred_and_first_is_queue_full(
    migrated_engine: Engine,
) -> None:
    factory = committed_factory(migrated_engine)
    surface = identity_surface(factory)
    _fill(migrated_engine, 98)
    assert _pending(migrated_engine) == 98

    assert submit(surface, fresh_login("q99")).status == 201
    hundredth = fresh_login("q100")
    answer = submit(surface, hundredth)
    assert answer.status == 201, answer.body
    assert _pending(migrated_engine) == 100

    refused = submit(surface, fresh_login("q101"), correlation="qa49-queue-full")
    assert refused.status == 409, refused.body
    body = envelope(refused)
    assert body["error_code"] == "conflict", body
    assert body.get("details") == {"conflict_reason": "queue_full"}, body
    assert _pending(migrated_engine) == 100

    # A decision frees a place: the cap counts pending requests only.
    with factory() as session:
        admin = make_account(
            session,
            login=fresh_login("queue-admin"),
            names=("Очередёва", "Ада", None),
            roles=("expert", "admin"),
        )
        session.commit()
        admin_cred = credential_for(session, admin)
        row = request_row(session, hundredth)
    assert row is not None
    assert reject(surface, admin_cred, row["request_id"]).status == 200
    assert submit(surface, fresh_login("q100-again")).status == 201
    assert _pending(migrated_engine) == 100
    assert submit(surface, fresh_login("q101-again")).status == 409
    # And an approval frees one too.
    with factory() as session:
        first = request_row(session, "qa49-queue-000@qa.invalid")
    assert first is not None
    assert approve(surface, admin_cred, first["request_id"]).status == 200
    assert submit(surface, fresh_login("q100-third")).status == 201
    assert _pending(migrated_engine) == 100


def test_two_applications_racing_for_the_last_place_get_one(migrated_engine: Engine) -> None:
    factory = committed_factory(migrated_engine)
    _fill(migrated_engine, 99)
    left, right = identity_surface(factory), identity_surface(factory)
    first, second = fresh_login("last-a"), fresh_login("last-b")

    # The hold is the advisory key the submission serialises on (read from
    # `access/registrations.py`, `_QUEUE_LOCK_KEY`), so with the shipped code both
    # submissions wait on it and are released together. Without that lock nothing holds
    # them and they simply run at once -- which is the race in its natural form. Either way
    # what is asserted is the outcome, never the interleaving.
    answers, _forced = race(
        migrated_engine,
        hold="SELECT pg_advisory_xact_lock(1380272977)",  # 0x52454751, the queue's own key
        params={},
        calls=[lambda: submit(left, first), lambda: submit(right, second)],
    )
    report = [(answer.status, answer.body) for answer in answers]
    assert sorted(answer.status for answer in answers) == [201, 409], report
    assert envelope(next(a for a in answers if a.status == 409)).get("details") == {
        "conflict_reason": "queue_full"
    }, report
    assert _pending(migrated_engine) == 100
