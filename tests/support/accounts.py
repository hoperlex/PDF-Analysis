"""A credential that names an account that exists, for the suites that drive a real API.

Why this module had to be written, in one sentence: **since `W39-REVOKE` a credential is
refused unless the account it names still exists and still accepts that credential's
generation**, so a suite that minted one for an identity it invented is presenting
something the seam is now correct to reject.

Seven suites did exactly that, each with its own copy of the same four lines::

    signer = build_signer({API_TOKEN_VARIABLE: DEPLOYMENT_SECRET})
    STATIC_TOKEN = signer.issue(Subject(user_uid="usr_01M25...", login="…")).token

That was true of the credential's *shape* and false about the deployment. The comment in
``tests/e2e/pc01/driver.py`` said so out loud -- *"it is a signed statement and not a row,
so it names a subject the deployment need not still have"* -- and treated it as a property
worth noting rather than a fiction, which it was right to do while nothing could revoke.

What this module does instead: write the row, read the epoch back out of it, and mint from
what the database says. The credential is then the same kind of thing the application's own
exchange produces, and a suite using it is driving the seam rather than stepping around it.

**It is idempotent and it is safe against a shared lane.** `OPERATING_CONSTRAINTS.md` §6 and
§9: the integration database is long-lived, shared and append-only by design, so a helper
that assumed an empty ``app_user`` would fail on its second run and on every parallel one.
``provisioned_credential`` creates the account when it is absent and re-reads it when it is
there, and it never changes a password or an epoch -- a suite that revoked something here
would sign out every other suite running against the same lane.

**`W49-SEAL-01`: every suite account is a complete ``expert`` account.** The authorization
seam now refuses an incomplete profile everything but its own profile and password, and
every product change needs the ``expert`` role (`R-59`, `R-60`). So the label a suite passes
is no longer the login itself: it is the local part of an e-mail login
(``<label>@suite.invalid``), the account is created with fixed names -- its display label is
therefore the name form :data:`SUITE_DISPLAY_LABEL` -- and it holds ``expert``. One helper
does it for every suite, so a later rule about accounts changes this file and not seven.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

__all__ = [
    "REPOSITORY_ROOT",
    "SUITE_DISPLAY_LABEL",
    "SUITE_NAMES",
    "complete_expert_account",
    "database_url",
    "provisioned_credential",
    "provisioned_record",
    "suite_login",
]

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

#: The password every suite account is created with. It is not a secret and it is not used
#: to sign in: these suites mint with the deployment key rather than through ``issueToken``,
#: so this value only has to satisfy the column's own constraints. It is a literal so that
#: reading this file tells you everything the row contains.
SUITE_PASSWORD = "w39-suite-account-password"

#: The names every suite account carries (`W49-SEAL-01`): a complete profile needs them, and
#: they are fixed rather than derived from the label so the label a decision records is one
#: known literal. The name form is what `R-55` shows a complete profile under.
SUITE_NAMES = ("Сьютова", "Ева")
SUITE_DISPLAY_LABEL = "Сьютова Е."

#: The domain of every suite login. ``.invalid`` is reserved (RFC 2606), so no suite login
#: can ever be somebody's address.
SUITE_DOMAIN = "suite.invalid"


def suite_login(label: str) -> str:
    """The e-mail login a suite label becomes: ``<label>@suite.invalid``."""
    return f"{label}@{SUITE_DOMAIN}"


def complete_expert_account(session: Any, label: str) -> Any:
    """The complete ``expert`` account for ``label`` in ``session``'s database, created if absent.

    Idempotent: an account this helper made before is returned as it is -- its epoch may
    have moved, and minting under what the row says now is the point. Created, it is three
    steps of the access boundary's own: the row, the profile completion (one UPDATE), the
    role grant. The caller commits.
    """
    from auditmanager.access.accounts import AccountRepository
    from auditmanager.access.repository import UserRepository

    users = UserRepository()
    login = suite_login(label)
    existing = users.find_by_login(session, login)
    if existing is not None:
        return existing
    created = users.create_user(session, login, SUITE_PASSWORD)
    accounts = AccountRepository()
    accounts.complete_profile(
        session,
        user_uid=str(created.user_uid),
        email=None,
        last_name=SUITE_NAMES[0],
        first_name=SUITE_NAMES[1],
    )
    accounts.grant_role(session, user_uid=str(created.user_uid), role="expert", granted_by=None)
    # Re-read: the grant raised the epoch, and a credential minted under the creation's
    # epoch would be refused by the very next request.
    return users.find_by_login(session, login)


def database_url() -> str:
    """``DATABASE_URL`` from the process, else from the lane's ``.env``.

    The same two places and the same order ``tests/integration/auth/conftest.py`` and
    ``tests/integration/api/conftest.py`` already read them in, so a suite using this helper
    works from a bare shell in a provisioned lane. Raises rather than returning a default: a
    helper that invented a connection string would point a suite at somebody else's lane.
    """
    configured = os.environ.get("DATABASE_URL")
    if configured:
        return configured
    dotenv = REPOSITORY_ROOT / ".env"
    if dotenv.is_file():
        for raw in dotenv.read_text(encoding="utf-8").splitlines():
            line = raw.strip().removeprefix("export ").strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            if name.strip() != "DATABASE_URL":
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            if value:
                os.environ["DATABASE_URL"] = value
                return value
    raise RuntimeError(
        "DATABASE_URL is not set and the lane's .env does not carry one. A credential now "
        "has to name an account that exists, so a suite driving the real API needs the "
        "database its application is wired to."
    )


def provisioned_record(login: str) -> Any:
    """The ``UserRecord`` for the suite label ``login``, creating the account if absent.

    ``login`` is the suite's label (``pc01-acceptance``, ``composition-suite``): the account
    signs in as ``<label>@suite.invalid`` and is complete and ``expert``
    (:func:`complete_expert_account`).

    Opens its own engine and disposes of it. That costs a connection per call and is worth
    it: the alternative is a module-level engine held for the whole session by a helper
    nobody owns, in a suite that may never call this.
    """
    from sqlalchemy.orm import Session

    from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
    from auditmanager.shared.db.engine import create_database_engine

    engine = create_database_engine(
        DatabaseSettings(url=parse_database_url(database_url()))
    )
    try:
        with Session(engine) as session:
            # Returned as-is when it exists. Its epoch may be above 1 because an earlier run
            # of this very suite, or a revocation test in another one, moved it -- and
            # minting under what the row says now is the whole point of reading it.
            record = complete_expert_account(session, login)
            session.commit()
            return record
    finally:
        engine.dispose()


def provisioned_credential(deployment_secret: str, login: str) -> str:
    """A credential this lane's API will accept, for an account this lane really has.

    ``deployment_secret`` is the suite's own -- each suite configures its application with a
    literal of its own choosing, and a helper that reached for one would make every suite
    share a key. The signing key is derived from it exactly as the application derives it.
    """
    from auditmanager.api.security import Subject, build_signer

    record = provisioned_record(login)
    signer = build_signer({"AUDITMANAGER_API_TOKEN": deployment_secret})
    assert signer is not None, "the suite's own secret derives a signing key"
    return signer.issue(
        Subject(
            user_uid=str(record.user_uid),
            login=record.login,
            # Read from the row, never assumed. A constant here would be a credential that
            # works until the first time anything in this lane revokes anything.
            token_epoch=record.token_epoch,
            # `R-37`, and the same rule one field along: the label is the record's own
            # answer -- the name form of a complete profile (`R-55`). A literal here would
            # make this helper mint credentials that disagree with the rows it just read,
            # which is the whole defect this module exists to have stopped.
            display_label=record.display_label,
        ),
        is_default_credential=False,
    ).token
