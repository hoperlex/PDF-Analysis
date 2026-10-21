"""`D-147` -- a pending request and an active account never hold one login.

``uq_registration_request_pending_login`` keeps one pending request per login and
``uq_app_user_login`` one active account per login; neither relates a request to an account.
That relation is kept by the registration queue's advisory lock (``access/queue_lock.py``) and a
read, in every writer that can make an account active under a login: approval, profile
completion and restoring an archived account, as submit already did.

The races below run on a real PostgreSQL, in two sessions on two threads, and are *arranged*
rather than hoped for: the submitting thread is paused by a ``before_cursor_execute`` hook right
before the statement that asks "is a request pending for this login?", after it has already been
told "no active account holds it". The other writer is then started. With the lock it waits for
the submitter (observed in ``pg_stat_activity``); without it, it completes in the gap, and the
submitter goes on to file a request for a login an account now holds. What is asserted is the
invariant after both finish, never an interleaving.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import pytest
from sqlalchemy import Engine, event, text
from sqlalchemy.orm import Session

from auditmanager.access.accounts import AccountRepository
from auditmanager.access.registrations import RegistrationRepository
from auditmanager.access.repository import UserRepository
from auditmanager.shared.errors import DomainError

PASSWORD = "an-applicant-password"  # noqa: S105 - a test literal

users = UserRepository()
accounts = AccountRepository()
registrations = RegistrationRepository()

#: Fragments of the one statement the submitter is paused in front of: the pending-request
#: EXISTS of ``access/queue_lock.py``.
_PENDING_CHECK = ("registration_request", "EXISTS", "status = 'pending'")

#: Pending requests that share a login with an active account: the invariant, as a count.
_BROKEN_PAIRS = text(
    "SELECT count(*) FROM registration_request r "
    "JOIN app_user u ON u.login = r.login AND u.archived_at IS NULL "
    "WHERE r.status = 'pending'"
)


@dataclass
class _Outcome:
    value: Any = None
    error: DomainError | None = None
    finished: threading.Event = field(default_factory=threading.Event)

    @property
    def reason(self) -> str | None:
        return None if self.error is None else self.error.detail_fields.get("conflict_reason")


def _run(outcome: _Outcome, work: Callable[[], Any]) -> None:
    try:
        outcome.value = work()
    except DomainError as exc:
        outcome.error = exc
    finally:
        outcome.finished.set()


def _backend_waits_on_a_lock(engine: Engine) -> bool:
    # A fresh connection per probe: pg_stat_activity is a per-transaction snapshot.
    with engine.connect() as probe:
        return bool(
            probe.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE datname = current_database() AND wait_event_type = 'Lock'"
                )
            ).scalar_one()
        )


def _race_with_a_submit_in_the_gap(
    engine: Engine, *, submit: Callable[[Session], Any], other: Callable[[Session], Any]
) -> tuple[_Outcome, _Outcome, bool]:
    """Run ``submit`` paused before its pending-request check, start ``other``, then release.

    Returns both outcomes and whether ``other`` was seen waiting on a lock while the submitter
    was paused (the shipped behaviour) rather than finishing in the gap (the defect).
    """
    submitted, interleaved = _Outcome(), _Outcome()

    def submitting() -> Any:
        with Session(engine) as session:
            result = submit(session)
            session.commit()
            return result

    def interleaving() -> Any:
        with Session(engine) as session:
            result = other(session)
            session.commit()
            return result

    submitter = threading.Thread(target=_run, args=(submitted, submitting))
    reached, release = threading.Event(), threading.Event()

    def pause(conn, cursor, statement, parameters, context, executemany) -> None:
        if threading.current_thread() is submitter and all(f in statement for f in _PENDING_CHECK):
            reached.set()
            assert release.wait(30), "the paused submitter was never released"

    event.listen(engine, "before_cursor_execute", pause)
    interleaver = threading.Thread(target=_run, args=(interleaved, interleaving))
    waited = False
    try:
        submitter.start()
        assert reached.wait(20), "the submitter never reached its pending-request check"
        interleaver.start()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not interleaved.finished.is_set():
            if _backend_waits_on_a_lock(engine):
                waited = True
                break
            time.sleep(0.05)
    finally:
        release.set()
        submitter.join(30)
        interleaver.join(30)
        event.remove(engine, "before_cursor_execute", pause)
    assert submitted.finished.is_set() and interleaved.finished.is_set(), "a writer never finished"
    return submitted, interleaved, waited


def _broken_pairs(engine: Engine) -> int:
    with engine.connect() as connection:
        return int(connection.execute(_BROKEN_PAIRS).scalar_one())


def _submit_for(session: Session, login: str) -> Any:
    return registrations.submit(
        session, login=login, password=PASSWORD, last_name="Петрова", first_name="Анна"
    )


def _admin(engine: Engine) -> str:
    with Session(engine) as session:
        record = users.find_by_login(session, "admin")
        assert record is not None
        return str(record.user_uid)


# --- the races ------------------------------------------------------------------------


def test_an_approval_cannot_interleave_with_a_submit_for_the_same_login(
    migrated_engine: Engine,
) -> None:
    """The defect as `W53-CLOSE-INT` recorded it: the submit read "no account yet", the
    approval then committed the account and decided the request, and the submit's next read
    found nothing pending -- so it filed a second request for a login an account now held."""
    login = "race-approve@example.com"
    admin = _admin(migrated_engine)
    with Session(migrated_engine) as setup:
        request_id = _submit_for(setup, login).request_id
        setup.commit()

    submitted, approved, waited = _race_with_a_submit_in_the_gap(
        migrated_engine,
        submit=lambda session: _submit_for(session, login),
        other=lambda session: registrations.approve(
            session, actor_uid=admin, request_id=request_id, roles=["expert"]
        ),
    )

    assert _broken_pairs(migrated_engine) == 0, "a pending request and an account hold one login"
    assert waited, "the approval did not wait for the submitter: it took no queue lock"
    # The submitter held the lock and the first request was still pending: it is told so.
    assert submitted.reason == "request_pending", (submitted.value, submitted.error)
    assert approved.error is None, approved.error


def test_a_profile_completion_cannot_interleave_with_a_submit_for_the_same_login(
    migrated_engine: Engine,
) -> None:
    login = "race-profile@example.com"
    with Session(migrated_engine) as setup:
        legacy = users.create_user(setup, "legacy-race", PASSWORD)
        setup.commit()
        uid = str(legacy.user_uid)

    submitted, completed, waited = _race_with_a_submit_in_the_gap(
        migrated_engine,
        submit=lambda session: _submit_for(session, login),
        other=lambda session: accounts.complete_profile(
            session, user_uid=uid, email=login, last_name="Иванов", first_name="Пётр"
        ),
    )

    assert _broken_pairs(migrated_engine) == 0, "a pending request and an account hold one login"
    assert waited, "the completion did not wait for the submitter: it took no queue lock"
    assert submitted.error is None, submitted.error
    # The request was filed first, so the completion is the one refused -- with the closed
    # reason `login_taken`, which `completeProfile` already declares.
    assert completed.reason == "login_taken", (completed.value, completed.error)


def test_a_restore_cannot_interleave_with_a_submit_for_the_same_login(
    migrated_engine: Engine,
) -> None:
    login = "race-restore@example.com"
    admin = _admin(migrated_engine)
    with Session(migrated_engine) as setup:
        victim = users.create_user(setup, login, PASSWORD)
        uid = str(victim.user_uid)
        accounts.archive_account(setup, actor_uid=admin, user_uid=uid)
        setup.commit()

    submitted, restored, waited = _race_with_a_submit_in_the_gap(
        migrated_engine,
        submit=lambda session: _submit_for(session, login),
        other=lambda session: accounts.restore_account(session, actor_uid=admin, user_uid=uid),
    )

    assert _broken_pairs(migrated_engine) == 0, "a pending request and an account hold one login"
    assert waited, "the restore did not wait for the submitter: it took no queue lock"
    assert submitted.error is None, submitted.error
    assert restored.reason == "login_taken", (restored.value, restored.error)


# --- the sequential halves: the check, with no race at all ---------------------------------


def test_a_profile_completion_is_refused_while_a_pending_request_holds_the_email(
    migrated_engine: Engine,
) -> None:
    login = "held-by-request@example.com"
    with Session(migrated_engine) as session:
        legacy = users.create_user(session, "legacy-held", PASSWORD)
        _submit_for(session, login)
        session.commit()
        with pytest.raises(DomainError) as caught:
            accounts.complete_profile(
                session,
                user_uid=str(legacy.user_uid),
                email=login,
                last_name="Иванов",
                first_name="Пётр",
            )
        assert caught.value.detail_fields == {"conflict_reason": "login_taken"}
        session.rollback()
        # Nothing moved: the account keeps its legacy login and its incomplete profile.
        again = users.find_by_login(session, "legacy-held")
        assert again is not None and again.profile_completed_at is None
    assert _broken_pairs(migrated_engine) == 0


def test_a_profile_completion_that_changes_no_login_is_not_refused_for_a_request(
    migrated_engine: Engine,
) -> None:
    """The check is for a login the account does not hold yet: completing the names of an
    account whose login already is the e-mail claims nothing new."""
    login = "already-email@example.com"
    with Session(migrated_engine) as session:
        legacy = users.create_user(session, login, PASSWORD)
        session.commit()
        record = accounts.complete_profile(
            session, user_uid=str(legacy.user_uid), email=None, last_name="Иванов", first_name="Пётр"
        )
        session.commit()
    assert record.login == login and record.profile_complete


def test_restoring_an_archived_account_is_refused_while_a_pending_request_holds_its_login(
    migrated_engine: Engine,
) -> None:
    """An archived account holds no login, so a request for it may be filed -- and restoring the
    account would then make the pair `D-147` is about."""
    login = "restore-held@example.com"
    admin = _admin(migrated_engine)
    with Session(migrated_engine) as session:
        victim = users.create_user(session, login, PASSWORD)
        uid = str(victim.user_uid)
        accounts.archive_account(session, actor_uid=admin, user_uid=uid)
        session.commit()
        _submit_for(session, login)
        session.commit()
        with pytest.raises(DomainError) as caught:
            accounts.restore_account(session, actor_uid=admin, user_uid=uid)
        assert caught.value.detail_fields == {"conflict_reason": "login_taken"}
        session.rollback()
        assert accounts.get_account(session, uid).record.archived
    assert _broken_pairs(migrated_engine) == 0


def test_the_queue_has_one_lock_key_and_registrations_still_names_it() -> None:
    """The key is spelled once, in ``queue_lock``; ``registrations._QUEUE_LOCK_KEY`` is an alias."""
    from auditmanager.access import registrations as module
    from auditmanager.access.queue_lock import QUEUE_LOCK_KEY

    assert QUEUE_LOCK_KEY == 0x52454751
    assert module._QUEUE_LOCK_KEY == QUEUE_LOCK_KEY
