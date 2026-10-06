"""`W49-QA-01` -- how the independent tests call the identity surface.

Written from `W49-PLAN.md` §3 and the frozen `contracts/api/v1/openapi.json`, not from the
lane reports. Everything here only *calls* the system: requests through the served
application (the shipped account, registration and credential adapters, via
``identity_surface``) and plain reads of the rows those requests leave behind. No helper
here decides an outcome; every expectation is written in the test that asserts it.

The passwords below are test literals for throwaway rows in a disposable database. They are
not, and never were, a credential of any deployment.
"""

from __future__ import annotations

import json
import secrets
import time
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from w13_api_driver import Answer, Surface

from ..identity_surface import credential_for, identity_surface, make_account

__all__ = [
    "APPLICANT_NAMES",
    "PASSWORD",
    "Answer",
    "Surface",
    "account_row",
    "approve",
    "committed_factory",
    "credential_for",
    "envelope",
    "exchange",
    "fresh_login",
    "identity_surface",
    "make_account",
    "race",
    "reject",
    "request_row",
    "send",
    "status_read",
    "submit",
]

#: The applicant's password in every registration these tests submit. Passes `R-48`
#: (length, not the login, not a name, not the product name, not the shipped default).
PASSWORD = "qa49-applicant-passphrase"

#: Names an applicant gives: a complete profile's three parts, Cyrillic, policy-clean.
APPLICANT_NAMES: tuple[str, str, str | None] = ("Заявкина", "Мария", "Петровна")


def fresh_login(tag: str) -> str:
    """A login no other test uses: an e-mail address in a reserved domain."""
    return f"qa49-{tag}-{secrets.token_hex(4)}@qa.invalid"


def send(
    surface: Surface,
    method: str,
    path: str,
    *,
    credential: str | None = None,
    body: Any = None,
    headers: Mapping[str, str] | None = None,
    correlation: str | None = None,
) -> Answer:
    """One request through the served application. ``credential=None`` presents none."""
    sent = dict(headers or {})
    payload = b""
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        sent["Content-Type"] = "application/json"
    if correlation is not None:
        sent["X-Correlation-Id"] = correlation
    return surface.send(method, path, headers=sent, body=payload, credential=credential)


def envelope(answer: Answer) -> dict[str, Any]:
    return json.loads(answer.body)


def submit(
    surface: Surface,
    login: str,
    *,
    password: str = PASSWORD,
    names: tuple[str, str, str | None] = APPLICANT_NAMES,
    correlation: str | None = None,
) -> Answer:
    """``submitRegistration``, unauthenticated."""
    last, first, middle = names
    body: dict[str, Any] = {
        "login": login,
        "password": password,
        "last_name": last,
        "first_name": first,
    }
    if middle is not None:
        body["middle_name"] = middle
    return send(surface, "POST", "/registrations", body=body, correlation=correlation)


def status_read(
    surface: Surface, login: str, password: str, *, correlation: str | None = None
) -> Answer:
    """``readRegistrationStatus``, unauthenticated."""
    return send(
        surface,
        "POST",
        "/registrations/status",
        body={"login": login, "password": password},
        correlation=correlation,
    )


def exchange(
    surface: Surface, login: str, password: str, *, correlation: str | None = None
) -> Answer:
    """``issueToken``, unauthenticated."""
    return send(
        surface,
        "POST",
        "/auth/token",
        body={"login": login, "password": password},
        correlation=correlation,
    )


def approve(
    surface: Surface,
    credential: str,
    request_id: str,
    *,
    roles: Sequence[str] = ("expert",),
    key: str | None = None,
) -> Answer:
    """``approveRegistration`` with an ``Idempotency-Key`` (a fresh one unless given)."""
    return send(
        surface,
        "POST",
        f"/registrations/{request_id}/approve",
        credential=credential,
        body={"roles": list(roles)},
        headers={"Idempotency-Key": key or f"qa49-approve-{secrets.token_hex(8)}"},
    )


def reject(
    surface: Surface, credential: str, request_id: str, *, reason: str = "Не прошла проверку."
) -> Answer:
    """``rejectRegistration``."""
    return send(
        surface,
        "POST",
        f"/registrations/{request_id}/reject",
        credential=credential,
        body={"reason": reason},
    )


def request_row(session: Session, login: str) -> dict[str, Any] | None:
    """The newest request for ``login``, as stored (no credential column is read)."""
    row = (
        session.execute(
            text(
                "SELECT request_id, status, decided_by, created_user_uid, rejection_reason, "
                "failed_sign_ins, sign_in_blocked_until, password_hash IS NULL AS password_nulled "
                "FROM registration_request WHERE login = :login "
                "ORDER BY submitted_at DESC, request_id DESC LIMIT 1"
            ),
            {"login": login},
        )
        .mappings()
        .first()
    )
    return None if row is None else dict(row)


def account_row(session: Session, user_uid: str) -> dict[str, Any] | None:
    """The account as stored, with its role set; ``None`` when there is no such row.

    ``password_marker`` is the digest's first eight characters -- enough to tell "the
    password changed" from "it did not", and not a credential.
    """
    row = (
        session.execute(
            text(
                "SELECT login, last_name, first_name, middle_name, token_epoch, archived_at, "
                "archived_by, is_default_credential, left(password_hash, 8) AS password_marker "
                "FROM app_user "
                "WHERE user_uid = :uid"
            ),
            {"uid": user_uid},
        )
        .mappings()
        .first()
    )
    if row is None:
        return None
    roles = session.execute(
        text("SELECT role FROM app_user_role WHERE user_uid = :uid ORDER BY role"),
        {"uid": user_uid},
    ).scalars().all()
    return {**dict(row), "roles": tuple(roles)}


def committed_factory(engine: Engine) -> sessionmaker[Session]:
    """Sessions on a fresh database whose commits are real, for the races."""
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


_LOCK_WAITERS = text(
    "SELECT count(*) FROM pg_stat_activity "
    "WHERE datname = current_database() AND wait_event_type = 'Lock'"
)


def race(
    engine: Engine,
    *,
    hold: str,
    params: Mapping[str, Any],
    calls: Sequence[Callable[[], Answer]],
    timeout: float = 60.0,
) -> tuple[list[Answer], bool]:
    """Run ``calls`` at once, all of them released from the same instant.

    A blocker transaction runs ``hold`` (a ``FOR UPDATE`` on the rows the operations must
    lock) before the calls start, so every call passes the seam and then waits on that lock;
    once ``len(calls)`` backends are waiting -- or every call has already finished, which
    means the operation took no lock and the race was not forced -- the blocker rolls back
    and the calls contend for real. Returns the answers in call order, and whether every
    call was seen waiting.
    """
    blocker = engine.connect()
    held = blocker.begin()
    released = False
    try:
        blocker.execute(text(hold), dict(params))
        with ThreadPoolExecutor(max_workers=len(calls)) as pool:
            futures: list[Future[Answer]] = [pool.submit(call) for call in calls]
            forced = False
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                with engine.connect() as probe:
                    waiting = int(probe.execute(_LOCK_WAITERS).scalar_one())
                if waiting >= len(calls):
                    forced = True
                    break
                if all(future.done() for future in futures):
                    break
                time.sleep(0.05)
            held.rollback()
            released = True
            answers = [future.result(timeout=timeout) for future in futures]
        return answers, forced
    finally:
        if not released:
            held.rollback()
        blocker.close()
