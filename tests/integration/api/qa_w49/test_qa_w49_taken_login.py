"""`W49-QA-01`, item 7 -- a registration for a login that is taken.

`W49-PLAN.md` §3.3: "A request for a login held by an active account, or already pending,
answers ``conflict``", with ``conflict_reason`` ``login_taken`` or ``request_pending``; §3.1:
the login is the *normalised* e-mail (trimmed, zero-width characters removed, lower-cased).
So a spelling that normalises to a held login is the same login, and a refused application
writes no row. A login held only by an archived account is not taken (the partial unique
index of §3.1) -- the counter-case that keeps the first assertion honest.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from .qa_kit import envelope, fresh_login, identity_surface, make_account, submit


def _requests(session: Session) -> int:
    return int(session.execute(text("SELECT count(*) FROM registration_request")).scalar_one())


def _spellings(login: str) -> list[str]:
    local, domain = login.split("@")
    return [
        login,
        f"  {login.upper()}  ",
        f"{local}​@{domain}",  # a zero-width space inside the address
        f"{local.title()}@{domain.upper()}",
    ]


@pytest.mark.parametrize("spelling", range(4), ids=["exact", "upper-padded", "zero-width", "mixed"])
def test_a_login_an_active_account_holds_is_login_taken(
    session_factory: sessionmaker[Session], session: Session, spelling: int
) -> None:
    surface = identity_surface(session_factory)
    login = fresh_login("held")
    make_account(session, login=login, names=("Занятая", "Анна", None), roles=("expert",))
    before = _requests(session)

    answer = submit(surface, _spellings(login)[spelling])
    assert answer.status == 409, answer.body
    body = envelope(answer)
    assert body["error_code"] == "conflict", body
    assert body.get("details") == {"conflict_reason": "login_taken"}, body
    assert _requests(session) == before, "a refused application wrote a row"


@pytest.mark.parametrize("spelling", range(4), ids=["exact", "upper-padded", "zero-width", "mixed"])
def test_a_login_already_applied_for_is_request_pending(
    session_factory: sessionmaker[Session], session: Session, spelling: int
) -> None:
    surface = identity_surface(session_factory)
    login = fresh_login("applied")
    assert submit(surface, login).status == 201
    before = _requests(session)

    answer = submit(surface, _spellings(login)[spelling])
    assert answer.status == 409, answer.body
    body = envelope(answer)
    assert body["error_code"] == "conflict", body
    assert body.get("details") == {"conflict_reason": "request_pending"}, body
    assert _requests(session) == before


def test_a_login_held_only_by_an_archived_account_is_not_taken(
    session_factory: sessionmaker[Session], session: Session
) -> None:
    surface = identity_surface(session_factory)
    login = fresh_login("archived-holder")
    archiver = make_account(
        session, login=fresh_login("archiver"), names=("Архивова", "Ася", None), roles=("admin",)
    )
    holder = make_account(session, login=login, names=("Бывшая", "Бэла", None), roles=("expert",))
    session.execute(
        text("UPDATE app_user SET archived_at = now(), archived_by = :by WHERE user_uid = :uid"),
        {"by": archiver, "uid": holder},
    )
    assert submit(surface, login).status == 201
