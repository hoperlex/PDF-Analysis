"""`D-176` -- the upload front door and the seam read one credential, and learn what it refuses.

Two defects of one door (``BodyCapMiddleware``'s ``verify_credential``, `W55B-FIX` X-3):

1. **Header order.** The door read the *last* ``Authorization`` and ``Content-Type`` of a request
   where Starlette -- the seam's ``HTTPBearer``, the form parser, FastAPI's choice of body
   reader -- reads the *first* (``Headers.__getitem__``). A request with two of either was judged
   on one credential or media type and served on the other. Now both read the first.
2. **Revocation.** The door checks a signature and an expiry and no database, so an account's
   revoked, archived or deleted credential passed it for up to an hour and had its body read
   before the seam's ``401``. ``RevocationNotices`` is the database-free memory the seam fills
   when the account's standing refuses a pair and the door consults; one instance is passed to
   both builders.

No database is used: the account is a stub that counts how often it is asked, because "the door
reads no database" is the property under test and a counter proves it where a real table
cannot.
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi import FastAPI, File, UploadFile
from starlette.datastructures import Headers
from starlette.testclient import TestClient

from auditmanager.api.routers import install_exception_handlers
from auditmanager.api.routers.correlation import CorrelationMiddleware
from auditmanager.api.routers.multipart import BodyCapMiddleware
from auditmanager.api.security import (
    API_TOKEN_VARIABLE,
    AccountStanding,
    RevocationNotices,
    Subject,
    build_authorization_dependency,
    build_credential_precheck,
    build_signer,
)

ENVIRON = {API_TOKEN_VARIABLE: "d-176-deployment-secret"}
UPLOAD = "/projects/prj_01ARZ3NDEKTSV4RRFFQ69G5FAV/documents"
BOUNDARY = "d176boundary"
MULTIPART = f"multipart/form-data; boundary={BOUNDARY}"
JSON = "application/json"
UID = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
BODY = (
    f"--{BOUNDARY}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"a.pdf\"\r\n"
    f"Content-Type: application/pdf\r\n\r\n%PDF-1.7\r\n--{BOUNDARY}--\r\n"
).encode()


def _credential(epoch: int = 1, *, environ: dict[str, str] = ENVIRON) -> str:
    signer = build_signer(environ)
    assert signer is not None
    subject = Subject(user_uid=UID, login="a@example.com", token_epoch=epoch, display_label="A")
    return signer.issue(subject, is_default_credential=False).token


def _bearer(token: str) -> str:
    return f"Bearer {token}"


# --- the door alone: which header it reads ----------------------------------------------------


class _Inner:
    """The application behind the door: records whether the request reached it."""

    def __init__(self) -> None:
        self.reached = 0
        self.body_bytes = 0

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        self.reached += 1
        while True:
            message = await receive()
            if message["type"] != "http.request":
                break
            self.body_bytes += len(message.get("body", b""))
            if not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})


@dataclass
class _Answer:
    status: int | None = None
    headers: list[tuple[bytes, bytes]] = field(default_factory=list)


def _drive(door: Any, headers: list[tuple[bytes, bytes]], body: bytes = BODY) -> _Answer:
    answer = _Answer()
    sent = False

    async def receive() -> dict[str, Any]:
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        if message["type"] == "http.response.start":
            answer.status = message["status"]

    scope = {
        "type": "http", "method": "POST", "path": UPLOAD, "root_path": "", "query_string": b"",
        "headers": headers,
    }

    async def go() -> None:
        # The door's refusal envelope reads the correlation id, so it sits behind the same
        # outer layer the application puts there.
        await CorrelationMiddleware(door)(scope, receive, send)

    asyncio.run(asyncio.wait_for(go(), 20))
    return answer


def _spying_door(inner: _Inner) -> tuple[BodyCapMiddleware, list[str]]:
    presented: list[str] = []

    def verify(token: str) -> bool:
        presented.append(token)
        return token == "good"

    return BodyCapMiddleware(inner, verify_credential=verify), presented


def _h(name: str, value: str) -> tuple[bytes, bytes]:
    return name.encode(), value.encode("latin-1")


@pytest.mark.parametrize(
    ("order", "expected_status", "reaches"),
    [
        (("Bearer good", "Bearer forged"), 204, 1),
        (("Bearer forged", "Bearer good"), 401, 0),
    ],
    ids=["a signed first credential behind a forged one", "a forged first behind a signed one"],
)
def test_the_door_judges_the_first_authorization_header_as_starlette_reads_it(
    order: tuple[str, str], expected_status: int, reaches: int
) -> None:
    inner = _Inner()
    door, presented = _spying_door(inner)
    headers = [_h("content-type", MULTIPART), _h("authorization", order[0]), _h("authorization", order[1])]

    answer = _drive(door, headers)

    # The premise, stated against the library rather than assumed: Starlette reads the first.
    starlette_reads = Headers(raw=headers).get("authorization")
    assert starlette_reads == order[0]
    assert presented == [order[0].removeprefix("Bearer ")], "the door verified a different header"
    assert (answer.status, inner.reached) == (expected_status, reaches)
    if reaches == 0:
        assert inner.body_bytes == 0, "a refused credential had its body read"


@pytest.mark.parametrize(
    ("first", "second", "multipart_is_read"),
    [(MULTIPART, JSON, True), (JSON, MULTIPART, False)],
    ids=["multipart first", "json first"],
)
def test_the_door_judges_the_first_content_type_header_as_starlette_reads_it(
    first: str, second: str, multipart_is_read: bool
) -> None:
    """A body is read as a form only when the *first* ``Content-Type`` says so. Otherwise the
    application is handed an empty body, as for any non-multipart upload."""
    inner = _Inner()
    door, _ = _spying_door(inner)
    headers = [
        _h("content-type", first), _h("content-type", second), _h("authorization", "Bearer good")
    ]

    answer = _drive(door, headers)

    assert Headers(raw=headers).get("content-type") == first
    assert answer.status == 204 and inner.reached == 1
    assert (inner.body_bytes > 0) is multipart_is_read, (first, second, inner.body_bytes)
    assert door.gate.in_flight == 0


def test_a_single_header_is_read_as_before() -> None:
    inner = _Inner()
    door, presented = _spying_door(inner)
    answer = _drive(door, [_h("content-type", MULTIPART), _h("authorization", "Bearer good")])
    assert (answer.status, inner.reached, presented) == (204, 1, ["good"])


# --- the same, through the real seam ----------------------------------------------------------


@dataclass
class _Standings:
    """The account, as the seam reads it. Counts the reads: the door must make none."""

    epoch: int = 1
    archived: bool = False
    exists: bool = True
    reads: int = 0

    def standing_of(self, user_uid: str) -> AccountStanding | None:
        self.reads += 1
        if not self.exists or user_uid != UID:
            return None
        return AccountStanding(
            token_epoch=self.epoch,
            is_default_credential=False,
            archived=self.archived,
            profile_complete=True,
            roles=frozenset({"expert"}),
            login="a@example.com",
            display_label="A",
        )


@dataclass
class _Record:
    reached: int = 0
    body_bytes: int = 0


class _Behind:
    """Sits just behind the door (inside it) and records what got through."""

    def __init__(self, app: Any, record: _Record) -> None:
        self.app = app
        self.record = record

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        self.record.reached += 1

        async def counted() -> Any:
            message = await receive()
            if message["type"] == "http.request":
                self.record.body_bytes += len(message.get("body", b""))
            return message

        await self.app(scope, counted, send)


def _served(standings: _Standings, notices: RevocationNotices | None) -> tuple[TestClient, _Record]:
    app = FastAPI(
        dependencies=[build_authorization_dependency(ENVIRON, standings=standings, notices=notices)]
    )

    @app.post("/projects/{project_uid}/documents", operation_id="uploadDocument")
    async def upload(project_uid: str, file: UploadFile = File(...)) -> dict[str, bool]:
        return {"ok": True}

    install_exception_handlers(app)
    record = _Record()
    # `add_middleware` puts the last one added outermost: the recorder is innermost, then the
    # door, then the correlation id outside both -- the order the application assembles them in.
    app.add_middleware(_Behind, record=record)
    app.add_middleware(
        BodyCapMiddleware, verify_credential=build_credential_precheck(ENVIRON, notices=notices)
    )
    app.add_middleware(CorrelationMiddleware)
    return TestClient(app, raise_server_exceptions=False), record


def _post(client: TestClient, authorization: list[str]) -> int:
    headers: list[tuple[str, str]] = [("Content-Type", MULTIPART)]
    headers += [("Authorization", value) for value in authorization]
    return client.post(UPLOAD, headers=headers, content=BODY).status_code


def test_through_the_real_seam_a_forged_first_credential_never_has_its_body_read() -> None:
    standings = _Standings()
    client, behind = _served(standings, None)
    token = _credential()
    behind.reached, behind.body_bytes = 0, 0

    status = _post(client, [_bearer("forged"), _bearer(token)])

    assert status == 401
    assert behind.reached == 0 and behind.body_bytes == 0, "the door admitted what the seam refuses"
    assert standings.reads == 0


def test_through_the_real_seam_a_signed_first_credential_behind_a_forged_one_is_served() -> None:
    standings = _Standings()
    client, behind = _served(standings, None)
    behind.reached = 0

    status = _post(client, [_bearer(_credential()), _bearer("forged")])

    assert status == 200, "the door refused a request the seam accepts"
    assert behind.reached == 1


# --- the revocation memory --------------------------------------------------------------------


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_a_noted_pair_is_revoked_until_its_lifetime_has_passed() -> None:
    clock = _Clock()
    notices = RevocationNotices(ttl_seconds=60, clock=clock)
    assert not notices.is_revoked(UID, 1)
    notices.note(UID, 1)
    assert notices.is_revoked(UID, 1)
    assert not notices.is_revoked(UID, 2), "a later generation is another credential"
    assert not notices.is_revoked("usr_other", 1)
    clock.now += 59
    assert notices.is_revoked(UID, 1)
    clock.now += 2
    assert not notices.is_revoked(UID, 1)
    assert len(notices) == 0, "an expired entry is dropped when it is met"


def test_noting_again_refreshes_the_lifetime() -> None:
    clock = _Clock()
    notices = RevocationNotices(ttl_seconds=60, clock=clock)
    notices.note(UID, 1)
    clock.now += 50
    notices.note(UID, 1)
    clock.now += 50
    assert notices.is_revoked(UID, 1)


def test_a_full_memory_drops_expired_entries_first_and_then_the_oldest() -> None:
    clock = _Clock()
    notices = RevocationNotices(ttl_seconds=60, capacity=3, clock=clock)
    notices.note("a", 1)
    clock.now += 100
    notices.note("b", 1)
    notices.note("c", 1)
    notices.note("d", 1)  # full: "a" has expired and goes; nothing live is lost
    assert [notices.is_revoked(u, 1) for u in "abcd"] == [False, True, True, True]
    notices.note("e", 1)  # full of live entries: the oldest ("b") is forgotten
    assert [notices.is_revoked(u, 1) for u in "bcde"] == [False, True, True, True]
    assert len(notices) == 3


def test_it_is_safe_under_concurrent_writers_and_readers() -> None:
    notices = RevocationNotices(capacity=50)
    errors: list[BaseException] = []

    def work(n: int) -> None:
        try:
            for i in range(300):
                notices.note(f"u{n}", i)
                notices.is_revoked(f"u{n}", i - 1)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=work, args=(n,)) for n in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    assert errors == [] and len(notices) <= 50


@pytest.mark.parametrize("ttl, capacity", [(0, 1), (1, 0)])
def test_a_memory_needs_a_lifetime_and_a_capacity(ttl: int, capacity: int) -> None:
    with pytest.raises(ValueError):
        RevocationNotices(ttl_seconds=ttl, capacity=capacity)


def test_the_precheck_refuses_a_noted_pair_and_nothing_else() -> None:
    notices = RevocationNotices()
    check = build_credential_precheck(ENVIRON, notices=notices)
    plain = build_credential_precheck(ENVIRON)
    assert check(_credential(1)) and check(_credential(2))
    notices.note(UID, 1)
    assert check(_credential(1)) is False
    assert check(_credential(2)) is True
    assert plain(_credential(1)) is True, "with no memory the door is the signature and the expiry"
    assert check("am2.not.signed") is False
    other = {API_TOKEN_VARIABLE: "another-secret"}
    assert check(_credential(2, environ=other)) is False


# --- the seam fills it; the door then refuses without a read --------------------------------------


@pytest.mark.parametrize(
    ("label", "standings", "token_epoch", "noted"),
    [
        ("a later generation", _Standings(epoch=2), 1, True),
        ("an archived account", _Standings(epoch=1, archived=True), 1, True),
        ("no such account", _Standings(exists=False), 1, True),
        # An epoch *below* the credential's is a restored database, not a revocation: it may
        # catch up, so the pair is refused by the seam and never remembered.
        ("a credential from the future", _Standings(epoch=1), 3, False),
        ("a live credential", _Standings(epoch=1), 1, False),
    ],
)
def test_the_seam_notes_exactly_the_refusals_that_cannot_turn_into_acceptances(
    label: str, standings: _Standings, token_epoch: int, noted: bool
) -> None:
    notices = RevocationNotices()
    client, _ = _served(standings, notices)

    status = _post(client, [_bearer(_credential(token_epoch))])

    assert (status == 401) is (label != "a live credential"), (label, status)
    assert notices.is_revoked(UID, token_epoch) is noted, label


def test_after_the_first_refusal_the_door_refuses_the_same_credential_without_a_read() -> None:
    standings = _Standings(epoch=2)  # the account's credentials were revoked: epoch 1 -> 2
    notices = RevocationNotices()
    client, behind = _served(standings, notices)
    stale = _credential(1)
    behind.reached, behind.body_bytes = 0, 0
    standings.reads = 0

    first = _post(client, [_bearer(stale)])
    # The door could not know: it read the body and the seam said no, and wrote it down.
    assert first == 401
    assert behind.reached == 1 and behind.body_bytes > 0 and standings.reads == 1

    behind.reached, behind.body_bytes = 0, 0
    second = _post(client, [_bearer(stale)])
    assert second == 401
    assert behind.reached == 0 and behind.body_bytes == 0, "the door read a revoked credential's body"
    assert standings.reads == 1, "the door asked the database about a credential it already knew"

    # A credential of the new generation is not caught by the old one's entry.
    fresh = _post(client, [_bearer(_credential(2))])
    assert fresh == 200 and behind.reached == 1


def test_with_no_memory_wired_the_door_is_what_it_was() -> None:
    standings = _Standings(epoch=2)
    client, behind = _served(standings, None)
    stale = _credential(1)
    behind.reached = 0
    assert _post(client, [_bearer(stale)]) == 401
    assert _post(client, [_bearer(stale)]) == 401
    assert behind.reached == 2, "without a memory both attempts reach the seam, as they always did"
    assert standings.reads == 2
