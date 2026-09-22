"""Report which accounts are still on the password this system seeded them with::

    PYTHONPATH=src .venv/bin/python -m auditmanager.access.check

Why this exists as a command rather than only as a column: the state it reports is
supposed to be temporary, and a temporary state nobody can see from outside becomes
permanent. An operator can answer "is the default ``admin`` password still live?"
without opening a SQL client, without logging in as that user, and without reading any
credential material -- the query projects the login and the timestamps and nothing else.

It is **not** wired into ``make check-db`` or any gate. That target belongs to
``P1-INT-00`` and this stream does not own the Makefile; a stream adding a private
target or editing a frozen one is working around the ownership rule rather than
extending it. Whoever owns the deployment checklist can add the invocation above.

Exit status: ``0`` when no account is on a default credential, ``1`` when at least one
is, and ``2`` when the database could not be read. The first two are both *successful
readings*; the distinction is there so a checklist can assert on it.
"""

from __future__ import annotations

import sys

from sqlalchemy.orm import Session

from auditmanager.access.repository import UserRepository
from auditmanager.shared.db.config import DatabaseSettings, load_settings
from auditmanager.shared.db.engine import create_database_engine

__all__ = ["main", "run_check"]

#: Printed when nothing is on a default credential. Stable text, so a checklist can grep.
CLEAN_SENTINEL = "access-check OK no default credentials"

#: Printed, once per account, when something is. Also stable.
FINDING_PREFIX = "access-check DEFAULT CREDENTIAL"


def run_check(settings: DatabaseSettings | None = None) -> int:
    resolved = settings if settings is not None else load_settings()
    engine = create_database_engine(resolved)
    try:
        with Session(engine) as session:
            users = UserRepository().users_on_default_credentials(session)
    finally:
        engine.dispose()

    if not users:
        print(CLEAN_SENTINEL, flush=True)
        return 0
    for user in users:
        print(
            f"{FINDING_PREFIX}: login={user.login} user_uid={user.user_uid} "
            f"created_at={user.created_at.isoformat()} "
            f"password_unchanged_since={user.password_updated_at.isoformat()}",
            flush=True,
        )
    print(
        f"access-check: {len(users)} account(s) still hold the seeded password. "
        "Anyone who has read the deployment notes can sign in as them.",
        flush=True,
    )
    return 1


def main() -> int:
    try:
        return run_check()
    except Exception as exc:  # noqa: BLE001 - a CLI boundary reports rather than raises
        print(f"access-check FAILED: {exc}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":  # pragma: no cover - exercised as a subprocess
    raise SystemExit(main())
