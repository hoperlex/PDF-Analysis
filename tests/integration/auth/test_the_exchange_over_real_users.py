"""The exchange, end to end: a row in ``app_user``, a password, a credential, the seam.

This is where the three parts of wave 34 meet, and it is the only suite in which all
three are real at once: `W34-DOM`'s repository and its PBKDF2 digest, `W34-API`'s adapter
and signer, and the served operation `W34-CONTRACT` declared. Everything else about the
exchange is asserted against fakes somewhere, on purpose -- and a fake can agree with
another fake forever.

**This suite needs `W34-DOM` merged.** It imports ``auditmanager.access`` and reads
``app_user``; on a checkout of ``agent/w34-api`` alone it fails at import, which is the
honest reading of "the exchange has nothing to authenticate against". It does not skip:
the wave's whole claim is that these two halves fit, and a suite that skipped would report
success for a tree in which they do not.
"""

from __future__ import annotations

import json
import secrets
from collections.abc import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient

from auditmanager.access.models import UserRecord
from auditmanager.access.repository import UserRepository
from auditmanager.api.app import create_asgi_app
from auditmanager.api.routers import build_router
from auditmanager.api.security import API_TOKEN_VARIABLE, build_signer
from auditmanager.bootstrap.adapters import CredentialAdapter

#: This suite's deployment secret. Not a credential -- the key the credential is signed
#: with is derived from it, and presenting it is one of the refusals asserted below.
DEPLOYMENT_SECRET = "w34-auth-suite-deployment-secret"

#: The password the created account holds. Distinctive enough that finding it in a
#: response body or a log line means something.
PASSWORD = "correct-horse-battery-staple-4471"


@pytest.fixture
def user(
    app_user_table: object, session_factory: sessionmaker[Session]
) -> Iterator[UserRecord]:
    """One real account, created through the repository and removed afterwards.

    The login is randomised so two runs, or two lanes sharing a database, cannot collide
    on the UNIQUE constraint -- and so that no test here can accidentally depend on the
    seeded ``admin`` account, whose password is published in a migration.
    """
    login = f"w34auth-{secrets.token_hex(6)}"
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
    """The served surface, with the exchange wired exactly as the composition root wires it.

    The other six ports are ``None``: this suite drives one operation, and a port it never
    calls is a dependency it would otherwise have to build a database fixture for. The
    seam itself is the application's, through ``create_asgi_app``.
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


def _exchange(client: TestClient, login: str, password: str) -> object:
    return client.post("/auth/token", json={"login": login, "password": password})


def test_a_real_pair_is_exchanged_for_a_credential_naming_that_user(
    client: TestClient, user: UserRecord
) -> None:
    """The wave, in one assertion: the row, the password, the credential, the subject.

    The credential is not compared to a literal -- it is *verified*, with the same key the
    application signed it with, and the subject that comes back is the ``user_uid`` the
    repository allocated for this account.
    """
    response = _exchange(client, user.login, PASSWORD)
    assert response.status_code == 200, response.text
    body = response.json()
    assert sorted(body) == ["expires_in", "token"], body
    assert body["expires_in"] == 3600

    signer = build_signer({API_TOKEN_VARIABLE: DEPLOYMENT_SECRET})
    assert signer is not None
    subject = signer.verify(body["token"])
    assert subject is not None
    assert subject.user_uid == str(user.user_uid)
    assert subject.login == user.login


def test_the_login_is_folded_the_way_the_repository_folds_it(
    client: TestClient, user: UserRecord
) -> None:
    """``" ADA "`` and ``"ada"`` are one account, and the exchange does not decide that.

    The folding rule belongs to `W34-DOM`'s ``normalize_login`` and is asserted there. What
    is asserted here is that the exchange passes the login through to it rather than
    comparing strings itself -- which is what would make the API a second place the rule
    lives.
    """
    response = _exchange(client, f"  {user.login.upper()}  ", PASSWORD)
    assert response.status_code == 200, response.text


@pytest.mark.parametrize(
    "label",
    ["the right login and a wrong password", "a login with no row", "a login of the wrong shape"],
)
def test_every_refusal_is_the_same_refusal(
    client: TestClient, user: UserRecord, label: str
) -> None:
    """401 ``authentication_required``, identical for all three.

    "No such user", "wrong password" and "that could not be a login" are three different
    facts about this deployment, and a caller who learns which one it was can enumerate
    accounts with a form and a list of names.
    """
    pair = {
        "the right login and a wrong password": (user.login, "not-the-password"),
        "a login with no row": (f"w34auth-{secrets.token_hex(6)}", PASSWORD),
        "a login of the wrong shape": ("Not A Login!", PASSWORD),
    }[label]
    response = _exchange(client, *pair)
    assert response.status_code == 401, (label, response.text)
    envelope = response.json()
    assert envelope["error_code"] == "authentication_required", envelope
    assert envelope["retryable"] is False, envelope
    assert envelope["contract_version"] == "1.0.0-draft.1", envelope
    assert response.headers["X-Correlation-Id"]
    # The envelope is the catalog's, not a story about what went wrong.
    assert user.login not in response.text, response.text


def test_nothing_of_the_request_comes_back_in_any_answer(
    client: TestClient, user: UserRecord
) -> None:
    """The password appears in no body, on either outcome. Asserted on the bytes."""
    for password in (PASSWORD, "another-password-entirely-91823"):
        response = _exchange(client, user.login, password)
        assert PASSWORD not in response.text, response.text
        assert password not in response.text, response.text


def test_no_digest_or_salt_can_reach_the_caller(
    client: TestClient, user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """The stored credential material, read directly, and searched for in the response.

    `W34-DOM`'s port cannot return a digest, so this cannot fail by construction -- which
    is exactly why it is worth one test: the day somebody widens that port, this is the
    assertion that notices the widening reached the wire.
    """
    with session_factory() as session:
        stored = session.execute(
            text(
                "SELECT password_salt, password_hash FROM app_user WHERE login = :login"
            ),
            {"login": user.login},
        ).one()
    salt, digest = stored

    response = _exchange(client, user.login, PASSWORD)
    assert response.status_code == 200, response.text
    assert salt not in response.text
    assert digest not in response.text


def test_the_deployment_secret_is_not_accepted_as_a_credential_by_this_application(
    client: TestClient, user: UserRecord
) -> None:
    """The alpha's static token, against a fully wired exchange.

    The minted credential is what the seam accepts; the configured secret is not. Both
    halves are asserted here rather than one, because "the new thing works" and "the old
    thing stopped working" are two claims and only one of them is about a replacement.
    """
    minted = _exchange(client, user.login, PASSWORD).json()["token"]
    signer = build_signer({API_TOKEN_VARIABLE: DEPLOYMENT_SECRET})
    assert signer is not None
    assert signer.verify(minted) is not None
    assert signer.verify(DEPLOYMENT_SECRET) is None


def test_two_exchanges_are_two_credentials_and_not_a_replay(
    client: TestClient, user: UserRecord
) -> None:
    """No ``Idempotency-Key``, and no recorded outcome to replay.

    Nothing is created, so the second exchange is a second exchange. The two credentials
    may be equal only because they were minted in the same whole second; what must not
    happen is a 409, a stored outcome, or a refusal to exchange twice.
    """
    first = _exchange(client, user.login, PASSWORD)
    second = _exchange(client, user.login, PASSWORD)
    assert first.status_code == 200 and second.status_code == 200
    signer = build_signer({API_TOKEN_VARIABLE: DEPLOYMENT_SECRET})
    assert signer is not None
    assert signer.verify(second.json()["token"]) == signer.verify(first.json()["token"])


def test_a_body_the_contract_refuses_never_reaches_the_repository(
    client: TestClient, user: UserRecord
) -> None:
    """422 before a database read, for each way the declared body can be wrong.

    Asserted through the answer rather than by counting queries: ``validation_failed`` is
    a statement about the *request*, and ``authentication_required`` would be a statement
    about the *deployment's user table* -- which this request never got far enough to be
    about.
    """
    for body in (
        {"login": user.login},
        {"password": PASSWORD},
        {"login": user.login, "password": PASSWORD, "extra": 1},
        {"login": "", "password": PASSWORD},
        {"login": user.login, "password": ""},
        {"login": user.login, "password": "x" * 1025},
    ):
        response = client.post("/auth/token", json=body)
        assert response.status_code == 422, (body, response.text)
        assert response.json()["error_code"] == "validation_failed", response.text


def test_the_exchange_needs_no_credential_of_its_own(
    client: TestClient, user: UserRecord
) -> None:
    """No ``Authorization`` header anywhere above, stated once as its own assertion.

    Every request in this suite is anonymous; this is the test that says so on purpose, so
    that the property survives somebody adding a default header to the client fixture.
    """
    request = client.build_request("POST", "/auth/token", json={"login": "x", "password": "y"})
    assert "authorization" not in {name.lower() for name in request.headers}

    with_credential = client.post(
        "/auth/token",
        json={"login": user.login, "password": PASSWORD},
        headers={"Authorization": "Bearer not-a-credential-at-all"},
    )
    # A credential that is presented anyway is neither required nor honoured: the exchange
    # is open, so a nonsense one cannot turn a valid pair into a refusal.
    assert with_credential.status_code == 200, with_credential.text
    assert json.loads(with_credential.text)["expires_in"] == 3600
