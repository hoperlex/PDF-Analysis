"""`JUDGE-FIXES-F1-01` (finding 5): ``access.sign_in_blocked`` under overlapping failed attempts.

Real PostgreSQL, a private migrated clone per test (the ``access`` suite's fixtures), two
connections. ADR-0023 section 4 journals a failed sign-in **only when it starts a cooling-off
period**. The repository used to say that this happens exactly once per period "however hard
anybody knocks". It does not under concurrency: two attempts that are both in flight when the
account is still open both pass the blocked check, and the second ``UPDATE`` -- after waiting for
the first one's row lock -- re-evaluates ``failed + 1 >= allowance`` on the row the first one
wrote, extends the block and returns a non-NULL ``sign_in_blocked_until`` exactly as the first one
did. Each such attempt wrote an event.

The interleaving is built **here**, from the outside, with no hook in product code: the first
attempt runs to its ``UPDATE`` and is left uncommitted (it holds the account's row lock and its
block is invisible to every other connection); the second attempt is started in a thread, passes
the blocked check on the committed row, and is observed in ``pg_stat_activity`` waiting on a lock;
only then is the first attempt committed (or rolled back) and the second released.

What is guaranteed, and so what is asserted:

* **at most one** ``access.sign_in_blocked`` event per cooling-off period, however the attempts
  overlap -- the one that found the account open (``sign_in_blocked_until`` NULL or already spent)
  and shut it;
* the event is in the transaction of the change: when the winning transaction rolls back its event
  goes with it, and the attempt that then finds the account open is the one that journals;
* it is **not** a promise that the second attempt leaves the row alone: it was in flight, it was
  counted, and it may extend the block by the length of the overlap (the same figure as before
  this lane; the event table is the thing that does not grow).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from auditmanager.access import repository
from auditmanager.access.repository import FAILED_SIGN_IN_ALLOWANCE, UserRepository

PASSWORD = "a-long-enough-password-7731"  # noqa: S105 - a test literal
WRONG = "wrong-password-0000"  # noqa: S105 - a test literal
NEW_PASSWORD = "another-long-password-3"  # noqa: S105 - a test literal
LOGIN = "anna@example.com"
WAIT_SECONDS = 30.0

users = UserRepository()


# --- helpers -------------------------------------------------------------------------------------


def _blocked_events(engine: Engine) -> list[dict[str, Any]]:
    """The committed ``access.sign_in_blocked`` rows, read over a connection of their own."""
    with engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT aggregate_id, payload FROM audit_event "
            "WHERE event_type = 'access.sign_in_blocked' ORDER BY sequence_no")).mappings().all()
    return [dict(row) for row in rows]


def _row(engine: Engine) -> dict[str, Any]:
    with engine.connect() as connection:
        found = connection.execute(text(
            "SELECT user_uid, failed_sign_ins, sign_in_blocked_until "
            "FROM app_user WHERE login = :login"), {"login": LOGIN}).mappings().one()
    return dict(found)


def _account_one_failure_from_the_block(engine: Engine, allowance: int | None = None) -> str:
    """Create the account and bring it to ``allowance - 1`` committed failures; return its uid."""
    wanted = FAILED_SIGN_IN_ALLOWANCE if allowance is None else allowance
    with Session(engine) as session:
        uid = str(users.create_user(session, LOGIN, PASSWORD).user_uid)
        session.commit()
        for _ in range(wanted - 1):
            assert users.authenticate(session, LOGIN, WRONG) is None
            session.commit()
    assert _blocked_events(engine) == [] and _row(engine)["sign_in_blocked_until"] is None
    return uid


def _wait_until_waiting_on_a_lock(engine: Engine, pid: int) -> None:
    """The barrier: the backend ``pid`` is blocked on a lock another transaction holds."""
    deadline = time.monotonic() + WAIT_SECONDS
    with engine.connect() as connection:
        while time.monotonic() < deadline:
            state = connection.execute(text(
                "SELECT wait_event_type FROM pg_stat_activity WHERE pid = :pid"),
                {"pid": pid}).scalar()
            if state == "Lock":
                return
            time.sleep(0.02)
    pytest.fail(f"the second attempt (backend {pid}) never waited on the first one's row lock")


def _overlap(
    engine: Engine,
    second_attempt: Callable[[Session, str], object],
    *,
    first_commits: bool,
) -> tuple[object, str]:
    """Two failed attempts on the account at ``allowance - 1`` failures, interleaved.

    The first attempt is the one that spends the allowance; it runs to the end of its work and is
    left open. The second is started in a thread, is let past the blocked check by the first one's
    uncommitted state, and is held at its ``UPDATE`` by the first one's row lock. Then the first is
    committed or rolled back and the second is released. Returns what the second attempt returned
    and the account's uid."""
    uid = _account_one_failure_from_the_block(engine)
    first = Session(engine)
    outcome: dict[str, Any] = {}
    announced: list[int] = []
    announce = threading.Event()

    def second() -> None:
        with Session(engine) as session:
            try:
                announced.append(session.execute(text("SELECT pg_backend_pid()")).scalar_one())
                announce.set()
                outcome["value"] = second_attempt(session, uid)
                session.commit()
            except BaseException as error:  # noqa: BLE001 - re-raised in the test thread
                outcome["error"] = error
                session.rollback()
                announce.set()

    thread = threading.Thread(target=second, daemon=True)
    try:
        assert users.authenticate(first, LOGIN, WRONG) is None  # spends the allowance, uncommitted
        assert _blocked_events(engine) == []  # ... and nothing of it is visible yet
        thread.start()
        assert announce.wait(WAIT_SECONDS), "the second attempt never started"
        assert "error" not in outcome, outcome.get("error")
        _wait_until_waiting_on_a_lock(engine, announced[0])
        (first.commit if first_commits else first.rollback)()
        thread.join(WAIT_SECONDS)
        assert not thread.is_alive(), "the second attempt never finished"
    finally:
        first.close()
    if "error" in outcome:
        raise outcome["error"]
    return outcome["value"], uid


def _second_sign_in(session: Session, uid: str) -> object:
    return users.authenticate(session, LOGIN, WRONG)


def _second_password_proof(session: Session, uid: str) -> object:
    return users.change_password(
        session, user_uid=uid, current_password=WRONG, new_password=NEW_PASSWORD)


SECOND_ATTEMPTS = pytest.mark.parametrize(
    "second_attempt",
    [_second_sign_in, _second_password_proof],
    ids=["a second failed sign-in", "a second failed password proof"],
)


# --- the tests -----------------------------------------------------------------------------------


class TestOverlappingFailedAttempts:
    @SECOND_ATTEMPTS
    def test_two_attempts_in_flight_together_journal_one_event(
        self, migrated_engine: Engine, second_attempt: Callable[[Session, str], object]
    ) -> None:
        result, uid = _overlap(migrated_engine, second_attempt, first_commits=True)
        assert result is None  # the second attempt failed too: it was counted, not forgiven
        events = _blocked_events(migrated_engine)
        assert len(events) == 1, events  # was 2: the second UPDATE returned a non-NULL block as well
        (event,) = events
        assert event["aggregate_id"] == uid
        assert event["payload"] == {
            "subject_uid": uid, "source": "api", "failures": FAILED_SIGN_IN_ALLOWANCE}
        row = _row(migrated_engine)
        assert row["sign_in_blocked_until"] is not None
        assert row["failed_sign_ins"] >= FAILED_SIGN_IN_ALLOWANCE

    @SECOND_ATTEMPTS
    def test_when_the_attempt_that_shut_the_account_rolls_back_the_next_one_journals(
        self, migrated_engine: Engine, second_attempt: Callable[[Session, str], object]
    ) -> None:
        # The event rides the transaction of the change. If the first attempt's transaction is
        # rolled back, its block and its event never existed; the second attempt then finds the
        # account open at the allowance, shuts it, and is the one period's single event.
        result, uid = _overlap(migrated_engine, second_attempt, first_commits=False)
        assert result is None
        events = _blocked_events(migrated_engine)
        assert len(events) == 1, events
        assert events[0]["payload"] == {
            "subject_uid": uid, "source": "api", "failures": FAILED_SIGN_IN_ALLOWANCE}
        row = _row(migrated_engine)
        assert row["sign_in_blocked_until"] is not None
        assert row["failed_sign_ins"] == FAILED_SIGN_IN_ALLOWANCE  # the first attempt left no trace

    def test_a_new_period_after_the_last_one_ended_journals_again(
        self, migrated_engine: Engine
    ) -> None:
        # The other half of "once per period": the bound is per period, not per account. The block
        # is served (its end moved into the past); the next run of failures shuts the account
        # again and that is a second event.
        _account_one_failure_from_the_block(migrated_engine)
        with Session(migrated_engine) as session:
            assert users.authenticate(session, LOGIN, WRONG) is None
            session.commit()
        assert len(_blocked_events(migrated_engine)) == 1
        with migrated_engine.begin() as connection:
            connection.execute(text(
                "UPDATE app_user SET sign_in_blocked_until = now() - interval '1 second' "
                "WHERE login = :login"), {"login": LOGIN})
        with Session(migrated_engine) as session:
            for _ in range(FAILED_SIGN_IN_ALLOWANCE):
                assert users.authenticate(session, LOGIN, WRONG) is None
                session.commit()
        assert len(_blocked_events(migrated_engine)) == 2

    def test_an_attempt_that_finds_a_spent_block_and_shuts_the_account_again_journals(
        self, migrated_engine: Engine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # With an allowance of one, the statement that finds a *spent* (expired, not yet cleared)
        # block restarts the count at one and so shuts the account again in the same breath: the
        # previous ``sign_in_blocked_until`` is non-NULL but over, and that is a new period.
        monkeypatch.setattr(repository, "FAILED_SIGN_IN_ALLOWANCE", 1)
        _account_one_failure_from_the_block(migrated_engine, allowance=1)
        with Session(migrated_engine) as session:
            assert users.authenticate(session, LOGIN, WRONG) is None
            session.commit()
        assert len(_blocked_events(migrated_engine)) == 1
        with migrated_engine.begin() as connection:
            connection.execute(text(
                "UPDATE app_user SET sign_in_blocked_until = now() - interval '1 second' "
                "WHERE login = :login"), {"login": LOGIN})
        assert _row(migrated_engine)["sign_in_blocked_until"] is not None  # spent, not cleared
        with Session(migrated_engine) as session:
            assert users.authenticate(session, LOGIN, WRONG) is None
            session.commit()
        assert len(_blocked_events(migrated_engine)) == 2
