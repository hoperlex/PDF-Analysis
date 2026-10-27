"""`SMALL-HARDENING-02` / `R-146ay`: registration stays open, and the queue cannot be flooded.

Registration and sign-in stay public; what the owner added is a limit the application owns
(the edge limits an address, and the browser's own registration never meets the edge's zone):
at most ``MAX_REQUESTS_PER_DAY`` requests stand or were approved in any rolling 24 hours, counted
from ``registration_request.submitted_at`` over the ``pending`` and ``approved`` requests (a
``rejected`` one is the administrator's lever and frees its place), and the next one is refused
with the existing ``conflict`` / ``queue_full``.

Each test gets its own clone of a migrated database (``conftest.py``) and commits what it
writes. The rows that fill the window are written directly with a stored digest of zeros --
the queue's own content is not under test and each real submission costs a PBKDF2 derivation
-- and are aged with the database's clock, so the boundary of the window is the database's.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.access.accounts import AccountRepository
from auditmanager.access.registrations import (
    MAX_PENDING_REQUESTS,
    MAX_REQUESTS_PER_DAY,
    REQUEST_WINDOW_HOURS,
    RegistrationRepository,
)
from auditmanager.access.repository import UserRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity.ids import RegistrationRequestId

PASSWORD = "an-applicant-password"  # noqa: S105 - a test literal

registrations = RegistrationRepository()
users = UserRepository()
accounts = AccountRepository()


def _fill(session: Session, count: int, *, age: str, prefix: str = "filler") -> list[str]:
    """``count`` pending rows, written ``age`` ago by the database's clock. Returns the ids."""
    ids: list[str] = []
    for index in range(count):
        request_id = str(RegistrationRequestId.new())
        session.execute(
            text(
                "INSERT INTO registration_request (request_id, login, last_name, first_name, "
                "password_algorithm, password_iterations, password_salt, password_hash, "
                "submitted_at) VALUES (:rid, :login, 'Петрова', 'Анна', 'pbkdf2_sha256', "
                "600000, :s, :d, now() - CAST(:age AS interval))"
            ),
            {
                "rid": request_id,
                "login": f"{prefix}{index}@example.com",
                "s": "0" * 32,
                "d": "0" * 64,
                "age": age,
            },
        )
        ids.append(request_id)
    session.commit()
    return ids


def _submit(session: Session, login: str = "new@example.com"):
    record = registrations.submit(
        session, login=login, password=PASSWORD, last_name="Иванова", first_name="Мария"
    )
    session.commit()
    return record


def _rows(session: Session) -> int:
    return int(session.execute(text("SELECT count(*) FROM registration_request")).scalar_one())


def _refused_as_queue_full(session: Session, login: str) -> DomainError:
    with pytest.raises(DomainError) as caught:
        _submit(session, login)
    session.rollback()
    assert caught.value.code is ErrorCode.CONFLICT
    assert caught.value.detail_fields == {"conflict_reason": "queue_full"}
    return caught.value


def test_the_numbers_are_the_documented_ones() -> None:
    """40 a day, a 24-hour window, well below the pending cap of 100."""
    assert (MAX_REQUESTS_PER_DAY, REQUEST_WINDOW_HOURS, MAX_PENDING_REQUESTS) == (40, 24, 100)


def test_the_fortieth_request_of_a_day_is_accepted_and_the_forty_first_is_queue_full(
    migrated_engine,
) -> None:
    with Session(migrated_engine) as session:
        _fill(session, MAX_REQUESTS_PER_DAY - 1, age="1 hour")
        assert _submit(session, "fortieth@example.com").status == "pending"
        assert _rows(session) == MAX_REQUESTS_PER_DAY

        _refused_as_queue_full(session, "forty-first@example.com")
        # The cap that refused it is the day's, not the queue's: 40 are pending, not 100.
        assert registrations.pending_total(session) == MAX_REQUESTS_PER_DAY < MAX_PENDING_REQUESTS
        # A refusal writes nothing, so it does not spend the window either.
        assert _rows(session) == MAX_REQUESTS_PER_DAY
        _refused_as_queue_full(session, "forty-second@example.com")
        assert _rows(session) == MAX_REQUESTS_PER_DAY


def test_a_rejected_request_frees_a_place_in_the_day_and_an_approved_one_does_not(
    migrated_engine,
) -> None:
    """The day counts requests that stand (pending) or were accepted (approved). A rejected one
    was refused by the administrator, so it frees the place: the administrator's lever when
    spam fills the day. Before this rule every state counted and nothing could clear the day.

    ``SMALL-HARDENING-02`` asserted here that after one reject and one approve the day was
    still spent; now the same two decisions leave 39 counted, so one more is accepted."""
    with Session(migrated_engine) as session:
        admin = users.find_by_login(session, "admin")
        assert admin is not None
        ids = _fill(session, MAX_REQUESTS_PER_DAY, age="2 hours")
        _refused_as_queue_full(session, "before-decisions@example.com")

        registrations.approve(
            session, actor_uid=str(admin.user_uid), request_id=ids[1], roles=("expert",)
        )
        session.commit()
        # An approval is a request accepted: the day is still spent.
        _refused_as_queue_full(session, "after-approval@example.com")

        registrations.reject(session, actor_uid=str(admin.user_uid), request_id=ids[0], reason="нет")
        session.commit()
        assert registrations.pending_total(session) == MAX_REQUESTS_PER_DAY - 2
        # 38 pending + 1 approved = 39 stand: one place is free, and only one.
        assert _submit(session, "after-reject@example.com").status == "pending"
        _refused_as_queue_full(session, "one-too-many@example.com")

        # Rejecting another request frees another place.
        registrations.reject(session, actor_uid=str(admin.user_uid), request_id=ids[2], reason="нет")
        session.commit()
        assert _submit(session, "after-second-reject@example.com").status == "pending"
        _refused_as_queue_full(session, "and-again@example.com")


def test_a_day_full_of_rejected_requests_is_an_open_door(migrated_engine) -> None:
    """Forty requests rejected inside the window leave the count at zero: the administrator who
    clears a flood reopens registration at once."""
    with Session(migrated_engine) as session:
        admin = users.find_by_login(session, "admin")
        assert admin is not None
        ids = _fill(session, MAX_REQUESTS_PER_DAY, age="1 hour")
        for request_id in ids:
            registrations.reject(
                session, actor_uid=str(admin.user_uid), request_id=request_id, reason="спам"
            )
        session.commit()
        assert registrations.pending_total(session) == 0
        assert _submit(session, "all-rejected@example.com").status == "pending"


@pytest.mark.parametrize(
    ("age", "accepted"),
    [
        ("23 hours 59 minutes", False),
        ("24 hours 1 minute", True),
        ("3 days", True),
    ],
    ids=["just-inside-the-window", "just-outside-the-window", "long-outside"],
)
def test_the_window_is_a_rolling_twenty_four_hours_by_the_databases_clock(
    migrated_engine, age: str, accepted: bool
) -> None:
    with Session(migrated_engine) as session:
        _fill(session, MAX_REQUESTS_PER_DAY, age=age)
        if accepted:
            assert _submit(session, "late@example.com").status == "pending"
        else:
            _refused_as_queue_full(session, "early@example.com")


def test_the_refusal_is_the_same_for_every_login_so_it_discloses_nothing_new(
    migrated_engine,
) -> None:
    """With the day spent, a login nobody holds and a login no one has ever mentioned get the
    identical answer; the cap adds no way to ask whether a login exists (`E-9` is not part)."""
    with Session(migrated_engine) as session:
        _fill(session, MAX_REQUESTS_PER_DAY, age="1 hour")
        first = _refused_as_queue_full(session, "somebody@example.com")
        second = _refused_as_queue_full(session, "somebody.else@example.org")
        assert (first.code, first.detail_fields) == (second.code, second.detail_fields)
        assert str(first) == str(second)
