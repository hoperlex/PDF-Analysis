"""`W49-QA-01`, item 4 (API half) -- a credential after a role removal.

`W49-PLAN.md` §3.2: "Any role change ... bumps ``token_epoch``, so every credential of that
account answers ``authentication_required`` on its next request ... the account signs in
again and only then meets a ``permission_denied`` on what it lost." The BFF half of the item
(the 401 closes the session row and the envelope is answered) is
``web/tests/unit/qa_w49/epoch-401-closes-the-session.test.ts``.

The credential is minted by the real exchange, not by the suite's signer, so the epoch it
carries is the one the row held when the account signed in.
"""

from __future__ import annotations

import pytest
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

_PASSWORD = "qa49-demoted-admin-password"


@pytest.mark.parametrize(
    ("held", "kept", "lost_capability", "probe"),
    [
        (("expert", "admin"), ["expert"], "role:admin", ("GET", "/users")),
        (("expert", "admin"), ["admin"], "role:expert", ("POST", "/projects")),
    ],
    ids=["admin-removed", "expert-removed"],
)
def test_the_old_credential_is_refused_and_the_new_one_meets_the_loss(
    session_factory: sessionmaker[Session],
    session: Session,
    held: tuple[str, ...],
    kept: list[str],
    lost_capability: str,
    probe: tuple[str, str],
) -> None:
    surface = identity_surface(session_factory)
    login = fresh_login("demoted")
    target = make_account(
        session, login=login, names=("Понижённая", "Вера", None), roles=held, password=_PASSWORD
    )
    actor = make_account(
        session,
        login=fresh_login("demoter"),
        names=("Админская", "Зоя", None),
        roles=("expert", "admin"),
    )
    signed_in = exchange(surface, login, _PASSWORD)
    assert signed_in.status == 200, signed_in.body
    old = envelope(signed_in)["token"]
    assert send(surface, "GET", "/me", credential=old).status == 200

    changed = send(
        surface,
        "PATCH",
        f"/users/{target}",
        credential=credential_for(session, actor),
        body={"roles": kept},
    )
    assert changed.status == 200, changed.body
    assert envelope(changed)["roles"] == kept

    # The very next request with the credential minted before the change.
    refused = send(surface, "GET", "/me", credential=old, correlation="qa49-after-demotion")
    assert refused.status == 401, refused.body
    body = envelope(refused)
    assert body["error_code"] == "authentication_required", body
    assert not body.get("details"), body

    # Signing in again works, and only now is the loss met -- as a 403 naming the role.
    again = exchange(surface, login, _PASSWORD)
    assert again.status == 200, again.body
    fresh = envelope(again)["token"]
    assert send(surface, "GET", "/me", credential=fresh).status == 200
    method, path = probe
    lost = send(
        surface,
        method,
        path,
        credential=fresh,
        body={"name": "QA49"} if method == "POST" else None,
        headers={"Idempotency-Key": "qa49-probe-key"} if method == "POST" else None,
    )
    assert lost.status == 403, lost.body
    denial = envelope(lost)
    assert denial["error_code"] == "permission_denied", denial
    assert denial.get("details") == {"required_capability": lost_capability}, denial
