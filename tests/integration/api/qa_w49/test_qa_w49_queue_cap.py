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
from auditmanager.access.queue_lock import QUEUE_LOCK_KEY
from auditmanager.access.registrations import MAX_REQUESTS_PER_DAY
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


def _fill(engine: Engine, count: int, *, age: str = "3 days") -> None:
    """``count`` pending rows written directly, ``age`` old.

    Three days old by default: the day cap of `R-146ay` counts requests accepted in the last
    24 hours, and the tests that fill the queue to 100 are about the pending cap alone."""
    stored = hash_password("qa49-direct-row-passphrase")
    with engine.begin() as connection:
        for index in range(count):
            connection.execute(
                text(
                    "INSERT INTO registration_request (request_id, login, last_name, first_name, "
                    "password_algorithm, password_iterations, password_salt, password_hash, "
                    "submitted_at) "
                    "VALUES (:rid, :login, 'Очередная', 'Ева', :alg, :it, :salt, :digest, "
                    "now() - CAST(:age AS interval))"
                ),
                {
                    "rid": str(RegistrationRequestId.new()),
                    "login": f"qa49-queue-{index:03d}@qa.invalid",
                    "alg": stored.algorithm,
                    "it": stored.iterations,
                    "salt": stored.salt,
                    "digest": stored.digest,
                    "age": age,
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
        # The queue's own key, imported: this line used to spell it as the decimal 1380272977,
        # which is 0x52454B51 and not 0x52454751 (1380271953), so the hold took a lock nothing
        # waits on and the race was never forced (`D-147`).
        hold="SELECT pg_advisory_xact_lock(:key)",
        params={"key": QUEUE_LOCK_KEY},
        calls=[lambda: submit(left, first), lambda: submit(right, second)],
    )
    report = [(answer.status, answer.body) for answer in answers]
    assert sorted(answer.status for answer in answers) == [201, 409], report
    assert envelope(next(a for a in answers if a.status == 409)).get("details") == {
        "conflict_reason": "queue_full"
    }, report
    assert _pending(migrated_engine) == 100


def test_the_forty_first_application_of_a_day_is_queue_full_over_http(
    migrated_engine: Engine,
) -> None:
    """`R-146ay`: the day cap, through the served ``submitRegistration``. The answer is the
    queue's own: ``409``, ``conflict``, ``queue_full`` -- no new code, no new field."""
    factory = committed_factory(migrated_engine)
    surface = identity_surface(factory)
    _fill(migrated_engine, MAX_REQUESTS_PER_DAY - 1, age="1 hour")

    assert submit(surface, fresh_login("day40")).status == 201
    refused = submit(surface, fresh_login("day41"), correlation="qa49-day-cap")
    assert refused.status == 409, refused.body
    body = envelope(refused)
    assert body["error_code"] == "conflict", body
    assert body.get("details") == {"conflict_reason": "queue_full"}, body
    # The queue is nowhere near its own cap: it is the day that is spent.
    assert _pending(migrated_engine) == MAX_REQUESTS_PER_DAY < 100


def test_two_applications_racing_for_the_last_place_of_the_day_get_one(
    migrated_engine: Engine,
) -> None:
    """The day count is read under the queue lock, so two submissions cannot both take the
    fortieth place (the same forced interleaving as the pending cap's race above)."""
    factory = committed_factory(migrated_engine)
    _fill(migrated_engine, MAX_REQUESTS_PER_DAY - 1, age="1 hour")
    left, right = identity_surface(factory), identity_surface(factory)
    first, second = fresh_login("day-last-a"), fresh_login("day-last-b")

    answers, _forced = race(
        migrated_engine,
        hold="SELECT pg_advisory_xact_lock(:key)",
        params={"key": QUEUE_LOCK_KEY},
        calls=[lambda: submit(left, first), lambda: submit(right, second)],
    )
    report = [(answer.status, answer.body) for answer in answers]
    assert sorted(answer.status for answer in answers) == [201, 409], report
    assert envelope(next(a for a in answers if a.status == 409)).get("details") == {
        "conflict_reason": "queue_full"
    }, report
    assert _pending(migrated_engine) == MAX_REQUESTS_PER_DAY
