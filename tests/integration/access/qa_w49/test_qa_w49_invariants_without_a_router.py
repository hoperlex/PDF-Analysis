"""`W49-QA-01`, items 2 and 3 below the router -- the §3.2 invariants in ``auditmanager.access``.

`W49-PLAN.md` §3.2: "Invariants, enforced in ``auditmanager.access`` and tested without the
router: an account cannot archive, purge, demote or reset itself; the last active account
holding ``admin`` cannot be archived or lose ``admin``".

Through the served operations the last-administrator rule is reachable only as a race (the
actor must itself hold ``admin`` to pass the seam -- see
``tests/integration/api/qa_w49/test_qa_w49_last_admin.py``). Here, with no seam in front, the
sequential case is driven directly: the rule must hold whoever the actor is, because the
operator's commands and any future caller reach these methods without a seam. Every refusal
must leave the database as it was.

A fresh database per test (``tests/integration/access/conftest.py``); the seeded ``admin`` row's
``admin`` role is removed first, so the account made here is the only administrator.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.access.passwords import hash_password
from auditmanager.access.public import (
    LAST_ADMIN,
    SELF_ACTION,
    AccountInvariantViolation,
    AccountRepository,
    UserUid,
)
from auditmanager.shared.errors import ErrorCode

ACCOUNTS = AccountRepository()


def _account(session: Session, roles: tuple[str, ...]) -> str:
    uid = str(UserUid.new())
    stored = hash_password("qa49-invariant-password")
    session.execute(
        text(
            "INSERT INTO app_user (user_uid, login, password_algorithm, password_iterations, "
            "password_salt, password_hash, is_default_credential, last_name, first_name, "
            "profile_completed_at) VALUES (:uid, :login, :alg, :it, :salt, :digest, false, "
            "'Инвариантова', 'Ира', now())"
        ),
        {
            "uid": uid,
            "login": f"qa49-inv-{secrets.token_hex(4)}@qa.invalid",
            "alg": stored.algorithm,
            "it": stored.iterations,
            "salt": stored.salt,
            "digest": stored.digest,
        },
    )
    for role in roles:
        session.execute(
            text("INSERT INTO app_user_role (user_uid, role) VALUES (:uid, :role)"),
            {"uid": uid, "role": role},
        )
    return uid


def _snapshot(session: Session) -> list[tuple[object, ...]]:
    users = session.execute(
        text(
            "SELECT user_uid, token_epoch, archived_at, archived_by, password_hash "
            "FROM app_user ORDER BY user_uid"
        )
    ).all()
    roles = session.execute(
        text("SELECT user_uid, role FROM app_user_role ORDER BY user_uid, role")
    ).all()
    return [tuple(row) for row in users] + [tuple(row) for row in roles]


@pytest.fixture
def sole_admin(session: Session) -> str:
    session.execute(text("DELETE FROM app_user_role WHERE role = 'admin'"))
    uid = _account(session, ("expert", "admin"))
    session.commit()
    return uid


_LAST_ADMIN_ACTS: dict[str, Callable[[Session, str, str], object]] = {
    "archive_account": lambda s, actor, target: ACCOUNTS.archive_account(
        s, actor_uid=actor, user_uid=target
    ),
    "set_roles (drop admin)": lambda s, actor, target: ACCOUNTS.set_roles(
        s, actor_uid=actor, user_uid=target, roles=("expert",)
    ),
    "set_roles (to nothing)": lambda s, actor, target: ACCOUNTS.set_roles(
        s, actor_uid=actor, user_uid=target, roles=()
    ),
    "revoke_role admin": lambda s, actor, target: ACCOUNTS.revoke_role(
        s, actor_uid=actor, user_uid=target, role="admin"
    ),
}


@pytest.mark.parametrize("act", sorted(_LAST_ADMIN_ACTS))
def test_the_last_active_administrator_cannot_be_removed_by_anyone(
    session: Session, sole_admin: str, act: str
) -> None:
    actor = _account(session, ("expert",))
    session.commit()
    before = _snapshot(session)

    with pytest.raises(AccountInvariantViolation) as refused:
        _LAST_ADMIN_ACTS[act](session, actor, sole_admin)
    assert refused.value.invariant == LAST_ADMIN
    assert refused.value.code is ErrorCode.CONFLICT
    session.rollback()
    assert _snapshot(session) == before


@pytest.mark.parametrize("act", sorted(_LAST_ADMIN_ACTS))
def test_with_a_second_active_administrator_the_same_act_succeeds(
    session: Session, sole_admin: str, act: str
) -> None:
    # The counter-case: the refusal above is the last-administrator rule, not a refusal of
    # every such act.
    actor = _account(session, ("expert", "admin"))
    session.commit()
    _LAST_ADMIN_ACTS[act](session, actor, sole_admin)
    session.commit()
    remaining = session.execute(
        text(
            "SELECT count(*) FROM app_user u JOIN app_user_role r ON r.user_uid = u.user_uid "
            "AND r.role = 'admin' WHERE u.archived_at IS NULL"
        )
    ).scalar_one()
    assert remaining == 1


_SELF_ACTS: dict[str, Callable[[Session, str], object]] = {
    "archive_account": lambda s, me: ACCOUNTS.archive_account(s, actor_uid=me, user_uid=me),
    "purge_account": lambda s, me: ACCOUNTS.purge_account(s, actor_uid=me, user_uid=me),
    "set_roles (drop admin)": lambda s, me: ACCOUNTS.set_roles(
        s, actor_uid=me, user_uid=me, roles=("expert",)
    ),
    "set_roles (drop expert, add nothing)": lambda s, me: ACCOUNTS.set_roles(
        s, actor_uid=me, user_uid=me, roles=("admin",)
    ),
    "revoke_role expert": lambda s, me: ACCOUNTS.revoke_role(
        s, actor_uid=me, user_uid=me, role="expert"
    ),
    "reset_password": lambda s, me: ACCOUNTS.reset_password(
        s, actor_uid=me, user_uid=me, temporary_password="qa49-temporary-self"
    ),
}


@pytest.mark.parametrize("act", sorted(_SELF_ACTS))
@pytest.mark.parametrize("sole", [True, False], ids=["sole-admin", "another-admin"])
def test_an_account_cannot_act_on_itself(
    session: Session, sole_admin: str, act: str, sole: bool
) -> None:
    if not sole:
        _account(session, ("expert", "admin"))
        session.commit()
    before = _snapshot(session)

    with pytest.raises(AccountInvariantViolation) as refused:
        _SELF_ACTS[act](session, sole_admin)
    assert refused.value.invariant == SELF_ACTION
    assert refused.value.code is ErrorCode.PERMISSION_DENIED
    assert not refused.value.detail_fields, "an act on oneself carries no detail"
    session.rollback()
    assert _snapshot(session) == before
