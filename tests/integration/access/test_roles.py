"""The role set: grant, revoke, set, the epoch bump, and the §3.2 invariants -- no router.

`W49-ACCESS-01c`, `W49-PLAN.md` §3.2.
"""

from __future__ import annotations

import threading
import time

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from auditmanager.access.accounts import (
    LAST_ADMIN,
    SELF_ACTION,
    AccountInvariantViolation,
    AccountRepository,
)
from auditmanager.access.repository import UserRepository
from auditmanager.shared.errors import DomainError, ErrorCode

PASSWORD = "a-long-enough-password"  # noqa: S105 - a test literal

users = UserRepository()
accounts = AccountRepository()


def _create(session: Session, email: str, *, roles: tuple[str, ...] = ("expert",)) -> str:
    uid = str(users.create_user(session, email, PASSWORD).user_uid)
    accounts.complete_profile(
        session, user_uid=uid, email=None, last_name="Петрова", first_name="Анна"
    )
    for role in roles:
        accounts.grant_role(session, user_uid=uid, role=role, granted_by=None)
    session.commit()
    return uid


def _seed(session: Session) -> str:
    record = users.find_by_login(session, "admin")
    assert record is not None
    return str(record.user_uid)


def _epoch(session: Session, uid: str) -> int:
    return int(
        session.execute(
            text("SELECT token_epoch FROM app_user WHERE user_uid = :u"), {"u": uid}
        ).scalar_one()
    )


class TestGrantAndRevoke:
    def test_a_grant_records_the_administrator_and_bumps_once(self, session: Session) -> None:
        seed = _seed(session)
        uid = _create(session, "anna@example.com", roles=())
        before = _epoch(session, uid)
        assert accounts.grant_role(session, user_uid=uid, role="admin", granted_by=seed)
        assert not accounts.grant_role(session, user_uid=uid, role="admin", granted_by=seed)
        session.commit()
        assert _epoch(session, uid) == before + 1
        granted_by = session.execute(
            text("SELECT granted_by FROM app_user_role WHERE user_uid = :u"), {"u": uid}
        ).scalar_one()
        assert granted_by == seed

    def test_a_revocation_bumps_and_the_standing_sees_it_at_once(self, session: Session) -> None:
        seed = _seed(session)
        uid = _create(session, "anna@example.com", roles=("expert", "admin"))
        before = _epoch(session, uid)
        assert accounts.revoke_role(session, actor_uid=seed, user_uid=uid, role="expert")
        assert accounts.account_standing(session, uid).roles == frozenset({"admin"})
        assert not accounts.revoke_role(session, actor_uid=seed, user_uid=uid, role="expert")
        session.commit()
        assert _epoch(session, uid) == before + 1

    def test_an_account_cannot_demote_itself(self, session: Session) -> None:
        seed = _seed(session)
        _create(session, "anna@example.com", roles=("admin",))
        with pytest.raises(AccountInvariantViolation) as caught:
            accounts.revoke_role(session, actor_uid=seed, user_uid=seed, role="expert")
        assert caught.value.invariant == SELF_ACTION
        assert caught.value.code is ErrorCode.PERMISSION_DENIED

    def test_the_last_active_administrator_cannot_lose_admin(self, session: Session) -> None:
        seed = _seed(session)
        other = _create(session, "anna@example.com", roles=("expert",))
        with pytest.raises(AccountInvariantViolation) as caught:
            accounts.revoke_role(session, actor_uid=other, user_uid=seed, role="admin")
        assert caught.value.invariant == LAST_ADMIN
        assert caught.value.code is ErrorCode.CONFLICT
        session.rollback()
        second = _create(session, "boris@example.com", roles=("admin",))
        assert accounts.revoke_role(session, actor_uid=second, user_uid=seed, role="admin")

    def test_an_unknown_role_is_refused(self, session: Session) -> None:
        with pytest.raises(DomainError) as caught:
            accounts.grant_role(session, user_uid=_seed(session), role="root", granted_by=None)
        assert caught.value.code is ErrorCode.VALIDATION_FAILED


class TestSetRoles:
    def test_a_change_bumps_once_and_no_change_bumps_nothing(self, session: Session) -> None:
        seed = _seed(session)
        uid = _create(session, "anna@example.com", roles=("expert",))
        before = _epoch(session, uid)
        assert accounts.set_roles(
            session, actor_uid=seed, user_uid=uid, roles={"admin"}
        ) == frozenset({"admin"})
        assert _epoch(session, uid) == before + 1
        accounts.set_roles(session, actor_uid=seed, user_uid=uid, roles=("admin",))
        assert _epoch(session, uid) == before + 1
        assert accounts.roles_of(session, uid) == frozenset({"admin"})

    def test_an_empty_set_is_allowed_for_anyone_but_the_last_administrator(
        self, session: Session
    ) -> None:
        seed = _seed(session)
        uid = _create(session, "anna@example.com", roles=("expert",))
        assert accounts.set_roles(session, actor_uid=seed, user_uid=uid, roles=()) == frozenset()
        with pytest.raises(AccountInvariantViolation) as caught:
            accounts.set_roles(session, actor_uid=uid, user_uid=seed, roles={"expert"})
        assert caught.value.invariant == LAST_ADMIN

    def test_a_self_loss_is_refused_even_beside_a_gain(self, session: Session) -> None:
        seed = _seed(session)
        _create(session, "anna@example.com", roles=("admin",))
        with pytest.raises(AccountInvariantViolation) as caught:
            accounts.set_roles(session, actor_uid=seed, user_uid=seed, roles={"admin"})
        assert caught.value.invariant == SELF_ACTION

    def test_a_self_grant_without_loss_is_not_a_demotion(self, session: Session) -> None:
        uid = _create(session, "anna@example.com", roles=("admin",))
        assert accounts.set_roles(
            session, actor_uid=uid, user_uid=uid, roles={"admin", "expert"}
        ) == frozenset({"admin", "expert"})


def test_two_concurrent_revocations_of_the_last_two_administrators_leave_one(
    migrated_engine: Engine,
) -> None:
    """As the archive race in ``test_account_management.py``, for losing the role."""
    with Session(migrated_engine) as setup:
        seed = _seed(setup)
        a = _create(setup, "anna@example.com", roles=("admin",))
        b = _create(setup, "boris@example.com", roles=("admin",))
        x = _create(setup, "xenia@example.com")
        y = _create(setup, "yuri@example.com")
        accounts.revoke_role(setup, actor_uid=a, user_uid=seed, role="admin")
        setup.commit()

    outcome: dict[str, object] = {}
    first = Session(migrated_engine)
    accounts.revoke_role(first, actor_uid=x, user_uid=b, role="admin")

    def second() -> None:
        with Session(migrated_engine) as other:
            other.execute(text("SET lock_timeout = '20s'"))
            try:
                accounts.revoke_role(other, actor_uid=y, user_uid=a, role="admin")
                other.commit()
                outcome["second"] = "revoked"
            except AccountInvariantViolation as exc:
                outcome["second"] = exc.invariant

    worker = threading.Thread(target=second)
    worker.start()
    waiting = 0
    deadline = time.monotonic() + 5
    # A fresh connection per probe: pg_stat_activity is a per-transaction snapshot
    # (stats_fetch_consistency = cache), so one connection polling inside one transaction
    # would read the first answer for ever.
    while time.monotonic() < deadline and not outcome:
        with migrated_engine.connect() as probe:
            waiting = probe.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE datname = current_database() AND wait_event_type = 'Lock'"
                )
            ).scalar_one()
        if waiting:
            break
        time.sleep(0.05)
    first.commit()
    first.close()
    worker.join(30)
    with Session(migrated_engine) as check:
        admins = check.execute(
            text(
                "SELECT count(*) FROM app_user u JOIN app_user_role r USING (user_uid) "
                "WHERE r.role = 'admin' AND u.archived_at IS NULL"
            )
        ).scalar_one()
    assert admins == 1, "both administrators lost the role"
    assert outcome == {"second": LAST_ADMIN}
    assert waiting
