"""`W49-QA-01`, item 3 -- removing the last administrator through ``updateUser`` and ``archiveUser``.

`W49-PLAN.md` §3.2: "the last active account holding ``admin`` cannot be archived or lose
``admin``"; §3.3: "so does removing, archiving or demoting the last active administrator"
answer ``conflict``, with ``conflict_reason: last_admin`` (the closed set of §3.3).

Through the served operations this is reachable only as a race. The acting administrator
passes the seam only while it holds ``admin`` itself, so a sequential request always leaves
the actor as a second administrator; the last one disappears only when two administrators
remove each other at the same instant. That is the case driven here, on a fresh database
whose only administrators are the two of them (the seeded ``admin`` row's role is removed
first), both requests released together after each has passed the seam. Whatever the
interleaving, exactly one may succeed, the other must be ``409 conflict / last_admin``, and
one active administrator must remain.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from sqlalchemy import Engine, text

from .qa_kit import (
    Answer,
    Surface,
    committed_factory,
    credential_for,
    envelope,
    fresh_login,
    identity_surface,
    make_account,
    race,
    send,
)

_HOLD_ADMINS = "SELECT 1 FROM app_user WHERE user_uid IN (:a, :b) FOR UPDATE"


def _demote(surface: Surface, credential: str, target: str) -> Answer:
    return send(
        surface, "PATCH", f"/users/{target}", credential=credential, body={"roles": ["expert"]}
    )


def _archive(surface: Surface, credential: str, target: str) -> Answer:
    return send(surface, "POST", f"/users/{target}/archive", credential=credential)


_OPERATIONS: dict[str, tuple[Callable[..., Answer], Callable[..., Answer]]] = {
    "updateUser vs updateUser": (_demote, _demote),
    "archiveUser vs archiveUser": (_archive, _archive),
    "updateUser vs archiveUser": (_demote, _archive),
}


def _active_admins(engine: Engine) -> list[str]:
    with engine.connect() as connection:
        return list(
            connection.execute(
                text(
                    "SELECT u.user_uid FROM app_user u JOIN app_user_role r "
                    "ON r.user_uid = u.user_uid AND r.role = 'admin' "
                    "WHERE u.archived_at IS NULL ORDER BY u.user_uid"
                )
            ).scalars()
        )


@pytest.mark.parametrize("pair", sorted(_OPERATIONS))
def test_two_administrators_removing_each_other_leave_one(
    migrated_engine: Engine, pair: str
) -> None:
    factory = committed_factory(migrated_engine)
    with factory() as session:
        first = make_account(
            session,
            login=fresh_login("la-a"),
            names=("Альфина", "Алла", None),
            roles=("expert", "admin"),
        )
        second = make_account(
            session,
            login=fresh_login("la-b"),
            names=("Бетова", "Белла", None),
            roles=("expert", "admin"),
        )
        # The seeded `admin` row of migration 0006 holds `admin` after 0015's backfill; it
        # would be the third administrator and the rule could never fire.
        session.execute(
            text("DELETE FROM app_user_role WHERE role = 'admin' AND user_uid NOT IN (:a, :b)"),
            {"a": first, "b": second},
        )
        session.commit()
        first_cred, second_cred = credential_for(session, first), credential_for(session, second)
    assert _active_admins(migrated_engine) == sorted([first, second])

    by_first, by_second = _OPERATIONS[pair]
    left, right = identity_surface(factory), identity_surface(factory)
    answers, forced = race(
        migrated_engine,
        hold=_HOLD_ADMINS,
        params={"a": first, "b": second},
        calls=[
            lambda: by_first(left, first_cred, second),
            lambda: by_second(right, second_cred, first),
        ],
    )
    assert forced, "both requests should have passed the seam and waited on the administrators"

    report = [(answer.status, answer.body) for answer in answers]
    assert sorted(answer.status for answer in answers) == [200, 409], report
    refusal = envelope(next(answer for answer in answers if answer.status == 409))
    assert refusal["error_code"] == "conflict", refusal
    assert refusal.get("details") == {"conflict_reason": "last_admin"}, refusal
    assert len(_active_admins(migrated_engine)) == 1, report
