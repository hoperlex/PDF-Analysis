"""`W49-SEAL-01b` -- the shipped adapter's standing read, over real rows.

``CredentialAdapter.standing_of`` is the one read the seam makes on every guarded request.
Since `W49-SEAL-01` it answers the archive state, the profile completeness, the role set and
the row's login and display label beside the epoch and the default credential, from the
access boundary's management half in one statement. The API suite drives the seam with an
in-memory standing; this drives the translation itself against the database, so a field the
adapter dropped or defaulted is red here rather than permissive in a deployment.
"""

from __future__ import annotations

import secrets
from collections.abc import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.access.accounts import AccountRepository
from auditmanager.access.repository import UserRepository
from auditmanager.api.security import ROLE_ADMIN, ROLE_EXPERT, build_signer
from auditmanager.bootstrap.adapters import CredentialAdapter, _seam_role
from auditmanager.shared.errors import DomainError, ErrorCode

PASSWORD = "standing-suite-password-7781"


@pytest.fixture
def adapter(session_factory: sessionmaker[Session]) -> CredentialAdapter:
    signer = build_signer({"AUDITMANAGER_API_TOKEN": "standing-suite-secret"})
    assert signer is not None
    return CredentialAdapter(
        session_factory,
        users=UserRepository(),
        accounts=AccountRepository(),
        signer=signer,
    )


@pytest.fixture
def account(session_factory: sessionmaker[Session]) -> Iterator[str]:
    """A fresh legacy account -- incomplete, roleless -- removed afterwards."""
    login = f"w49standing-{secrets.token_hex(5)}"
    with session_factory() as session:
        record = UserRepository().create_user(session, login, PASSWORD)
        session.commit()
    uid = str(record.user_uid)
    try:
        yield uid
    finally:
        with session_factory() as session:
            session.execute(text("DELETE FROM app_user WHERE user_uid = :u"), {"u": uid})
            session.commit()


def test_a_new_legacy_account_is_incomplete_and_roleless(
    adapter: CredentialAdapter, account: str
) -> None:
    standing = adapter.standing_of(account)
    assert standing is not None
    assert standing.archived is False
    assert standing.profile_complete is False
    assert standing.roles == frozenset()
    assert standing.is_default_credential is False
    assert standing.login.startswith("w49standing-")
    assert standing.display_label == standing.login


def test_completion_and_roles_reach_the_standing(
    adapter: CredentialAdapter,
    account: str,
    session_factory: sessionmaker[Session],
) -> None:
    """Each fact the seam decides on moves when the row moves, and only then."""
    accounts = AccountRepository()
    email = f"standing-{secrets.token_hex(5)}@suite.invalid"
    with session_factory() as session:
        accounts.complete_profile(
            session,
            user_uid=account,
            email=email,
            last_name="Стендова",
            first_name="Анна",
            middle_name=None,
        )
        accounts.grant_role(session, user_uid=account, role="expert", granted_by=None)
        accounts.grant_role(session, user_uid=account, role="admin", granted_by=None)
        session.commit()

    standing = adapter.standing_of(account)
    assert standing is not None
    assert standing.profile_complete is True
    assert standing.roles == frozenset({ROLE_EXPERT, ROLE_ADMIN})
    assert standing.login == email
    assert standing.display_label == "Стендова А."


def test_an_archive_reaches_the_standing_with_its_epoch(
    adapter: CredentialAdapter,
    account: str,
    session_factory: sessionmaker[Session],
) -> None:
    """Archived by another account, through the access boundary's own operation."""
    accounts = AccountRepository()
    actor_login = f"w49standing-actor-{secrets.token_hex(4)}"
    with session_factory() as session:
        actor = str(UserRepository().create_user(session, actor_login, PASSWORD).user_uid)
        session.commit()
    try:
        before = adapter.standing_of(account)
        assert before is not None and before.archived is False
        with session_factory() as session:
            accounts.archive_account(session, actor_uid=actor, user_uid=account)
            session.commit()
        archived = adapter.standing_of(account)
        assert archived is not None
        assert archived.archived is True
        assert archived.token_epoch == before.token_epoch + 1
    finally:
        with session_factory() as session:
            session.execute(text("DELETE FROM app_user WHERE user_uid = :u"), {"u": account})
            session.execute(text("DELETE FROM app_user WHERE user_uid = :u"), {"u": actor})
            session.commit()


def test_no_such_account_has_no_standing(adapter: CredentialAdapter) -> None:
    assert adapter.standing_of("usr_01M2545JSD15ETSNNV904X99ZZ") is None


def test_a_role_the_seam_does_not_know_is_a_fault_and_never_dropped() -> None:
    """The translation table refuses; a set that silently lost a member would be a
    privilege decision made by a dictionary."""
    assert _seam_role("expert") == ROLE_EXPERT
    assert _seam_role("admin") == ROLE_ADMIN
    with pytest.raises(DomainError) as refused:
        _seam_role("reviewer")
    assert refused.value.code is ErrorCode.INTERNAL_ERROR
