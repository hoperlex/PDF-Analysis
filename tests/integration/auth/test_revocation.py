"""Revocation, end to end, over real rows: the column, the seam, the change, the command.

`R-26`. Until `W39-REVOKE` a credential this deployment minted could not be taken back:
it is a signed statement with an expiry, and until that expiry passed the only lever was
rotating the deployment secret -- which signs everybody out, including the operator, and
needs a redeploy.

This suite is where the four halves of the repair meet and the only place all four are
real at once: migration ``0007_credential_epoch``'s column, `W39-REVOKE`'s repository
writes, the seam's comparison on a served request, and the operator command. Everything
else about revocation is asserted against something fake somewhere, deliberately -- and a
fake can agree with another fake forever.

**It does not skip.** The claim is that a credential stops being accepted, and a suite that
skipped would report success for a tree in which it does not.

**Every account here is randomised and removed afterwards.** `OPERATING_CONSTRAINTS.md` §6
and §9: this database is long-lived and shared, so a suite that revoked the seeded ``admin``
account -- or any account it did not create -- would sign out whatever else is running
against the same lane. Nothing below touches a row it did not write.
"""

from __future__ import annotations

import os
import secrets
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient

from auditmanager.access.models import UserRecord
from auditmanager.access.repository import CREDENTIALS_REVOKED, UserRepository
from auditmanager.access.revoke import NOTHING_SENTINEL, REVOKED_PREFIX
from auditmanager.api.app import create_asgi_app
from auditmanager.api.routers import build_router
from auditmanager.api.security import API_TOKEN_VARIABLE, Subject, build_signer
from auditmanager.bootstrap.adapters import CredentialAdapter
from auditmanager.shared.errors import DomainError, ErrorCode

def _tree_under_test() -> Path:
    """The root of the tree pytest actually imported, derived from the module under test.

    **Not** ``Path(__file__).parents[3]``, and the difference is the whole reason this
    function exists. The operator command below is driven as a *subprocess*, so it gets its
    own interpreter and its own ``PYTHONPATH``; a path derived from **this file** points at
    whichever checkout the test module was read from, which in a
    ``make mutation-copy`` run is the pristine one. The subprocess would then execute
    unmutated code and report green, and a green from a mutation that never reached the
    code is indistinguishable from a guard that cannot fail.

    Measured, not feared: the first sweep of this wave mutated
    ``access/revoke.py``'s required-argument group and its "nothing matched" exit status,
    and **both cases reddened nothing** -- ``20 passed`` twice -- because of exactly this.
    ``OPERATING_CONSTRAINTS.md`` §10 records the same fix for the ledger tool, in the same
    words: resolve it *test-side* from ``auditmanager.__file__`` so a mutation run gets the
    copy rather than silently reading the pristine tree.
    """
    import auditmanager

    return Path(auditmanager.__file__).resolve().parents[2]


#: This suite's deployment secret. Not a credential: it is what the signing key is derived
#: from, and presenting it is a refusal like any other string.
DEPLOYMENT_SECRET = "w39-revoke-suite-deployment-secret"

#: The password the created account holds, and the one it is changed to. Distinctive enough
#: that finding either in a response body or a log line means something.
PASSWORD = "correct-horse-battery-staple-4471"
NEW_PASSWORD = "a-different-horse-entirely-9920"


@pytest.fixture
def user(
    app_user_table: object, session_factory: sessionmaker[Session]
) -> Iterator[UserRecord]:
    """One real account, created through the repository and removed afterwards.

    The login is randomised so two runs, or two lanes sharing a database, cannot collide on
    the UNIQUE constraint -- and so that nothing here can revoke the seeded ``admin``
    account, whose password is published in a migration and which another suite may be
    signing in as while this one runs.
    """
    login = f"w39rev-{secrets.token_hex(6)}"
    repository = UserRepository()
    with session_factory() as session:
        record = repository.create_user(session, login, PASSWORD)
        session.commit()
    try:
        yield record
    finally:
        with session_factory() as session:
            session.execute(
                text("DELETE FROM app_user WHERE login = :login"), {"login": login}
            )
            session.commit()


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> TestClient:
    """The served surface, wired exactly as the composition root wires it.

    The other six ports are ``None``: this suite drives two operations and a port it never
    calls is a database fixture it would otherwise have to build. The seam itself is the
    application's, through ``create_asgi_app`` -- which is the point, since what is under
    test is a comparison the seam performs on every request.
    """
    signer = build_signer({API_TOKEN_VARIABLE: DEPLOYMENT_SECRET})
    assert signer is not None
    router = build_router(
        projects=None,  # type: ignore[arg-type]
        documents=None,  # type: ignore[arg-type]
        runs=None,  # type: ignore[arg-type]
        findings=None,  # type: ignore[arg-type]
        decisions=None,  # type: ignore[arg-type]
        exports=None,  # type: ignore[arg-type]
        credentials=CredentialAdapter(
            session_factory, users=UserRepository(), signer=signer
        ),
    )

    class _Built:
        """What ``create_asgi_app`` reads off a built application, and nothing more."""

        def __init__(self) -> None:
            from auditmanager.runs import InlineCarrier

            self.router = router
            self.carrier = InlineCarrier()

    app = create_asgi_app(
        environ={API_TOKEN_VARIABLE: DEPLOYMENT_SECRET}, application=_Built()
    )
    return TestClient(app, raise_server_exceptions=False)


def _exchange(client: TestClient, login: str, password: str) -> str | None:
    """Sign in and return the credential, or ``None`` when the pair was refused."""
    response = client.post("/auth/token", json={"login": login, "password": password})
    return None if response.status_code != 200 else str(response.json()["token"])


def _change(client: TestClient, credential: str, current: str, new: str) -> object:
    return client.post(
        "/auth/password",
        headers={"Authorization": f"Bearer {credential}"},
        json={"current_password": current, "new_password": new},
    )


def _probe(client: TestClient, credential: str) -> int:
    """Present ``credential`` on a guarded operation and return the status.

    ``changePassword`` with a body this account's own password cannot satisfy: the seam runs
    before the handler, so a credential the seam refuses answers ``401`` without the port
    behind the operation ever being reached. A credential the seam *accepts* reaches the
    handler and is refused there for the password -- also ``401``, which would make the two
    indistinguishable, so the probe deliberately sends the **right** current password and a
    different new one and reads ``200`` as "the seam accepted this".
    """
    response = client.post(
        "/auth/password",
        headers={"Authorization": f"Bearer {credential}"},
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    return int(response.status_code)


# =======================================================================================
# The column, and what the repository does to it.
# =======================================================================================


def test_a_new_account_starts_at_the_initial_epoch(user: UserRecord) -> None:
    """One, and never zero: see the migration. A falsy epoch would be a readable-as-absent one."""
    assert user.token_epoch == 1
    assert user.token_epoch_updated_at is not None


def test_revoking_raises_the_epoch_and_dates_it(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    repository = UserRepository()
    with session_factory() as session:
        revoked = repository.revoke_credentials(session, login=user.login)
        session.commit()
    assert [record.login for record in revoked] == [user.login]
    assert revoked[0].token_epoch == user.token_epoch + 1
    assert revoked[0].token_epoch_updated_at >= user.token_epoch_updated_at


def test_revoking_an_unknown_login_is_a_fact_and_not_an_error(
    app_user_table: object, session_factory: sessionmaker[Session]
) -> None:
    """Empty means nothing matched. The caller decides whether that is a problem."""
    repository = UserRepository()
    with session_factory() as session:
        assert repository.revoke_credentials(session, login="w39rev-nobody-at-all") == ()
        session.commit()


def test_changing_the_password_raises_the_epoch_in_the_same_write(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """The property the whole operation exists for, asserted on the row rather than inferred.

    Two statements would leave a window in which the password is new and the old password's
    credentials still work. One UPDATE cannot.
    """
    repository = UserRepository()
    with session_factory() as session:
        changed = repository.change_password(
            session,
            user_uid=str(user.user_uid),
            current_password=PASSWORD,
            new_password=NEW_PASSWORD,
        )
        session.commit()
    assert changed is not None
    assert changed.token_epoch == user.token_epoch + 1
    assert changed.password_updated_at > user.password_updated_at


def test_changing_the_password_clears_the_default_credential_flag(
    app_user_table: object, session_factory: sessionmaker[Session]
) -> None:
    """`0006_app_user`'s own column comment, which until this wave had no code under it.

    *"Whoever changes the password sets this to false in the same statement."* Nothing could
    change a password at all before `W39-REVOKE`, so that sentence described an obligation
    with no implementation; this is the implementation and this is the assertion.

    **The account is created with the flag already TRUE, and that is the whole point of the
    fixture being local rather than the module's.** The first version of this check lived in
    ``test_changing_the_password_raises_the_epoch_in_the_same_write`` and read
    ``assert changed.is_default_credential is False`` against the shared ``user`` fixture --
    whose flag is ``False`` from the moment it is created. Mutating
    ``is_default_credential = false`` to ``is_default_credential = is_default_credential``
    in the UPDATE **reddened nothing**: 160 passed. The assertion was true either way, which
    is a coverage report and not a check.
    """
    login = f"w39rev-{secrets.token_hex(6)}"
    repository = UserRepository()
    with session_factory() as session:
        seeded = repository.create_user(
            session, login, PASSWORD, is_default_credential=True
        )
        session.commit()
    assert seeded.is_default_credential is True, "the fixture must start from a flagged row"
    try:
        with session_factory() as session:
            changed = repository.change_password(
                session,
                user_uid=str(seeded.user_uid),
                current_password=PASSWORD,
                new_password=NEW_PASSWORD,
            )
            session.commit()
        assert changed is not None
        assert changed.is_default_credential is False
        # And read back, not merely returned: the RETURNING clause and the row must agree.
        with session_factory() as session:
            again = repository.find_by_login(session, login)
            assert again is not None
            assert again.is_default_credential is False
            assert again.token_epoch == seeded.token_epoch + 1
    finally:
        with session_factory() as session:
            session.execute(
                text("DELETE FROM app_user WHERE login = :login"), {"login": login}
            )
            session.commit()


def test_the_old_password_stops_working_and_the_new_one_starts(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    repository = UserRepository()
    with session_factory() as session:
        assert (
            repository.change_password(
                session,
                user_uid=str(user.user_uid),
                current_password=PASSWORD,
                new_password=NEW_PASSWORD,
            )
            is not None
        )
        session.commit()
    with session_factory() as session:
        assert repository.authenticate(session, user.login, PASSWORD) is None
        assert repository.authenticate(session, user.login, NEW_PASSWORD) is not None


def test_a_wrong_current_password_changes_nothing(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    repository = UserRepository()
    with session_factory() as session:
        assert (
            repository.change_password(
                session,
                user_uid=str(user.user_uid),
                current_password="not-this-account's-password",
                new_password=NEW_PASSWORD,
            )
            is None
        )
        session.commit()
    with session_factory() as session:
        again = repository.find_by_login(session, user.login)
        assert again is not None
        # Neither half moved: not the digest, and -- the part a reader is likelier to miss
        # -- not the epoch. A refused change that revoked anyway would be a way to sign
        # somebody out by guessing at their password.
        assert again.token_epoch == user.token_epoch
        assert repository.authenticate(session, user.login, PASSWORD) is not None


def test_a_new_password_equal_to_the_current_one_is_refused_and_revokes_nothing(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    repository = UserRepository()
    with session_factory() as session:
        with pytest.raises(DomainError) as refused:
            repository.change_password(
                session,
                user_uid=str(user.user_uid),
                current_password=PASSWORD,
                new_password=PASSWORD,
            )
        session.rollback()
    assert refused.value.code is ErrorCode.VALIDATION_FAILED
    with session_factory() as session:
        again = repository.find_by_login(session, user.login)
        assert again is not None
        assert again.token_epoch == user.token_epoch


def test_an_account_that_is_gone_has_no_epoch(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """``None``, which the seam reads as a refusal -- so deleting a row revokes for free."""
    repository = UserRepository()
    with session_factory() as session:
        assert repository.token_epoch(session, str(user.user_uid)) == user.token_epoch
        session.execute(
            text("DELETE FROM app_user WHERE login = :login"), {"login": user.login}
        )
        session.commit()
    with session_factory() as session:
        assert repository.token_epoch(session, str(user.user_uid)) is None


def test_revocation_is_loud(
    user: UserRecord,
    session_factory: sessionmaker[Session],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An operator asking "when, and to whom?" must be able to read the answer in a log.

    Not suppressible and not rate-limited, for the same reason the default-credential
    warning is not: revocation is rare, irreversible for everyone holding a credential at
    that moment, and the question that follows it is always the same one.
    """
    repository = UserRepository()
    with caplog.at_level("WARNING"):
        with session_factory() as session:
            repository.revoke_credentials(session, login=user.login)
            session.commit()
    assert any(CREDENTIALS_REVOKED in record.getMessage() for record in caplog.records)
    assert any(user.login in record.getMessage() for record in caplog.records)


# =======================================================================================
# The seam, on a served request.
# =======================================================================================


def test_a_credential_stops_being_accepted_the_moment_the_account_is_revoked(
    client: TestClient, user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """The wave, in one assertion.

    The same credential, the same request, one statement in between. This is the thing that
    could not be done before `W39-REVOKE` at any price short of a redeploy.
    """
    credential = _exchange(client, user.login, PASSWORD)
    assert credential is not None
    assert _probe(client, credential) == 200

    # Re-exchange, because the probe above just changed the password and therefore revoked.
    credential = _exchange(client, user.login, NEW_PASSWORD)
    assert credential is not None

    with session_factory() as session:
        UserRepository().revoke_credentials(session, login=user.login)
        session.commit()

    response = client.post(
        "/auth/password",
        headers={"Authorization": f"Bearer {credential}"},
        json={"current_password": NEW_PASSWORD, "new_password": PASSWORD},
    )
    assert response.status_code == 401, response.text
    assert response.json()["error_code"] == "authentication_required"


def test_a_credential_minted_under_a_stale_epoch_is_refused(
    client: TestClient, user: UserRecord
) -> None:
    """Minted by hand at the wrong generation, so nothing else about it can be blamed.

    The signature is this deployment's, the expiry has not passed and the subject exists.
    The only thing wrong with it is the epoch, which is precisely what makes this a test of
    the epoch rather than of the signature.
    """
    signer = build_signer({API_TOKEN_VARIABLE: DEPLOYMENT_SECRET})
    assert signer is not None
    stale = signer.issue(
        Subject(
            user_uid=str(user.user_uid),
            login=user.login,
            token_epoch=user.token_epoch + 5,
        )
    ).token
    # Verified by the signer itself -- so the refusal below cannot be a malformed credential.
    assert signer.verify(stale) is not None
    assert _probe(client, stale) == 401


def test_a_credential_naming_no_account_is_refused(client: TestClient) -> None:
    """The property that makes deleting a row a revocation."""
    signer = build_signer({API_TOKEN_VARIABLE: DEPLOYMENT_SECRET})
    assert signer is not None
    orphan = signer.issue(
        Subject(
            user_uid="usr_01M2545JSD15ETSNNV904X9911",
            login="w39rev-never-existed",
            token_epoch=1,
        )
    ).token
    assert signer.verify(orphan) is not None
    assert _probe(client, orphan) == 401


def test_the_change_operation_hands_back_a_credential_that_works(
    client: TestClient, user: UserRecord
) -> None:
    """Succeeding must not sign the caller out, and the replacement proves the order.

    The credential presented is revoked by the very write that succeeded. If the adapter
    minted before the change, or from a record read before it, the replacement would carry
    the old epoch and the next request would answer 401 -- a password change that looks
    exactly like a broken one.
    """
    credential = _exchange(client, user.login, PASSWORD)
    assert credential is not None

    response = _change(client, credential, PASSWORD, NEW_PASSWORD)
    assert response.status_code == 200, response.text  # type: ignore[attr-defined]
    body = response.json()  # type: ignore[attr-defined]
    assert sorted(body) == ["expires_in", "token"], body
    replacement = body["token"]
    assert replacement != credential

    # The replacement works.
    assert (
        client.post(
            "/auth/password",
            headers={"Authorization": f"Bearer {replacement}"},
            json={"current_password": NEW_PASSWORD, "new_password": PASSWORD},
        ).status_code
        == 200
    )
    # And the one that was presented does not.
    assert _probe(client, credential) == 401


def test_the_operation_changes_the_callers_password_and_no_one_elses(
    client: TestClient, user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """There is no login in the body, so there is no account to aim it at but your own."""
    other_login = f"w39rev-{secrets.token_hex(6)}"
    repository = UserRepository()
    with session_factory() as session:
        other = repository.create_user(session, other_login, PASSWORD)
        session.commit()
    try:
        credential = _exchange(client, user.login, PASSWORD)
        assert credential is not None
        assert _change(client, credential, PASSWORD, NEW_PASSWORD).status_code == 200  # type: ignore[attr-defined]

        with session_factory() as session:
            untouched = repository.find_by_login(session, other_login)
            assert untouched is not None
            assert untouched.token_epoch == other.token_epoch
            assert repository.authenticate(session, other_login, PASSWORD) is not None
    finally:
        with session_factory() as session:
            session.execute(
                text("DELETE FROM app_user WHERE login = :login"), {"login": other_login}
            )
            session.commit()


def test_a_wrong_current_password_is_the_same_refusal_a_missing_credential_gets(
    client: TestClient, user: UserRecord
) -> None:
    """One answer, because "this deployment does not accept this" is one fact."""
    credential = _exchange(client, user.login, PASSWORD)
    assert credential is not None
    refused = _change(client, credential, "not-the-current-password", NEW_PASSWORD)
    assert refused.status_code == 401  # type: ignore[attr-defined]
    assert refused.json()["error_code"] == "authentication_required"  # type: ignore[attr-defined]

    absent = client.post(
        "/auth/password",
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert absent.status_code == 401
    assert absent.json()["error_code"] == "authentication_required"


def test_a_new_password_equal_to_the_current_one_is_validation_and_not_refusal(
    client: TestClient, user: UserRecord
) -> None:
    """A statement about the request, reported only to somebody who proved the current one."""
    credential = _exchange(client, user.login, PASSWORD)
    assert credential is not None
    response = _change(client, credential, PASSWORD, PASSWORD)
    assert response.status_code == 422, response.text  # type: ignore[attr-defined]
    assert response.json()["error_code"] == "validation_failed"  # type: ignore[attr-defined]
    # And nothing was revoked by the refusal: the credential still works.
    assert _probe(client, credential) == 200


def test_no_password_reaches_the_answer_or_the_credential(
    client: TestClient, user: UserRecord
) -> None:
    credential = _exchange(client, user.login, PASSWORD)
    assert credential is not None
    response = _change(client, credential, PASSWORD, NEW_PASSWORD)
    rendered = response.text + "".join(  # type: ignore[attr-defined]
        f"{name}: {value}" for name, value in response.headers.items()  # type: ignore[attr-defined]
    )
    assert PASSWORD not in rendered
    assert NEW_PASSWORD not in rendered
    assert DEPLOYMENT_SECRET not in rendered
    # The replacement is a credential, not a transcript: the payload names the subject and
    # the epoch and carries nothing a password could be read out of.
    signer = build_signer({API_TOKEN_VARIABLE: DEPLOYMENT_SECRET})
    assert signer is not None
    subject = signer.verify(response.json()["token"])  # type: ignore[attr-defined]
    assert subject is not None
    assert subject.user_uid == str(user.user_uid)


# =======================================================================================
# The operator command.
# =======================================================================================


def _run_revoke(*arguments: str) -> subprocess.CompletedProcess[str]:
    """Run the command as an operator runs it: a subprocess, reading its own environment."""
    tree = _tree_under_test()
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(tree / "src")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "auditmanager.access.revoke", *arguments],
        cwd=tree,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_the_command_revokes_one_account_and_says_which(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    result = _run_revoke("--login", user.login)
    assert result.returncode == 0, result.stderr
    assert REVOKED_PREFIX in result.stdout
    assert user.login in result.stdout
    with session_factory() as session:
        again = UserRepository().find_by_login(session, user.login)
        assert again is not None
        assert again.token_epoch == user.token_epoch + 1


def test_the_command_reports_matching_nothing_as_its_own_status(
    app_user_table: object,
) -> None:
    """``1`` and not ``0``. ``--login typo`` must not look like a revocation that happened."""
    result = _run_revoke("--login", f"w39rev-{secrets.token_hex(6)}")
    assert result.returncode == 1, result.stdout + result.stderr
    assert NOTHING_SENTINEL in result.stdout


def test_the_command_refuses_to_run_with_no_target(app_user_table: object) -> None:
    """Neither default is defensible: see the module note. Nothing happened, and it exits 2.

    ``--everyone`` is deliberately **not** driven anywhere in this suite. It is correct, it
    is covered by ``revoke_credentials(login=None)`` at the repository level, and running it
    here would raise the epoch of every account in a shared lane -- including the seeded
    ``admin`` and including whatever another live suite is holding a credential for.
    `OPERATING_CONSTRAINTS.md` §6.
    """
    result = _run_revoke()
    assert result.returncode == 2, result.stdout + result.stderr
    assert "--everyone" in result.stderr
