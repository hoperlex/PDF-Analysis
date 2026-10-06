"""`W49-QA-01`, item 8 -- the status read: pending, a rejected pair, and the throttle.

`W49-PLAN.md` §3.3 and `R-56` with its 2026-10-06 addendum: ``readRegistrationStatus``
answers ``{status: pending}`` for a pair that matches a pending request, "and the same generic
refusal for every other pair -- including a decided request ... A rejected applicant sees
nothing at sign-in". "The request's throttle columns count both kinds of attempts" -- the
failed exchange and the status read -- with the account brake's rules.

"Exactly like an unknown pair" is checked byte for byte: the same status, the same headers
and the same body, with the caller's correlation id fixed so the one value that is allowed to
differ between two requests does not.
"""

from __future__ import annotations

import json

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
    reject,
    request_row,
    status_read,
    submit,
)

_CORRELATION = "qa49-status-read-compare"


def _comparable(answer: Answer) -> tuple[int, tuple[tuple[str, str], ...], bytes]:
    """Status, every header (sorted, names folded) and the exact body bytes."""
    headers = tuple(sorted((name.lower(), value) for name, value in answer.headers))
    return answer.status, headers, answer.body


def _admin(session: Session) -> str:
    uid = make_account(
        session,
        login=fresh_login("status-admin"),
        names=("Решалова", "Рита", None),
        roles=("expert", "admin"),
    )
    return credential_for(session, uid)


def test_a_pending_pair_reads_pending_and_nothing_else(
    session_factory: sessionmaker[Session], session: Session
) -> None:
    surface = identity_surface(session_factory)
    login = fresh_login("pending")
    assert submit(surface, login).status == 201

    answer = status_read(surface, login, PASSWORD)
    assert answer.status == 200, answer.body
    assert json.loads(answer.body) == {"status": "pending"}
    # The normalised spelling is the same login here too.
    assert status_read(surface, f" {login.upper()} ", PASSWORD).status == 200


def test_a_rejected_or_approved_pair_is_answered_exactly_like_an_unknown_pair(
    session_factory: sessionmaker[Session], session: Session
) -> None:
    surface = identity_surface(session_factory)
    admin_cred = _admin(session)
    rejected, approved = fresh_login("rejected"), fresh_login("approved")
    for login in (rejected, approved):
        assert submit(surface, login).status == 201
    rejected_row, approved_row = request_row(session, rejected), request_row(session, approved)
    assert rejected_row is not None and approved_row is not None
    assert reject(surface, admin_cred, rejected_row["request_id"], reason="Не знаем вас.").status == 200
    assert approve(surface, admin_cred, approved_row["request_id"]).status == 200

    unknown = status_read(surface, fresh_login("nobody"), PASSWORD, correlation=_CORRELATION)
    assert unknown.status == 401, unknown.body
    assert envelope(unknown)["error_code"] == "authentication_required"

    for login in (rejected, approved):
        answer = status_read(surface, login, PASSWORD, correlation=_CORRELATION)
        assert _comparable(answer) == _comparable(unknown), (login, answer.body)
    # Nor does the rejection reason travel anywhere near the applicant.
    assert "Не знаем" not in status_read(surface, rejected, PASSWORD).body.decode("utf-8")
    # A wrong password on a pending request is the same refusal as well.
    pending = fresh_login("pending-wrong")
    assert submit(surface, pending).status == 201
    wrong = status_read(surface, pending, "qa49-not-the-password", correlation=_CORRELATION)
    assert _comparable(wrong) == _comparable(unknown)


def test_five_refused_attempts_of_either_kind_brake_the_request(
    session_factory: sessionmaker[Session], session: Session
) -> None:
    surface = identity_surface(session_factory)
    unknown = status_read(surface, fresh_login("nobody"), PASSWORD, correlation=_CORRELATION)

    # Four refusals -- two status reads, two exchanges -- leave the right pair working, and
    # the right pair clears what they recorded.
    login = fresh_login("braked")
    assert submit(surface, login).status == 201
    for attempt in range(2):
        assert status_read(surface, login, f"qa49-wrong-{attempt}").status == 401
        assert exchange(surface, login, f"qa49-wrong-x-{attempt}").status == 401
    session.expire_all()
    assert request_row(session, login)["failed_sign_ins"] == 4  # type: ignore[index]
    assert status_read(surface, login, PASSWORD).status == 200
    session.expire_all()
    assert request_row(session, login)["failed_sign_ins"] == 0  # type: ignore[index]

    # Five refusals of either kind shut it: the right pair is now refused, and refused
    # exactly as an unknown pair is.
    for attempt in range(3):
        assert exchange(surface, login, f"qa49-wrong-y-{attempt}").status == 401
    for attempt in range(2):
        assert status_read(surface, login, f"qa49-wrong-z-{attempt}").status == 401
    session.expire_all()
    braked = request_row(session, login)
    assert braked is not None and braked["sign_in_blocked_until"] is not None
    answer = status_read(surface, login, PASSWORD, correlation=_CORRELATION)
    assert _comparable(answer) == _comparable(unknown), answer.body
