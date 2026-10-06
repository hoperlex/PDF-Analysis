"""`W49-QA-01`, item 9 -- an archived account's sign-in is the generic refusal, byte for byte.

`W49-PLAN.md` §3.1: "``standing_of`` returns no standing for an archived account, so sign-in
and every credentialed request answer the generic ``authentication_required``". The archived
account presents its **own correct password**; the answer must be indistinguishable from an
unknown login's and from a wrong password's -- the same status, the same headers, the same
body bytes -- with the caller's correlation id fixed so nothing that may legitimately differ
does. Its old credential is refused the same way, and its status read (it applied once, and
was approved) is the status read's generic refusal.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from .qa_kit import (
    PASSWORD,
    Answer,
    approve,
    credential_for,
    envelope,
    exchange,
    fresh_login,
    identity_surface,
    make_account,
    request_row,
    send,
    status_read,
    submit,
)

_CORRELATION = "qa49-archived-compare"


def _comparable(answer: Answer) -> tuple[int, tuple[tuple[str, str], ...], bytes]:
    headers = tuple(sorted((name.lower(), value) for name, value in answer.headers))
    return answer.status, headers, answer.body


def test_an_archived_account_signing_in_gets_exactly_the_generic_refusal(
    session_factory: sessionmaker[Session], session: Session
) -> None:
    surface = identity_surface(session_factory)
    admin = make_account(
        session,
        login=fresh_login("archiving-admin"),
        names=("Хранитель", "Глеб", None),
        roles=("expert", "admin"),
    )
    admin_cred = credential_for(session, admin)

    # An account made the product's way: applied, approved, signed in once.
    login = fresh_login("to-archive")
    assert submit(surface, login).status == 201
    row = request_row(session, login)
    assert row is not None
    approved = approve(surface, admin_cred, row["request_id"])
    assert approved.status == 200, approved.body
    account = envelope(approved)["created_user_uid"]
    first = exchange(surface, login, PASSWORD)
    assert first.status == 200, first.body
    held = envelope(first)["token"]

    archived = send(surface, "POST", f"/users/{account}/archive", credential=admin_cred)
    assert archived.status == 200, archived.body

    unknown = exchange(surface, fresh_login("never-existed"), PASSWORD, correlation=_CORRELATION)
    assert unknown.status == 401, unknown.body
    assert envelope(unknown)["error_code"] == "authentication_required"
    wrong = exchange(surface, _login_of(session, admin), "qa49-wrong", correlation=_CORRELATION)

    own_pair = exchange(surface, login, PASSWORD, correlation=_CORRELATION)
    assert _comparable(own_pair) == _comparable(unknown), own_pair.body
    assert _comparable(own_pair) == _comparable(wrong), own_pair.body

    # The credential it held before the archive: the seam's generic 401.
    stale = send(surface, "GET", "/me", credential=held, correlation=_CORRELATION)
    no_credential = send(surface, "GET", "/me", correlation=_CORRELATION)
    assert _comparable(stale) == _comparable(no_credential), stale.body

    # The status read for its (approved) request: the status read's generic refusal.
    status_unknown = status_read(
        surface, fresh_login("never-applied"), PASSWORD, correlation=_CORRELATION
    )
    status_own = status_read(surface, login, PASSWORD, correlation=_CORRELATION)
    assert _comparable(status_own) == _comparable(status_unknown), status_own.body


def _login_of(session: Session, user_uid: str) -> str:
    return str(
        session.execute(
            text("SELECT login FROM app_user WHERE user_uid = :u"), {"u": user_uid}
        ).scalar_one()
    )
