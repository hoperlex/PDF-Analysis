"""`R-150e`, `R-150x`: «Наблюдатель» (``viewer``) is the only role of an account that holds it.

Roles are written in three places -- an administrator's role update (``set_roles``), a
registration approval (``approve``) and the host command (``grant_role``) -- and the rule is
enforced in each before the first write. A refusal writes nothing and does not raise the
account's ``token_epoch``. The column CHECK of ``0050_viewer_role`` admits the value; the
exclusivity is the boundary's, because a CHECK cannot see the account's other rows.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.access.accounts import AccountRepository
from auditmanager.access.models import require_exclusive_viewer
from auditmanager.access.repository import UserRepository
from auditmanager.shared.errors import DomainError, ErrorCode

PASSWORD = "a-long-enough-password"  # noqa: S105 - a test literal

users = UserRepository()
accounts = AccountRepository()

COMBINED = (
    frozenset({"viewer", "expert"}),
    frozenset({"viewer", "admin"}),
    frozenset({"viewer", "expert", "admin"}),
)


def _create(session: Session, email: str, *roles: str) -> str:
    record = users.create_user(session, email, PASSWORD)
    uid = str(record.user_uid)
    accounts.complete_profile(
        session, user_uid=uid, email=None, last_name="Петрова", first_name="Анна"
    )
    for role in roles:
        accounts.grant_role(session, user_uid=uid, role=role, granted_by=None)
    session.commit()
    return uid


def _seed(session: Session) -> str:
    seed = users.find_by_login(session, "admin")
    assert seed is not None
    return str(seed.user_uid)


def _epoch(session: Session, uid: str) -> int:
    return int(
        session.execute(
            text("SELECT token_epoch FROM app_user WHERE user_uid = :u"), {"u": uid}
        ).scalar_one()
    )


def _assert_viewer_exclusive(caught: pytest.ExceptionInfo[DomainError]) -> None:
    assert caught.value.code is ErrorCode.VALIDATION_FAILED
    assert caught.value.detail_fields.get("constraint") == "viewer_exclusive"
    assert caught.value.detail_fields.get("field") == "roles"


class TestTheRule:
    @pytest.mark.parametrize("roles", COMBINED)
    def test_a_combination_is_refused(self, roles: frozenset[str]) -> None:
        with pytest.raises(DomainError) as caught:
            require_exclusive_viewer(roles)
        _assert_viewer_exclusive(caught)

    @pytest.mark.parametrize(
        "roles",
        [
            frozenset(),
            frozenset({"viewer"}),
            frozenset({"expert"}),
            frozenset({"admin"}),
            frozenset({"expert", "admin"}),
        ],
    )
    def test_every_other_set_passes_unchanged(self, roles: frozenset[str]) -> None:
        assert require_exclusive_viewer(roles) == roles


class TestTheThreeWritePaths:
    def test_the_viewer_alone_is_written_and_read_back(self, session: Session) -> None:
        uid = _create(session, "viewer@example.com", "viewer")
        assert accounts.roles_of(session, uid) == frozenset({"viewer"})

    @pytest.mark.parametrize("roles", COMBINED)
    def test_set_roles_refuses_a_combination_and_writes_nothing(
        self, session: Session, roles: frozenset[str]
    ) -> None:
        seed = _seed(session)
        uid = _create(session, "anna@example.com", "expert")
        before = _epoch(session, uid)
        with pytest.raises(DomainError) as caught:
            accounts.set_roles(session, actor_uid=seed, user_uid=uid, roles=set(roles))
        _assert_viewer_exclusive(caught)
        session.rollback()
        assert accounts.roles_of(session, uid) == frozenset({"expert"})
        assert _epoch(session, uid) == before

    def test_set_roles_moves_an_account_between_expert_and_viewer(self, session: Session) -> None:
        seed = _seed(session)
        uid = _create(session, "anna@example.com", "expert")
        accounts.set_roles(session, actor_uid=seed, user_uid=uid, roles={"viewer"})
        session.commit()
        assert accounts.roles_of(session, uid) == frozenset({"viewer"})
        accounts.set_roles(session, actor_uid=seed, user_uid=uid, roles={"expert"})
        session.commit()
        assert accounts.roles_of(session, uid) == frozenset({"expert"})

    @pytest.mark.parametrize(("held", "added"), [("viewer", "expert"), ("expert", "viewer"), ("admin", "viewer")])
    def test_grant_role_refuses_what_would_combine_and_writes_nothing(
        self, session: Session, held: str, added: str
    ) -> None:
        uid = _create(session, "anna@example.com", held)
        before = _epoch(session, uid)
        with pytest.raises(DomainError) as caught:
            accounts.grant_role(session, user_uid=uid, role=added, granted_by=None)
        _assert_viewer_exclusive(caught)
        session.rollback()
        assert accounts.roles_of(session, uid) == frozenset({held})
        assert _epoch(session, uid) == before

    def test_grant_role_of_the_viewer_to_a_roleless_account_is_written(self, session: Session) -> None:
        uid = _create(session, "anna@example.com")
        accounts.grant_role(session, user_uid=uid, role="viewer", granted_by=None)
        session.commit()
        assert accounts.roles_of(session, uid) == frozenset({"viewer"})


class TestTheColumnCheck:
    def test_the_check_admits_the_viewer_and_still_refuses_an_unknown_role(
        self, session: Session
    ) -> None:
        uid = _create(session, "anna@example.com")
        session.execute(
            text("INSERT INTO app_user_role (user_uid, role) VALUES (:u, 'viewer')"), {"u": uid}
        )
        session.flush()
        with pytest.raises(Exception, match="ck_app_user_role_role"):
            with session.begin_nested():
                session.execute(
                    text("INSERT INTO app_user_role (user_uid, role) VALUES (:u, 'superuser')"),
                    {"u": uid},
                )
