"""``renewToken`` over real rows: the sliding session's one API operation.

Owner ruling of 2026-11-18: a reviewer who is working is not signed out. The web tier holds the
credential server-side and asks for another one, with a new lifetime, before the old one is
close to its end. What the API owes it is narrow, and this suite asserts each half against a
real ``app_user`` row, the real adapter and the served seam -- none of the three is a fake:

* a credential the seam accepts is answered with **another** credential for the same account
  and the full lifetime;
* a credential the seam refuses -- a raised epoch (a reset, a password change), an archived
  account, an expired one, a forged one, none at all -- is the seam's own ``401``, so renewal
  cannot keep alive what revocation ended;
* an account on a **default credential** and one with an **incomplete profile** can renew
  (the web tier renews every session it holds), and the flag is the row's, not laundered;
* the epoch is compared **again** at the moment of minting: a revocation landing between the
  seam's read and the mint is refused by the adapter rather than undone.

**It does not skip.** The claim is about rows, and a suite that skipped would report success
for a tree in which it does not hold. Every account is randomised and removed afterwards.
"""

from __future__ import annotations

import secrets
import time
from collections.abc import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient

from auditmanager.access.accounts import AccountRepository
from auditmanager.access.models import UserRecord
from auditmanager.access.repository import UserRepository
from auditmanager.api.app import create_asgi_app
from auditmanager.api.routers import build_router
from auditmanager.api.security import (
    API_TOKEN_VARIABLE,
    TOKEN_LIFETIME_SECONDS,
    Subject,
    build_signer,
)
from auditmanager.bootstrap.adapters import CredentialAdapter

DEPLOYMENT_SECRET = "renew1118-suite-deployment-secret"
PASSWORD = "correct-horse-battery-staple-4471"
NEW_PASSWORD = "a-different-horse-entirely-9920"


def _signer():
    signer = build_signer({API_TOKEN_VARIABLE: DEPLOYMENT_SECRET})
    assert signer is not None
    return signer


@pytest.fixture
def adapter(session_factory: sessionmaker[Session]) -> CredentialAdapter:
    return CredentialAdapter(
        session_factory,
        users=UserRepository(),
        accounts=AccountRepository(),
        signer=_signer(),
    )


@pytest.fixture
def client(adapter: CredentialAdapter) -> TestClient:
    """The served surface, wired as the composition root wires the credential port."""
    router = build_router(
        projects=None,  # type: ignore[arg-type]
        documents=None,  # type: ignore[arg-type]
        runs=None,  # type: ignore[arg-type]
        findings=None,  # type: ignore[arg-type]
        decisions=None,  # type: ignore[arg-type]
        exports=None,  # type: ignore[arg-type]
        credentials=adapter,
    )

    class _Built:
        def __init__(self) -> None:
            from auditmanager.runs import InlineCarrier

            self.router = router
            self.carrier = InlineCarrier()

    app = create_asgi_app(environ={API_TOKEN_VARIABLE: DEPLOYMENT_SECRET}, application=_Built())
    return TestClient(app, raise_server_exceptions=False)


def _create(
    session_factory: sessionmaker[Session], *, is_default_credential: bool = False
) -> UserRecord:
    login = f"renew1118-{secrets.token_hex(6)}"
    with session_factory() as session:
        record = UserRepository().create_user(
            session, login, PASSWORD, is_default_credential=is_default_credential
        )
        session.commit()
    return record


def _remove(session_factory: sessionmaker[Session], login: str) -> None:
    with session_factory() as session:
        session.execute(text("DELETE FROM app_user WHERE login = :login"), {"login": login})
        session.commit()


#: The accounts that archived somebody in this module, removed after the account they archived: the
#: archived row's ``archived_by`` points at its actor (``fk_app_user_archived_by``), so the actor cannot
#: be deleted first.
_ACTORS: list[str] = []


def _archive(session_factory: sessionmaker[Session], record: UserRecord) -> None:
    """Archive ``record`` through the access boundary's own operation, as another account.

    A direct ``UPDATE ... archived_at`` is refused by ``ck_app_user_archive_pair`` (an archive names
    who did it), and the real operation also raises the credential epoch, which is what an archive
    does in a deployment.
    """
    login = f"renew1118-actor-{secrets.token_hex(4)}"
    with session_factory() as session:
        actor = str(UserRepository().create_user(session, login, PASSWORD).user_uid)
        session.commit()
    _ACTORS.append(login)
    with session_factory() as session:
        AccountRepository().archive_account(session, actor_uid=actor, user_uid=str(record.user_uid))
        session.commit()


@pytest.fixture
def user(
    app_user_table: object, session_factory: sessionmaker[Session]
) -> Iterator[UserRecord]:
    record = _create(session_factory)
    try:
        yield record
    finally:
        _remove(session_factory, record.login)
        while _ACTORS:
            _remove(session_factory, _ACTORS.pop())


def _credential(client: TestClient, record: UserRecord) -> str:
    response = client.post("/auth/token", json={"login": record.login, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return str(response.json()["token"])


def _renew(client: TestClient, credential: str | None) -> object:
    headers = {} if credential is None else {"Authorization": f"Bearer {credential}"}
    return client.post("/auth/token/renew", headers=headers)


def test_the_lifetime_is_the_idle_window_plus_the_renewal_cadence() -> None:
    """Eight hours and ten minutes: the number the web tier's renewal arithmetic stands on."""
    assert TOKEN_LIFETIME_SECONDS == 8 * 3600 + 600


def test_a_valid_credential_is_answered_with_a_new_one_and_the_new_lifetime(
    client: TestClient, user: UserRecord
) -> None:
    held = _credential(client, user)
    response = _renew(client, held)
    assert response.status_code == 200, response.text
    body = response.json()
    assert sorted(body) == ["expires_in", "is_default_credential", "token"], body
    assert body["expires_in"] == TOKEN_LIFETIME_SECONDS == 8 * 3600 + 600
    assert body["is_default_credential"] is False

    subject = _signer().verify(body["token"])
    assert subject is not None
    assert subject.user_uid == str(user.user_uid)
    assert subject.login == user.login
    assert subject.token_epoch == user.token_epoch


def test_the_new_credential_is_one_the_seam_accepts_and_the_old_one_still_is(
    client: TestClient, user: UserRecord
) -> None:
    """Renewing does not revoke the credential presented: it stays valid until its own end."""
    held = _credential(client, user)
    renewed = _renew(client, held).json()["token"]
    assert _renew(client, renewed).status_code == 200
    assert _renew(client, held).status_code == 200


def test_a_raised_epoch_is_refused(
    client: TestClient, user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    held = _credential(client, user)
    with session_factory() as session:
        UserRepository().revoke_credentials(session, login=user.login)
        session.commit()
    response = _renew(client, held)
    assert response.status_code == 401, response.text
    assert response.json()["error_code"] == "authentication_required"


def test_a_password_change_refuses_the_credential_it_replaced(
    client: TestClient, user: UserRecord
) -> None:
    """The other route to a raised epoch, driven through the served operation."""
    held = _credential(client, user)
    changed = client.post(
        "/auth/password",
        headers={"Authorization": f"Bearer {held}"},
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert changed.status_code == 200, changed.text
    assert _renew(client, held).status_code == 401
    assert _renew(client, changed.json()["token"]).status_code == 200


def test_an_archived_account_is_refused(
    client: TestClient, user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    held = _credential(client, user)
    _archive(session_factory, user)
    response = _renew(client, held)
    assert response.status_code == 401, response.text
    assert response.json()["error_code"] == "authentication_required"


def test_a_deleted_account_is_refused(
    client: TestClient, user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    held = _credential(client, user)
    _remove(session_factory, user.login)
    assert _renew(client, held).status_code == 401


def test_an_expired_credential_is_refused(client: TestClient, user: UserRecord) -> None:
    expired = _signer().issue(
        Subject(
            user_uid=str(user.user_uid),
            login=user.login,
            token_epoch=user.token_epoch,
            display_label=user.display_label,
        ),
        is_default_credential=False,
        now=time.time() - TOKEN_LIFETIME_SECONDS - 1,
    )
    response = _renew(client, expired.token)
    assert response.status_code == 401, response.text
    assert response.json()["error_code"] == "authentication_required"


def test_no_credential_and_a_forged_one_are_refused(client: TestClient) -> None:
    assert _renew(client, None).status_code == 401
    assert _renew(client, "not-a-credential-at-all").status_code == 401


def test_the_deployment_secret_is_not_a_credential_here_either(client: TestClient) -> None:
    assert _renew(client, DEPLOYMENT_SECRET).status_code == 401


def test_an_account_on_a_default_credential_can_renew_and_the_flag_is_the_rows(
    app_user_table: object, client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """`R-50`'s register lets ``renewToken`` through, and renewing does not launder the flag."""
    record = _create(session_factory, is_default_credential=True)
    try:
        held = _credential(client, record)
        # Control: another guarded operation is refused for this account, so the 200 below
        # is the register's doing and not an account the seam waves through.
        refused = client.get("/projects", headers={"Authorization": f"Bearer {held}"})
        assert refused.status_code == 403, refused.text
        response = _renew(client, held)
        assert response.status_code == 200, response.text
        assert response.json()["is_default_credential"] is True
    finally:
        _remove(session_factory, record.login)


def test_an_account_with_an_incomplete_profile_can_renew(
    client: TestClient, user: UserRecord
) -> None:
    """A legacy account created through ``create_user`` has no names yet and no roles."""
    held = _credential(client, user)
    assert _renew(client, held).status_code == 200


def test_the_adapter_compares_the_epoch_again_at_the_moment_of_minting(
    adapter: CredentialAdapter, user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """The window between the seam's read and the mint, closed rather than narrowed.

    The seam compared the credential's epoch with the row; an administrator's reset in the
    next instant raises it. The adapter is handed the epoch the credential carries and
    refuses when the row has moved on, so a revoked credential cannot buy a live one.
    """
    assert adapter.renew(user_uid=str(user.user_uid), token_epoch=user.token_epoch) is not None
    with session_factory() as session:
        UserRepository().revoke_credentials(session, login=user.login)
        session.commit()
    assert adapter.renew(user_uid=str(user.user_uid), token_epoch=user.token_epoch) is None
    assert adapter.renew(user_uid=str(user.user_uid), token_epoch=user.token_epoch + 1) is not None


def test_the_adapter_refuses_an_archived_account_itself(
    adapter: CredentialAdapter, user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """The seam refuses an archived account first; the adapter does not rely on that, because the
    row can be archived between the seam's read and this one.

    An archive also raises the epoch, so the credential's own epoch would be refused by the epoch
    comparison and hide the archive check. The call is made with the epoch the **row holds now**, so
    that the only thing left to refuse it is the archive."""
    assert adapter.renew(user_uid=str(user.user_uid), token_epoch=user.token_epoch) is not None
    _archive(session_factory, user)
    standing = adapter.standing_of(str(user.user_uid))
    assert standing is not None and standing.archived is True
    assert standing.token_epoch == user.token_epoch + 1
    assert adapter.renew(user_uid=str(user.user_uid), token_epoch=standing.token_epoch) is None


def test_the_adapter_refuses_an_account_that_does_not_exist(adapter: CredentialAdapter) -> None:
    assert adapter.renew(user_uid="usr_00000000000000000000000000", token_epoch=1) is None
