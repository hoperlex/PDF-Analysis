"""`W49-QA-01`, item 2 -- archive, purge, demote and reset of oneself (`W49-PLAN.md` §3.2-§3.4).

"An account cannot archive, purge, demote or reset itself" (§3.2), and "an act on oneself
stays ``permission_denied`` with no detail -- the screens never offer it" (§3.3). Each act is
driven through its served operation by an administrator on its own ``user_uid``, twice: once
while another active administrator exists (so the last-administrator rule cannot be what
refuses) and once as the only one (so a ``conflict`` cannot stand in for the self refusal).
Every refusal must leave the row exactly as it was -- no epoch bump, no archive, no lost role,
no new password.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from .qa_kit import (
    account_row,
    credential_for,
    envelope,
    exchange,
    fresh_login,
    identity_surface,
    make_account,
    send,
)

_ACTS: dict[str, tuple[str, str, Any]] = {
    "archive": ("POST", "/users/{uid}/archive", None),
    "purge": ("DELETE", "/users/{uid}", None),
    "demote (drop admin)": ("PATCH", "/users/{uid}", {"roles": ["expert"]}),
    "demote (drop expert, keep admin)": ("PATCH", "/users/{uid}", {"roles": ["admin"]}),
    "demote (to nothing)": ("PATCH", "/users/{uid}", {"roles": []}),
    # One request, two changes: a rename (which alone is allowed) with a self-demotion. The
    # refusal must take the rename with it -- one transaction, nothing half-applied.
    "demote with a rename": (
        "PATCH",
        "/users/{uid}",
        {"names": {"last_name": "Переименова", "first_name": "Инна"}, "roles": ["expert"]},
    ),
    "reset": ("POST", "/users/{uid}/password", {"temporary_password": "qa49-temporary-pass"}),
}

_SELF_PASSWORD = "qa49-self-admin-password"


def _sole_admin(session: Session, keep: str) -> None:
    """Inside the test's rolled-back transaction: nobody but ``keep`` holds ``admin``."""
    session.execute(
        text("DELETE FROM app_user_role WHERE role = 'admin' AND user_uid <> :keep"),
        {"keep": keep},
    )


@pytest.mark.parametrize("sole", [False, True], ids=["another-admin-exists", "sole-admin"])
@pytest.mark.parametrize("act", sorted(_ACTS))
def test_an_act_on_oneself_is_permission_denied_with_no_detail_and_changes_nothing(
    session_factory: sessionmaker[Session], session: Session, act: str, sole: bool
) -> None:
    surface = identity_surface(session_factory)
    login = fresh_login("self")
    me = make_account(
        session,
        login=login,
        names=("Самова", "Ирина", None),
        roles=("expert", "admin"),
        password=_SELF_PASSWORD,
    )
    if sole:
        _sole_admin(session, me)
    else:
        make_account(
            session,
            login=fresh_login("other-admin"),
            names=("Другова", "Ольга", None),
            roles=("expert", "admin"),
        )
    before = account_row(session, me)
    credential = credential_for(session, me)

    method, template, body = _ACTS[act]
    answer = send(surface, method, template.format(uid=me), credential=credential, body=body)

    assert answer.status == 403, (act, answer.status, answer.body)
    refusal = envelope(answer)
    assert refusal["error_code"] == "permission_denied", refusal
    assert not refusal.get("details"), f"an act on oneself carries no detail: {refusal}"

    session.expire_all()
    assert account_row(session, me) == before, f"the refused {act} changed the row"
    # The credential still works -- nothing was revoked -- and so does the old password.
    still = send(surface, "GET", "/me", credential=credential)
    assert still.status == 200, still.body
    assert exchange(surface, login, _SELF_PASSWORD).status == 200
