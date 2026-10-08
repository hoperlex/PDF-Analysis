"""`W49-QA-01`, item 10 -- an administrator's reset forces the password change.

`W49-PLAN.md` §3.1: "``is_default_credential`` keeps its wire name and widens its meaning to
'must change password': seeded, or reset by an administrator"; §3.4 ``resetUserPassword``:
"temporary password under the R-48 policy; sets must-change; bumps epoch"; §3.2: a default
credential reaches ``{issueToken, changePassword, getMe}`` and nothing else
(``permission_denied``, ``required_capability: password_changed``, `R-50`).

So after the reset: every credential the account held is refused; signing in with the
temporary password says ``is_default_credential: true``; that credential reaches ``getMe``
and ``changePassword`` and is refused everything else, including what its roles would allow;
the change clears the flag and opens the account again.
"""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from .qa_kit import (
    credential_for,
    envelope,
    exchange,
    fresh_login,
    identity_surface,
    make_account,
    send,
)

_ORIGINAL = "qa49-original-password"
_TEMPORARY = "qa49-temporary-from-admin"
_CHOSEN = "qa49-chosen-after-reset"


def test_after_an_administrators_reset_the_account_must_change_its_password(
    session_factory: sessionmaker[Session], session: Session
) -> None:
    surface = identity_surface(session_factory)
    admin = make_account(
        session,
        login=fresh_login("resetter"),
        names=("Сбросова", "Сима", None),
        roles=("expert", "admin"),
    )
    login = fresh_login("reset-target")
    # The target is an administrator too, so "refused everything else" includes operations
    # its roles reach -- the refusal must be the default credential's, not a role's.
    target = make_account(
        session,
        login=login,
        names=("Забывчивая", "Зина", None),
        roles=("expert", "admin"),
        password=_ORIGINAL,
    )
    before = exchange(surface, login, _ORIGINAL)
    assert before.status == 200 and envelope(before)["is_default_credential"] is False
    old = envelope(before)["token"]

    reset = send(
        surface,
        "POST",
        f"/users/{target}/password",
        credential=credential_for(session, admin),
        body={"temporary_password": _TEMPORARY},
    )
    assert reset.status == 200, reset.body
    assert envelope(reset)["is_default_credential"] is True
    assert _TEMPORARY not in reset.body.decode("utf-8")

    assert send(surface, "GET", "/me", credential=old).status == 401
    assert exchange(surface, login, _ORIGINAL).status == 401

    signed_in = exchange(surface, login, _TEMPORARY)
    assert signed_in.status == 200, signed_in.body
    assert envelope(signed_in)["is_default_credential"] is True
    temporary = envelope(signed_in)["token"]

    me = send(surface, "GET", "/me", credential=temporary)
    assert me.status == 200 and envelope(me)["is_default_credential"] is True, me.body
    for method, path, body in (
        ("GET", "/users", None),
        ("GET", f"/users/{admin}", None),
        ("GET", "/registrations", None),
        ("PATCH", "/me", {"last_name": "Забывчивая", "first_name": "Зина"}),
    ):
        refused = send(surface, method, path, credential=temporary, body=body)
        assert refused.status == 403, (path, refused.body)
        denial = envelope(refused)
        assert denial["error_code"] == "permission_denied", denial
        assert denial.get("details") == {"required_capability": "password_changed"}, denial

    changed = send(
        surface,
        "POST",
        "/auth/password",
        credential=temporary,
        body={"current_password": _TEMPORARY, "new_password": _CHOSEN},
    )
    assert changed.status == 200, changed.body
    assert envelope(changed)["is_default_credential"] is False
    replacement = envelope(changed)["token"]
    assert send(surface, "GET", "/users", credential=replacement).status == 200
    assert send(surface, "GET", "/users", credential=temporary).status == 401

    again = exchange(surface, login, _CHOSEN)
    assert again.status == 200 and envelope(again)["is_default_credential"] is False
    assert exchange(surface, login, _TEMPORARY).status == 401
