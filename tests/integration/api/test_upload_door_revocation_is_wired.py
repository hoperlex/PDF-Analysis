"""`D-176` -- the revocation memory is wired into the served application, end to end.

`ACCESS-STORAGE-HARDEN-01` built :class:`~auditmanager.api.security.RevocationNotices` and proved
its parts against a stub account. Nothing proved the memory reaches the application that is
actually served, because ``api/app.py`` did not pass it to either builder. This file drives the
**assembled** application (:func:`~auditmanager.api.app.create_asgi_app`) over real accounts in a
real PostgreSQL and asserts the two halves of the door's promise:

* **the first upload under a credential the account has since revoked may still have its body
  read** -- the door checks a signature and an expiry and no database, so it cannot know; the
  seam then reads the row, refuses, and writes the (user, epoch) pair down;
* **every later one is refused before its body is read and without a database read** -- the
  application never asks the client for a byte of the body, the account port is not called, and
  not one SQL statement reaches the database.

How "no read" is asserted, and why it can fail. The body: the test calls the application as a
bare ASGI callable and counts how many times it asked ``receive`` for the request body; a
refusal at the door answers without ever calling it. The database: the account port is wrapped by
a counter *and* a SQLAlchemy ``before_cursor_execute`` listener counts every statement the engine
runs, so a read that bypassed the port would still show. Both counters are asserted to be positive
on the first, admitted-then-refused attempt, which proves they can see a read at all.

Every account is real: created through ``access``, signed in through ``POST /auth/token``, archived
or revoked through the repositories the operators use. Each application gets its own cloned database
(``tests/integration/db/conftest.py``), dropped afterwards.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Iterator
from contextlib import ExitStack
from dataclasses import dataclass, field
from typing import Any

import pytest
from sqlalchemy import Engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient

from auditmanager.access.public import AccountRepository, UserRepository
from auditmanager.api.app import create_asgi_app
from auditmanager.api.routers import build_router
from auditmanager.api.security import API_TOKEN_VARIABLE, Subject, build_signer
from auditmanager.bootstrap.adapters import CredentialAdapter
from auditmanager.runs import InlineCarrier
from auditmanager.shared.db.config import DatabaseSettings
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.db.session import create_session_factory
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.db.conftest import (  # type: ignore[import-not-found]  # noqa: F401
    configured_settings,
    maintenance_engine,
    migrated_database_factory,
    migrated_template,
)

SECRET = "d-176-wiring-deployment-secret"
ENVIRON = {API_TOKEN_VARIABLE: SECRET}
PASSWORD = "a-long-enough-password"  # noqa: S105 - a test literal
PROJECT = "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV"
UPLOAD = f"/projects/{PROJECT}/documents"
BOUNDARY = "d176wiringboundary"
BODY = (
    f"--{BOUNDARY}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"a.pdf\"\r\n"
    f"Content-Type: application/pdf\r\n\r\n%PDF-1.7\r\n--{BOUNDARY}--\r\n"
).encode()

users = UserRepository()
accounts = AccountRepository()


# --- the application under test ---------------------------------------------------------------


class _Documents:
    """The one port an admitted upload reaches. Answers ``not_found`` and records the call.

    ``not_found`` is the natural answer of a documents port to a project it does not hold, and it
    is distinguishable from the seam's ``401``: the status alone tells "admitted" from "refused".
    """

    def __init__(self) -> None:
        self.calls = 0

    def upload_document(self, **_: Any) -> Any:
        self.calls += 1
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Project")

    def __getattr__(self, name: str) -> Any:  # pragma: no cover - never called
        """Any other ``DocumentPort`` method is an operation this file never drives.

        ``tests/integration/composition/test_every_port_implementation_is_whole.py`` (`D-74`)
        reads every ``build_router(documents=...)`` in the tree and requires the class behind it
        to carry the whole port, except a stand-in that answers to any attribute with a refusal
        (a class with ``__getattr__`` "cannot be caught out by a missing method"). This stand-in
        drives ``upload_document`` and nothing else, so it says so: a request that reaches another
        operation fails loudly here instead of becoming an ``AttributeError`` behind a ``500``.
        """
        raise AssertionError(f"the D-176 wiring test does not drive DocumentPort.{name}")


class _CountingCredentials:
    """The shipped credential adapter, plus a count of the account reads the seam makes."""

    def __init__(self, inner: CredentialAdapter) -> None:
        self._inner = inner
        self.standing_reads = 0

    def standing_of(self, user_uid: str) -> Any:
        self.standing_reads += 1
        return self._inner.standing_of(user_uid)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _Built:
    """What ``create_asgi_app`` reads off a built application, and nothing more."""

    def __init__(self, router: Any) -> None:
        self.router = router
        self.carrier = InlineCarrier()


@dataclass
class Served:
    """One assembled application over one cloned database, and what it did."""

    app: Any
    engine: Engine
    factory: sessionmaker[Session]
    documents: _Documents
    credentials: _CountingCredentials
    statements: list[str] = field(default_factory=list)

    def session(self) -> Session:
        return self.factory()


@dataclass(frozen=True)
class Sent:
    status: int
    envelope: dict[str, Any]
    body_reads: int  # how many times the application asked for the request body


def _upload(app: Any, token: str) -> Sent:
    """One ``uploadDocument`` call as a bare ASGI callable, counting how often the body is asked for."""
    headers = [
        (b"host", b"testserver"),
        (b"content-type", f"multipart/form-data; boundary={BOUNDARY}".encode()),
        (b"content-length", str(len(BODY)).encode()),
        (b"authorization", f"Bearer {token}".encode()),
        (b"idempotency-key", b"d176-wiring-0001"),
    ]
    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST",
        "scheme": "http", "path": UPLOAD, "raw_path": UPLOAD.encode(), "root_path": "",
        "query_string": b"", "headers": headers, "server": ("testserver", 80),
        "client": ("testclient", 50000),
    }
    reads = 0
    delivered = False
    status = 0
    chunks: list[bytes] = []

    async def receive() -> dict[str, Any]:
        nonlocal reads, delivered
        if delivered:
            return {"type": "http.disconnect"}
        delivered = True
        reads += 1
        return {"type": "http.request", "body": BODY, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        nonlocal status
        if message["type"] == "http.response.start":
            status = message["status"]
        elif message["type"] == "http.response.body":
            chunks.append(message.get("body", b""))

    asyncio.run(asyncio.wait_for(app(scope, receive, send), 30))
    raw = b"".join(chunks)
    return Sent(status, json.loads(raw) if raw else {}, reads)


@pytest.fixture
def serve(
    migrated_database_factory: Callable[[], DatabaseSettings],
) -> Iterator[Callable[[], Served]]:
    """Assemble the served application over a fresh clone of the migrated template, any number of times."""
    stack = ExitStack()

    def build() -> Served:
        engine = create_database_engine(migrated_database_factory())
        stack.callback(engine.dispose)
        factory = create_session_factory(engine)
        signer = build_signer(ENVIRON)
        assert signer is not None
        credentials = _CountingCredentials(
            CredentialAdapter(factory, users=users, accounts=accounts, signer=signer)
        )
        documents = _Documents()
        router = build_router(
            projects=None,  # type: ignore[arg-type]
            documents=documents,  # type: ignore[arg-type]
            runs=None,  # type: ignore[arg-type]
            findings=None,  # type: ignore[arg-type]
            decisions=None,  # type: ignore[arg-type]
            exports=None,  # type: ignore[arg-type]
            credentials=credentials,  # type: ignore[arg-type]
        )
        served = Served(
            app=create_asgi_app(environ=ENVIRON, application=_Built(router)),
            engine=engine, factory=factory, documents=documents, credentials=credentials,
        )

        def count(connection: Any, cursor: Any, statement: str, *_: Any) -> None:
            served.statements.append(statement)

        event.listen(engine, "before_cursor_execute", count)
        return served

    try:
        yield build
    finally:
        stack.close()


# --- the accounts -----------------------------------------------------------------------------


def _expert(served: Served, email: str) -> str:
    """A complete ``expert`` account; its user uid."""
    with served.session() as session:
        uid = str(users.create_user(session, email, PASSWORD).user_uid)
        accounts.complete_profile(
            session, user_uid=uid, email=None, last_name="Петрова", first_name="Анна"
        )
        accounts.grant_role(session, user_uid=uid, role="expert", granted_by=None)
        session.commit()
    return uid


def _sign_in(served: Served, email: str) -> str:
    """The credential the account obtains from the real exchange."""
    response = TestClient(served.app, raise_server_exceptions=False).post(
        "/auth/token", json={"login": email, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return str(response.json()["token"])


def _archive(served: Served, uid: str) -> None:
    with served.session() as session:
        actor = users.find_by_login(session, "admin")
        assert actor is not None
        accounts.archive_account(session, actor_uid=str(actor.user_uid), user_uid=uid)
        session.commit()


def _raise_epoch(served: Served, email: str) -> None:
    with served.session() as session:
        assert len(users.revoke_credentials(session, login=email)) == 1
        session.commit()


REVOCATIONS: dict[str, Callable[[Served, str, str], None]] = {
    "the account is archived": lambda served, uid, email: _archive(served, uid),
    "the credential epoch is raised": lambda served, uid, email: _raise_epoch(served, email),
}


# --- the door's promise, end to end -------------------------------------------------------------


@pytest.mark.parametrize("revoke", list(REVOCATIONS), ids=list(REVOCATIONS))
def test_a_revoked_credentials_later_uploads_are_refused_before_the_body_and_without_a_read(
    serve: Callable[[], Served], revoke: str
) -> None:
    served = serve()
    holder_uid = _expert(served, "holder@example.com")
    other_uid = _expert(served, "bystander@example.com")
    assert holder_uid != other_uid
    held = _sign_in(served, "holder@example.com")
    bystander = _sign_in(served, "bystander@example.com")

    # Before anything is revoked the credential works: the door and the seam admit it and the
    # port is reached. (Without this the refusals below could be a broken fixture.)
    admitted = _upload(served.app, held)
    assert (admitted.status, admitted.envelope["error_code"]) == (404, "not_found")
    assert served.documents.calls == 1 and admitted.body_reads >= 1
    # So does the bystander's, twice: nothing the seam admits is ever written down.
    for _ in range(2):
        untouched = _upload(served.app, bystander)
        assert (untouched.status, untouched.envelope["error_code"]) == (404, "not_found")
        assert untouched.body_reads >= 1
    assert served.documents.calls == 3

    REVOCATIONS[revoke](served, holder_uid, "holder@example.com")
    calls, reads, statements = served.documents.calls, served.credentials.standing_reads, len(served.statements)

    # The first attempt under the revoked credential: the door cannot know. It admits it, so the
    # body IS asked for; the seam reads the account, refuses, and notes the pair.
    first = _upload(served.app, held)
    assert (first.status, first.envelope["error_code"]) == (401, "authentication_required")
    assert first.body_reads >= 1, "the door was expected not to know yet"
    assert served.credentials.standing_reads == reads + 1, "the seam must have read the account"
    assert len(served.statements) > statements, "the statement counter must be able to see a read"
    assert served.documents.calls == calls
    reads, statements = served.credentials.standing_reads, len(served.statements)

    # Every later attempt: refused before one byte of the body is asked for, with the same
    # answer, and with no read of any kind -- not the account port, not a single statement.
    for attempt in range(3):
        later = _upload(served.app, held)
        assert (later.status, later.envelope["error_code"]) == (401, "authentication_required")
        assert later.body_reads == 0, f"attempt {attempt + 2}: the door asked for a revoked credential's body"
        assert served.credentials.standing_reads == reads, f"attempt {attempt + 2}: the account was read"
        assert len(served.statements) == statements, (
            f"attempt {attempt + 2}: the database was touched: {served.statements[statements:]}"
        )
        assert served.documents.calls == calls
        assert later.envelope["message"] == first.envelope["message"], "the two refusals differ"

    # An account nobody revoked is unaffected, before and after the others were refused.
    still = _upload(served.app, bystander)
    assert (still.status, still.envelope["error_code"]) == (404, "not_found")
    assert still.body_reads >= 1 and served.documents.calls == calls + 1
    assert _upload(served.app, bystander).body_reads >= 1 and served.documents.calls == calls + 2


def test_a_later_generation_of_the_same_account_is_not_caught_by_the_old_entry(
    serve: Callable[[], Served]
) -> None:
    served = serve()
    _expert(served, "renewed@example.com")
    stale = _sign_in(served, "renewed@example.com")
    _raise_epoch(served, "renewed@example.com")

    assert _upload(served.app, stale).status == 401  # noted
    assert _upload(served.app, stale).body_reads == 0  # refused at the door

    renewed = _sign_in(served, "renewed@example.com")  # a new generation of the same account
    admitted = _upload(served.app, renewed)
    assert (admitted.status, admitted.envelope["error_code"]) == (404, "not_found")
    assert admitted.body_reads >= 1 and served.documents.calls == 1
    assert _upload(served.app, stale).body_reads == 0, "the old generation is still refused"


def test_a_credential_that_signs_but_names_no_account_is_noted_after_its_first_refusal(
    serve: Callable[[], Served]
) -> None:
    """A deleted account's credential: no row at all, the third refusal the seam notes."""
    served = serve()
    _expert(served, "deleted@example.com")
    held = _sign_in(served, "deleted@example.com")
    with served.session() as session:
        session.execute(text("DELETE FROM app_user WHERE login = 'deleted@example.com'"))
        session.commit()

    assert _upload(served.app, held).body_reads >= 1
    reads, statements = served.credentials.standing_reads, len(served.statements)
    later = _upload(served.app, held)
    assert (later.status, later.body_reads) == (401, 0)
    assert (served.credentials.standing_reads, len(served.statements)) == (reads, statements)


# --- per application, not per process -------------------------------------------------------------


def test_two_applications_in_one_process_do_not_share_what_either_has_learned(
    serve: Callable[[], Served]
) -> None:
    """Clones of one migrated template share their seeded account's ``user_uid`` and epoch, so a
    process-wide memory would carry one database's revocation into the other's. The same signed
    credential is therefore valid in both applications until one of them revokes it."""
    one, two = serve(), serve()
    renamed = "seeded.admin@example.com"  # completing the profile makes the e-mail the login
    for served in (one, two):
        with served.session() as session:
            seeded = users.find_by_login(session, "admin")
            assert seeded is not None
            uid = str(seeded.user_uid)
            accounts.complete_profile(
                session, user_uid=uid, email=renamed, last_name="Иванов", first_name="Пётр"
            )
            # The seeded password is public; a seeded account on it reaches almost nothing.
            session.execute(
                text("UPDATE app_user SET is_default_credential = false WHERE user_uid = :uid"),
                {"uid": uid},
            )
            session.commit()
    with one.session() as session, two.session() as other:
        a, b = users.find_by_login(session, renamed), users.find_by_login(other, renamed)
        assert a is not None and b is not None
        assert (a.user_uid, a.token_epoch) == (b.user_uid, b.token_epoch), "the premise of the test"
        subject = Subject(
            user_uid=str(a.user_uid), login=a.login, token_epoch=a.token_epoch,
            display_label=a.display_label,
        )
    signer = build_signer(ENVIRON)
    assert signer is not None
    shared = signer.issue(subject, is_default_credential=False).token

    # Admitted by both while it is valid in both.
    for served in (one, two):
        sent = _upload(served.app, shared)
        assert (sent.status, sent.envelope["error_code"]) == (404, "not_found"), sent
        assert served.documents.calls == 1

    # Revoked in the first database only.
    with one.session() as session:
        assert len(users.revoke_credentials(session, login=renamed)) == 1
        session.commit()
    assert _upload(one.app, shared).status == 401
    assert _upload(one.app, shared).body_reads == 0, "the first application has learned it"

    # The second application knows nothing of that: its door admits the credential (its body is
    # asked for) and its account still accepts it.
    other_sent = _upload(two.app, shared)
    assert (other_sent.status, other_sent.envelope["error_code"]) == (404, "not_found")
    assert other_sent.body_reads >= 1, "the second application's door was told about the first's database"
    assert two.documents.calls == 2

    # And it learns for itself, from its own database, only when that revokes the credential.
    with two.session() as session:
        assert len(users.revoke_credentials(session, login=renamed)) == 1
        session.commit()
    assert _upload(two.app, shared).body_reads >= 1, "the first attempt in this application"
    assert _upload(two.app, shared).body_reads == 0
