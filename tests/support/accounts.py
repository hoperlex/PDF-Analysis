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
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

__all__ = [
    "REPOSITORY_ROOT",
    "database_url",
    "provisioned_credential",
    "provisioned_record",
]

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

#: The password every suite account is created with. It is not a secret and it is not used
#: to sign in: these suites mint with the deployment key rather than through ``issueToken``,
#: so this value only has to satisfy the column's own constraints. It is a literal so that
#: reading this file tells you everything the row contains.
SUITE_PASSWORD = "w39-suite-account-password"


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
    """The ``UserRecord`` for ``login``, creating the account if this lane has none.

    Opens its own engine and disposes of it. That costs a connection per call and is worth
    it: the alternative is a module-level engine held for the whole session by a helper
    nobody owns, in a suite that may never call this.
    """
    from sqlalchemy.orm import Session

    from auditmanager.access.repository import UserRepository
    from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
    from auditmanager.shared.db.engine import create_database_engine

    engine = create_database_engine(
        DatabaseSettings(url=parse_database_url(database_url()))
    )
    try:
        users = UserRepository()
        with Session(engine) as session:
            existing = users.find_by_login(session, login)
            if existing is not None:
                # Deliberately returned as-is. Its epoch may be above 1 because an earlier
                # run of this very suite, or a revocation test in another one, moved it --
                # and minting under what the row says now is the whole point of reading it.
                return existing
            created = users.create_user(session, login, SUITE_PASSWORD)
            session.commit()
            return created
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
        )
    ).token
